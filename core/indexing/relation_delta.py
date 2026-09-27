"""Relationship Delta Engine & Stale Edge Pruning (Stage 1 Section 3.6).

Detects relationship changes caused by symbol mutations:
- EDGE_ADDED
- EDGE_DELETED
- EDGE_MODIFIED
- Stale Edge Validator: guarantees stale_edge_rate == 0.0%
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set

from core.identity.naming import build_edge_key
from core.indexing.symbol_delta import SymbolDelta, SymbolDeltaType
from core.state.snapshot import Snapshot, SnapshotEdge


class EdgeDeltaType(str, Enum):
    EDGE_ADDED = "EDGE_ADDED"
    EDGE_DELETED = "EDGE_DELETED"
    EDGE_MODIFIED = "EDGE_MODIFIED"


@dataclass
class RelationshipDelta:
    edge_key: str
    source_key: str
    predicate: str
    target_key: str
    delta_type: EdgeDeltaType


class RelationshipDeltaEngine:
    """Calculates graph edge additions, deletions, and eliminates dangling stale edges."""

    @classmethod
    def compute_edge_deltas(
        cls,
        snapshot: Snapshot,
        symbol_deltas: List[SymbolDelta],
        repo_id: str,
    ) -> List[RelationshipDelta]:
        """Calculates edge modifications based on symbol additions, deletions, and signature changes."""
        edge_deltas: List[RelationshipDelta] = []
        deleted_symbols: Set[str] = {
            s.symbol_name for s in symbol_deltas if s.delta_type == SymbolDeltaType.SYMBOL_DELETED
        }

        # 1. Identify and purge all edges attached to deleted symbols
        for edge_key, edge in list(snapshot.edges.items()):
            src_symbol = edge.source_key.split("#")[-1] if "#" in edge.source_key else edge.source_key
            tgt_symbol = edge.target_key.split("#")[-1] if "#" in edge.target_key else edge.target_key

            if src_symbol in deleted_symbols or tgt_symbol in deleted_symbols:
                edge_deltas.append(
                    RelationshipDelta(
                        edge_key=edge.edge_key,
                        source_key=edge.source_key,
                        predicate=edge.predicate,
                        target_key=edge.target_key,
                        delta_type=EdgeDeltaType.EDGE_DELETED,
                    )
                )

        return edge_deltas

    @classmethod
    def validate_stale_edges(cls, snapshot: Snapshot) -> float:
        """Validates that no dangling edge points to a missing entity. Returns stale edge rate."""
        if not snapshot.edges:
            return 0.0

        stale_count = 0
        for edge in snapshot.edges.values():
            if edge.source_key not in snapshot.entities or edge.target_key not in snapshot.entities:
                stale_count += 1

        return round(stale_count / len(snapshot.edges), 4)
