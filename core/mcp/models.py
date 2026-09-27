"""MCP Models and Structured Envelopes (Stage 3 Section 5.3, 5.4, 5.7).

Implements:
- McpToolEnvelope: Standard structured output schema for all read-only tools
- McpErrorEnvelope: Standard error contract
- McpInvocationLog: Observability and audit schema without raw sensitive source leaks
- McpToolDefinition: Formal schema descriptor for external Agents (Cursor/Claude/Codex)
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class McpToolEnvelope(BaseModel, Generic[T]):
    """Standardized structured response envelope for all LKIO MCP tools.
    Agents can programmatically access result, snapshot, confidence, and evidence.
    """

    result: T
    snapshot_id: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    warnings: List[str] = Field(default_factory=list)
    truncated: bool = False
    nondeterministic: bool = False
    nondeterministic_reason: Optional[str] = None


class McpErrorEnvelope(BaseModel):
    """Standardized error contract for LKIO MCP tools."""

    is_error: bool = True
    error_code: str  # PERMISSION_DENIED, INVALID_ARGUMENT, TIMEOUT, NOT_FOUND, INTERNAL_ERROR
    message: str
    details: Optional[Dict[str, Any]] = None


class McpInvocationLog(BaseModel):
    """Observability record captured per MCP tool call (Section 5.7)."""

    request_id: str
    agent_id: Optional[str] = None
    tool: str
    repo: str
    snapshot: str
    parameters_hash: str
    latency_ms: float
    result_count: int
    truncated: bool
    confidence: float
    error: Optional[str] = None


class McpToolDefinition(BaseModel):
    """Formal MCP tool metadata and JSON Schema."""

    name: str
    description: str
    read_only: bool = True
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    timeout_sec: float = 30.0
    max_result_size: int = 100
