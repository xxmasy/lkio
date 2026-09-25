"""LKIO Code Symbol Persistence & Incremental Synchronization
Persists extracted SymbolCandidate DTOs into Knowledge Core (entities & relations),
with deterministic keys, atomic per-file upserts, and automatic soft-deletion of vanished symbols.
"""

from decimal import Decimal
from pathlib import Path
from typing import Any
import uuid
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from core.db.session import SessionLocal
from core.extraction.dto import SymbolCandidate
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from core.models.source import Source


class SymbolSyncService:
    """Manages atomic symbol upserts, 'defines' relations, and soft-delete synchronization."""

    def __init__(self, orchestrator: SymbolExtractionOrchestrator | None = None):
        self.orchestrator = orchestrator or SymbolExtractionOrchestrator()

    def sync_file_symbols(
        self,
        db: Session,
        project_id: uuid.UUID,
        project_key: str,
        file_entity: Entity,
        code_bytes: bytes,
        source_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """Extracts and synchronizes code symbols for a single file within the current DB session."""
        rel_path = file_entity.path or ""
        if not self.orchestrator.is_supported(rel_path):
            return {"extracted": 0, "created": 0, "updated": 0, "deleted": 0}

        # 1. Extract symbols
        extracted = self.orchestrator.extract_file_symbols(
            code_bytes=code_bytes,
            project_key=project_key,
            file_path=rel_path,
            file_rel_path=rel_path,
        )

        # 2. Query existing symbols attached to this file via 'defines' relation
        existing_relations = db.scalars(
            select(Relation).where(
                Relation.subject_entity_id == file_entity.id,
                Relation.predicate == "defines",
            )
        ).all()
        existing_symbol_ids = [r.object_entity_id for r in existing_relations]

        existing_symbols: list[Entity] = []
        if existing_symbol_ids:
            existing_symbols = db.scalars(
                select(Entity).where(Entity.id.in_(existing_symbol_ids))
            ).all()

        existing_sym_by_key = {s.entity_key: s for s in existing_symbols}
        existing_rel_by_obj_id = {r.object_entity_id: r for r in existing_relations}

        # Batch fetch any entities already existing by key that aren't yet linked
        keys_to_fetch = [k for k, _ in extracted if k not in existing_sym_by_key]
        if keys_to_fetch:
            extra_entities = db.scalars(
                select(Entity).where(Entity.entity_key.in_(keys_to_fetch))
            ).all()
            for e in extra_entities:
                existing_sym_by_key[e.entity_key] = e

        seen_keys: set[str] = set()
        created_count = 0
        updated_count = 0

        # 3. Upsert newly extracted symbols
        for sym_key, cand in extracted:
            seen_keys.add(sym_key)

            metadata_payload = {
                "symbol_type": cand.symbol_type,
                "base_symbol_type": cand.base_symbol_type,
                "classification_method": cand.classification_method,
                "qualified_name": cand.qualified_name,
                "start_line": cand.start_line,
                "end_line": cand.end_line,
                "start_column": cand.start_column,
                "end_column": cand.end_column,
                "signature": cand.signature,
                "signature_discriminator": cand.signature_discriminator,
                "language": cand.language,
                "parser_version": cand.parser_version,
                "extractor_version": cand.extractor_version,
                "modifiers": cand.modifiers,
                "is_exported": cand.is_exported,
                "annotations": cand.annotations,
                "docstring": cand.docstring,
                "extra": cand.metadata,
            }

            sym_entity = existing_sym_by_key.get(sym_key)

            if not sym_entity:
                # Create new symbol Entity
                sym_entity = Entity(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    entity_type=cand.symbol_type,
                    entity_key=sym_key,
                    name=cand.name,
                    canonical_name=f"{project_key}_{cand.qualified_name}",
                    path=rel_path,
                    status="ACTIVE",
                    metadata_=metadata_payload,
                )
                db.add(sym_entity)
                existing_sym_by_key[sym_key] = sym_entity
                created_count += 1
            else:
                # Update existing symbol Entity
                sym_entity.status = "ACTIVE"
                sym_entity.entity_type = cand.symbol_type
                sym_entity.name = cand.name
                sym_entity.canonical_name = f"{project_key}_{cand.qualified_name}"
                sym_entity.path = rel_path
                sym_entity.metadata_ = metadata_payload
                updated_count += 1

            # Ensure 'defines' relation exists
            if sym_entity.id not in existing_rel_by_obj_id:
                rel = Relation(
                    id=uuid.uuid4(),
                    subject_entity_id=file_entity.id,
                    predicate="defines",
                    object_entity_id=sym_entity.id,
                    confidence=Decimal("1.00000"),
                    source_id=source_id,
                    metadata_={
                        "extraction_method": "static_ast",
                        "symbol_type": cand.symbol_type,
                        "base_symbol_type": cand.base_symbol_type,
                    },
                )
                db.add(rel)
                existing_rel_by_obj_id[sym_entity.id] = rel

        # 4. Soft-delete vanished symbols previously defined by this file
        deleted_count = 0
        for sym_key, sym_entity in existing_sym_by_key.items():
            if sym_key not in seen_keys and sym_entity.status != "deleted":
                sym_entity.status = "deleted"
                deleted_count += 1

        db.flush()

        return {
            "extracted": len(extracted),
            "created": created_count,
            "updated": updated_count,
            "deleted": deleted_count,
        }

    def sync_project_symbols(
        self,
        project_key_or_id: str,
        db: Session | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Scans active code files in a project and synchronizes symbols."""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            # Resolve Project
            try:
                u_id = uuid.UUID(project_key_or_id)
                stmt = select(Project).where(Project.id == u_id)
            except ValueError:
                stmt = select(Project).where(Project.key == project_key_or_id)

            project = db.scalars(stmt).first()
            if not project:
                raise ValueError(f"Project '{project_key_or_id}' not found")

            # Resolve Source
            source = db.scalars(
                select(Source).where(Source.project_id == project.id)
            ).first()
            source_id = source.id if source else None

            # Get all active FILE entities
            files = db.scalars(
                select(Entity).where(
                    Entity.project_id == project.id,
                    Entity.entity_type == "FILE",
                    Entity.status == "ACTIVE",
                )
            ).all()

            project_root = Path(project.local_path)
            stats = {
                "project_key": project.key,
                "scanned_files": 0,
                "supported_files": 0,
                "total_symbols_extracted": 0,
                "created": 0,
                "updated": 0,
                "deleted": 0,
            }

            for f_ent in files:
                stats["scanned_files"] += 1
                if not f_ent.path or not self.orchestrator.is_supported(f_ent.path):
                    continue

                full_path = project_root / f_ent.path
                if not full_path.exists():
                    continue

                stats["supported_files"] += 1
                code_bytes = full_path.read_bytes()

                res = self.sync_file_symbols(
                    db=db,
                    project_id=project.id,
                    project_key=project.key,
                    file_entity=f_ent,
                    code_bytes=code_bytes,
                    source_id=source_id,
                )
                stats["total_symbols_extracted"] += res["extracted"]
                stats["created"] += res["created"]
                stats["updated"] += res["updated"]
                stats["deleted"] += res["deleted"]

                if limit is not None and stats["supported_files"] >= limit:
                    break

            db.commit()
            return stats

        finally:
            if should_close:
                db.close()
