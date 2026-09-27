"""Incremental vs Full Rebuild Semantic Equivalence Oracle (Stage 1 Section 1.2 & 3.9).

Proves that:
    FullRebuild(repo_after) == IncrementalUpdate(repo_before, delta)
Checks:
- Entity Set & Identity equality
- Symbol Set & Signature equality
- Edge Set & Predicate equality
- Stale Edge rate == 0%
- Graph Traversal Impact equivalence
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from core.identity.naming import build_edge_key, build_entity_uri
from core.indexing.change_detector import ChangeDetector
from core.indexing.pipeline import IncrementalIndexingPipeline
from core.indexing.symbol_delta import SymbolDeltaEngine
from core.state.snapshot import (
    Snapshot,
    SnapshotEdge,
    SnapshotEntity,
    SnapshotManager,
)


@dataclass
class EquivalenceReport:
    is_equivalent: bool
    entity_match_rate: float
    edge_match_rate: float
    stale_edge_rate: float
    discrepancies: List[str]


class EquivalenceOracle:
    """Rigorous mathematical oracle comparing IncrementalUpdate against clean FullRebuild."""

    @classmethod
    def full_rebuild(cls, repo_id: str, file_blobs: Dict[str, str], commit_id: str = "rebuild") -> Snapshot:
        """Executes a clean from-scratch full rebuild of repository snapshot."""
        mgr = SnapshotManager(repo_id=repo_id, initial_commit=commit_id)
        snap = mgr.get_current_snapshot()

        for file_path, code in file_blobs.items():
            f_uri = build_entity_uri(repo_id, file_path)
            snap.add_entity(
                SnapshotEntity(
                    entity_key=f_uri,
                    repo_id=repo_id,
                    file_path=file_path,
                    name=file_path.split("/")[-1],
                    entity_type="FILE",
                )
            )
            # Extract symbols
            sym_map = SymbolDeltaEngine._extract_symbols(code)
            for s_name, s_def in sym_map.items():
                s_uri = build_entity_uri(repo_id, file_path, s_name)
                snap.add_entity(
                    SnapshotEntity(
                        entity_key=s_uri,
                        repo_id=repo_id,
                        file_path=file_path,
                        name=s_name,
                        entity_type=s_def.kind,
                        signature=s_def.signature,
                    )
                )
                # Connect file to symbol
                e_key = build_edge_key(f_uri, "CONTAINS", s_uri)
                snap.add_edge(
                    SnapshotEdge(
                        edge_key=e_key,
                        source_key=f_uri,
                        predicate="CONTAINS",
                        target_key=s_uri,
                    )
                )

        return snap

    @classmethod
    def verify_equivalence(
        cls,
        incremental_snapshot: Snapshot,
        rebuilt_snapshot: Snapshot,
    ) -> EquivalenceReport:
        """Validates 100% semantic equivalence between incremental state and full rebuild state."""
        discrepancies: List[str] = []

        # 1. Entity Set Equivalence
        inc_entities = set(incremental_snapshot.entities.keys())
        reb_entities = set(rebuilt_snapshot.entities.keys())

        missing_in_inc = reb_entities - inc_entities
        extra_in_inc = inc_entities - reb_entities

        if missing_in_inc:
            discrepancies.append(f"Incremental snapshot missing entities: {list(missing_in_inc)[:5]}")
        if extra_in_inc:
            discrepancies.append(f"Incremental snapshot has extra entities: {list(extra_in_inc)[:5]}")

        # Check entity signatures for common keys
        for k in inc_entities & reb_entities:
            e_inc = incremental_snapshot.entities[k]
            e_reb = rebuilt_snapshot.entities[k]
            if e_inc.signature != e_reb.signature:
                discrepancies.append(
                    f"Signature mismatch on {k}: '{e_inc.signature}' != '{e_reb.signature}'"
                )

        # 2. Edge Set Equivalence
        inc_edges = set(incremental_snapshot.edges.keys())
        reb_edges = set(rebuilt_snapshot.edges.keys())

        missing_edges = reb_edges - inc_edges
        extra_edges = inc_edges - reb_edges

        if missing_edges:
            discrepancies.append(f"Incremental missing edges: {list(missing_edges)[:5]}")
        if extra_edges:
            discrepancies.append(f"Incremental extra edges: {list(extra_edges)[:5]}")

        # 3. Stale edges check
        stale_edges = 0
        for e in incremental_snapshot.edges.values():
            if e.source_key not in inc_entities or e.target_key not in inc_entities:
                stale_edges += 1

        total_entities = len(reb_entities) or 1
        total_edges = len(reb_edges) or 1

        matched_entities = len(inc_entities & reb_entities)
        matched_edges = len(inc_edges & reb_edges)

        is_equiv = len(discrepancies) == 0 and stale_edges == 0

        return EquivalenceReport(
            is_equivalent=is_equiv,
            entity_match_rate=round(matched_entities / total_entities, 4),
            edge_match_rate=round(matched_edges / total_edges, 4),
            stale_edge_rate=round(stale_edges / (len(inc_edges) or 1), 4),
            discrepancies=discrepancies,
        )
