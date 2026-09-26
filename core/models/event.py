"""Event Model for MVP5 Event & Change Intelligence
Represents discrete temporal facts, changes, and audit records in LKIO Knowledge Core.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventType(str, Enum):
    """Event Types recognized by LKIO (Baseline Section 27.1 & 27.3)."""
    # Core temporal code change events
    COMMIT = "COMMIT"
    FILE_CHANGED = "FILE_CHANGED"
    ENTITY_CHANGED = "ENTITY_CHANGED"

    # Baseline 27.1 Types
    CODE_CHANGE = "CODE_CHANGE"
    REQUIREMENT_CHANGE = "REQUIREMENT_CHANGE"
    BUSINESS_RULE_CHANGE = "BUSINESS_RULE_CHANGE"
    API_CHANGE = "API_CHANGE"
    DATABASE_CHANGE = "DATABASE_CHANGE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    DEPLOYMENT = "DEPLOYMENT"
    INCIDENT = "INCIDENT"
    OPERATION = "OPERATION"
    DOCUMENT_CHANGE = "DOCUMENT_CHANGE"
    AI_DECISION = "AI_DECISION"
    HUMAN_DECISION = "HUMAN_DECISION"
    METRIC_CHANGE = "METRIC_CHANGE"


class ActorType(str, Enum):
    """Actor Types responsible for triggering events."""
    GIT = "git"
    HUMAN = "human"
    SYSTEM = "system"
    CI = "ci"
    AI = "ai"


class SourceType(str, Enum):
    """Source origin of events."""
    GIT_COMMIT = "git_commit"
    PULL_REQUEST = "pull_request"
    MANUAL = "manual"
    MONITOR = "monitor"
    PIPELINE = "pipeline"


class Event(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a discrete temporal event in the LKIO Knowledge Core."""
    __tablename__ = "events"

    # Deterministic global key for idempotency: e.g. EVENT:<project_key>:COMMIT:<sha>
    event_key: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)

    # Core event attributes
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    actor_type: Mapped[str] = mapped_column(String(32), default=ActorType.GIT.value, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    before_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    after_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_type: Mapped[str] = mapped_column(String(64), default=SourceType.GIT_COMMIT.value, nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project | None"] = relationship(  # type: ignore[name-defined]
        "Project",
        back_populates="events",
    )
    entity: Mapped["Entity | None"] = relationship(  # type: ignore[name-defined]
        "Entity",
    )

    __table_args__ = (
        Index("ix_events_project_timestamp", "project_id", "timestamp"),
    )
