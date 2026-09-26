"""Unit tests for Event model and enums in core/models/event.py
"""

from datetime import datetime, timezone
import uuid
from core.models.event import ActorType, Event, EventType, SourceType
from core.models.project import Project


def test_event_type_enums():
    assert EventType.COMMIT.value == "COMMIT"
    assert EventType.FILE_CHANGED.value == "FILE_CHANGED"
    assert EventType.ENTITY_CHANGED.value == "ENTITY_CHANGED"
    assert EventType.API_CHANGE.value == "API_CHANGE"
    assert EventType.DATABASE_CHANGE.value == "DATABASE_CHANGE"


def test_actor_and_source_type_enums():
    assert ActorType.GIT.value == "git"
    assert ActorType.HUMAN.value == "human"
    assert SourceType.GIT_COMMIT.value == "git_commit"


def test_event_instantiation():
    now = datetime.now(timezone.utc)
    proj_id = uuid.uuid4()
    event = Event(
        event_key="EVENT:HELLO_BE:COMMIT:abcdef123456",
        event_type=EventType.COMMIT.value,
        project_id=proj_id,
        actor_type=ActorType.GIT.value,
        actor_id="dev@example.com",
        timestamp=now,
        before_state={"status": "initial"},
        after_state={"status": "committed"},
        reason="feat: add lead conversion service",
        source_type=SourceType.GIT_COMMIT.value,
        confidence=1.0,
        metadata_={
            "commit_sha": "abcdef123456",
            "message": "feat: add lead conversion service",
            "insertions": 120,
            "deletions": 5,
        },
    )
    assert event.event_key == "EVENT:HELLO_BE:COMMIT:abcdef123456"
    assert event.event_type == "COMMIT"
    assert event.confidence == 1.0
    assert event.metadata_["commit_sha"] == "abcdef123456"
