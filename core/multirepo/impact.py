"""Cross-Repository Impact Analysis Engine (Stage 2 Section 4.7 & 4.8).

Traverses impact blast radius across multi-repository topologies:
- End-to-end provenance: Backend DTO -> Controller -> API Contract -> Frontend Client -> Component
- Multi-Repo Invariant 1: Cycle-safety across repo loops (termination = 100%, depth violation = 0)
- Multi-Repo Invariant 4: Shortest-hop preservation across cross-repo alternate paths
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from core.multirepo.models import CrossRepoEdge, EvidenceLevel


@dataclass
class CrossRepoImpactNode:
    entity_key: str
    repo_id: str
    depth: int
    impact_level: str  # DIRECT, INDIRECT, POTENTIAL
    evidence_sources: List[str] = field(default_factory=list)


@dataclass
class CrossRepoImpactResult:
    seed_keys: List[str]
    max_depth: int
    affected_nodes: Dict[str, CrossRepoImpactNode]
    evidence_paths: List[List[str]]
    visited_sequence: List[str]
    is_cycle_safe: bool = True
    depth_violation_count: int = 0


class CrossRepoImpactAnalyzer:
    """Bounded, cycle-safe shortest-path graph impact analyzer across repository boundaries."""

    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth

    def analyze_cross_repo_impact(
        self,
        seed_keys: List[str],
        edges: List[CrossRepoEdge],
    ) -> CrossRepoImpactResult:
        """Executes shortest-path BFS traversal honoring cycle invariants across repos."""
        # 1. Build adjacency list
        adj: Dict[str, List[CrossRepoEdge]] = {}
        for e in edges:
            adj.setdefault(e.source_entity, []).append(e)

        affected: Dict[str, CrossRepoImpactNode] = {}
        evidence_paths: List[List[str]] = []
        visited_sequence: List[str] = []
        queue: deque[Tuple[str, int, List[str]]] = deque()

        # Initialize queue with seeds at depth 0
        for s in seed_keys:
            queue.append((s, 0, [s]))

        while queue:
            curr_key, curr_depth, curr_path = queue.popleft()
            visited_sequence.append(curr_key)

            if curr_depth >= self.max_depth:
                continue

            for edge in adj.get(curr_key, []):
                nxt_key = edge.target_entity
                nxt_depth = curr_depth + 1
                nxt_path = curr_path + [f"{edge.edge_type}:{edge.target_repo}", nxt_key]

                # Assign impact level based on depth
                level = "DIRECT" if nxt_depth == 1 else ("INDIRECT" if nxt_depth == 2 else "POTENTIAL")

                if nxt_key not in affected:
                    # First discovery: this is the shortest hop in BFS
                    affected[nxt_key] = CrossRepoImpactNode(
                        entity_key=nxt_key,
                        repo_id=edge.target_repo,
                        depth=nxt_depth,
                        impact_level=level,
                        evidence_sources=[edge.edge_key],
                    )
                    evidence_paths.append(nxt_path)
                    queue.append((nxt_key, nxt_depth, nxt_path))
                else:
                    # Invariant 4 Defense: Shortest-Hop Preservation
                    existing = affected[nxt_key]
                    if nxt_depth < existing.depth:
                        # Relaxation to shorter path
                        existing.depth = nxt_depth
                        existing.impact_level = level
                    # Accumulate multi-path evidence
                    if edge.edge_key not in existing.evidence_sources:
                        existing.evidence_sources.append(edge.edge_key)

        # Check for depth boundary violations
        depth_violations = sum(1 for node in affected.values() if node.depth > self.max_depth)

        return CrossRepoImpactResult(
            seed_keys=seed_keys,
            max_depth=self.max_depth,
            affected_nodes=affected,
            evidence_paths=evidence_paths,
            visited_sequence=visited_sequence,
            is_cycle_safe=True,
            depth_violation_count=depth_violations,
        )
