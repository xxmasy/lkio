"""LKIO MVP1 - Read-Only Integrity & Pipeline Resiliency Tests
Validates:
1. Strict read-only guarantee across source repositories (git status unchanged before/after scan).
2. Soft deletion of vanished files.
3. Partial failure isolation.
"""

import subprocess
import sys
from pathlib import Path
import pytest
from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.db.session import SessionLocal
from core.models.entity import Entity
from core.models.project import Project
from ingestion.pipeline import run_all_projects_ingestion, run_project_ingestion


def get_git_status_porcelain(repo_path: str) -> str:
    """Invokes Git CLI to get exact working tree porcelain output."""
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def test_source_projects_strict_readonly():
    """Verify that scanning all projects causes 0 changes to source repositories."""
    with SessionLocal() as db:
        projects = db.scalars(select(Project).where(Project.status == "ACTIVE")).all()

    # 1. Capture status before scan
    status_before = {}
    for p in projects:
        if Path(p.local_path).exists():
            status_before[p.key] = get_git_status_porcelain(p.local_path)

    # 2. Run ingestion on all projects
    summary = run_all_projects_ingestion()
    assert summary["status"] in ["COMPLETED", "PARTIAL"]
    assert summary["succeeded"] >= 3

    # 3. Capture status after scan
    for p in projects:
        if Path(p.local_path).exists():
            status_after = get_git_status_porcelain(p.local_path)
            assert status_after == status_before[p.key], (
                f"Source project '{p.key}' was modified during scan! "
                f"Before:\n{status_before[p.key]}\nAfter:\n{status_after}"
            )


def test_soft_deletion_of_vanished_files():
    """Verify that a vanished file in the database is soft-deleted (status='deleted') on next scan."""
    with SessionLocal() as db:
        p = db.scalars(select(Project).where(Project.key == "HELLO_FE")).first()
        assert p is not None

        # Insert a synthetic active file entity that doesn't actually exist on disk
        ghost_key = f"FILE:{p.key}:nonexistent_ghost_file.ts"
        ghost = db.scalars(select(Entity).where(Entity.entity_key == ghost_key)).first()
        if not ghost:
            ghost = Entity(
                project_id=p.id,
                entity_type="FILE",
                entity_key=ghost_key,
                name="nonexistent_ghost_file.ts",
                canonical_name=f"{p.key}_FILE_ghost",
                path="nonexistent_ghost_file.ts",
                status="ACTIVE",
                metadata_={},
            )
            db.add(ghost)
            db.commit()

        # Run ingestion
        run = run_project_ingestion(p.key, db=db)
        assert run.status == "COMPLETED"

        # Check that the ghost entity is now marked 'deleted'
        db.refresh(ghost)
        assert ghost.status == "deleted"


def test_partial_failure_isolation():
    """Verify that an invalid/failing project does not roll back or corrupt valid projects."""
    with SessionLocal() as db:
        # Create a temporary broken project with nonexistent path
        fake_proj = db.scalars(select(Project).where(Project.key == "TEST_BROKEN_PROJ")).first()
        if not fake_proj:
            fake_proj = Project(
                key="TEST_BROKEN_PROJ",
                name="Broken Project",
                kind="test",
                role="test_role",
                local_path="C:\\NonExistent\\Path\\To\\Nowhere_12345",
                status="ACTIVE",
            )
            db.add(fake_proj)
            db.commit()

        # Run all projects ingestion
        summary = run_all_projects_ingestion()
        assert summary["status"] == "PARTIAL"
        assert summary["runs"]["TEST_BROKEN_PROJ"]["status"] == "FAILED"
        assert summary["runs"]["HELLO_FE"]["status"] == "COMPLETED"
        assert summary["runs"]["HELLO_BE"]["status"] == "COMPLETED"

        # Clean up fake project
        db.delete(fake_proj)
        db.commit()
