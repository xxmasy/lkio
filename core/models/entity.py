"""Entity Model
Represents a structured domain/architectural/code entity in LKIO Knowledge Core.
"""

import uuid
from typing import Any
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Entity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entities"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )  # PROJECT, REPOSITORY, FRONTEND, BACKEND, DIRECTORY, FILE, MODULE, PAGE, COMPONENT, SERVICE, API, etc.
    entity_key: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
        nullable=False,
    )  # Logical idempotent identity: e.g. PROJECT:HELLO_FE or SYMBOL:... (untruncated)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project | None"] = relationship(  # type: ignore[name-defined]
        "Project",
        back_populates="entities",
    )
    outgoing_relations: Mapped[list["Relation"]] = relationship(  # type: ignore[name-defined]
        "Relation",
        foreign_keys="Relation.subject_entity_id",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    incoming_relations: Mapped[list["Relation"]] = relationship(  # type: ignore[name-defined]
        "Relation",
        foreign_keys="Relation.object_entity_id",
        back_populates="object",
        cascade="all, delete-orphan",
    )
