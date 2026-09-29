"""Repository State & Snapshot Abstraction (Stage 1 Section 3.7 & Section 7.2).

Implements:
- SnapshotStatus: BUILDING, VALIDATING, PUBLISHED, FAILED, DISCARDED
- SnapshotMetadata
- Immutable Repository Snapshot with Copy-on-Write cloning
- Thread-safe SnapshotManager with Atomic Publish and Zero-Downtime SWMR semantics
"""

import copy
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from core.identity.naming import build_edge_key, build_entity_uri


class SnapshotStatus(str, Enum):
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DISCARDED = "DISCARDED"


@dataclass
class SnapshotMetadata:
    snapshot_id: str
    repo_id: str
    branch: str = "master"
    commit_id: str = "HEAD"
    parent_snapshot_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    status: SnapshotStatus = SnapshotStatus.BUILDING
    graph_revision: int = 1
    retrieval_revision: int = 1


@dataclass
class SnapshotEntity:
    entity_key: str
    repo_id: str
    file_path: str
    name: str
    entity_type: str
    signature: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotEdge:
    edge_key: str
    source_key: str
    predicate: str
    target_key: str
    confidence: float = 1.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)


class Snapshot:
    """An isolated snapshot of the repository intelligence graph and symbols."""

    def __init__(self, metadata: SnapshotMetadata):
        self.metadata = metadata
        self.entities: Dict[str, SnapshotEntity] = {}
        self.edges: Dict[str, SnapshotEdge] = {}
        # Inbound and outbound adjacency indices
        self.out_edges: Dict[str, Set[str]] = {}
        self.in_edges: Dict[str, Set[str]] = {}

    def clone_candidate(self, new_commit_id: str) -> "Snapshot":
        """Copy-on-write clone to produce a candidate snapshot."""
        candidate_meta = SnapshotMetadata(
            snapshot_id=f"snap_{uuid.uuid4().hex[:8]}",
            repo_id=self.metadata.repo_id,
            branch=self.metadata.branch,
            commit_id=new_commit_id,
            parent_snapshot_id=self.metadata.snapshot_id,
            status=SnapshotStatus.BUILDING,
            graph_revision=self.metadata.graph_revision + 1,
            retrieval_revision=self.metadata.retrieval_revision + 1,
        )
        candidate = Snapshot(candidate_meta)
        candidate.entities = copy.deepcopy(self.entities)
        candidate.edges = copy.deepcopy(self.edges)
        candidate.out_edges = {k: set(v) for k, v in self.out_edges.items()}
        candidate.in_edges = {k: set(v) for k, v in self.in_edges.items()}
        return candidate

    def add_entity(self, entity: SnapshotEntity) -> None:
        self.entities[entity.entity_key] = entity

    def remove_entity(self, entity_key: str) -> Optional[SnapshotEntity]:
        entity = self.entities.pop(entity_key, None)
        # Purge attached edges
        out_e = list(self.out_edges.get(entity_key, set()))
        in_e = list(self.in_edges.get(entity_key, set()))
        for e_key in out_e + in_e:
            self.remove_edge(e_key)
        return entity

    def add_edge(self, edge: SnapshotEdge) -> None:
        self.edges[edge.edge_key] = edge
        self.out_edges.setdefault(edge.source_key, set()).add(edge.edge_key)
        self.in_edges.setdefault(edge.target_key, set()).add(edge.edge_key)

    def remove_edge(self, edge_key: str) -> Optional[SnapshotEdge]:
        edge = self.edges.pop(edge_key, None)
        if edge:
            if edge.source_key in self.out_edges:
                self.out_edges[edge.source_key].discard(edge_key)
            if edge.target_key in self.in_edges:
                self.in_edges[edge.target_key].discard(edge_key)
        return edge


