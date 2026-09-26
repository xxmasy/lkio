"""Unit tests for RAG Chunking and Index Hub Builder."""

from core.rag.builder import DeterministicLocalEmbedder, RAGIndexHub
from core.rag.chunking.chunker import MarkdownDocChunker


def test_deterministic_embedder():
    embedder = DeterministicLocalEmbedder(dimension=64)
    v1 = embedder.embed("LeadAllocationService for North America")
    v2 = embedder.embed("LeadAllocationService for North America")
    v3 = embedder.embed("Completely unrelated text about cooking pancakes")

    # Determinism
    assert len(v1) == 64
    assert v1 == v2

    # Dot product similarity
    sim_same = sum(x * y for x, y in zip(v1, v2))
    sim_diff = sum(x * y for x, y in zip(v1, v3))
    assert abs(sim_same - 1.0) < 1e-4
    assert sim_same > sim_diff


def test_markdown_chunker():
    chunker = MarkdownDocChunker()
    doc_content = """# System Overview
This is the main system overview.

## Architecture
Architecture contains frontend and backend.

### Microservices
We have multiple microservices.
"""
    chunks = chunker.chunk(doc_content, file_path="docs/overview.md", project_key="HELLO_FE")
    assert len(chunks) == 3
    assert chunks[0].title == "System Overview"
    assert chunks[1].title == "Architecture"
    assert chunks[2].title == "Microservices"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 3


def test_index_hub_integration():
    hub = RAGIndexHub(dimension=64)
    hub.index_entity(
        entity_key="SYMBOL:HELLO_BE:LeadController",
        name="LeadController",
        canonical_name="org.example.controller.LeadController",
        project_key="HELLO_BE",
        entity_type="CLASS",
        file_path="src/main/java/controller/LeadController.java",
        start_line=15,
        end_line=120,
        docstring="Handles HTTP requests for Leads",
    )
    hub.index_document(
        file_path="docs/lead_rules.md",
        content="# Lead Rules\nSales reps are assigned based on geography.",
        project_key="HELLO_BE",
    )
    hub.index_api_trace(
        trace_id="TRACE:leads:get",
        http_method="GET",
        http_path="/api/leads/list",
        frontend_call_site="fetchLeads()",
        frontend_project="HELLO_FE",
        backend_controller="LeadController",
        backend_service="LeadService",
        backend_project="HELLO_BE",
    )
    hub.index_commit(
        commit_hash="c0ffee123456",
        message="feat: add lead rules doc",
        author="Bob",
        timestamp="2026-09-24 14:00:00",
        project_key="HELLO_BE",
        files_changed=["docs/lead_rules.md"],
    )

    assert hub.entity_index.total_count == 1
    assert hub.keyword_index.total_count >= 3
    assert hub.vector_index.total_count >= 2
    assert hub.graph_index.total_edges == 0  # no relation added yet
    assert hub.temporal_index.total_count == 1
