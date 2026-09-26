"""Unit tests for TemporalQueryEngine in core/events/temporal_engine.py
"""

from datetime import datetime, timezone, timedelta
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db.base import Base
from core.events.temporal_engine import TemporalQueryEngine
from core.models.event import ActorType, Event, EventType, SourceType


@pytest.fixture
def sqlite_events_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    proj_id = uuid.uuid4()
    base_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Event 1: Introduction of LeadService on Sep 1
    e1 = Event(
        event_key="EVENT:HELLO_BE:COMMIT:sha_001",
        event_type=EventType.COMMIT.value,
        project_id=proj_id,
        actor_type=ActorType.GIT.value,
        actor_id="alice@dev.com",
        timestamp=base_time,
        reason="feat: introduce LeadService",
        metadata_={
            "commit_sha": "sha_001",
            "message": "feat: introduce LeadService",
        },
    )
    e1_file = Event(
        event_key="EVENT:HELLO_BE:FILE:sha_001:src/services/LeadService.java",
        event_type=EventType.FILE_CHANGED.value,
        project_id=proj_id,
        actor_type=ActorType.GIT.value,
        actor_id="alice@dev.com",
        timestamp=base_time,
        reason="ADDED: src/services/LeadService.java",
        metadata_={
            "commit_sha": "sha_001",
            "file_rel_path": "src/services/LeadService.java",
            "change_type": "ADDED",
            "insertions": 150,
            "deletions": 0,
        },
    )

    # Event 2: Modification of LeadService on Sep 10
    time_2 = base_time + timedelta(days=9)
    e2 = Event(
        event_key="EVENT:HELLO_BE:COMMIT:sha_002",
        event_type=EventType.COMMIT.value,
        project_id=proj_id,
        actor_type=ActorType.GIT.value,
        actor_id="bob@dev.com",
        timestamp=time_2,
        reason="fix: update lead conversion rate",
        metadata_={
            "commit_sha": "sha_002",
            "message": "fix: update lead conversion rate",
        },
    )
    e2_file = Event(
        event_key="EVENT:HELLO_BE:FILE:sha_002:src/services/LeadService.java",
        event_type=EventType.FILE_CHANGED.value,
        project_id=proj_id,
        actor_type=ActorType.GIT.value,
        actor_id="bob@dev.com",
        timestamp=time_2,
        reason="MODIFIED: src/services/LeadService.java",
        metadata_={
            "commit_sha": "sha_002",
            "file_rel_path": "src/services/LeadService.java",
            "change_type": "MODIFIED",
            "insertions": 20,
            "deletions": 5,
        },
    )

    # Event 3: Third change by Charlie on Sep 20
    time_3 = base_time + timedelta(days=19)
    e3_file = Event(
        event_key="EVENT:HELLO_BE:FILE:sha_003:src/services/LeadService.java",
        event_type=EventType.FILE_CHANGED.value,
        project_id=proj_id,
        actor_type=ActorType.GIT.value,
        actor_id="charlie@dev.com",
        timestamp=time_3,
        reason="refactor: clean up methods",
        metadata_={
            "commit_sha": "sha_003",
            "file_rel_path": "src/services/LeadService.java",
            "change_type": "MODIFIED",
            "insertions": 10,
            "deletions": 12,
        },
    )

    session.add_all([e1, e1_file, e2, e2_file, e3_file])
    session.commit()

    yield session, proj_id
    session.close()


def test_first_appearance_query(sqlite_events_db):
    session, proj_id = sqlite_events_db
    engine = TemporalQueryEngine()

    result = engine.query_first_appearance(session, proj_id, "LeadService.java")
    assert result["found"] is True
    assert result["author"] == "alice@dev.com"
    assert result["commit_sha"] == "sha_001"
    assert result["change_type"] == "ADDED"


def test_change_frequency_query(sqlite_events_db):
    session, proj_id = sqlite_events_db
    engine = TemporalQueryEngine()

    freq = engine.query_change_frequency(session, proj_id, "LeadService.java")
    assert freq["total_modifications"] == 3
    assert freq["unique_authors_count"] == 3
    assert "alice@dev.com" in freq["authors"]
    assert "bob@dev.com" in freq["authors"]
    assert "charlie@dev.com" in freq["authors"]
    assert freq["total_insertions"] == 180
    assert freq["total_deletions"] == 17


def test_changes_since_commit(sqlite_events_db):
    session, proj_id = sqlite_events_db
    engine = TemporalQueryEngine()

    changes = engine.query_changes_since(session, proj_id, commit_sha="sha_001")
    # All events after sha_001 (e2, e2_file, e3_file)
    assert len(changes) == 3
    shas = {c.metadata_.get("commit_sha") for c in changes}
    assert "sha_002" in shas
    assert "sha_003" in shas
    assert "sha_001" not in shas


def test_project_timeline_ordering(sqlite_events_db):
    session, proj_id = sqlite_events_db
    engine = TemporalQueryEngine()

    timeline = engine.get_project_timeline(session, project_id=proj_id)
    assert len(timeline) == 5
    # Must be reverse chronological
    for i in range(len(timeline) - 1):
        assert timeline[i].timestamp >= timeline[i + 1].timestamp
