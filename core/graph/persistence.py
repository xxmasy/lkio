"""Static Relations Persistence & Dedup Pipeline (C-04)
Persists RelationCandidate DTOs into the Knowledge Core database relations table.

Enforces:
- LOCK-GRAPH-02: Persistence Layer Integrity (batch upsert keyed by relation_key).
- LOCK-GRAPH-09: Relational Edge Granularity (occurrences merged per logical edge).
- LOCK-GRAPH-10: Identity Invariance (relation_key unchanged across resolution).
- LOCK-GRAPH-11: Subject entity key resolution.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)
from core.models.entity import Entity
from core.models.relation import Relation

logger = logging.getLogger(__name__)


@dataclass
class RelationPersistenceResult:
    """Outcome of relation persistence operation."""
    total_candidates: int = 0
    unique_edges: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    reactivated: int = 0
    unresolved_subjects: int = 0
    relation_keys: list[str] = field(default_factory=list)


def merge_relation_candidates(candidates: list[RelationCandidate]) -> list[RelationCandidate]:
    """Merges multiple relation occurrences for the same relation_key into single RelationCandidate (LOCK-GRAPH-09)."""
    merged: dict[str, RelationCandidate] = {}

    for cand in candidates:
        key = cand.relation_key
        if key not in merged:
            merged[key] = cand
        else:
            existing = merged[key]
            # Union occurrences deduplicated by (line, column)
            seen_sites = {(occ.line, occ.column) for occ in existing.occurrences}
            combined_occs = list(existing.occurrences)
            for occ in cand.occurrences:
                site = (occ.line, occ.column)
                if site not in seen_sites:
                    seen_sites.add(site)
                    combined_occs.append(occ)

            # Sort occurrences deterministically by line then column
            combined_occs.sort(key=lambda o: (o.line, o.column))

            # Shallow merge metadata
            new_meta = dict(existing.metadata)
            new_meta.update(cand.metadata)

            # Maintain highest confidence if differing
            max_conf = max(existing.confidence, cand.confidence)

            # Preserve resolved object_entity_key if any candidate resolved it
            obj_key = existing.object_entity_key or cand.object_entity_key
            res_status = ResolutionStatus.RESOLVED if (existing.resolution_status == ResolutionStatus.RESOLVED or cand.resolution_status == ResolutionStatus.RESOLVED) else ResolutionStatus.UNRESOLVED

            merged[key] = RelationCandidate(
                project_key=existing.project_key,
                subject_entity_key=existing.subject_entity_key,
                predicate=existing.predicate,
                normalized_raw_target=existing.normalized_raw_target,
                relation_kind=existing.relation_kind,
                candidate_discriminator=existing.candidate_discriminator,
                confidence=max_conf,
                resolution_status=res_status,
                occurrences=tuple(combined_occs),
                object_entity_key=obj_key,
                source_file_rel_path=existing.source_file_rel_path,
                metadata=new_meta,
            )

    return list(merged.values())


class RelationPersistenceService:
    """Manages batch upsert, occurrence deduplication, and relational integrity of code relations."""

    def __init__(self, strict_subjects: bool = False):
        self.strict_subjects = strict_subjects

    def persist_relations(
        self,
        db: Session,
        project_id: uuid.UUID,
        project_key: str,
        candidates: list[RelationCandidate],
        source_id: uuid.UUID | None = None,
    ) -> RelationPersistenceResult:
        """Persists a batch of RelationCandidate DTOs into the relations table.

        Performs:
        1. In-memory occurrence merging per logical relation_key (LOCK-GRAPH-09).
        2. Bulk subject entity key resolution to subject_entity_id (LOCK-GRAPH-11).
        3. Optional bulk object entity key resolution if object_entity_key provided.
        4. Idempotent upsert by relation_key (LOCK-GRAPH-02, LOCK-GRAPH-10).
        """
        result = RelationPersistenceResult(total_candidates=len(candidates))
        if not candidates:
            return result

        # 1. Deduplicate & merge occurrences across candidates
        merged_cands = merge_relation_candidates(candidates)
        result.unique_edges = len(merged_cands)

        # 2. Collect entity keys to resolve (subjects and objects)
        subject_keys = {c.subject_entity_key for c in merged_cands}
        object_keys = {c.object_entity_key for c in merged_cands if c.object_entity_key}

        all_keys_to_resolve = subject_keys | object_keys
        entity_map: dict[str, Entity] = {}
        if all_keys_to_resolve:
            entities = db.scalars(
                select(Entity).where(
                    Entity.project_id == project_id,
                    Entity.entity_key.in_(list(all_keys_to_resolve)),
                )
            ).all()
            entity_map = {e.entity_key: e for e in entities}

        # 3. Query existing relations by relation_key
        cand_keys = [c.relation_key for c in merged_cands]
        existing_rels = db.scalars(
            select(Relation).where(Relation.relation_key.in_(cand_keys))
        ).all()
        existing_map: dict[str, Relation] = {r.relation_key: r for r in existing_rels}

        # 4. Upsert loop
        for cand in merged_cands:
            sub_entity = entity_map.get(cand.subject_entity_key)
            if not sub_entity:
                if self.strict_subjects:
                    raise ValueError(
                        f"Relational Integrity Violation (LOCK-GRAPH-11): "
                        f"Subject entity key '{cand.subject_entity_key}' not found in project '{project_key}'."
                    )
                result.unresolved_subjects += 1
                logger.warning(
                    "Subject entity key %s not found in DB; skipping relation %s",
                    cand.subject_entity_key,
                    cand.relation_key,
                )
                continue

            # Resolve object entity if object_entity_key is present
            obj_id = None
            res_status = cand.resolution_status
            if cand.object_entity_key and cand.object_entity_key in entity_map:
                obj_id = entity_map[cand.object_entity_key].id
                res_status = ResolutionStatus.RESOLVED

            rel_key = cand.relation_key
            result.relation_keys.append(rel_key)
            occ_dicts = [occ.to_dict() for occ in cand.occurrences]

            if rel_key in existing_map:
                existing = existing_map[rel_key]
                was_deleted = existing.status == "DELETED"
                if was_deleted:
                    existing.status = "ACTIVE"
                    result.reactivated += 1

                # Update target / resolution if improved
                if obj_id and existing.object_entity_id != obj_id:
                    existing.object_entity_id = obj_id
                    existing.resolution_status = ResolutionStatus.RESOLVED.value

                # Merge occurrences in DB
                existing_occs = existing.occurrences or []
                existing_sites = {(o["line"], o["column"]) for o in existing_occs}
                for od in occ_dicts:
                    site = (od["line"], od["column"])
                    if site not in existing_sites:
                        existing_sites.add(site)
                        existing_occs.append(od)
                existing_occs.sort(key=lambda o: (o["line"], o["column"]))
                existing.occurrences = existing_occs

                # Update metadata & confidence
                meta = dict(existing.metadata_ or {})
                meta.update(cand.metadata)
                existing.metadata_ = meta
                existing.confidence = cand.confidence

                result.updated += 1
            else:
                new_rel = Relation(
                    id=uuid.uuid4(),
                    relation_key=rel_key,
                    subject_entity_id=sub_entity.id,
                    predicate=cand.predicate.value,
                    object_entity_id=obj_id,
                    relation_kind=cand.relation_kind.value,
                    resolution_status=res_status.value,
                    raw_target=cand.normalized_raw_target,
                    status="ACTIVE",
                    confidence=cand.confidence,
                    occurrences=occ_dicts,
                    source_id=source_id,
                    metadata_=dict(cand.metadata),
                )
                db.add(new_rel)
                existing_map[rel_key] = new_rel
                result.created += 1

        db.flush()
        return result

    def sync_file_relations(
        self,
        db: Session,
        project_id: uuid.UUID,
        project_key: str,
        file_entity: Entity,
        candidates: list[RelationCandidate],
        source_id: uuid.UUID | None = None,
    ) -> RelationPersistenceResult:
        """Synchronizes relations for a file with atomic upsert, resurrection, and soft-deletion (LOCK-GRAPH-08).

        Guarantees:
        - Never physically deletes relations (soft-delete status='DELETED').
        - Resurrects reappearing relations to status='ACTIVE'.
        - Never touches MVP2-B 'defines' relations.
        """
        # 1. Upsert/reactivate all current candidates
        res = self.persist_relations(db, project_id, project_key, candidates, source_id=source_id)

        # 2. Collect subject IDs belonging to this file (file entity and defined symbols)
        defined_sym_ids = db.scalars(
            select(Relation.object_entity_id).where(
                Relation.subject_entity_id == file_entity.id,
                Relation.predicate == "defines",
            )
        ).all()
        all_subject_ids = [file_entity.id] + [sid for sid in defined_sym_ids if sid is not None]

        # 3. Soft-delete vanished structural graph relations
        active_keys = set(res.relation_keys)
        existing_relations = db.scalars(
            select(Relation).where(
                Relation.subject_entity_id.in_(all_subject_ids),
                Relation.predicate != "defines",
                Relation.status == "ACTIVE",
            )
        ).all()

        for rel in existing_relations:
            if rel.relation_key not in active_keys:
                rel.status = "DELETED"
                res.deleted += 1

        db.flush()
        return res
