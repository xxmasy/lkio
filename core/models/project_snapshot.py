"""ProjectSnapshot Model
Captures high-level milestone state of a project after each scan run.
"""

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, UUIDPrimaryKeyMixin, utc_now


class ProjectSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "project_snapshots"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_runs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    head: Mapped[str | None] = mapped_column(String(64), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    directory_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dependency_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    frameworks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    languages: Mapped[list[dict[str, Any]]] = mapped_column(
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]
        "Project",
        foreign_keys=[project_id],
    )
    ingestion_run: Mapped["IngestionRun | None"] = relationship(  # type: ignore[name-defined]
        "IngestionRun",
        foreign_keys=[ingestion_run_id],
        back_populates="snapshots",
    )
