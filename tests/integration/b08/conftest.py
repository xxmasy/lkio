"""Shared fixtures and utilities for B-08 System-Level Real Projects Verification.
Provides safe directory traversal, in-memory DB isolation, and temporary verification workspaces.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Generator
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from core.db.base import Base
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from core.models.source import Source

REPOS = {
    "HELLO_FE": Path("C:/WorkSpace/hello"),
    "HELLO_BE": Path("C:/WorkSpace/hello-backend"),
    "L2C_FE": Path("C:/WorkSpace/L2C project"),
}

SUPPORTED_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".java", ".vue"}
PRUNED_DIRS = {".git", "node_modules", "target", "dist", ".idea", ".vscode", ".cursor", "build", "out", ".output"}


def discover_supported_files(repo_path: Path) -> list[Path]:
    """Safely traverses a repository, pruning artifact directories in-flight, returning supported source files."""
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in PRUNED_DIRS and not d.startswith(".")]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTS:
                results.append(Path(dirpath) / f)
    # Sort deterministically
    return sorted(results, key=lambda p: str(p).replace("\\", "/"))


def capture_git_porcelain() -> dict[str, str]:
    """Captures exact porcelain output for each external repository."""
    snapshots = {}
    for name, root in REPOS.items():
        if root.exists():
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            snapshots[name] = res.stdout.strip()
    return snapshots


@pytest.fixture
def b08_db() -> Generator[Session, None, None]:
    """Fresh in-memory SQLite session with JSONB/UUID compilation support."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def b08_projects(b08_db: Session) -> dict[str, Project]:
    """Initializes the 3 real project records in the verification DB."""
    projects = {}
    for key, path in REPOS.items():
        role = "backend" if "BE" in key else "frontend"
        proj = Project(
            id=uuid.uuid4(),
            key=key,
            name=f"LKIO Verified Project {key}",
            kind="real_workspace",
            role=role,
            local_path=str(path),
            status="ACTIVE",
        )
        b08_db.add(proj)
        projects[key] = proj
    b08_db.commit()
    return projects


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Provides an isolated temporary workspace directory for safe file mutation drills (LOCK-VERIFY-02)."""
    with tempfile.TemporaryDirectory(prefix="lkio_b08_verify_") as tmp_dir:
        yield Path(tmp_dir)
