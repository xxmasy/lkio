"""LKIO Code Symbol Persistence & Incremental Synchronization (B-07 Approved)
Persists extracted SymbolCandidate DTOs into Knowledge Core (entities & relations),
with deterministic keys, atomic per-file upserts, soft-deletion of vanished symbols,
and automatic resurrection of reappearing symbols under strict architecture locks.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
from pathlib import Path
import time
from typing import Any
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core.db.session import SessionLocal
from core.extraction.dto import (
    FileExtractionResult,
    SymbolCandidate,
)
from core.extraction.normalizer import normalize_rel_path
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from core.models.source import Source


def _truncate_string(val: str, max_len: int = 255) -> str:
    """Defensively truncates strings exceeding max column length while preserving uniqueness (Gate M)."""
    if len(val) <= max_len:
        return val
    hash_suffix = "_" + hashlib.sha256(val.encode("utf-8")).hexdigest()[:10]
    prefix_len = max_len - len(hash_suffix)
    return val[:prefix_len] + hash_suffix


@dataclass
class FilePersistenceResult:
    """Detailed outcome of symbol persistence for a single file (LOCK-PERSIST-06)."""
    file_rel_path: str
    success: bool
    extracted: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    reactivated: int = 0
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchPersistenceSummary:
    """Summary of batch symbol persistence with strict counter integrity (LOCK-PERSIST-06)."""
    project_key: str
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_extracted: int = 0
    total_created: int = 0
    total_updated: int = 0
    total_deleted: int = 0
    total_reactivated: int = 0
    duration_ms: float = 0.0
    results: list[FilePersistenceResult] = field(default_factory=list)

    def verify_counter_integrity(self) -> bool:
        """Verifies the counter integrity invariants:
        total_files == successful_files + failed_files + skipped_files
        total_extracted == total_created + total_updated
        """
        files_valid = self.total_files == (
            self.successful_files + self.failed_files + self.skipped_files
        )
        symbols_valid = self.total_extracted == (
            self.total_created + self.total_updated
        )
        return files_valid and symbols_valid


class SymbolPersistenceService:
    """Manages atomic symbol upserts, 'defines' relations, and soft-delete synchronization."""

    def __init__(self, orchestrator: SymbolExtractionOrchestrator | None = None):
        self.orchestrator = orchestrator or SymbolExtractionOrchestrator()

    def persist_file_symbols(
        self,
        db: Session,
        project_id: uuid.UUID,
        project_key: str,
        file_entity: Entity,
        extraction_result: FileExtractionResult,
        source_id: uuid.UUID | None = None,
    ) -> FilePersistenceResult:
        """Persists symbols from a FileExtractionResult into the database within an isolated savepoint.

        Adheres strictly to:
        - LOCK-PERSIST-01: Pure DTO consumer (zero AST parsing).
        - LOCK-PERSIST-02: Idempotent upsert keyed by entity_key.
        - LOCK-PERSIST-03: Soft deletion of vanished symbols (status='DELETED').
        - LOCK-PERSIST-04: Reactivation of resurrected symbols (status='ACTIVE').
        - LOCK-PERSIST-05: Strict 'defines' relation boundary.
        - LOCK-PERSIST-06: Atomic transaction savepoint per file.
        """
        start_time = time.perf_counter()
        rel_path = normalize_rel_path(file_entity.path or extraction_result.file_rel_path or "")

        # If extraction failed or was unsupported, record diagnostic and return
        if not extraction_result.success:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return FilePersistenceResult(
                file_rel_path=rel_path,
                success=False,
                error=extraction_result.error_detail or extraction_result.error_reason or "Extraction unsuccessful",
                duration_ms=duration_ms,
            )

        # Open nested transaction (Savepoint) for file-level isolation (LOCK-PERSIST-06)
        savepoint = db.begin_nested()
        try:
            # Pair symbols with keys
            symbols = extraction_result.symbols
            symbol_keys = extraction_result.symbol_keys
            if len(symbol_keys) != len(symbols):
                symbol_keys = [cand.compute_key() for cand in symbols]

            # De-duplicate candidates with identical keys in the same file
            unique_candidates: dict[str, SymbolCandidate] = {}
            for k, cand in zip(symbol_keys, symbols):
                unique_candidates[k] = cand

            # 1. Query existing symbols attached to this file via 'defines' relation
            existing_relations = db.scalars(
                select(Relation).where(
                    Relation.subject_entity_id == file_entity.id,
                    Relation.predicate == "defines",
                )
            ).all()
            existing_rel_by_obj_id = {r.object_entity_id: r for r in existing_relations}
            existing_symbol_ids = list(existing_rel_by_obj_id.keys())

            existing_symbols: list[Entity] = []
            if existing_symbol_ids:
                existing_symbols = list(
                    db.scalars(
                        select(Entity).where(Entity.id.in_(existing_symbol_ids))
                    ).all()
                )

            existing_sym_by_key: dict[str, Entity] = {s.entity_key: s for s in existing_symbols}

            # Batch fetch any entities already existing by key that aren't yet linked
            keys_to_fetch = [k for k in unique_candidates if k not in existing_sym_by_key]
            if keys_to_fetch:
                extra_entities = db.scalars(
                    select(Entity).where(Entity.entity_key.in_(keys_to_fetch))
                ).all()
                for e in extra_entities:
                    existing_sym_by_key[e.entity_key] = e

            seen_keys: set[str] = set()
            created_count = 0
            updated_count = 0
            reactivated_count = 0

            # 2. Upsert symbols
            for sym_key, cand in unique_candidates.items():
                seen_keys.add(sym_key)

                metadata_payload = {
                    "symbol_type": cand.symbol_type,
                    "base_symbol_type": cand.base_symbol_type,
                    "classification_method": cand.classification_method,
                    "name": cand.name,
                    "qualified_name": cand.qualified_name,
                    "start_line": cand.start_line,
                    "end_line": cand.end_line,
                    "start_column": cand.start_column,
                    "end_column": cand.end_column,
                    "signature": cand.signature,
                    "canonical_signature": cand.canonical_signature,
                    "signature_discriminator": cand.signature_discriminator,
                    "language": cand.language,
                    "parser_version": cand.parser_version,
                    "extractor_version": cand.extractor_version,
                    "modifiers": cand.modifiers,
                    "annotations": cand.annotations,
                    "is_exported": cand.is_exported,
                    "export_kind": cand.export_kind,
                    "docstring": cand.docstring,
                    "extra": cand.metadata,
                }

                safe_name = _truncate_string(cand.name, 255)
                raw_canonical = f"{project_key}_{cand.qualified_name}"
                safe_canonical = _truncate_string(raw_canonical, 255)

                sym_entity = existing_sym_by_key.get(sym_key)

                if not sym_entity:
                    # Create new symbol Entity (LOCK-PERSIST-02)
                    sym_entity = Entity(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        entity_type=cand.symbol_type,
                        entity_key=sym_key,
                        name=safe_name,
                        canonical_name=safe_canonical,
                        path=rel_path,
                        status="ACTIVE",
                        metadata_=metadata_payload,
                    )
                    db.add(sym_entity)
                    existing_sym_by_key[sym_key] = sym_entity
                    created_count += 1
                else:
                    # Update existing symbol Entity
                    if sym_entity.status in ["DELETED", "deleted"]:
                        reactivated_count += 1  # LOCK-PERSIST-04: Resurrection
                    sym_entity.status = "ACTIVE"
                    sym_entity.entity_type = cand.symbol_type
                    sym_entity.name = safe_name
                    sym_entity.canonical_name = safe_canonical
                    sym_entity.path = rel_path
                    sym_entity.metadata_ = metadata_payload
                    updated_count += 1

                # 3. Ensure 'defines' relation exists (LOCK-PERSIST-05)
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
                            "language": cand.language,
                        },
                    )
                    db.add(rel)
                    existing_rel_by_obj_id[sym_entity.id] = rel

            # 4. Soft-delete vanished symbols previously defined by this file (LOCK-PERSIST-03)
            deleted_count = 0
            for sym_key, sym_entity in existing_sym_by_key.items():
                if sym_entity.id in existing_rel_by_obj_id and sym_key not in seen_keys:
                    if sym_entity.status not in ["DELETED", "deleted"]:
                        sym_entity.status = "DELETED"
                        deleted_count += 1

            db.flush()
            savepoint.commit()

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return FilePersistenceResult(
                file_rel_path=rel_path,
                success=True,
                extracted=len(seen_keys),
                created=created_count,
                updated=updated_count,
                deleted=deleted_count,
                reactivated=reactivated_count,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            savepoint.rollback()
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return FilePersistenceResult(
                file_rel_path=rel_path,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
            )

    def persist_batch_symbols(
        self,
        db: Session,
        project_id: uuid.UUID,
        project_key: str,
        file_items: list[tuple[Entity, FileExtractionResult]],
        source_id: uuid.UUID | None = None,
    ) -> BatchPersistenceSummary:
        """Persists a batch of (file_entity, FileExtractionResult) tuples with deterministic ordering and counter integrity."""
        batch_start = time.perf_counter()
        sorted_items = sorted(
            file_items,
            key=lambda item: normalize_rel_path(item[0].path or item[1].file_rel_path or ""),
        )

        total_files = len(sorted_items)
        successful_files = 0
        failed_files = 0
        skipped_files = 0
        total_extracted = 0
        total_created = 0
        total_updated = 0
        total_deleted = 0
        total_reactivated = 0
        results: list[FilePersistenceResult] = []

        for file_ent, ext_res in sorted_items:
            if not ext_res.success:
                failed_files += 1
                results.append(
                    FilePersistenceResult(
                        file_rel_path=normalize_rel_path(file_ent.path or ext_res.file_rel_path),
                        success=False,
                        error=ext_res.error_detail or ext_res.error_reason,
                    )
                )
                continue

            file_persist_res = self.persist_file_symbols(
                db=db,
                project_id=project_id,
                project_key=project_key,
                file_entity=file_ent,
                extraction_result=ext_res,
                source_id=source_id,
            )
            results.append(file_persist_res)

            if file_persist_res.success:
                successful_files += 1
                total_extracted += file_persist_res.extracted
                total_created += file_persist_res.created
                total_updated += file_persist_res.updated
                total_deleted += file_persist_res.deleted
                total_reactivated += file_persist_res.reactivated
            else:
                failed_files += 1

        duration_ms = (time.perf_counter() - batch_start) * 1000.0
        return BatchPersistenceSummary(
            project_key=project_key,
            total_files=total_files,
            successful_files=successful_files,
            failed_files=failed_files,
            skipped_files=skipped_files,
            total_extracted=total_extracted,
            total_created=total_created,
            total_updated=total_updated,
            total_deleted=total_deleted,
            total_reactivated=total_reactivated,
            duration_ms=duration_ms,
            results=results,
        )

    def sync_file_symbols(
        self,
        db: Session,
        project_id: uuid.UUID,
        project_key: str,
        file_entity: Entity,
        code_bytes: bytes,
        source_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """Extracts and synchronizes code symbols for a single file within the current DB session (backward compatible)."""
        rel_path = normalize_rel_path(file_entity.path or "")
        if not self.orchestrator.is_supported(rel_path):
            return {"extracted": 0, "created": 0, "updated": 0, "deleted": 0, "reactivated": 0}

        ext_result = self.orchestrator.extract_file(
            code_bytes=code_bytes,
            project_key=project_key,
            file_path=rel_path,
            file_rel_path=rel_path,
        )

        persist_res = self.persist_file_symbols(
            db=db,
            project_id=project_id,
            project_key=project_key,
            file_entity=file_entity,
            extraction_result=ext_result,
            source_id=source_id,
        )

        return {
            "extracted": persist_res.extracted,
            "created": persist_res.created,
            "updated": persist_res.updated,
            "deleted": persist_res.deleted,
            "reactivated": persist_res.reactivated,
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
                "reactivated": 0,
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
                stats["reactivated"] += res["reactivated"]

                if limit is not None and stats["supported_files"] >= limit:
                    break

            db.commit()
            return stats

        finally:
            if should_close:
                db.close()


# Backward compatibility alias
SymbolSyncService = SymbolPersistenceService
