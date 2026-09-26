"""LKIO Unified RAG Engine
Coordinates Query Routing, Multi-Channel Retrieval from IndexHub, RRF Fusion, and Evidence Citation.
"""

from dataclasses import dataclass, field
from core.rag.builder import RAGIndexHub
from core.rag.fusion.reranker import HybridReranker
from core.rag.models import (
    EvidenceCitation,
    FusedResult,
    IndexType,
    RetrievalCandidate,
)
from core.rag.router.router import QueryPlan, QueryRouter


@dataclass
class RAGQueryResult:
    """Complete response from the RAG retrieval pipeline."""
    query: str
    plan: QueryPlan
    results: list[FusedResult]
    top_evidences: list[EvidenceCitation] = field(default_factory=list)


class RAGEngine:
    """End-to-End Hybrid RAG Query Engine."""

    def __init__(
        self,
        index_hub: RAGIndexHub,
        router: QueryRouter | None = None,
        reranker: HybridReranker | None = None,
    ) -> None:
        self.hub = index_hub
        self.router = router or QueryRouter()
        self.reranker = reranker or HybridReranker()

    def query(
        self,
        query_text: str,
        project_key: str | None = None,
        limit: int = 10,
    ) -> RAGQueryResult:
        """Executes full hybrid RAG pipeline: Router -> Multi-Index Search -> RRF Rerank -> Evidence."""
        # 1. Route Intent and Plan
        plan = self.router.route(query_text)
        if project_key:
            plan.target_project = project_key

        channel_results: dict[IndexType, list[RetrievalCandidate]] = {}
        fetch_limit = limit * 2

        # 2. Query Active Channels
        for ch_type, weight in plan.channels.items():
            if weight <= 0.05:
                continue

            if ch_type == IndexType.ENTITY:
                cands = self.hub.entity_index.search(
                    plan.clean_query,
                    project_key=plan.target_project,
                    limit=fetch_limit,
                )
                # If extracted entities exist, also search those
                for ent_name in plan.extracted_entities:
                    extra = self.hub.entity_index.search(
                        ent_name,
                        project_key=plan.target_project,
                        limit=fetch_limit,
                    )
                    cands.extend(extra)
                channel_results[IndexType.ENTITY] = cands

            elif ch_type == IndexType.KEYWORD:
                cands = self.hub.keyword_index.search(
                    plan.clean_query,
                    project_key=plan.target_project,
                    limit=fetch_limit,
                )
                channel_results[IndexType.KEYWORD] = cands

            elif ch_type == IndexType.VECTOR:
                q_vec = self.hub.embedder(plan.clean_query)
                cands = self.hub.vector_index.search(
                    query_vector=q_vec,
                    project_key=plan.target_project,
                    limit=fetch_limit,
                )
                channel_results[IndexType.VECTOR] = cands

            elif ch_type == IndexType.GRAPH:
                graph_cands: list[RetrievalCandidate] = []
                # Check for API path or contract query
                q_lower = plan.clean_query.lower()
                if "/" in plan.clean_query or any(k in q_lower for k in ["api", "接口", "契约", "路由", "route"]):
                    api_cands = self.hub.graph_index.trace_api(
                        plan.clean_query,
                        limit=fetch_limit,
                    )
                    graph_cands.extend(api_cands)

                # Check extracted entities for neighbor expansion
                for ent_name in plan.extracted_entities:
                    ent_matches = self.hub.entity_index.search_exact(ent_name, project_key=plan.target_project)
                    for em in ent_matches:
                        if em.entity_key:
                            neighbors = self.hub.graph_index.get_neighbors(em.entity_key, limit=fetch_limit)
                            graph_cands.extend(neighbors)

                channel_results[IndexType.GRAPH] = graph_cands

            elif ch_type == IndexType.TEMPORAL:
                temp_cands: list[RetrievalCandidate] = []
                if plan.extracted_paths:
                    for p in plan.extracted_paths:
                        file_commits = self.hub.temporal_index.search_by_file(
                            p,
                            project_key=plan.target_project,
                            limit=fetch_limit,
                        )
                        temp_cands.extend(file_commits)
                else:
                    msg_commits = self.hub.temporal_index.search_by_message(
                        plan.clean_query,
                        project_key=plan.target_project,
                        limit=fetch_limit,
                    )
                    temp_cands.extend(msg_commits)
                channel_results[IndexType.TEMPORAL] = temp_cands

        # 3. Fuse and Rerank
        fused = self.reranker.fuse(channel_results, plan=plan, limit=limit)

        # 4. Extract Top Grounding Evidences
        all_evs: list[EvidenceCitation] = []
        seen_ev_keys: set[str] = set()
        for res in fused:
            for ev in res.evidences:
                ev_key = f"{ev.evidence_type}:{ev.project_key}:{ev.file_path}:{ev.start_line}"
                if ev_key not in seen_ev_keys:
                    seen_ev_keys.add(ev_key)
                    all_evs.append(ev)

        return RAGQueryResult(
            query=query_text,
            plan=plan,
            results=fused,
            top_evidences=all_evs[:limit],
        )
