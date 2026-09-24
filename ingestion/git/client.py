"""Git CLI Wrapper for Read-Only Repository Inspection
Strictly adheres to:
1. Subprocess-only Git CLI calls.
2. Read-only commands only (no write/pull/checkout).
3. No parsing of internal .git binary structures.
4. Remote credential redaction.
"""

from datetime import datetime
from pathlib import Path
import re
import subprocess
from typing import Any


class GitClientError(Exception):
    pass


class GitClient:
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def _run_git(self, repo_path: Path, args: list[str]) -> str:
        cmd = ["git", "-C", str(repo_path)] + args
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
                raise GitClientError(f"Git command failed: {' '.join(cmd)}\nStderr: {res.stderr.strip()}")
            return res.stdout
        except subprocess.TimeoutExpired as e:
            raise GitClientError(f"Git command timed out after {self.timeout_seconds}s: {' '.join(cmd)}") from e
        except FileNotFoundError as e:
            raise GitClientError("Git executable not found in system PATH") from e

    def is_inside_worktree(self, repo_path: Path) -> bool:
        try:
            output = self._run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
            return output.strip().lower() == "true"
        except GitClientError:
            return False

    def get_toplevel(self, repo_path: Path) -> str:
        output = self._run_git(repo_path, ["rev-parse", "--show-toplevel"])
        return str(Path(output.strip()))

    def get_branch(self, repo_path: Path) -> str | None:
        try:
            output = self._run_git(repo_path, ["branch", "--show-current"])
            branch = output.strip()
            return branch if branch else None
        except GitClientError:
            return None

    def get_head(self, repo_path: Path) -> str:
        output = self._run_git(repo_path, ["rev-parse", "HEAD"])
        return output.strip()

    def get_remotes(self, repo_path: Path) -> list[dict[str, str]]:
        try:
            output = self._run_git(repo_path, ["remote", "-v"])
        except GitClientError:
            return []

        remotes = []
        seen = set()
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                url = parts[1]
                # Redact credentials if embedded in URL: https://user:pass@host -> https://user:***@host
                redacted_url = re.sub(r"://([^:@]+):[^@]+@", r"://\1:***@", url)
                key = (name, redacted_url)
                if key not in seen:
                    seen.add(key)
                    remotes.append({
                        "name": name,
                        "url": redacted_url,
                    })
        return remotes

    def get_commits(self, repo_path: Path, max_count: int = 100) -> list[dict[str, Any]]:
        # Using %x1f (Unit Separator) and %x1e (Record Separator) to prevent delimiter collision
        log_format = "%H%x1f%P%x1f%an%x1f%ae%x1f%ad%x1f%s%x1e"
        try:
            output = self._run_git(
                repo_path,
                [
                    "log",
                    f"-n{max_count}",
                    "--date=iso-strict",
                    f"--pretty=format:{log_format}",
                ],
            )
        except GitClientError:
            return []

        commits = []
        records = output.split("\x1e")
        for rec in records:
            rec = rec.strip()
            if not rec:
                continue
            fields = rec.split("\x1f")
            if len(fields) >= 6:
                sha = fields[0]
                parents = fields[1].split() if fields[1] else []
                author_name = fields[2]
                author_email = fields[3]
                authored_at_str = fields[4]
                subject = fields[5]

                commits.append({
                    "sha": sha,
                    "parent_sha": parents[0] if parents else None,
                    "author_name": author_name,
                    "author_email": author_email,
                    "authored_at": authored_at_str,
                    "subject": subject,
                })
        return commits

    def ls_files(self, repo_path: Path) -> list[str]:
        """Lists repository files using git ls-files -co --exclude-standard -z
        Returns list of normalized relative paths.
        """
        output = self._run_git(repo_path, ["ls-files", "-co", "--exclude-standard", "-z"])
        raw_files = output.split("\0")
        files = []
        for f in raw_files:
            f = f.strip()
            if f:
                # Normalize slashes to '/'
                normalized = f.replace("\\", "/")
                files.append(normalized)
        return files
