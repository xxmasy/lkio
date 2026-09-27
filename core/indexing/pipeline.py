"""Incremental Indexing Pipeline with Atomic Publish and Rollback (Stage 1 Sections 3.7 & 12).

Orchestrates:
1. UPDATE_STARTED
2. FILES_CHANGED
3. AST_BUILT
4. SYMBOL_DELTA_READY
5. EDGE_DELTA_READY
6. INDEX_UPDATED
7. VALIDATION_STARTED
8. VALIDATION_PASSED
9. SNAPSHOT_PUBLISHED
(On failure: UPDATE_FAILED -> ROLLBACK_COMPLETED)
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.identity.naming import build_edge_key, build_entity_uri
from core.indexing.change_detector import ChangeClassification, FileDiff
from core.indexing.relation_delta import EdgeDeltaType, RelationshipDeltaEngine
from core.indexing.symbol_delta import SymbolDeltaEngine, SymbolDeltaType
from core.state.snapshot import (
    Snapshot,
    SnapshotEdge,
    SnapshotEntity,
    SnapshotManager,
    SnapshotStatus,
)


class PipelineEvent(str, Enum):
    UPDATE_STARTED = "UPDATE_STARTED"
    FILES_CHANGED = "FILES_CHANGED"
    AST_BUILT = "AST_BUILT"
    SYMBOL_DELTA_READY = "SYMBOL_DELTA_READY"
    EDGE_DELTA_READY = "EDGE_DELTA_READY"
    INDEX_UPDATED = "INDEX_UPDATED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    SNAPSHOT_PUBLISHED = "SNAPSHOT_PUBLISHED"
    UPDATE_FAILED = "UPDATE_FAILED"
    ROLLBACK_COMPLETED = "ROLLBACK_COMPLETED"


@dataclass
class PipelineAuditLog:
    update_id: str
    repo_id: str
    commit_id: str
    events: List[str] = field(default_factory=list)
    changed_files_count: int = 0
    changed_symbols_count: int = 0
    added_edges_count: int = 0
    deleted_edges_count: int = 0
    stale_edge_rate: float = 0.0
    latency_ms: float = 0.0
    status: str = "PENDING"


class IncrementalIndexingPipeline:
    """Zero-downtime, transactional incremental repository indexing engine."""

    def __init__(self, manager: SnapshotManager):
        self.manager = manager

    def apply_incremental_update(
        self,
        new_commit_id: str,
        file_diffs: List[FileDiff],
        force_fail_validation: bool = False,
    ) -> PipelineAuditLog:
        """Executes full incremental update lifecycle over candidate snapshot."""
        start_time = time.perf_counter()
        update_id = f"upd_{int(start_time * 1000)}"
        audit = PipelineAuditLog(
            update_id=update_id,
            repo_id=self.manager.repo_id,
            commit_id=new_commit_id,
        )

        audit.events.append(PipelineEvent.UPDATE_STARTED.value)
        candidate: Optional[Snapshot] = None

        try:
            # Step 1: Fork candidate snapshot
            candidate = self.manager.begin_candidate(new_commit_id)
            audit.events.append(PipelineEvent.FILES_CHANGED.value)
            audit.changed_files_count = len(file_diffs)

            all_symbol_deltas = []

            # Step 2: Process each changed file
            for diff in file_diffs:
                file_uri = build_entity_uri(self.manager.repo_id, diff.file_path)

                if diff.change_type == ChangeClassification.DELETED:
                    # Remove file entity and attached symbols
                    candidate.remove_entity(file_uri)
                    sym_deltas = SymbolDeltaEngine.compute_file_symbol_delta(diff.file_path, diff.old_blob, None)
                    all_symbol_deltas.extend(sym_deltas)
                elif diff.change_type in (ChangeClassification.ADDED, ChangeClassification.MODIFIED):
                    # Upsert file entity
                    candidate.add_entity(
                        SnapshotEntity(
                            entity_key=file_uri,
                            repo_id=self.manager.repo_id,
                            file_path=diff.file_path,
                            name=diff.file_path.split("/")[-1],
                            entity_type="FILE",
                        )
                    )
                    sym_deltas = SymbolDeltaEngine.compute_file_symbol_delta(
                        diff.file_path, diff.old_blob, diff.new_blob
                    )
                    all_symbol_deltas.extend(sym_deltas)

            audit.events.append(PipelineEvent.AST_BUILT.value)
            audit.events.append(PipelineEvent.SYMBOL_DELTA_READY.value)
            audit.changed_symbols_count = len(all_symbol_deltas)

            # Step 3: Apply symbol deltas
            for sym_d in all_symbol_deltas:
                sym_uri = build_entity_uri(self.manager.repo_id, sym_d.file_path, sym_d.symbol_name)
                file_uri = build_entity_uri(self.manager.repo_id, sym_d.file_path)

                if sym_d.delta_type == SymbolDeltaType.SYMBOL_DELETED:
                    candidate.remove_entity(sym_uri)
                elif sym_d.delta_type in (
                    SymbolDeltaType.SYMBOL_ADDED,
                    SymbolDeltaType.SYMBOL_MODIFIED,
                    SymbolDeltaType.SIGNATURE_CHANGED,
                ):
                    candidate.add_entity(
                        SnapshotEntity(
                            entity_key=sym_uri,
                            repo_id=self.manager.repo_id,
                            file_path=sym_d.file_path,
                            name=sym_d.symbol_name,
                            entity_type=sym_d.kind,
                            signature=sym_d.new_signature,
                        )
                    )
                    # Add CONTAINS edge from file to symbol
                    e_key = build_edge_key(file_uri, "CONTAINS", sym_uri)
                    candidate.add_edge(
                        SnapshotEdge(
                            edge_key=e_key,
                            source_key=file_uri,
                            predicate="CONTAINS",
                            target_key=sym_uri,
                        )
                    )

            # Step 4: Apply relationship deltas & stale edge pruning
            edge_deltas = RelationshipDeltaEngine.compute_edge_deltas(
                candidate, all_symbol_deltas, self.manager.repo_id
            )
            audit.events.append(PipelineEvent.EDGE_DELTA_READY.value)

            for ed in edge_deltas:
                if ed.delta_type == EdgeDeltaType.EDGE_DELETED:
                    candidate.remove_edge(ed.edge_key)
                    audit.deleted_edges_count += 1
                elif ed.delta_type == EdgeDeltaType.EDGE_ADDED:
                    candidate.add_edge(
                        SnapshotEdge(
                            edge_key=ed.edge_key,
                            source_key=ed.source_key,
                            predicate=ed.predicate,
                            target_key=ed.target_key,
                        )
                    )
                    audit.added_edges_count += 1

            audit.events.append(PipelineEvent.INDEX_UPDATED.value)

            # Step 5: Validation pipeline
            audit.events.append(PipelineEvent.VALIDATION_STARTED.value)
            stale_rate = RelationshipDeltaEngine.validate_stale_edges(candidate)
            audit.stale_edge_rate = stale_rate

            if force_fail_validation or stale_rate > 0.0 or not self.manager.validate_candidate(candidate):
                raise ValueError(f"Consistency validation failed. Stale edge rate: {stale_rate}")

            audit.events.append(PipelineEvent.VALIDATION_PASSED.value)

            # Step 6: Atomic publish
            self.manager.publish_atomic(candidate)
            audit.events.append(PipelineEvent.SNAPSHOT_PUBLISHED.value)
            audit.status = "SUCCESS"

        except Exception as exc:
            # Rollback: Discard candidate snapshot and keep current untouched
            audit.events.append(PipelineEvent.UPDATE_FAILED.value)
            if candidate:
                self.manager.rollback(candidate)
            audit.events.append(PipelineEvent.ROLLBACK_COMPLETED.value)
            audit.status = f"FAILED: {str(exc)}"

        audit.latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return audit
