"""API Traceability Relation Persistence & Lifecycle Synchronization (E-04)
Persists end-to-end API traceability links into the database with atomic upsert and soft-deletion.

Enforces:
- LOCK-TRACE-03: Multi-layer traceability linking.
- LOCK-TRACE-04: Deterministic relation_key format and 3-Set invariance.
"""

from dataclasses import dataclass, field
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.graph.api.models import ApiTraceCandidate
from core.graph.models import ResolutionStatus
from core.models.entity import Entity
from core.models.relation import Relation

logger = logging.getLogger(__name__)


@dataclass
class ApiTracePersistenceResult:
    """Outcome of API traceability persistence operation."""
    total_candidates: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    reactivated: int = 0
    unresolved_entities: int = 0
    relation_keys: list[str] = field(default_factory=list)


class ApiTracePersistenceService:
    """Manages database persistence and lifecycle synchronization of API traceability relations."""

    def __init__(self, strict_entities: bool = False):
        self.strict_entities = strict_entities

    def persist_trace_relations(
        self,
        db: Session,
        candidates: list[ApiTraceCandidate],
        source_id: uuid.UUID | None = None,
    ) -> ApiTracePersistenceResult:
        """Persists API trace candidates with batch entity lookups and idempotent upsert."""
        result = ApiTracePersistenceResult(total_candidates=len(candidates))
        if not candidates:
            return result

        # 1. Collect distinct entity keys across projects
        keys_to_resolve = set()
        for c in candidates:
            keys_to_resolve.add(c.subject_entity_key)
            if c.object_entity_key:
                keys_to_resolve.add(c.object_entity_key)

        entity_map: dict[str, Entity] = {}
        if keys_to_resolve:
            entities = db.scalars(
                select(Entity).where(Entity.entity_key.in_(list(keys_to_resolve)))
            ).all()
            entity_map = {e.entity_key: e for e in entities}

        # 2. Query existing relations by relation_key
        cand_keys = [c.relation_key for c in candidates]
        existing_rels = db.scalars(
            select(Relation).where(Relation.relation_key.in_(cand_keys))
        ).all()
        existing_map = {r.relation_key: r for r in existing_rels}

        # 3. Upsert loop
        for cand in candidates:
            sub_ent = entity_map.get(cand.subject_entity_key)
            obj_ent = entity_map.get(cand.object_entity_key) if cand.object_entity_key else None

            if not sub_ent or not obj_ent:
                if self.strict_entities:
                    missing = []
                    if not sub_ent:
                        missing.append(f"subject: {cand.subject_entity_key}")
                    if not obj_ent:
                        missing.append(f"object: {cand.object_entity_key}")
                    raise ValueError(f"Entity Key Resolution Failure: {', '.join(missing)}")
                result.unresolved_entities += 1
                logger.warning(
                    "Skipping trace relation %s due to unresolved entity keys", cand.relation_key
                )
                continue

            rel_key = cand.relation_key
            result.relation_keys.append(rel_key)
            occ_dicts = [occ.to_dict() for occ in cand.occurrences]

            if rel_key in existing_map:
                existing = existing_map[rel_key]
                was_deleted = existing.status == "DELETED"
                if was_deleted:
                    existing.status = "ACTIVE"
                    result.reactivated += 1

                existing.object_entity_id = obj_ent.id
                existing.resolution_status = ResolutionStatus.RESOLVED.value
                existing.confidence = cand.confidence
                existing.occurrences = occ_dicts

                meta = dict(existing.metadata_ or {})
                meta.update(cand.metadata)
                existing.metadata_ = meta

                result.updated += 1
            else:
                new_rel = Relation(
                    id=uuid.uuid4(),
                    relation_key=rel_key,
                    subject_entity_id=sub_ent.id,
                    predicate=cand.predicate.value,
                    object_entity_id=obj_ent.id,
                    relation_kind=cand.relation_kind.value,
                    resolution_status=ResolutionStatus.RESOLVED.value,
                    raw_target=cand.normalized_endpoint,
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

    def sync_trace_relations(
        self,
        db: Session,
        source_project_key: str,
        candidates: list[ApiTraceCandidate],
        source_id: uuid.UUID | None = None,
    ) -> ApiTracePersistenceResult:
        """Synchronizes API traceability relations with soft-deletion of vanished routes."""
        res = self.persist_trace_relations(db, candidates, source_id=source_id)

        # Soft-delete vanished trace relations originated by source_project_key
        prefix = f"RELATION:TRACE:{source_project_key}:"
        existing_trace_rels = db.scalars(
            select(Relation).where(
                Relation.relation_key.startswith(prefix),
                Relation.status == "ACTIVE",
            )
        ).all()

        active_keys = set(res.relation_keys)
        for r in existing_trace_rels:
            if r.relation_key not in active_keys:
                r.status = "DELETED"
                res.deleted += 1

        db.flush()
        return res
