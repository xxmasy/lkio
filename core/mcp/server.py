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


SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2025-11-25", "2026-07-28"]
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


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

            # Notifications in JSON-RPC 2.0 (no id) must NOT return a response
            if req_id is None:
                return ""

            if method == "initialize":
                client_ver = params.get("protocolVersion")
                negotiated_ver = client_ver if client_ver in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
                init_res = {
                    "protocolVersion": negotiated_ver,
                    "serverInfo": {"name": "lkio-mcp-server", "version": "1.0.0"},
                    "capabilities": {"tools": {"listChanged": False}},
                }
                return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": init_res})

            elif method == "ping":
                return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": {}})

            elif method == "tools/list":
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
                            "result": {
                                "content": [{"type": "text", "text": f"Error: {err.message}"}],
                                "isError": True,
                                "error": err.model_dump(),
                            },
                        },
                        ensure_ascii=False,
                    )

                env_dump = envelope.model_dump()
                res_obj = env_dump.get("result")

                # Prioritize pre-distilled local subagent briefing to dramatically compress Cloud LLM tokens
                if isinstance(res_obj, dict) and any(
                    isinstance(v, dict) and "distilled_briefing" in v for v in res_obj.values()
                ):
                    brief_sections = []
                    for rid, rdata in res_obj.items():
                        if isinstance(rdata, dict) and "distilled_briefing" in rdata:
                            ratio = rdata.get("token_compressed_ratio", "")
                            behind = rdata.get("behind_count", 0)
                            branch = rdata.get("tracking_branch", "")
                            header = f"### 📦 仓库 [{rid}] (分支: {branch} | 落后 {behind} 提交 | 本地压缩: {ratio})"
                            brief_sections.append(f"{header}\n\n{rdata['distilled_briefing']}")
                    text_content = "\n\n---\n\n".join(brief_sections)
                else:
                    text_content = (
                        json.dumps(res_obj, ensure_ascii=False, indent=2)
                        if isinstance(res_obj, (dict, list))
                        else str(res_obj)
                    )

                response_payload = dict(env_dump)
                response_payload["content"] = [{"type": "text", "text": text_content}]
                response_payload["isError"] = False

                return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": response_payload}, ensure_ascii=False)

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

    def run_stdio(self):
        """Standard IO JSON-RPC loop for MCP clients."""
        import sys

        if hasattr(sys.stdin, "reconfigure"):
            try:
                sys.stdin.reconfigure(encoding="utf-8")
            except Exception:
                pass
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            res = self.process_json_rpc(line)
            if res:
                sys.stdout.write(res + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    server = LKIO_MCPServer()
    server.run_stdio()

