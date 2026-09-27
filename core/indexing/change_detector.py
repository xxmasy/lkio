"""Change Detection Engine (Stage 1 Section 3.3).

Identifies file-level and content-level diffs from Git commits, working trees, or memory snapshots:
- ADDED, MODIFIED, DELETED, RENAMED, UNCHANGED
- Old/new blob extraction
- Format/comment-only change detection
"""

import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class ChangeClassification(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    UNCHANGED = "UNCHANGED"


@dataclass
class FileDiff:
    file_path: str
    change_type: ChangeClassification
    old_path: Optional[str] = None
    old_blob: Optional[str] = None
    new_blob: Optional[str] = None
    is_format_or_comment_only: bool = False


class ChangeDetector:
    """Engine responsible for extracting file-level mutations and blob states."""

    @staticmethod
    def _strip_comments_and_whitespace(code: str) -> str:
        # Strip C-style / Java / TS comments
        no_line_comments = re.sub(r"//.*", "", code)
        no_block_comments = re.sub(r"/\*[\s\S]*?\*/", "", no_line_comments)
        # Collapse all whitespaces
        return re.sub(r"\s+", "", no_block_comments)

    @classmethod
    def detect_from_memory(
        cls,
        old_blobs: Dict[str, str],
        new_blobs: Dict[str, str],
    ) -> List[FileDiff]:
        """Calculates FileDiffs between two in-memory file sets (for testing & benchmark suites)."""
        diffs = []
        old_keys = set(old_blobs.keys())
        new_keys = set(new_blobs.keys())

        # Added files
        for path in new_keys - old_keys:
            diffs.append(
                FileDiff(
                    file_path=path,
                    change_type=ChangeClassification.ADDED,
                    new_blob=new_blobs[path],
                )
            )

        # Deleted files
        for path in old_keys - new_keys:
            diffs.append(
                FileDiff(
                    file_path=path,
                    change_type=ChangeClassification.DELETED,
                    old_blob=old_blobs[path],
                )
            )

        # Common files
        for path in old_keys & new_keys:
            old_code = old_blobs[path]
            new_code = new_blobs[path]
            if old_code == new_code:
                continue

            # Check if format or comment only
            stripped_old = cls._strip_comments_and_whitespace(old_code)
            stripped_new = cls._strip_comments_and_whitespace(new_code)
            format_only = stripped_old == stripped_new

            diffs.append(
                FileDiff(
                    file_path=path,
                    change_type=ChangeClassification.MODIFIED,
                    old_blob=old_code,
                    new_blob=new_code,
                    is_format_or_comment_only=format_only,
                )
            )

        return diffs

    @classmethod
    def detect_from_git(
        cls,
        repo_dir: str,
        commit_range: Optional[str] = None,
    ) -> List[FileDiff]:
        """Detects changed files and extracts blobs via Git CLI."""
        target_path = Path(repo_dir)
        if not target_path.exists():
            raise FileNotFoundError(f"Repo path '{repo_dir}' not found.")

        # If commit range not specified, check working tree against HEAD
        range_arg = commit_range if commit_range else "HEAD"
        cmd = ["git", "-C", str(target_path), "diff", "--name-status", range_arg]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except Exception:
            # Fallback for empty/initial repos
            return []

        diffs = []
        for line in res.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            status_code = parts[0][0]
            if status_code == "A":
                path = parts[1]
                diffs.append(FileDiff(file_path=path, change_type=ChangeClassification.ADDED))
            elif status_code == "D":
                path = parts[1]
                diffs.append(FileDiff(file_path=path, change_type=ChangeClassification.DELETED))
            elif status_code == "M":
                path = parts[1]
                diffs.append(FileDiff(file_path=path, change_type=ChangeClassification.MODIFIED))
            elif status_code.startswith("R"):
                old_p = parts[1]
                new_p = parts[2]
                diffs.append(FileDiff(file_path=new_p, old_path=old_p, change_type=ChangeClassification.RENAMED))

        return diffs
