"""Unit tests for Local LLM Gateway and Grounded Answer Synthesizer."""

from core.rag.engine import RAGQueryResult
from core.rag.gateway import GroundedAnswerSynthesizer, MockOfflineLLMProvider
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    FusedResult,
    IndexType,
    QueryIntent,
)
from core.rag.router.router import QueryPlan


def test_mock_offline_llm_provider():
    provider = MockOfflineLLMProvider(dimension=32)
    resp = provider.chat([{"role": "user", "content": "What is LeadService?"}])
    assert "LKIO Grounded Response" in resp

    embeddings = provider.embed(["test query"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 32


def test_grounded_answer_synthesizer():
    plan = QueryPlan(
        raw_query="LeadService",
        clean_query="LeadService",
        intent=QueryIntent.ENTITY_LOOKUP,
        confidence=0.9,
        channels={IndexType.ENTITY: 1.0},
    )
    ev = EvidenceCitation(
        evidence_type=EvidenceType.SYMBOL_DEF,
        project_key="HELLO_BE",
        file_path="src/service/LeadService.java",
        start_line=10,
        entity_key="SYMBOL:HELLO_BE:LeadService",
    )
    res = FusedResult(
        id="ent:LeadService",
        fused_score=0.98,
        channel_scores={"entity_index": 1.0},
        channel_ranks={"entity_index": 1},
        project_key="HELLO_BE",
        name="LeadService",
        title="[SERVICE] LeadService",
        summary="Service interface for leads",
        file_path="src/service/LeadService.java",
        entity_key="SYMBOL:HELLO_BE:LeadService",
        evidences=[ev],
    )
    query_res = RAGQueryResult(
        query="LeadService 在哪里？",
        plan=plan,
        results=[res],
        top_evidences=[ev],
    )

    synthesizer = GroundedAnswerSynthesizer()
    answer = synthesizer.synthesize(query_res)

    assert "LeadService 在哪里？" in answer
    assert "HELLO_BE" in answer
    assert "src/service/LeadService.java" in answer
    assert "L10" in answer
    assert "溯源证据链 (Grounding Evidence Citations)" in answer
