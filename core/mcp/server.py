"""LKIO Model Context Protocol (MCP) Server Infrastructure (Stage 3).

Exposes the unified facts layer to external AI Agents (Claude Code, Cursor, Codex).
Adheres strictly to the JSON-RPC 2.0 MCP protocol specifications.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import threading
from typing import Any, Dict, List, Optional
from core.mcp.models import (
    McpErrorEnvelope,
    McpInvocationLog,
    McpToolDefinition,
    McpToolEnvelope,
)
from core.mcp.tools import McpToolRegistry
from core.sdk.lkio import LKIO


class LKIO_MCPServer:
    """Production MCP Server delivering structured repository intelligence to agents."""

    def __init__(self, sdk: Optional[LKIO] = None, max_workers: int = 16):
        self.registry = McpToolRegistry(sdk=sdk)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns JSON-RPC compliant tool schemas."""
        defs = self.registry.get_tool_definitions()
        return [
            {
                "name": d.name,
                "description": d.description,
                "inputSchema": d.input_schema,
                "outputSchema": d.output_schema,
                "readOnly": d.read_only,
            }
            for d in defs
        ]

    def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        request_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Direct programmatic invocation returning structured dictionary."""
        envelope, err = self.registry.execute_tool(name, arguments, request_id=request_id, agent_id=agent_id)
        if err:
            return err.model_dump()
        return envelope.model_dump()

    def process_json_rpc(self, request_payload: str) -> str:
        """Processes standard JSON-RPC 2.0 text messages (stdio transport)."""
        try:
            req = json.loads(request_payload)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "tools/list":
                res = {"tools": self.list_tools()}
                return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res})

            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                envelope, err = self.registry.execute_tool(tool_name, args, request_id=str(req_id))
                if err:
                    return json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32000,
                                "message": err.message,
                                "data": err.model_dump(),
                            },
                        }
                    )
                return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": envelope.model_dump()})

            elif method == "initialize":
                init_res = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "lkio-mcp-server", "version": "1.0.0"},
                    "capabilities": {"tools": {"listChanged": False}},
                }
                return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": init_res})

            else:
                return json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }
                )

        except json.JSONDecodeError:
            return json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
        except Exception as e:
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                }
            )

    @property
    def logs(self) -> List[McpInvocationLog]:
        return self.registry.observability_logs
