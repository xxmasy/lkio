"""Unit test for RAGEngine full pipeline."""

from core.rag.builder import RAGIndexHub
from core.rag.engine import RAGEngine
from core.rag.gateway import GroundedAnswerSynthesizer


def test_rag_engine_end_to_end():
    hub = RAGIndexHub(dimension=64)

    # 1. Index code symbol
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:LeadAllocationService",
        name="LeadAllocationService",
        canonical_name="org.example.service.LeadAllocationService",
        project_key="HELLO_BE",
        entity_type="SERVICE",
        file_path="src/main/java/service/LeadAllocationService.java",
        start_line=15,
        end_line=120,
        docstring="Allocates leads among sales reps based on quota and conversion",
    )

    # 2. Index documentation
    hub.index_document(
        file_path="docs/business/lead_rules.md",
        content=(
            "# Lead Allocation Rules\n"
            "Each morning at 08:00, unassigned leads are distributed among sales reps."
        ),
        project_key="HELLO_BE",
    )

    # 3. Index API trace
    hub.index_api_trace(
        trace_id="TRACE:leads:allocate:post",
        http_method="POST",
        http_path="/api/leads/allocate",
        frontend_call_site="allocateLeadsApi()",
        frontend_project="HELLO_FE",
        backend_controller="LeadController",
        backend_service="LeadAllocationService",
        backend_project="HELLO_BE",
        file_path="src/api/lead.ts",
        start_line=30,
    )

    # 4. Index Git commit
    hub.index_commit(
        commit_hash="deadbeef12345678",
        message="feat(lead): implement daily quota allocation",
        author="Charlie",
        timestamp="2026-09-24 16:00:00",
        project_key="HELLO_BE",
        files_changed=["src/main/java/service/LeadAllocationService.java"],
    )

    engine = RAGEngine(index_hub=hub)
    synthesizer = GroundedAnswerSynthesizer()

    # Query 1: Entity lookup
    res1 = engine.query("LeadAllocationService 在哪里？")
    assert len(res1.results) >= 1
    assert res1.results[0].name == "LeadAllocationService"
    assert len(res1.top_evidences) >= 1
    ans1 = synthesizer.synthesize(res1)
    assert "LeadAllocationService.java" in ans1

    # Query 2: API contract trace
    res2 = engine.query("哪些页面调用 /api/leads/allocate 接口？")
    assert len(res2.results) >= 1
    assert any("/api/leads/allocate" in r.name for r in res2.results)

    # Query 3: History query
    res3 = engine.query("谁最近修改了 LeadAllocationService.java？")
    assert len(res3.results) >= 1
    assert any("deadbeef" in r.id for r in res3.results)
