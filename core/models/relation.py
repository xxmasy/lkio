"""Relation Model
Represents a directed relationship triple between two entities with confidence and evidence.
"""

import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Relation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "relations"

    relation_key: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
        nullable=False,
    )  # Logical idempotent identity: e.g. RELATION:HELLO_BE:FILE:...:imports:...
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
    )  # defines, imports, exports, extends, implements, calls, etc.
    object_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )  # Nullable for UNRESOLVED external/pending dependencies (LOCK-GRAPH-06)
    relation_kind: Mapped[str] = mapped_column(
        String(32),
        default="STATIC",
        index=True,
        nullable=False,
    )  # STATIC | INFERRED (LOCK-GRAPH-03)
    resolution_status: Mapped[str] = mapped_column(
        String(32),
        default="RESOLVED",
        index=True,
        nullable=False,
    )  # RESOLVED | UNRESOLVED (LOCK-GRAPH-06, LOCK-GRAPH-10)
    raw_target: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )  # Un-truncated raw target string from source AST (LOCK-GRAPH-12)
    status: Mapped[str] = mapped_column(
        String(32),
        default="ACTIVE",
        index=True,
        nullable=False,
    )  # ACTIVE | DELETED (LOCK-GRAPH-08 Lifecycle)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(6, 5),
        default=Decimal("1.00000"),
        nullable=False,
    )
    occurrences: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )  # Aggregated source call/import sites (LOCK-GRAPH-09)
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
        Index("ix_relations_subject_predicate", "subject_entity_id", "predicate"),
    )

    def __init__(self, *args, **kwargs):
        # Backwards compatibility: Auto-generate relation_key if omitted (e.g. B-07 'defines' relations)
        if "relation_key" not in kwargs or not kwargs["relation_key"]:
            sub = kwargs.get("subject_entity_id") or uuid.uuid4().hex
            pred = kwargs.get("predicate", "defines")
            obj = kwargs.get("object_entity_id") or kwargs.get("raw_target") or uuid.uuid4().hex
            kind = kwargs.get("relation_kind", "STATIC")
            disc = kwargs.get("candidate_discriminator", "default")
            kwargs["relation_key"] = f"RELATION:{sub}:{pred}:{obj}:{kind}:{disc}"
        if "occurrences" not in kwargs:
            kwargs["occurrences"] = []
        if "raw_target" not in kwargs:
            kwargs["raw_target"] = ""
        if "relation_kind" not in kwargs:
            kwargs["relation_kind"] = "STATIC"
        if "resolution_status" not in kwargs:
            kwargs["resolution_status"] = "RESOLVED" if kwargs.get("object_entity_id") is not None else "UNRESOLVED"
        if "status" not in kwargs:
            kwargs["status"] = "ACTIVE"
        super().__init__(*args, **kwargs)

    # Relationships
    subject: Mapped["Entity"] = relationship(  # type: ignore[name-defined]
        "Entity",
        foreign_keys=[subject_entity_id],
        back_populates="outgoing_relations",
    )
    object: Mapped["Entity | None"] = relationship(  # type: ignore[name-defined]
        "Entity",
        foreign_keys=[object_entity_id],
        back_populates="incoming_relations",
    )
    source: Mapped["Source | None"] = relationship(  # type: ignore[name-defined]
        "Source",
        foreign_keys=[source_id],
    )

