"""Unit tests for EventPipeline and double-pass persistence in core/events/pipeline.py
"""

from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.db.base import Base
from core.events.models import ChangeType, CommitEventDTO, FileChangeDTO
from core.events.pipeline import EventPipeline
from core.models.entity import Entity
from core.models.event import Event, EventType
from core.models.project import Project


@pytest.fixture
def sqlite_db_session():
    """In-memory SQLite session configured for LKIO models."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_generate_events_and_entity_linking():
    pipeline = EventPipeline()
    now = datetime.now(timezone.utc)
    proj_id = uuid.uuid4()

    mock_commits = [
        CommitEventDTO(
            sha="c111222333444555",
            parent_sha="p000111",
            author_name="Alice",
            author_email="alice@test.com",
            authored_at=now,
            message="feat: add user controller and service",
            changed_files=[
                FileChangeDTO(
                    file_path="src/controllers/UserController.java",
                    change_type=ChangeType.MODIFIED,
                    insertions=20,
                    deletions=2,
                ),
                FileChangeDTO(
                    file_path="src/services/UserService.java",
                    change_type=ChangeType.ADDED,
                    insertions=100,
                    deletions=0,
                ),
            ],
            total_insertions=120,
            total_deletions=2,
        )
    ]

    mock_entity = Entity(
        id=uuid.uuid4(),
        project_id=proj_id,
        entity_type="CLASS",
        entity_key="SYMBOL:HELLO_BE:UserController",
        name="UserController",
        canonical_name="UserController",
        path="src/controllers/UserController.java",
        status="ACTIVE",
    )

    entities_by_path = {"src/controllers/UserController.java": [mock_entity]}

    events = pipeline.generate_events_for_commits(
        project_key="HELLO_BE",
        project_id=proj_id,
        commits=mock_commits,
        entities_by_path=entities_by_path,
    )

    # 1 COMMIT event + 2 FILE_CHANGED events + 1 ENTITY_CHANGED event = 4 events
    assert len(events) == 4

    commit_events = [e for e in events if e.event_type == EventType.COMMIT.value]
    assert len(commit_events) == 1
    assert commit_events[0].metadata_["commit_sha"] == "c111222333444555"

    file_events = [e for e in events if e.event_type == EventType.FILE_CHANGED.value]
    assert len(file_events) == 2

    entity_events = [e for e in events if e.event_type == EventType.ENTITY_CHANGED.value]
    assert len(entity_events) == 1
    assert entity_events[0].entity_id == mock_entity.id
    assert entity_events[0].metadata_["entity_name"] == "UserController"


def test_double_pass_idempotency(sqlite_db_session):
    pipeline = EventPipeline()
    now = datetime.now(timezone.utc)
    proj_id = uuid.uuid4()

    mock_commits = [
        CommitEventDTO(
            sha="sha_test_123",
            author_name="Bob",
            author_email="bob@test.com",
            authored_at=now,
            message="fix: resolve memory leak in pipeline",
            changed_files=[
                FileChangeDTO(
                    file_path="src/pipeline.py",
                    change_type=ChangeType.MODIFIED,
                    insertions=5,
                    deletions=3,
                )
            ],
            total_insertions=5,
            total_deletions=3,
        )
    ]

    events_pass1 = pipeline.generate_events_for_commits(
        project_key="TEST_PROJ",
        project_id=proj_id,
        commits=mock_commits,
    )

    # Pass 1
    res1 = pipeline.persist_events(sqlite_db_session, events_pass1)
    assert res1["created"] == 2  # 1 commit + 1 file
    assert res1["updated"] == 0

    all_in_db_1 = sqlite_db_session.scalars(select(Event)).all()
    assert len(all_in_db_1) == 2

    # Pass 2: Identical rescan
    events_pass2 = pipeline.generate_events_for_commits(
        project_key="TEST_PROJ",
        project_id=proj_id,
        commits=mock_commits,
    )
    res2 = pipeline.persist_events(sqlite_db_session, events_pass2)
    assert res2["created"] == 0
    assert res2["updated"] == 2

    all_in_db_2 = sqlite_db_session.scalars(select(Event)).all()
    assert len(all_in_db_2) == 2  # No duplicates created
