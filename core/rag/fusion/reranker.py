"""LKIO Hybrid Fusion and Reranker
Implements Reciprocal Rank Fusion (RRF) and Evidence Packaging across the 5 index channels.
"""

from core.rag.models import (
    EvidenceCitation,
    FusedResult,
    IndexType,
    RetrievalCandidate,
)
from core.rag.router.router import QueryPlan


class HybridReranker:
    """Merges and reranks candidates from multiple index channels with evidence aggregation."""

    def __init__(self, rrf_k: int = 60, alpha: float = 0.5) -> None:
        self.rrf_k = rrf_k
        self.alpha = alpha

    def fuse(
        self,
        channel_results: dict[IndexType, list[RetrievalCandidate]],
        plan: QueryPlan,
        limit: int = 10,
    ) -> list[FusedResult]:
        """Fuses multi-channel candidate lists into a unified ranked list of FusedResult."""
        # Key: canonical identity (e.g. entity_key, or file_path, or commit_hash, or candidate.id)
        fused_map: dict[str, dict] = {}

        for ch_type, candidates in channel_results.items():
            ch_weight = plan.channels.get(ch_type, 0.1)

            for rank_0, cand in enumerate(candidates):
                rank = rank_0 + 1
                dedup_key = self._get_dedup_key(cand)

                if dedup_key not in fused_map:
                    fused_map[dedup_key] = {
                        "id": cand.id,
                        "project_key": cand.project_key,
                        "name": cand.name,
                        "title": cand.title,
                        "summary": cand.summary,
                        "file_path": cand.file_path,
                        "entity_key": cand.entity_key,
                        "channel_scores": {},
                        "channel_ranks": {},
                        "rrf_score": 0.0,
                        "weighted_score": 0.0,
                        "evidences": [],
                        "metadata": dict(cand.metadata),
                    }

                entry = fused_map[dedup_key]
                # Accumulate RRF score
                rrf_term = ch_weight / (self.rrf_k + rank)
                entry["rrf_score"] += rrf_term

                # Accumulate weighted continuous score
                entry["weighted_score"] += ch_weight * cand.score
                entry["channel_scores"][ch_type.value] = cand.score
                entry["channel_ranks"][ch_type.value] = rank

                # Append evidence if present
                if cand.evidence:
                    # Avoid duplicate evidence
                    existing_evs = entry["evidences"]
                    is_dup = any(
                        e.file_path == cand.evidence.file_path
                        and e.start_line == cand.evidence.start_line
                        and e.evidence_type == cand.evidence.evidence_type
                        for e in existing_evs
                    )
                    if not is_dup:
                        existing_evs.append(cand.evidence)

        if not fused_map:
            return []

        # Normalize RRF scores
        max_rrf = max(e["rrf_score"] for e in fused_map.values()) or 1.0

        final_list: list[FusedResult] = []
        for entry in fused_map.values():
            norm_rrf = entry["rrf_score"] / max_rrf
            fused_score = self.alpha * norm_rrf + (1.0 - self.alpha) * min(1.0, entry["weighted_score"])

            # Filter by target project if specified in plan
            if plan.target_project and entry["project_key"] != plan.target_project:
                # Soft penalty for mismatched project when query explicitly requested a project
                fused_score *= 0.2

            final_list.append(
                FusedResult(
                    id=entry["id"],
                    fused_score=round(fused_score, 4),
                    channel_scores=entry["channel_scores"],
                    channel_ranks=entry["channel_ranks"],
                    project_key=entry["project_key"],
                    name=entry["name"],
                    title=entry["title"],
                    summary=entry["summary"],
                    file_path=entry["file_path"],
                    entity_key=entry["entity_key"],
                    evidences=entry["evidences"],
                    metadata=entry["metadata"],
                )
            )

        # Sort by fused score descending
        final_list.sort(key=lambda x: x.fused_score, reverse=True)
        return final_list[:limit]

    def _get_dedup_key(self, cand: RetrievalCandidate) -> str:
        """Determines identity key for cross-channel merging."""
        if cand.entity_key:
            return f"ENT:{cand.entity_key}"
        if cand.evidence and cand.evidence.commit_hash:
            return f"COMMIT:{cand.evidence.commit_hash}"
        if cand.file_path:
            return f"FILE:{cand.project_key}:{cand.file_path}"
        return cand.id
