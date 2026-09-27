"""Independent Oracle for Tested Canonical State Subset (Stage 1 G1.8 Hard Gate).

Architectural Rule:
The Independent Oracle MUST NOT share code, AST traversal, or delta logic with the
production Incremental Indexing Engine. It exists solely as an adversarial, independent
verifier to guarantee that incremental state transitions never reproduce or mask
engine-internal extraction bugs.

Scope & Boundary Notice:
This Oracle strictly validates the fundamental structural subset:
- Canonical Entities: FILE, CLASS, INTERFACE, METHOD
- Canonical Relations: CONTAINS (lexical container hierarchy)
It intentionally does NOT assert or attempt full reproduction of complex graph semantics
(e.g., cross-file IMPORTS, CALLS, EXTENDS, REST API routes, DTO lineage, or Vue template bindings),
which are validated by dedicated Stage 2 multi-repo contract and graph traversal test suites.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set
from core.state.snapshot import Snapshot


@dataclass(frozen=True)
class CanonicalNode:
    entity_key: str
    kind: str
    signature: str
    file_path: str


@dataclass(frozen=True)
class CanonicalEdge:
    edge_key: str
    source_key: str
    predicate: str
    target_key: str


@dataclass
class CanonicalGraph:
    repo_id: str
    nodes: Dict[str, CanonicalNode] = field(default_factory=dict)
    edges: Dict[str, CanonicalEdge] = field(default_factory=dict)


@dataclass
class IndependentAuditReport:
    gate_id: str = "G1.8_INDEPENDENT_ORACLE"
    passed: bool = False
    node_precision: float = 0.0
    node_recall: float = 0.0
    edge_precision: float = 0.0
    edge_recall: float = 0.0
    stale_edges_count: int = 0
    discrepancies: List[str] = field(default_factory=list)


class IndependentOracle:
    """Independent canonical state extractor and mathematical verifier."""

    @classmethod
    def build_canonical_graph(cls, repo_id: str, file_blobs: Dict[str, str]) -> CanonicalGraph:
        """Independently extracts canonical nodes and edges directly from raw source texts.
        Uses clean-room independent parsing logic completely isolated from SymbolDeltaEngine.
        """
        graph = CanonicalGraph(repo_id=repo_id)

        for file_path, code in file_blobs.items():
            file_key = f"repo://{repo_id}/{file_path}"
            # 1. Canonical file node
            graph.nodes[file_key] = CanonicalNode(
                entity_key=file_key,
                kind="FILE",
                signature=f"file:{file_path}",
                file_path=file_path,
            )

            # 2. Independent class / interface extractor
            # Clean pattern matching independent of production delta regex
            class_iter = re.finditer(
                r"\b(?:public\s+|export\s+|default\s+)*(?:class|interface)\s+([A-Za-z0-9_]+)",
                code,
            )
            for m in class_iter:
                sym_name = m.group(1)
                sym_key = f"repo://{repo_id}/{file_path}#{sym_name}"
                full_sig = m.group(0).strip()
                graph.nodes[sym_key] = CanonicalNode(
                    entity_key=sym_key,
                    kind="CLASS",
                    signature=full_sig,
                    file_path=file_path,
                )
                edge_key = f"edge://{file_key}->CONTAINS->{sym_key}"
                graph.edges[edge_key] = CanonicalEdge(
                    edge_key=edge_key,
                    source_key=file_key,
                    predicate="CONTAINS",
                    target_key=sym_key,
                )

            # 3. Independent method / function extractor
            method_iter = re.finditer(
                r"\b(?:public|private|protected|async|function)?\s*(?:[A-Za-z0-9_<>[\]]+\s+)?([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?::\s*[A-Za-z0-9_<>[\]]+)?\s*\{",
                code,
            )
            for m in method_iter:
                func_name = m.group(1)
                if func_name in ("if", "for", "while", "switch", "catch", "class", "interface"):
                    continue
                args = m.group(2).strip()
                sym_key = f"repo://{repo_id}/{file_path}#{func_name}"
                sig = f"{func_name}({args})"
                graph.nodes[sym_key] = CanonicalNode(
                    entity_key=sym_key,
                    kind="METHOD",
                    signature=sig,
                    file_path=file_path,
                )
                edge_key = f"edge://{file_key}->CONTAINS->{sym_key}"
                graph.edges[edge_key] = CanonicalEdge(
                    edge_key=edge_key,
                    source_key=file_key,
                    predicate="CONTAINS",
                    target_key=sym_key,
                )

        return graph

    @classmethod
    def audit_snapshot_against_canonical(
        cls,
        snapshot: Snapshot,
        canonical: CanonicalGraph,
    ) -> IndependentAuditReport:
        """Verifies candidate or incremental snapshot against the independent canonical state."""
        discrepancies = []

        snap_node_keys = set(snapshot.entities.keys())
        canon_node_keys = set(canonical.nodes.keys())

        missing_nodes = canon_node_keys - snap_node_keys
        extra_nodes = snap_node_keys - canon_node_keys

        if missing_nodes:
            discrepancies.append(f"Missing canonical nodes in snapshot: {sorted(list(missing_nodes))}")
        if extra_nodes:
            discrepancies.append(f"Unexpected extra nodes in snapshot: {sorted(list(extra_nodes))}")

        snap_edge_keys = set(snapshot.edges.keys())
        canon_edge_keys = set(canonical.edges.keys())

        missing_edges = canon_edge_keys - snap_edge_keys
        extra_edges = snap_edge_keys - canon_edge_keys

        # Check for stale dangling edges (edges whose endpoints don't exist in canonical)
        stale_edges = 0
        for e_key in snap_edge_keys:
            e = snapshot.edges[e_key]
            if e.source_key not in canon_node_keys or e.target_key not in canon_node_keys:
                stale_edges += 1
                discrepancies.append(f"Stale dangling edge discovered: {e_key}")

        node_recall = (
            len(canon_node_keys & snap_node_keys) / len(canon_node_keys) if canon_node_keys else 1.0
        )
        node_prec = (
            len(canon_node_keys & snap_node_keys) / len(snap_node_keys) if snap_node_keys else 1.0
        )
        edge_recall = (
            len(canon_edge_keys & snap_edge_keys) / len(canon_edge_keys) if canon_edge_keys else 1.0
        )
        edge_prec = (
            len(canon_edge_keys & snap_edge_keys) / len(snap_edge_keys) if snap_edge_keys else 1.0
        )

        passed = (
            len(missing_nodes) == 0
            and len(extra_nodes) == 0
            and len(missing_edges) == 0
            and len(extra_edges) == 0
            and stale_edges == 0
        )

        return IndependentAuditReport(
            gate_id="G1.8_INDEPENDENT_ORACLE",
            passed=passed,
            node_precision=round(node_prec, 4),
            node_recall=round(node_recall, 4),
            edge_precision=round(edge_prec, 4),
            edge_recall=round(edge_recall, 4),
            stale_edges_count=stale_edges,
            discrepancies=discrepancies,
        )