class SnapshotManager:
    """Thread-safe manager enforcing Atomic Publish, Zero-Downtime SWMR, Rollback and Bounded Retention."""

    def __init__(self, repo_id: str, initial_commit: str = "init", max_history_snapshots: int = 50):
        self.repo_id = repo_id
        self.max_history_snapshots = max_history_snapshots
        initial_meta = SnapshotMetadata(
            snapshot_id=f"snap_{uuid.uuid4().hex[:8]}",
            repo_id=repo_id,
            commit_id=initial_commit,
            status=SnapshotStatus.PUBLISHED,
        )
        self._current_snapshot = Snapshot(initial_meta)
        self._base_snapshot_id = self._current_snapshot.metadata.snapshot_id
        self._history: Dict[str, Snapshot] = {self._base_snapshot_id: self._current_snapshot}
        self._history_order: List[str] = [self._base_snapshot_id]
        self._lock = threading.RLock()
        self._active_candidate: Optional[Snapshot] = None

    @property
    def history_count(self) -> int:
        with self._lock:
            return len(self._history)

    def get_current_snapshot(self) -> Snapshot:
        """Lock-free atomic read of published snapshot (readers never block on writers)."""
        return self._current_snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        with self._lock:
            return self._history.get(snapshot_id)

    def begin_candidate(self, commit_id: str) -> Snapshot:
        """Starts a candidate snapshot for incremental delta updates."""
        with self._lock:
            if self._active_candidate and self._active_candidate.metadata.status in (
                SnapshotStatus.BUILDING,
                SnapshotStatus.VALIDATING,
            ):
                raise RuntimeError("Another incremental update candidate is already in progress.")
            self._active_candidate = self._current_snapshot.clone_candidate(commit_id)
            return self._active_candidate

    def validate_candidate(self, candidate: Snapshot) -> bool:
        """Validates structural and graph invariants on candidate before publish."""
        with self._lock:
            candidate.metadata.status = SnapshotStatus.VALIDATING

            # 1. Stale edge check: verify every edge connects existing entities
            for edge in candidate.edges.values():
                if edge.source_key not in candidate.entities or edge.target_key not in candidate.entities:
                    candidate.metadata.status = SnapshotStatus.FAILED
                    return False

            # 2. Cycle-safety check: verify no self-referential corruption
            for edge in candidate.edges.values():
                if edge.source_key == edge.target_key and edge.predicate == "EXTENDS":
                    candidate.metadata.status = SnapshotStatus.FAILED
                    return False

            return True

    def publish_atomic(self, candidate: Snapshot) -> None:
        """Atomically switches the current published snapshot pointer and applies retention bounds."""
        with self._lock:
            if candidate.metadata.status != SnapshotStatus.VALIDATING:
                raise RuntimeError("Candidate snapshot must be VALIDATING before atomic publish.")

            candidate.metadata.status = SnapshotStatus.PUBLISHED
            self._current_snapshot = candidate
            self._history[candidate.metadata.snapshot_id] = candidate
            self._history_order.append(candidate.metadata.snapshot_id)
            self._active_candidate = None
            self._apply_retention_policy()

    def _apply_retention_policy(self) -> int:
        """Enforces sliding-window retention policy to prevent unbounded memory growth."""
        if self.max_history_snapshots <= 0:
            return 0
        pruned_count = 0
        # Retain base snapshot (at index 0) + up to max_history_snapshots recent snapshots
        while len(self._history_order) > self.max_history_snapshots + 1:
            # Evict the oldest non-base snapshot (index 1)
            oldest_id = self._history_order.pop(1)
            self._history.pop(oldest_id, None)
            pruned_count += 1
        return pruned_count

    def prune_history(self, keep_last_n: int = 10) -> int:
        """Explicitly prunes snapshot history, preserving the baseline snapshot and recent N snapshots."""
        with self._lock:
            old_limit = self.max_history_snapshots
            self.max_history_snapshots = max(1, keep_last_n)
            pruned = self._apply_retention_policy()
            self.max_history_snapshots = old_limit
            return pruned

    def rollback(self, candidate: Optional[Snapshot] = None) -> None:
        """Discards active candidate snapshot; current snapshot remains 100% untouched."""
        with self._lock:
            target = candidate or self._active_candidate
            if target:
                target.metadata.status = SnapshotStatus.DISCARDED
            self._active_candidate = None
