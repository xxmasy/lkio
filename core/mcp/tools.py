"""LKIO MCP Tool Implementations (Stage 3 Section 5.2 - 5.6).

Strictly read-only adapter delegating directly to the Unified LKIO SDK (`core.sdk.LKIO`).
Zero duplicate business logic.
"""

from hashlib import sha256
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from core.mcp.models import (
    McpErrorEnvelope,
    McpInvocationLog,
    McpToolDefinition,
    McpToolEnvelope,
)
from core.sdk.lkio import LKIO

FORBIDDEN_MUTATION_TOOLS = {
    "write_file",
    "modify_file",
    "commit",
    "push",
    "merge",
    "delete",
    "delete_file",
    "rebase",
}


class McpToolRegistry:
    """Maintains definitions and invocation adapters for the 9 core LKIO MCP tools."""

    def __init__(self, sdk: Optional[LKIO] = None):
        self.sdk = sdk or LKIO()
        self.observability_logs: List[McpInvocationLog] = []

    def get_tool_definitions(self) -> List[McpToolDefinition]:
        """Returns the formal schemas for all 9 core read-only MCP tools."""
        return [
            McpToolDefinition(
                name="lkio_search",
                description="Hybrid semantic and lexical code retrieval across repository files.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query or natural language description"},
                        "top_k": {"type": "integer", "default": 10, "description": "Maximum number of items to return"},
                        "repo_id": {"type": "string", "description": "Target repository ID"},
                    },
                    "required": ["query"],
                },
                output_schema={"type": "array", "items": {"type": "object"}},
            ),
            McpToolDefinition(
                name="lkio_symbol",
                description="Locates symbol AST definitions (classes, methods, DTOs, interfaces).",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "name_or_query": {"type": "string", "description": "Exact symbol name or fuzzy query"},
                        "repo_id": {"type": "string", "description": "Target repository ID"},
                    },
                    "required": ["name_or_query"],
                },
                output_schema={"type": "array", "items": {"type": "object"}},
            ),
            McpToolDefinition(
                name="lkio_references",
                description="Queries inbound and outbound references for an entity URI across repo boundaries.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "symbol_key": {"type": "string", "description": "Target entity URI, e.g., repo://fe/src/api.ts#fetchLead"},
                    },
                    "required": ["symbol_key"],
                },
                output_schema={"type": "array", "items": {"type": "object"}},
            ),
            McpToolDefinition(
                name="lkio_dependencies",
                description="Retrieves bounded dependency subgraph rooted at the given seed entity.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "seed_key": {"type": "string", "description": "Seed entity URI or file path"},
                        "depth": {"type": "integer", "default": 3, "description": "Traversal depth bound (1-5)"},
                    },
                    "required": ["seed_key"],
                },
                output_schema={"type": "object"},
            ),
            McpToolDefinition(
                name="lkio_impact",
                description="Computes cycle-safe shortest-hop impact blast radius for planned change seeds.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "changes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of changed entity URIs or file paths",
                        },
                        "depth": {"type": "integer", "default": 3, "description": "Traversal depth bound"},
                    },
                    "required": ["changes"],
                },
                output_schema={"type": "object"},
            ),
            McpToolDefinition(
                name="lkio_history",
                description="Traces Git commit evolution and symbol lifecycle changes.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "symbol_or_path": {"type": "string", "description": "File path or symbol name"},
                        "limit": {"type": "integer", "default": 10, "description": "Maximum commit history events"},
                    },
                    "required": ["symbol_or_path"],
                },
                output_schema={"type": "array", "items": {"type": "object"}},
            ),
            McpToolDefinition(
                name="lkio_snapshot",
                description="Reconstructs historical repository graph state at a specified commit.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "commit_id": {"type": "string", "description": "Git commit SHA-1"},
                    },
                    "required": ["commit_id"],
                },
                output_schema={"type": "object"},
            ),
            McpToolDefinition(
                name="lkio_explain",
                description="Explains architectural role, boundary relations, and business intent of an entity.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "entity_key": {"type": "string", "description": "Entity URI to explain"},
                    },
                    "required": ["entity_key"],
                },
                output_schema={"type": "object"},
            ),
            McpToolDefinition(
                name="lkio_decision",
                description="Executes calibrated decision gate evaluation backed by graph and statistical evidence.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Decision task, e.g., CHANGE_IMPACT, EVIDENCE_SUFFICIENCY",
                        },
                        "payload": {"type": "object", "description": "State, question options, and metadata context"},
                    },
                    "required": ["task", "payload"],
                },
                output_schema={"type": "object"},
            ),
            McpToolDefinition(
                name="lkio_remote_commits",
                description="Monitors team commits from remote GitLab repositories, detects divergence against local branches, and evaluates cross-repo impact radius.",
                read_only=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo_id": {
                            "type": "string",
                            "enum": ["all", "frontend", "backend"],
                            "default": "all",
                            "description": "Repository to inspect: 'frontend', 'backend', or 'all'",
                        },
                        "fetch": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to run read-only git fetch to query the latest GitLab remote state",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "description": "Max new remote commits to inspect per repo",
                        },
                    },
                },
                output_schema={"type": "object"},
            ),
        ]

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        request_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Tuple[Optional[McpToolEnvelope[Any]], Optional[McpErrorEnvelope]]:
        """Executes a tool with strict read-only enforcement, error envelope, and observability."""
        t0 = time.perf_counter()
        req_id = request_id or f"mcp_req_{int(time.time() * 1000)}"
        param_hash = sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()[:12]

        # 1. Enforce read-only constraint (Section 5.6)
        if tool_name in FORBIDDEN_MUTATION_TOOLS or "write" in tool_name or "delete" in tool_name or tool_name in ("commit", "push", "merge", "rebase"):
            err = McpErrorEnvelope(
                is_error=True,
                error_code="PERMISSION_DENIED",
                message=f"Operation '{tool_name}' is forbidden. LKIO MCP interface is strictly read-only.",
                details={"forbidden_tool": tool_name},
            )
            self._record_observability(req_id, agent_id, tool_name, "workspace", "current", param_hash, t0, 0, 0.0, err=err.message)
            return None, err

        try:
            envelope = self._dispatch_to_sdk(tool_name, arguments)
            latency = (time.perf_counter() - t0) * 1000
            res_count = len(envelope.result) if isinstance(envelope.result, list) else 1
            self._record_observability(
                req_id, agent_id, tool_name, self.sdk.default_repo_id, envelope.snapshot_id, param_hash, t0, res_count, envelope.confidence
            )
            return envelope, None

        except KeyError as ke:
            err = McpErrorEnvelope(
                is_error=True,
                error_code="INVALID_ARGUMENT",
                message=f"Missing required parameter: {ke}",
                details={"key": str(ke)},
            )
            self._record_observability(req_id, agent_id, tool_name, "workspace", "current", param_hash, t0, 0, 0.0, err=err.message)
            return None, err

        except Exception as e:
            err = McpErrorEnvelope(
                is_error=True,
                error_code="INTERNAL_ERROR",
                message=f"Internal tool execution failed: {str(e)}",
                details={"exception": type(e).__name__},
            )
            self._record_observability(req_id, agent_id, tool_name, "workspace", "current", param_hash, t0, 0, 0.0, err=err.message)
            return None, err

    def _dispatch_to_sdk(self, tool_name: str, args: Dict[str, Any]) -> McpToolEnvelope[Any]:
        """Dispatches call strictly to the LKIO SDK, wrapping in the standard envelope."""
        snap_id = f"snap_live_{self.sdk.default_repo_id}"

        if tool_name == "lkio_search":
            query = args["query"]
            top_k = args.get("top_k", 10)
            res = self.sdk.search(query, top_k=top_k)
            return McpToolEnvelope(
                result=[r.model_dump() for r in res],
                snapshot_id=snap_id,
                evidence=[{"type": "HYBRID_RETRIEVAL", "query": query, "hit_count": len(res)}],
                confidence=0.92,
                warnings=[],
                truncated=False,
            )

        elif tool_name == "lkio_symbol":
            name = args["name_or_query"]
            res = self.sdk.symbol(name)
            return McpToolEnvelope(
                result=[s.model_dump() for s in res],
                snapshot_id=snap_id,
                evidence=[{"type": "AST_LOOKUP", "symbol": name}],
                confidence=0.98,
                warnings=[],
            )

        elif tool_name == "lkio_references":
            key = args["symbol_key"]
            res = self.sdk.references(key)
            return McpToolEnvelope(
                result=[r.model_dump() for r in res],
                snapshot_id=snap_id,
                evidence=[{"type": "CROSS_REPO_GRAPH", "symbol": key}],
                confidence=0.95,
            )

        elif tool_name == "lkio_dependencies":
            seed = args["seed_key"]
            depth = args.get("depth", 3)
            res = self.sdk.dependencies(seed, depth=depth)
            return McpToolEnvelope(
                result=res.model_dump(),
                snapshot_id=snap_id,
                evidence=[{"type": "DEPENDENCY_GRAPH", "seed": seed, "depth": depth}],
                confidence=0.96,
            )

        elif tool_name == "lkio_impact":
            changes = args["changes"]
            depth = args.get("depth", 3)
            res = self.sdk.impact(changes, depth=depth)
            return McpToolEnvelope(
                result=res.model_dump(),
                snapshot_id=snap_id,
                evidence=[{"type": "BLAST_RADIUS", "seeds": changes, "depth": depth}],
                confidence=0.94,
            )

        elif tool_name == "lkio_history":
            target = args["symbol_or_path"]
            limit = args.get("limit", 10)
            res = self.sdk.history(target, limit=limit)
            return McpToolEnvelope(
                result=[h.model_dump() for h in res],
                snapshot_id=snap_id,
                evidence=[{"type": "GIT_COMMIT_LOG", "target": target}],
                confidence=1.0,
            )

        elif tool_name == "lkio_snapshot":
            commit = args["commit_id"]
            res = self.sdk.snapshot(commit)
            return McpToolEnvelope(
                result=res.model_dump(),
                snapshot_id=res.snapshot_id,
                evidence=[{"type": "HISTORICAL_RECONSTRUCTION", "commit": commit}],
                confidence=1.0,
            )

        elif tool_name == "lkio_explain":
            key = args["entity_key"]
            res = self.sdk.explain(key)
            return McpToolEnvelope(
                result=res.model_dump(),
                snapshot_id=snap_id,
                evidence=[{"type": "ARCHITECTURAL_ROLE", "entity": key}],
                confidence=0.90,
            )

        elif tool_name == "lkio_decision":
            task = args["task"]
            payload = args["payload"]
            res = self.sdk.decision(task, payload)
            return McpToolEnvelope(
                result=res.model_dump(),
                snapshot_id=snap_id,
                evidence=res.evidence,
                confidence=res.confidence,
                warnings=res.warnings,
            )

        elif tool_name == "lkio_remote_commits":
            repo_id = args.get("repo_id", "all")
            fetch = args.get("fetch", True)
            limit = args.get("limit", 10)
            from dataclasses import asdict
            from core.events.remote_monitor import GitRemoteMonitor
            from core.subagent.local_agent import LocalLLMSubagent

            monitor = GitRemoteMonitor()
            if repo_id == "all":
                data = monitor.check_all(fetch=fetch, limit_commits=limit)
                res_obj = {k: asdict(v) for k, v in data.items()}
            else:
                target_path = monitor.repos.get(repo_id)
                if not target_path:
                    raise KeyError(f"Unknown repo_id '{repo_id}'. Available: {list(monitor.repos.keys())}")
                status = monitor.inspect_repo(repo_id, target_path, fetch=fetch, limit_commits=limit)
                res_obj = {repo_id: asdict(status)}

            # Synthesize edge briefing via Local LLM Subagent to compress Cloud LLM tokens
            subagent = LocalLLMSubagent()
            briefings = {}
            for rid, sdata in res_obj.items():
                if sdata.get("behind_count", 0) > 0:
                    brief_res = subagent.synthesize_repo_briefing(rid, sdata, trigger_source="CURSOR_MCP")
                    briefings[rid] = brief_res.briefing_markdown
                    sdata["distilled_briefing"] = brief_res.briefing_markdown
                    sdata["token_compressed_ratio"] = f"{brief_res.token_compressed_ratio}%"

            return McpToolEnvelope(
                result=res_obj,
                snapshot_id=snap_id,
                evidence=[{"type": "REMOTE_GITLAB_MONITOR", "repo_id": repo_id, "fetch": fetch, "briefings": briefings}],
                confidence=1.0,
                warnings=[],
            )

        else:
            raise KeyError(f"Unknown MCP tool: {tool_name}")

    def _record_observability(
        self,
        req_id: str,
        agent_id: Optional[str],
        tool: str,
        repo: str,
        snapshot: str,
        param_hash: str,
        t0: float,
        result_count: int,
        confidence: float,
        err: Optional[str] = None,
    ):
        latency = round((time.perf_counter() - t0) * 1000, 2)
        log = McpInvocationLog(
            request_id=req_id,
            agent_id=agent_id,
            tool=tool,
            repo=repo,
            snapshot=snapshot,
            parameters_hash=param_hash,
            latency_ms=latency,
            result_count=result_count,
            truncated=False,
            confidence=confidence,
            error=err,
        )
        self.observability_logs.append(log)
