"""LKIO Incremental Wiki Pipeline and Persistence Service
Orchestrates full generation, stale detection, section-level incremental regeneration, and DB persistence.
"""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from core.models.wiki import StandardWikiSection, WikiSection, WikiSectionStatus
from core.rag.engine import RAGEngine
from core.rag.gateway.provider import LLMProvider
from core.wiki.generators.section_generators import (
    StandardSectionGenerator,
    WikiSectionGeneratorFactory,
)
from core.wiki.models import WikiSectionDTO
from core.wiki.stale_detector import StaleDetector


class WikiPipeline:
    """Manages the full lifecycle and incremental update of Project Wikis."""

    def __init__(self, stale_detector: StaleDetector | None = None) -> None:
        self.stale_detector = stale_detector or StaleDetector()

    def generate_full_wiki(
        self,
        project_key: str,
        engine: RAGEngine,
        provider: LLMProvider | None = None,
    ) -> list[WikiSectionDTO]:
        """Generates all 13 standard Wiki sections for the specified project."""
        return WikiSectionGeneratorFactory.generate_all_sections(
            project_key=project_key,
            engine=engine,
            provider=provider,
        )

    def regenerate_stale_sections(
        self,
        project_key: str,
        modified_files: list[str],
        engine: RAGEngine,
        provider: LLMProvider | None = None,
        existing_sections: list[WikiSectionDTO] | None = None,
    ) -> tuple[list[WikiSectionDTO], set[StandardWikiSection]]:
        """Identifies STALE sections caused by modified files and regenerates ONLY those sections."""
        existing_evidences: dict[StandardWikiSection, list[str]] = {}
        section_map: dict[StandardWikiSection, WikiSectionDTO] = {}

        if existing_sections:
            for s in existing_sections:
                section_map[s.section_name] = s
                recorded = list(s.source_document_paths) + list(s.source_entity_keys)
                existing_evidences[s.section_name] = recorded

        # 1. Detect stale sections
        stale_secs = self.stale_detector.detect_stale_sections(
            modified_files=modified_files,
            existing_section_evidences=existing_evidences if existing_sections else None,
        )

        # 2. Regenerate only stale sections
        regenerated_results: list[WikiSectionDTO] = []
        for sec_name in StandardWikiSection:
            if sec_name in stale_secs or not existing_sections:
                # Regenerate
                gen = StandardSectionGenerator(sec_name)
                dto = gen.generate(project_key=project_key, engine=engine, provider=provider)
                dto.status = WikiSectionStatus.GENERATED
                regenerated_results.append(dto)
            else:
                # Keep unchanged
                dto = section_map[sec_name]
                regenerated_results.append(dto)

        return regenerated_results, stale_secs

    def persist_sections(
        self,
        db: Session,
        sections: list[WikiSectionDTO],
        project_id: Any | None = None,
    ) -> dict[str, int]:
        """Idempotently syncs WikiSectionDTO records to the wiki_sections DB table."""
        created = 0
        updated = 0

        for dto in sections:
            existing = (
                db.query(WikiSection)
                .filter(WikiSection.section_key == dto.section_key)
                .first()
            )

            citations_data = [
                {
                    "evidence_type": ev.evidence_type.value,
                    "project_key": ev.project_key,
                    "file_path": ev.file_path,
                    "start_line": ev.start_line,
                    "end_line": ev.end_line,
                    "entity_key": ev.entity_key,
                    "relation_key": ev.relation_key,
                    "commit_hash": ev.commit_hash,
                    "confidence": ev.confidence,
                }
                for ev in dto.evidence_citations
            ]

            if existing:
                existing.title = dto.title
                existing.content = dto.content
                existing.source_entity_keys = dto.source_entity_keys
                existing.source_relation_keys = dto.source_relation_keys
                existing.source_document_paths = dto.source_document_paths
                existing.source_commit_hashes = dto.source_commit_hashes
                existing.evidence_citations = citations_data
                existing.model = dto.model
                existing.prompt_version = dto.prompt_version
                existing.confidence = dto.confidence
                existing.status = dto.status.value
                existing.generated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                new_sec = WikiSection(
                    project_id=project_id,
                    project_key=dto.project_key,
                    section_key=dto.section_key,
                    section_name=dto.section_name.value,
                    title=dto.title,
                    content=dto.content,
                    source_entity_keys=dto.source_entity_keys,
                    source_relation_keys=dto.source_relation_keys,
                    source_document_paths=dto.source_document_paths,
                    source_commit_hashes=dto.source_commit_hashes,
                    evidence_citations=citations_data,
                    model=dto.model,
                    prompt_version=dto.prompt_version,
                    confidence=dto.confidence,
                    status=dto.status.value,
                    generated_at=datetime.now(timezone.utc),
                )
                db.add(new_sec)
                created += 1

        db.commit()
        return {"created": created, "updated": updated, "total": len(sections)}
