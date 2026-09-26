"""WikiSection Model
Represents an evidence-grounded architectural knowledge projection section in LKIO.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StandardWikiSection(str, Enum):
    """13 Fixed Wiki Sections required by LKIO Baseline Section 25.2."""
    PROJECT_OVERVIEW = "project_overview"
    ARCHITECTURE = "architecture"
    FRONTEND = "frontend"
    BACKEND = "backend"
    API = "api"
    DATABASE = "database"
    BUSINESS_DOMAIN = "business_domain"
    BUSINESS_PROCESS = "business_process"
    BUSINESS_RULES = "business_rules"
    DEPENDENCIES = "dependencies"
    RECENT_CHANGES = "recent_changes"
    KNOWN_RISKS = "known_risks"
    OPEN_DECISIONS = "open_decisions"


class WikiSectionStatus(str, Enum):
    """Lifecycle states for Wiki Sections (Baseline Section 26)."""
    GENERATED = "GENERATED"
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"


class WikiSection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a discrete, incrementally updateable Wiki chapter."""
    __tablename__ = "wiki_sections"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    project_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    section_key: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    section_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Provenance and Grounding
    source_entity_keys: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    source_relation_keys: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    source_document_paths: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    source_commit_hashes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    evidence_citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)

    model: Mapped[str] = mapped_column(String(64), default="deterministic-synthesizer", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default=WikiSectionStatus.GENERATED.value, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationship
    project: Mapped["Project | None"] = relationship(  # type: ignore[name-defined]
        "Project",
        back_populates="wiki_sections",
    )

    def mark_stale(self) -> None:
        """Transitions section to STALE when underlying source entities or files change."""
        self.status = WikiSectionStatus.STALE.value

    def mark_verified(self) -> None:
        """Transitions section to VERIFIED after review or full evidence pass."""
        self.status = WikiSectionStatus.VERIFIED.value
        self.verified_at = datetime.now(timezone.utc)

    def mark_conflicted(self) -> None:
        """Transitions section to CONFLICTED when contradictory source facts emerge."""
        self.status = WikiSectionStatus.CONFLICTED.value
