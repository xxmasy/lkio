"""Project Model
Represents a registered software project under LKIO governance.
"""

from typing import Any
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # frontend, backend, fullstack, service, library, unknown
    role: Mapped[str] = mapped_column(String(64), nullable=False)  # primary_frontend, paired_backend, future_frontend, supporting_service, unknown
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    sources: Mapped[list["Source"]] = relationship(  # type: ignore[name-defined]
        "Source",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    entities: Mapped[list["Entity"]] = relationship(  # type: ignore[name-defined]
        "Entity",
        back_populates="project",
        cascade="all, delete-orphan",
    )
