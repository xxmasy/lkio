"""Unit tests for LKIO RAG Five Indices (Step 3.1)."""

import pytest
from core.rag.indices import (
    EntityIndex,
    GraphIndex,
    KeywordIndex,
    TemporalIndex,
    VectorIndex,
)
from core.rag.models import EvidenceType, IndexType


def test_entity_index():
    index = EntityIndex()
    index.add_entity(
        entity_key="SYMBOL:HELLO_BE:com.example.service.LeadService",
        name="LeadService",
        canonical_name="com.example.service.LeadService",
        project_key="HELLO_BE",
        entity_type="SERVICE",
        file_path="src/main/java/service/LeadService.java",
        start_line=10,
        end_line=50,
    )
    index.add_entity(
        entity_key="SYMBOL:HELLO_BE:com.example.service.LeadServiceImpl",
        name="LeadServiceImpl",
        canonical_name="com.example.service.LeadServiceImpl",
        project_key="HELLO_BE",
        entity_type="CLASS",
        file_path="src/main/java/service/LeadServiceImpl.java",
        start_line=12,
        end_line=90,
    )

    # Exact search
    res = index.search_exact("LeadService")
    assert len(res) == 1
    assert res[0].name == "LeadService"
    assert res[0].source_index == IndexType.ENTITY
    assert res[0].evidence.evidence_type == EvidenceType.SYMBOL_DEF
    assert res[0].evidence.start_line == 10

    # Prefix search
    res_prefix = index.search_prefix("Lead")
    assert len(res_prefix) == 2

    # Project key filter
    res_proj = index.search_exact("LeadService", project_key="HELLO_FE")
    assert len(res_proj) == 0


def test_keyword_index():
    kw_index = KeywordIndex()
    kw_index.add_document(
        doc_id="doc1",
        text="LeadAllocationService allocates leads to sales representatives based on rule engine",
        project_key="HELLO_BE",
        name="LeadAllocationService",
        title="Lead Allocation",
        summary="Service allocating leads to sales reps",
        file_path="src/main/java/service/LeadAllocationService.java",
    )
    kw_index.add_document(
        doc_id="doc2",
        text="OrderProcessingService handles checkout and payment processing",
        project_key="HELLO_BE",
        name="OrderProcessingService",
        title="Order Processing",
        summary="Service for checkout and payment",
        file_path="src/main/java/service/OrderProcessingService.java",
    )

    # Search with keyword
    res = kw_index.search("allocates leads sales")
    assert len(res) >= 1
    assert res[0].name == "LeadAllocationService"
    assert res[0].source_index == IndexType.KEYWORD
    assert res[0].score > 0.0

    # Chinese tokenization check
    kw_index.add_document(
        doc_id="doc3",
        text="销售日报表数据统计与前端展示模块",
        project_key="HELLO_BE",
        name="SalesReport",
        title="销售日报",
        summary="销售日报统计",
        file_path="src/main/java/report/SalesReport.java",
    )
    res_zh = kw_index.search("销售日报")
    assert len(res_zh) >= 1
    assert res_zh[0].name == "SalesReport"


def test_vector_index():
    v_index = VectorIndex(dimension=4)
    # Add dummy 4D vectors
    v_index.add_chunk(
        chunk_id="chunk1",
        vector=[1.0, 0.0, 0.0, 0.0],
        project_key="HELLO_FE",
        name="UserLoginChunk",
        title="User Login Authentication",
        summary="OAuth2 and JWT token auth flow",
        file_path="src/api/auth.ts",
    )
    v_index.add_chunk(
        chunk_id="chunk2",
        vector=[0.0, 1.0, 0.0, 0.0],
        project_key="HELLO_FE",
        name="PaymentChunk",
        title="Payment Gateway",
        summary="Stripe payment checkout flow",
        file_path="src/api/pay.ts",
    )

    # Query close to chunk1
    res = v_index.search(query_vector=[0.9, 0.1, 0.0, 0.0], limit=5)
    assert len(res) >= 1
    assert res[0].name == "UserLoginChunk"
    assert res[0].score > 0.8
    assert res[0].source_index == IndexType.VECTOR


def test_graph_index():
    g_index = GraphIndex()
    g_index.add_relation(
        relation_key="REL:HELLO_FE:page:calls:api",
        subject_key="SYMBOL:HELLO_FE:views/OrderView",
        predicate="calls",
        project_key="HELLO_FE",
        object_key="SYMBOL:HELLO_FE:api/orderApi",
        file_path="src/views/OrderView.vue",
        start_line=25,
    )
    g_index.add_api_trace(
        trace_id="TRACE:order:post",
        http_method="POST",
        http_path="/api/orders/create",
        frontend_call_site="createOrderApi()",
        frontend_project="HELLO_FE",
        backend_controller="OrderController",
        backend_service="OrderService",
        backend_project="HELLO_BE",
        file_path="src/api/order.ts",
        start_line=15,
    )

    # Neighbors search
    res = g_index.get_neighbors("SYMBOL:HELLO_FE:views/OrderView", direction="out")
    assert len(res) == 1
    assert res[0].source_index == IndexType.GRAPH
    assert res[0].name == "SYMBOL:HELLO_FE:api/orderApi"

    # API trace search
    trace_res = g_index.trace_api("/api/orders/create", http_method="POST")
    assert len(trace_res) == 1
    assert trace_res[0].evidence.evidence_type == EvidenceType.API_CONTRACT
    assert trace_res[0].score == 1.0


def test_temporal_index():
    t_index = TemporalIndex()
    t_index.add_commit(
        commit_hash="a1b2c3d4e5f6",
        message="feat(lead): implement daily lead allocation algorithm",
        author="Alice",
        timestamp="2026-09-24 10:00:00",
        project_key="HELLO_BE",
        files_changed=["src/main/java/service/LeadAllocationService.java"],
    )

    # Search by file
    by_file = t_index.search_by_file("LeadAllocationService.java")
    assert len(by_file) == 1
    assert by_file[0].name == "a1b2c3d4"
    assert by_file[0].source_index == IndexType.TEMPORAL
    assert by_file[0].evidence.commit_hash == "a1b2c3d4e5f6"

    # Search by message
    by_msg = t_index.search_by_message("allocation")
    assert len(by_msg) == 1
    assert by_msg[0].evidence.commit_hash == "a1b2c3d4e5f6"
