"""Unit tests for Stage 3 LKIO MCP Infrastructure.
Conforms to docs/LKIO_持续基础设施演进开发规范.md Section 5 (Stage 3 Gate).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import pytest
from core.mcp import (
    FORBIDDEN_MUTATION_TOOLS,
    LKIO_MCPServer,
    McpErrorEnvelope,
    McpToolEnvelope,
)
from core.sdk import LKIO


@pytest.fixture
def mcp_server():
    sdk = LKIO(default_repo_id="test-mcp-repo")
    return LKIO_MCPServer(sdk=sdk)


def test_mcp_tool_definitions_and_schema_freeze(mcp_server):
    tools = mcp_server.list_tools()
    assert len(tools) == 10

    names = {t["name"] for t in tools}
    expected_names = {
        "lkio_search",
        "lkio_symbol",
        "lkio_references",
        "lkio_dependencies",
        "lkio_impact",
        "lkio_history",
        "lkio_snapshot",
        "lkio_explain",
        "lkio_decision",
        "lkio_remote_commits",
    }
    assert names == expected_names

    for t in tools:
        assert t["readOnly"] is True
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"
        assert "properties" in t["inputSchema"]
        assert "outputSchema" in t


def test_mcp_all_nine_tools_structured_execution(mcp_server):
    # 1. lkio_search
    res = mcp_server.call_tool("lkio_search", {"query": "Sales Report", "top_k": 5})
    assert "result" in res
    assert res["confidence"] >= 0.90
    assert len(res["result"]) > 0

    # 2. lkio_symbol
    res = mcp_server.call_tool("lkio_symbol", {"name_or_query": "LeadDTO"})
    assert "result" in res
    assert res["evidence"][0]["type"] == "AST_LOOKUP"

    # 3. lkio_references
    res = mcp_server.call_tool("lkio_references", {"symbol_key": "repo://test-repo/src/Service.java#run"})
    assert "result" in res
    assert len(res["result"]) >= 2

    # 4. lkio_dependencies
    res = mcp_server.call_tool("lkio_dependencies", {"seed_key": "repo://test-repo/src/Service.java", "depth": 2})
    assert res["result"]["seed"] == "repo://test-repo/src/Service.java"
    assert len(res["result"]["nodes"]) > 0

    # 5. lkio_impact
    res = mcp_server.call_tool("lkio_impact", {"changes": ["repo://test-repo/src/Service.java"], "depth": 3})
    assert "direct" in res["result"]
    assert res["result"]["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    # 6. lkio_history
    res = mcp_server.call_tool("lkio_history", {"symbol_or_path": "src/Service.java", "limit": 5})
    assert len(res["result"]) > 0
    assert res["result"][0]["commit_id"]

    # 7. lkio_snapshot
    res = mcp_server.call_tool("lkio_snapshot", {"commit_id": "abc1234def"})
    assert res["result"]["commit_id"] == "abc1234def"
    assert res["result"]["status"] == "PUBLISHED"

    # 8. lkio_explain
    res = mcp_server.call_tool("lkio_explain", {"entity_key": "repo://test-repo/src/LeadService.java#LeadService"})
    assert "CORE_BUSINESS_SERVICE" in res["result"]["role"]

    # 9. lkio_decision
    payload = {
        "state": {"changed_entities": ["LeadService"]},
        "question": {"options": ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]},
    }
    res = mcp_server.call_tool("lkio_decision", {"task": "CHANGE_IMPACT", "payload": payload})
    assert res["result"]["decision"] in ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")

    # 10. lkio_remote_commits
    res = mcp_server.call_tool("lkio_remote_commits", {"repo_id": "backend", "fetch": False, "limit": 5})
    assert "result" in res
    assert "backend" in res["result"]
    assert "behind_count" in res["result"]["backend"]


def test_mcp_read_only_safety_enforcement(mcp_server):
    for bad_tool in ["write_file", "delete_file", "commit", "push", "merge"]:
        res = mcp_server.call_tool(bad_tool, {"path": "src/test.txt", "content": "malicious"})
        assert res.get("is_error") is True
        assert res["error_code"] == "PERMISSION_DENIED"
        assert "strictly read-only" in res["message"]


def test_mcp_structured_error_handling(mcp_server):
    # Missing required argument 'query'
    res = mcp_server.call_tool("lkio_search", {})
    assert res.get("is_error") is True
    assert res["error_code"] == "INVALID_ARGUMENT"


def test_mcp_json_rpc_protocol(mcp_server):
    # Test initialize
    init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    init_res = json.loads(mcp_server.process_json_rpc(init_req))
    assert init_res["result"]["serverInfo"]["name"] == "lkio-mcp-server"

    # Test tools/list
    list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    list_res = json.loads(mcp_server.process_json_rpc(list_req))
    assert len(list_res["result"]["tools"]) == 10

    # Test tools/call
    call_req = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "lkio_search", "arguments": {"query": "metrics"}},
        }
    )
    call_res = json.loads(mcp_server.process_json_rpc(call_req))
    assert "result" in call_res["result"]
    assert call_res["result"]["snapshot_id"]


def test_mcp_concurrency_and_observability(mcp_server):
    # Test 100 concurrent mixed read queries
    def make_call(i):
        if i % 3 == 0:
            return mcp_server.call_tool("lkio_search", {"query": f"metric_{i}"})
        elif i % 3 == 1:
            return mcp_server.call_tool("lkio_symbol", {"name_or_query": f"Symbol_{i}"})
        else:
            return mcp_server.call_tool("lkio_references", {"symbol_key": f"repo://test/file_{i}#func"})

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(make_call, i) for i in range(100)]
        results = [f.result() for f in as_completed(futures)]

    assert len(results) == 100
    for r in results:
        assert r.get("is_error") is not True

    # Observability validation
    assert len(mcp_server.logs) >= 100
    last_log = mcp_server.logs[-1]
    assert last_log.request_id.startswith("mcp_req_")
    assert last_log.latency_ms >= 0.0
    assert last_log.parameters_hash
