"""IngestionRun Model
Tracks execution history, diff metrics, errors, and audits of project scans.
"""

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class IngestionRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ingestion_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        index=True,
        nullable=False,
    )  # PENDING, RUNNING, COMPLETED, PARTIAL, FAILED
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    head_before: Mapped[str | None] = mapped_column(String(64), nullable=True)
    head_after: Mapped[str | None] = mapped_column(String(64), nullable=True)

    files_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    entities_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entities_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    relations_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    errors: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]
        "Project",
        foreign_keys=[project_id],
    )
    source: Mapped["Source | None"] = relationship(  # type: ignore[name-defined]
        "Source",
        foreign_keys=[source_id],
    )
    snapshots: Mapped[list["ProjectSnapshot"]] = relationship(  # type: ignore[name-defined]
        "ProjectSnapshot",
        back_populates="ingestion_run",
        cascade="all, delete-orphan",
    )
