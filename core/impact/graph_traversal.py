"""Impact Graph Traversal Engine for MVP7
Executes cycle-safe BFS traversal (1~3 hops) to trace affected nodes and paths.
"""

from collections import deque
from typing import Any
import uuid

from core.impact.models import (
    EvidenceKind,
    ImpactEdge,
    ImpactHopLevel,
    ImpactNode,
    ImpactPath,
)


class GraphTraversalError(Exception):
    pass


class ImpactGraphTraversal:
    """Cycle-safe multi-hop BFS traversal over knowledge graph relationships."""

    def __init__(self, max_depth: int = 3):
        self.max_depth = min(3, max(1, max_depth))

    def traverse(
        self,
        seed_keys: list[str],
        entities_by_key: dict[str, dict[str, Any]],
        relations: list[dict[str, Any]],
        direction: str = "both",  # "downstream", "upstream", "both"
    ) -> tuple[list[ImpactNode], list[ImpactPath]]:
        """Traverses the graph starting from seed_keys up to max_depth.
        Returns:
            affected_nodes: list of reached ImpactNodes
            impact_paths: list of full ImpactPaths from seeds
        """
        # Build adjacency maps
        # Forward: subject -> list of (object, rel)
        # Backward: object -> list of (subject, rel)
        adj_forward: dict[str, list[dict[str, Any]]] = {}
        adj_backward: dict[str, list[dict[str, Any]]] = {}

        for r in relations:
            sub = r.get("subject_key")
            obj = r.get("object_key")
            if sub and obj:
                adj_forward.setdefault(sub, []).append(r)
                adj_backward.setdefault(obj, []).append(r)

        visited: set[str] = set(seed_keys)
        # Queue item: (current_key, current_depth, path_nodes, path_edges)
        queue: deque[tuple[str, int, list[str], list[ImpactEdge]]] = deque()

        for seed in seed_keys:
            queue.append((seed, 0, [seed], []))

        affected_nodes_map: dict[str, ImpactNode] = {}
        all_paths: list[ImpactPath] = []

        while queue:
            curr_key, depth, path_nodes, path_edges = queue.popleft()

            if depth >= self.max_depth:
                continue

            next_depth = depth + 1
            hop_level = (
                ImpactHopLevel.DIRECT
                if next_depth == 1
                else (ImpactHopLevel.INDIRECT if next_depth == 2 else ImpactHopLevel.POTENTIAL)
            )

            # Discover neighbors according to direction
            candidate_edges: list[tuple[str, dict[str, Any]]] = []

            # In software changes, callers/importers are directly affected (backward traversal)
            if direction in ("downstream", "both"):
                for rel in adj_backward.get(curr_key, []):
                    caller_key = rel.get("subject_key")
                    if caller_key:
                        candidate_edges.append((caller_key, rel))

            # Outgoing dependencies (forward traversal)
            if direction in ("upstream", "both"):
                for rel in adj_forward.get(curr_key, []):
                    callee_key = rel.get("object_key")
                    if callee_key:
                        candidate_edges.append((callee_key, rel))

            for neighbor_key, rel in candidate_edges:
                edge_conf = float(rel.get("confidence", 1.0))
                rel_type = rel.get("relation_type", "DEPENDS_ON")
                edge = ImpactEdge(
                    source_key=rel.get("subject_key", curr_key),
                    target_key=rel.get("object_key", neighbor_key),
                    relation_type=rel_type,
                    confidence=edge_conf,
                    evidence_kind=EvidenceKind.CODE_RELATION,
                    evidence_details={"relation_id": rel.get("id"), "method": rel.get("method")},
                )

                new_nodes = path_nodes + [neighbor_key]
                new_edges = path_edges + [edge]

                # Compute cumulative path confidence (product of edge confidences * decay)
                decay = 0.95 ** (next_depth - 1)
                cum_conf = round(min(1.0, edge_conf * decay), 4)

                path = ImpactPath(
                    nodes=new_nodes,
                    edges=new_edges,
                    hops=next_depth,
                    path_confidence=cum_conf,
                    evidence_count=len(new_edges),
                    description=f"{' -> '.join(new_nodes)} ({next_depth} hops)",
                )
                all_paths.append(path)

                if neighbor_key not in affected_nodes_map and neighbor_key not in seed_keys:
                    ent_info = entities_by_key.get(neighbor_key, {})
                    node = ImpactNode(
                        entity_key=neighbor_key,
                        name=ent_info.get("name", neighbor_key.split(":")[-1]),
                        entity_type=ent_info.get("entity_type", "UNKNOWN"),
                        project_key=ent_info.get("project_key", neighbor_key.split(":")[1] if ":" in neighbor_key else "UNKNOWN"),
                        path=ent_info.get("path"),
                        hop=next_depth,
                        level=hop_level,
                        evidence_sources=[rel_type],
                    )
                    affected_nodes_map[neighbor_key] = node

                if neighbor_key not in visited:
                    visited.add(neighbor_key)
                    queue.append((neighbor_key, next_depth, new_nodes, new_edges))

        return list(affected_nodes_map.values()), all_paths
