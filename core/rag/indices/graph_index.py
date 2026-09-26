"""LKIO Graph Index
Provides graph adjacency traversals, k-hop neighbor expansion, and API contract traceability queries.
"""

from typing import Any
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    IndexType,
    RetrievalCandidate,
)


class GraphIndex:
    """In-memory graph adjacency index for structural and API relationships."""

    def __init__(self) -> None:
        # subject_key -> list of outgoing relations
        self._out_edges: dict[str, list[dict[str, Any]]] = {}
        # object_key -> list of incoming relations
        self._in_edges: dict[str, list[dict[str, Any]]] = {}
        # relation_key -> relation record
        self._by_relation_key: dict[str, dict[str, Any]] = {}

        # API routes: normalized_path -> list of api traces
        self._api_routes: dict[str, list[dict[str, Any]]] = {}

    def add_relation(
        self,
        relation_key: str,
        subject_key: str,
        predicate: str,
        project_key: str,
        object_key: str | None = None,
        raw_target: str | None = None,
        confidence: float = 1.0,
        file_path: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes a structural relationship edge."""
        rec = {
            "relation_key": relation_key,
            "subject_key": subject_key,
            "predicate": predicate,
            "object_key": object_key,
            "raw_target": raw_target,
            "project_key": project_key,
            "confidence": confidence,
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "metadata": metadata or {},
        }
        self._by_relation_key[relation_key] = rec
        self._out_edges.setdefault(subject_key, []).append(rec)
        if object_key:
            self._in_edges.setdefault(object_key, []).append(rec)

    def add_api_trace(
        self,
        trace_id: str,
        http_method: str,
        http_path: str,
        frontend_call_site: str,
        frontend_project: str,
        backend_controller: str | None = None,
        backend_service: str | None = None,
        backend_project: str | None = None,
        file_path: str | None = None,
        start_line: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes an API frontend-to-backend contract trace."""
        norm_path = http_path.strip().lower()
        rec = {
            "trace_id": trace_id,
            "http_method": http_method.upper(),
            "http_path": http_path,
            "norm_path": norm_path,
            "frontend_call_site": frontend_call_site,
            "frontend_project": frontend_project,
            "backend_controller": backend_controller,
            "backend_service": backend_service,
            "backend_project": backend_project,
            "file_path": file_path,
            "start_line": start_line,
            "metadata": metadata or {},
        }
        self._api_routes.setdefault(norm_path, []).append(rec)

    def get_neighbors(
        self,
        entity_key: str,
        direction: str = "both",
        predicates: list[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Gets 1-hop connected neighbors (incoming, outgoing, or both)."""
        candidates: list[RetrievalCandidate] = []
        seen_keys: set[str] = set()

        # Outgoing
        if direction in ("out", "both"):
            for edge in self._out_edges.get(entity_key, []):
                if predicates and edge["predicate"] not in predicates:
                    continue
                target = edge["object_key"] or edge["raw_target"] or "unknown"
                edge_id = f"out:{edge['relation_key']}"
                if edge_id in seen_keys:
                    continue
                seen_keys.add(edge_id)

                ev = EvidenceCitation(
                    evidence_type=EvidenceType.GRAPH_EDGE,
                    project_key=edge["project_key"],
                    file_path=edge["file_path"] or "",
                    start_line=edge["start_line"],
                    end_line=edge["end_line"],
                    entity_key=edge["subject_key"],
                    relation_key=edge["relation_key"],
                    confidence=edge["confidence"],
                )
                candidates.append(
                    RetrievalCandidate(
                        id=f"graph:{edge_id}",
                        score=0.9,
                        source_index=IndexType.GRAPH,
                        project_key=edge["project_key"],
                        name=target,
                        title=f"{edge['subject_key']} --[{edge['predicate']}]--> {target}",
                        summary=f"Relation '{edge['predicate']}' from {edge['subject_key']} to {target}",
                        file_path=edge["file_path"],
                        entity_key=edge["object_key"],
                        evidence=ev,
                        metadata=edge["metadata"],
                    )
                )

        # Incoming
        if direction in ("in", "both"):
            for edge in self._in_edges.get(entity_key, []):
                if predicates and edge["predicate"] not in predicates:
                    continue
                edge_id = f"in:{edge['relation_key']}"
                if edge_id in seen_keys:
                    continue
                seen_keys.add(edge_id)

                ev = EvidenceCitation(
                    evidence_type=EvidenceType.GRAPH_EDGE,
                    project_key=edge["project_key"],
                    file_path=edge["file_path"] or "",
                    start_line=edge["start_line"],
                    end_line=edge["end_line"],
                    entity_key=edge["subject_key"],
                    relation_key=edge["relation_key"],
                    confidence=edge["confidence"],
                )
                candidates.append(
                    RetrievalCandidate(
                        id=f"graph:{edge_id}",
                        score=0.9,
                        source_index=IndexType.GRAPH,
                        project_key=edge["project_key"],
                        name=edge["subject_key"],
                        title=f"{edge['subject_key']} --[{edge['predicate']}]--> {entity_key}",
                        summary=f"Inbound relation '{edge['predicate']}' from {edge['subject_key']} to {entity_key}",
                        file_path=edge["file_path"],
                        entity_key=edge["subject_key"],
                        evidence=ev,
                        metadata=edge["metadata"],
                    )
                )

        return candidates[:limit]

    def trace_api(
        self,
        path_query: str,
        http_method: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Traces API route to frontend call site and backend controller/service."""
        norm_q = path_query.strip().lower()
        candidates: list[RetrievalCandidate] = []
        import re
        q_tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", path_query) if len(t) >= 2]

        for route_path, traces in self._api_routes.items():
            for trace in traces:
                if http_method and trace["http_method"] != http_method.upper():
                    continue

                full_trace_text = (
                    f"{route_path} {trace['frontend_call_site']} "
                    f"{trace['backend_controller'] or ''} {trace['backend_service'] or ''}"
                ).lower()

                score = 0.0
                if norm_q in route_path or route_path in norm_q:
                    score = 1.0 if route_path == norm_q else 0.88
                else:
                    overlap = sum(1 for t in q_tokens if t in full_trace_text)
                    if overlap > 0:
                        score = min(0.85, 0.5 + overlap * 0.1)

                if score > 0.0:
                    ev = EvidenceCitation(
                        evidence_type=EvidenceType.API_CONTRACT,
                        project_key=trace["backend_project"] or trace["frontend_project"],
                        file_path=trace["file_path"] or "",
                        start_line=trace["start_line"],
                        confidence=score,
                    )
                    candidates.append(
                        RetrievalCandidate(
                            id=f"api:{trace['trace_id']}",
                            score=score,
                            source_index=IndexType.GRAPH,
                            project_key=trace["backend_project"] or trace["frontend_project"],
                            name=f"{trace['http_method']} {trace['http_path']}",
                            title=f"API Contract: {trace['http_method']} {trace['http_path']}",
                            summary=(
                                f"Frontend '{trace['frontend_call_site']}' -> "
                                f"Controller '{trace['backend_controller'] or 'N/A'}' -> "
                                f"Service '{trace['backend_service'] or 'N/A'}'"
                            ),
                            file_path=trace["file_path"],
                            evidence=ev,
                            metadata=trace["metadata"],
                        )
                    )

        if not candidates and self._api_routes:
            # Fallback to returning available API contracts
            for route_path, traces in self._api_routes.items():
                for trace in traces:
                    ev = EvidenceCitation(
                        evidence_type=EvidenceType.API_CONTRACT,
                        project_key=trace["backend_project"] or trace["frontend_project"],
                        file_path=trace["file_path"] or "",
                        start_line=trace["start_line"],
                        confidence=0.7,
                    )
                    candidates.append(
                        RetrievalCandidate(
                            id=f"api:{trace['trace_id']}",
                            score=0.7,
                            source_index=IndexType.GRAPH,
                            project_key=trace["backend_project"] or trace["frontend_project"],
                            name=f"{trace['http_method']} {trace['http_path']}",
                            title=f"API Contract: {trace['http_method']} {trace['http_path']}",
                            summary=(
                                f"Frontend '{trace['frontend_call_site']}' -> "
                                f"Controller '{trace['backend_controller'] or 'N/A'}' -> "
                                f"Service '{trace['backend_service'] or 'N/A'}'"
                            ),
                            file_path=trace["file_path"],
                            evidence=ev,
                            metadata=trace["metadata"],
                        )
                    )
                    if len(candidates) >= limit:
                        break
                if len(candidates) >= limit:
                    break

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:limit]

    @property
    def total_edges(self) -> int:
        return len(self._by_relation_key)
