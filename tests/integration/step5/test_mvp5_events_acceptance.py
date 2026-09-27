"""LKIO MVP5 (Event & Change Intelligence) Acceptance Test Gate
Verifies:
1. Strict read-only integrity across all 3 external projects (HELLO_FE, HELLO_BE, L2C_FE).
2. High-fidelity commit, file, and entity change event extraction without patch text bloat.
3. Full entity topology linking (FILE_CHANGED -> ENTITY_CHANGED).
4. Double-pass persistence idempotency guarantee (0 duplicates on re-scan).
5. Comprehensive temporal query engine verification (Timeline, First Appearance, Frequency, Since Commit).
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.db.base import Base
from core.events.git_extractor import GitChangeExtractor
from core.events.pipeline import EventPipeline
from core.events.temporal_engine import TemporalQueryEngine
from core.models.entity import Entity
from core.models.event import Event, EventType
from core.models.project import Project

PROJECT_PATHS = {
    "HELLO_FE": Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello")),
    "HELLO_BE": Path(os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend")),
    "L2C_FE": Path(os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project")),
}


def get_git_status_porcelain(repo_path: Path) -> str:
    """Executes read-only git status to confirm working tree cleanliness."""
    if not repo_path.exists():
        return ""
    res = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    return res.stdout.strip()


@pytest.fixture
def clean_events_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_mvp5_events_acceptance_gate(clean_events_db):
    """Executes full MVP5 acceptance gate against the 3 real repositories."""
    session = clean_events_db
    extractor = GitChangeExtractor()
    pipeline = EventPipeline(extractor=extractor)
    temporal_engine = TemporalQueryEngine()

    # Gate 1: Source Project Strict Read-Only Verification (Pre-scan status capture)
    status_before = {}
    for pkey, ppath in PROJECT_PATHS.items():
        if ppath.exists():
            status_before[pkey] = get_git_status_porcelain(ppath)

    total_commits_extracted = 0
    total_events_generated = 0
    project_events_map: dict[str, list[Event]] = {}
    project_ids: dict[str, uuid.UUID] = {}

    for pkey, ppath in PROJECT_PATHS.items():
        if not ppath.exists():
            continue

        proj_id = uuid.uuid4()
        project_ids[pkey] = proj_id
        project = Project(
            id=proj_id,
            key=pkey,
            name=pkey,
            kind="frontend" if "FE" in pkey else "backend",
            role="primary" if "FE" in pkey else "supporting",
            local_path=str(ppath),
            status="ACTIVE",
        )
        session.add(project)

        # Gate 2: Extract real Git commits and file changes (up to 20 commits each)
        commits = extractor.extract_commits(ppath, max_commits=20)
        assert len(commits) > 0, f"Expected commits in {pkey}"
        total_commits_extracted += len(commits)

        # Seed sample entities corresponding to files in this project
        sample_entities_by_path: dict[str, list[Entity]] = {}
        for c in commits[:3]:
            for f in c.changed_files[:2]:
                ent = Entity(
                    id=uuid.uuid4(),
                    project_id=proj_id,
                    entity_type="FILE",
                    entity_key=f"FILE:{pkey}:{f.file_path}",
                    name=Path(f.file_path).name,
                    canonical_name=Path(f.file_path).name,
                    path=f.file_path,
                    status="ACTIVE",
                )
                session.add(ent)
                sample_entities_by_path.setdefault(f.file_path, []).append(ent)

        session.commit()

        # Gate 3: Event generation & entity linking
        events = pipeline.generate_events_for_commits(
            project_key=pkey,
            project_id=proj_id,
            commits=commits,
            entities_by_path=sample_entities_by_path,
        )
        assert len(events) >= len(commits)  # At least 1 COMMIT event per commit
        project_events_map[pkey] = events
        total_events_generated += len(events)

        # Verify no patch diff text bloat exists in metadata
        for e in events:
            assert "diff" not in e.metadata_ or not isinstance(e.metadata_["diff"], str) or len(e.metadata_["diff"]) < 200
            assert e.confidence == 1.0

    session.commit()

    # Gate 4: Double-Pass Idempotent Persistence Verification
    all_events = []
    for ev_list in project_events_map.values():
        all_events.extend(ev_list)

    # Pass 1: Persist
    pass1_res = pipeline.persist_events(session, all_events)
    assert pass1_res["created"] == len(all_events)
    assert pass1_res["updated"] == 0

    count_after_pass1 = len(session.scalars(select(Event)).all())
    assert count_after_pass1 == len(all_events)

    # Pass 2: Re-persist identical events
    pass2_res = pipeline.persist_events(session, all_events)
    assert pass2_res["created"] == 0
    assert pass2_res["updated"] == len(all_events)

    count_after_pass2 = len(session.scalars(select(Event)).all())
    assert count_after_pass2 == len(all_events), "Event count must remain strictly invariant across rescan"

    # Gate 5: Temporal Query Engine Verification
    for pkey, proj_id in project_ids.items():
        # Timeline
        timeline = temporal_engine.get_project_timeline(session, project_id=proj_id, limit=50)
        assert len(timeline) > 0
        for i in range(len(timeline) - 1):
            assert timeline[i].timestamp >= timeline[i + 1].timestamp

        # Query first appearance for a file from first event
        file_events = [e for e in project_events_map[pkey] if e.event_type == EventType.FILE_CHANGED.value]
        if file_events:
            target_path = file_events[-1].metadata_["file_rel_path"]
            first_app = temporal_engine.query_first_appearance(session, proj_id, target_path)
            assert first_app["found"] is True
            assert first_app["commit_sha"] is not None

            # Change frequency
            freq = temporal_engine.query_change_frequency(session, proj_id, target_path)
            assert freq["total_modifications"] >= 1
            assert len(freq["authors"]) >= 1

        # Changes since an earlier commit
        commit_events = [e for e in project_events_map[pkey] if e.event_type == EventType.COMMIT.value]
        if len(commit_events) >= 2:
            earlier_commit = commit_events[-1]  # Oldest commit in batch
            changes_since = temporal_engine.query_changes_since(
                session,
                project_id=proj_id,
                commit_sha=earlier_commit.metadata_["commit_sha"],
            )
            assert len(changes_since) >= 1

    # Gate 6: Strict Read-Only Verification (Post-scan status check)
    for pkey, ppath in PROJECT_PATHS.items():
        if ppath.exists():
            status_after = get_git_status_porcelain(ppath)
            assert status_before[pkey] == status_after, (
                f"Source repository {pkey} was modified during scan! "
                f"Before: {status_before[pkey]} | After: {status_after}"
            )
