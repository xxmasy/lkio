"""LKIO Wiki Data Transfer Objects and Schemas."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from core.models.wiki import StandardWikiSection, WikiSectionStatus
from core.rag.models import EvidenceCitation


@dataclass
class WikiSectionDTO:
    """Transfer object representing a generated or regenerated Wiki Section."""
    project_key: str
    section_name: StandardWikiSection
    title: str
    content: str
    source_entity_keys: list[str] = field(default_factory=list)
    source_relation_keys: list[str] = field(default_factory=list)
    source_document_paths: list[str] = field(default_factory=list)
    source_commit_hashes: list[str] = field(default_factory=list)
    evidence_citations: list[EvidenceCitation] = field(default_factory=list)
    model: str = "deterministic-synthesizer"
    prompt_version: str = "v1.0"
    confidence: float = 1.0
    status: WikiSectionStatus = WikiSectionStatus.GENERATED
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def section_key(self) -> str:
        return f"WIKI:{self.project_key}:{self.section_name.value}"
