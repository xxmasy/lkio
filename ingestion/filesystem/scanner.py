"""Filesystem Scanner for Read-Only Source Inspection
Handles:
1. File property extraction (size, mtime, extension).
2. Binary vs text file detection.
3. SHA-256 calculation with large-file protection (>10MB).
4. Strict sensitive file protection (.env, *.key, *.pem, credentials, secrets).
5. Safe directory hierarchy extraction strictly bounded by project root.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re

MAX_HASH_SIZE = 10 * 1024 * 1024  # 10 MB

SENSITIVE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^.*\.pem$", re.IGNORECASE),
    re.compile(r"^.*\.key$", re.IGNORECASE),
    re.compile(r"^.*\.crt$", re.IGNORECASE),
    re.compile(r"^.*\.p12$", re.IGNORECASE),
    re.compile(r"^.*\.pfx$", re.IGNORECASE),
    re.compile(r"^id_rsa.*$", re.IGNORECASE),
    re.compile(r"^id_ed25519.*$", re.IGNORECASE),
    re.compile(r"^credentials\.json$", re.IGNORECASE),
    re.compile(r"^service-account.*\.json$", re.IGNORECASE),
    re.compile(r"^secrets?(\..+)?$", re.IGNORECASE),
]

DEFAULT_EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    ".vscode",
    ".idea",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    ".venv",
    "__pycache__",
    ".cache",
    "tmp",
    "temp",
    "logs",
}


@dataclass
class ScannedFileInfo:
    relative_path: str
    absolute_path: str
    filename: str
    extension: str
    size_bytes: int
    mtime: datetime
    sha256: str | None
    hash_status: str  # computed, skipped_large_file, unreadable
    is_binary: bool
    is_sensitive: bool


def is_sensitive_filename(filename: str) -> bool:
    """Checks whether a filename matches sensitive credential or secret patterns."""
    for pattern in SENSITIVE_PATTERNS:
        if pattern.match(filename):
            return True
    return False


def is_binary_file(file_path: Path) -> bool:
    """Detects whether a file is binary by checking for NUL bytes in the first 8KB."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except Exception:
        return False


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash in 64KB chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def scan_single_file(project_root: Path, relative_path: str) -> ScannedFileInfo | None:
    """Scans metadata of a single file in a project.

    Returns None if the file is sensitive or does not exist.
    """
    normalized_rel = relative_path.replace("\\", "/").strip("/")
    abs_path = project_root / normalized_rel

    if not abs_path.is_file():
        return None

    filename = abs_path.name

    # 1. Sensitive file check
    if is_sensitive_filename(filename):
        return ScannedFileInfo(
            relative_path=normalized_rel,
            absolute_path=str(abs_path),
            filename=filename,
            extension=abs_path.suffix.lower(),
            size_bytes=0,
            mtime=datetime.now(timezone.utc),
            sha256=None,
            hash_status="sensitive_excluded",
            is_binary=False,
            is_sensitive=True,
        )

    # 2. File stats
    try:
        st = abs_path.stat()
        size_bytes = st.st_size
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
    except Exception:
        return None

    # 3. Binary detection
    is_binary = is_binary_file(abs_path)

    # 4. Hash calculation
    if size_bytes > MAX_HASH_SIZE:
        sha256 = None
        hash_status = "skipped_large_file"
    else:
        try:
            sha256 = compute_sha256(abs_path)
            hash_status = "computed"
        except Exception:
            sha256 = None
            hash_status = "unreadable"

    return ScannedFileInfo(
        relative_path=normalized_rel,
        absolute_path=str(abs_path),
        filename=filename,
        extension=abs_path.suffix.lower(),
        size_bytes=size_bytes,
        mtime=mtime,
        sha256=sha256,
        hash_status=hash_status,
        is_binary=is_binary,
        is_sensitive=False,
    )


def extract_directory_hierarchy(relative_file_paths: list[str]) -> list[str]:
    """Derives sorted project-bounded relative directory paths from file paths.
    E.g. ['src/components/List.vue'] -> ['src', 'src/components']
    """
    directories: set[str] = set()

    for fp in relative_file_paths:
        parts = fp.replace("\\", "/").strip("/").split("/")
        # If there are directories before the filename
        if len(parts) > 1:
            dir_parts = parts[:-1]
            current = ""
            for p in dir_parts:
                current = f"{current}/{p}" if current else p
                directories.add(current)

    return sorted(directories)


def fallback_filesystem_scan(project_root: Path) -> list[str]:
    """Walks directory tree when git ls-files is unavailable, honoring default exclusions."""
    files: list[str] = []

    for root, dirs, filenames in os.walk(project_root):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDED_DIRS]

        rel_dir = os.path.relpath(root, project_root)
        for fname in filenames:
            if is_sensitive_filename(fname):
                continue
            if rel_dir == ".":
                files.append(fname)
            else:
                files.append(os.path.join(rel_dir, fname).replace("\\", "/"))

    return sorted(files)
