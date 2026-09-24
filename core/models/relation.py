"""Relation Model
Represents a directed relationship triple between two entities with confidence and evidence.
"""

import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Relation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "relations"

    subject_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    predicate: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )  # contains, belongs_to, paired_with, depends_on, uses, implements, calls, reads, writes, affects, etc.
    object_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(6, 5),
        default=Decimal("1.00000"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "subject_entity_id",
            "predicate",
            "object_entity_id",
            name="uq_relations_triple",
        ),
    )

    # Relationships
    subject: Mapped["Entity"] = relationship(  # type: ignore[name-defined]
        "Entity",
        foreign_keys=[subject_entity_id],
        back_populates="outgoing_relations",
    )
    object: Mapped["Entity"] = relationship(  # type: ignore[name-defined]
        "Entity",
        foreign_keys=[object_entity_id],
        back_populates="incoming_relations",
    )
    source: Mapped["Source | None"] = relationship(  # type: ignore[name-defined]
        "Source",
        foreign_keys=[source_id],
    )
