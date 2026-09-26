"""Git Change Extractor for MVP5 Event & Change Intelligence
Reads commit logs and per-file change statistics via read-only Git CLI subprocess.
Strictly adheres to:
1. Subprocess Git CLI only (no .git internal binary parsing).
2. Read-only operation (-c core.quotepath=false).
3. 0 diff patch text bloat (numstat and status summary only).
"""

from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
from typing import Any

from core.events.models import ChangeType, CommitEventDTO, FileChangeDTO


class GitChangeExtractorError(Exception):
    pass


class GitChangeExtractor:
    """Extracts high-fidelity commit events and file change metadata."""

    def __init__(self, timeout_seconds: int = 45):
        self.timeout_seconds = timeout_seconds

    def _run_git(self, repo_path: Path, args: list[str]) -> str:
        cmd = ["git", "-c", "core.quotepath=false", "-C", str(repo_path)] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
            if res.returncode != 0:
                raise GitChangeExtractorError(
                    f"Git command failed: {' '.join(cmd)}\nStderr: {res.stderr.strip()}"
                )
            return res.stdout
        except subprocess.TimeoutExpired as e:
            raise GitChangeExtractorError(
                f"Git command timed out after {self.timeout_seconds}s: {' '.join(cmd)}"
            ) from e
        except FileNotFoundError as e:
            raise GitChangeExtractorError("Git executable not found in system PATH") from e

    def extract_commits(
        self,
        repo_path: Path,
        max_commits: int = 100,
        since_sha: str | None = None,
    ) -> list[CommitEventDTO]:
        """Extracts chronological commits and file change metadata from repository."""
        if not repo_path.exists():
            raise GitChangeExtractorError(f"Repository path does not exist: {repo_path}")

        # 1. Fetch commit headers and file change status
        base_args = ["log", f"-n{max_commits}", "--date=iso-strict"]
        if since_sha:
            base_args.append(f"{since_sha}..HEAD")

        status_format = "COMMIT_RECORD%x1f%H%x1f%P%x1f%an%x1f%ae%x1f%ad%x1f%s"
        status_output = self._run_git(
            repo_path,
            base_args + [f"--pretty=format:{status_format}", "--name-status"],
        )

        # 2. Fetch numstat for insertion/deletion counts
        numstat_format = "COMMIT_RECORD%x1f%H"
        numstat_output = self._run_git(
            repo_path,
            base_args + [f"--pretty=format:{numstat_format}", "--numstat"],
        )

        numstat_map = self._parse_numstat_output(numstat_output)
        commits = self._parse_status_output(status_output, numstat_map)
        return commits

    def _parse_numstat_output(self, output: str) -> dict[str, dict[str, tuple[int, int]]]:
        """Maps commit_sha -> file_path -> (insertions, deletions)"""
        result: dict[str, dict[str, tuple[int, int]]] = {}
        current_sha: str | None = None

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("COMMIT_RECORD\x1f"):
                parts = line.split("\x1f")
                if len(parts) >= 2:
                    current_sha = parts[1].strip()
                    result[current_sha] = {}
                continue

            if current_sha is None:
                continue

            # Parse numstat: <insertions>\t<deletions>\t<path>
            tokens = line.split("\t")
            if len(tokens) >= 3:
                ins_str, del_str, path = tokens[0], tokens[1], tokens[2]
                ins = int(ins_str) if ins_str.isdigit() else 0
                deletions = int(del_str) if del_str.isdigit() else 0
                normalized_path = path.replace("\\", "/").strip('"')
                result[current_sha][normalized_path] = (ins, deletions)

        return result

    def _parse_status_output(
        self,
        output: str,
        numstat_map: dict[str, dict[str, tuple[int, int]]],
    ) -> list[CommitEventDTO]:
        """Parses commit header records and name-status lines into CommitEventDTOs."""
        commits: list[CommitEventDTO] = []
        current_commit: CommitEventDTO | None = None

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("COMMIT_RECORD\x1f"):
                if current_commit:
                    commits.append(current_commit)

                parts = line.split("\x1f")
                if len(parts) >= 7:
                    sha = parts[1].strip()
                    parents = parts[2].strip().split() if parts[2].strip() else []
                    author_name = parts[3].strip()
                    author_email = parts[4].strip()
                    authored_at_str = parts[5].strip()
                    subject = parts[6].strip()

                    try:
                        dt = datetime.fromisoformat(authored_at_str)
                    except ValueError:
                        dt = datetime.now(timezone.utc)

                    current_commit = CommitEventDTO(
                        sha=sha,
                        parent_sha=parents[0] if parents else None,
                        author_name=author_name,
                        author_email=author_email,
                        authored_at=dt,
                        message=subject,
                        changed_files=[],
                        total_insertions=0,
                        total_deletions=0,
                    )
                continue

            if current_commit is None:
                continue

            # Parse status line: e.g. M\tsrc/App.vue or R100\told/path\tnew/path
            tokens = line.split("\t")
            if len(tokens) >= 2:
                status_code = tokens[0].strip()
                old_path: str | None = None

                if status_code.startswith("R") and len(tokens) >= 3:
                    change_type = ChangeType.RENAMED
                    old_path = tokens[1].replace("\\", "/").strip('"')
                    file_path = tokens[2].replace("\\", "/").strip('"')
                elif status_code.startswith("A"):
                    change_type = ChangeType.ADDED
                    file_path = tokens[1].replace("\\", "/").strip('"')
                elif status_code.startswith("D"):
                    change_type = ChangeType.DELETED
                    file_path = tokens[1].replace("\\", "/").strip('"')
                elif status_code.startswith("M"):
                    change_type = ChangeType.MODIFIED
                    file_path = tokens[1].replace("\\", "/").strip('"')
                else:
                    change_type = ChangeType.UNKNOWN
                    file_path = tokens[1].replace("\\", "/").strip('"')

                # Fetch insertions & deletions from numstat_map
                sha_stats = numstat_map.get(current_commit.sha, {})
                stats = sha_stats.get(file_path, (0, 0))
                ins, dels = stats

                file_change = FileChangeDTO(
                    file_path=file_path,
                    change_type=change_type,
                    insertions=ins,
                    deletions=dels,
                    old_path=old_path,
                )
                current_commit.changed_files.append(file_change)
                current_commit.total_insertions += ins
                current_commit.total_deletions += dels

        if current_commit:
            commits.append(current_commit)

        return commits
