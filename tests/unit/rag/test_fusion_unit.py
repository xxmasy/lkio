"""Unit tests for Hybrid Fusion, RRF Reranking, and Evidence Aggregation."""

from core.rag.fusion.reranker import HybridReranker
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    IndexType,
    QueryIntent,
    RetrievalCandidate,
)
from core.rag.router.router import QueryPlan


def test_hybrid_reranker_fusion():
    reranker = HybridReranker()
    plan = QueryPlan(
        raw_query="LeadService",
        clean_query="LeadService",
        intent=QueryIntent.ENTITY_LOOKUP,
        confidence=0.9,
        channels={IndexType.ENTITY: 0.7, IndexType.KEYWORD: 0.3},
    )

    ev1 = EvidenceCitation(
        evidence_type=EvidenceType.SYMBOL_DEF,
        project_key="HELLO_BE",
        file_path="src/service/LeadService.java",
        start_line=10,
        entity_key="SYMBOL:HELLO_BE:LeadService",
    )
    cand_entity = RetrievalCandidate(
        id="ent:LeadService",
        score=1.0,
        source_index=IndexType.ENTITY,
        project_key="HELLO_BE",
        name="LeadService",
        title="LeadService Interface",
        summary="Service interface",
        file_path="src/service/LeadService.java",
        entity_key="SYMBOL:HELLO_BE:LeadService",
        evidence=ev1,
    )

    ev2 = EvidenceCitation(
        evidence_type=EvidenceType.DOC_CHUNK,
        project_key="HELLO_BE",
        file_path="docs/lead.md",
        start_line=1,
    )
    cand_kw = RetrievalCandidate(
        id="kw:LeadServiceDoc",
        score=0.8,
        source_index=IndexType.KEYWORD,
        project_key="HELLO_BE",
        name="LeadServiceDoc",
        title="LeadService Documentation",
        summary="Documentation of lead service",
        file_path="docs/lead.md",
        evidence=ev2,
    )

    channel_results = {
        IndexType.ENTITY: [cand_entity],
        IndexType.KEYWORD: [cand_kw],
    }

    fused = reranker.fuse(channel_results, plan=plan, limit=5)
    assert len(fused) == 2
    assert fused[0].id == "ent:LeadService"
    assert fused[0].fused_score > fused[1].fused_score
    assert len(fused[0].evidences) == 1
    assert fused[0].evidences[0].entity_key == "SYMBOL:HELLO_BE:LeadService"
