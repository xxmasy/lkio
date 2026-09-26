"""API Traceability Models & DTOs (MVP2-E)
Defines strongly-typed representations for HTTP Endpoints, Methods, and Traceability Candidates.

Enforces:
- LOCK-TRACE-01: Objective endpoint contract derived from AST.
- LOCK-TRACE-02: Path normalization.
- LOCK-TRACE-03: Multi-layer traceability predicates.
- LOCK-TRACE-04: Deterministic relation_key format.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import re
from typing import Any

from core.graph.models import RelationKind, ResolutionStatus, SourceOccurrence


class HttpMethod(str, Enum):
    """Standard HTTP Methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"
    ANY = "ANY"


class ApiTracePredicate(str, Enum):
    """Predicates representing steps in the end-to-end API traceability chain (LOCK-TRACE-03)."""
    ROUTES_TO = "routes_to"       # Frontend Caller -> HTTP Endpoint
    HANDLED_BY = "handled_by"     # HTTP Endpoint -> Backend Controller
    TRACES_TO = "traces_to"       # Frontend Caller -> Backend Controller / Service


def normalize_api_path(path: str) -> str:
    """Normalizes an API path (LOCK-TRACE-02).
    - Ensures leading slash.
    - Strips trailing slash.
    - Collapses consecutive slashes.
    - Normalizes parameter segments: '/users/:id' or '/users/{id}' -> '/users/{param}'.
    """
    if not path:
        return "/"

    p = path.strip().replace("\\", "/")
    if not p.startswith("/"):
        p = "/" + p

    # Remove query string if present
    if "?" in p:
        p = p.split("?")[0]

    # Collapse double slashes
    p = re.sub(r"/+", "/", p)

    # Remove trailing slash unless root
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]

    # Normalize variable parameters :param and {param} to {param}
    p = re.sub(r"/:[a-zA-Z0-9_]+", "/{param}", p)
    p = re.sub(r"/\{[a-zA-Z0-9_]+\}", "/{param}", p)

    return p


@dataclass(frozen=True)
class ApiEndpoint:
    """Represents a discovered HTTP endpoint from client or server side."""
    project_key: str
    http_method: HttpMethod
    raw_path: str
    normalized_path: str
    source_file_rel_path: str
    line: int
    enclosing_symbol_key: str
    is_backend_handler: bool = False
    downstream_service_calls: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def endpoint_key(self) -> str:
        return f"ENDPOINT:{self.http_method.value}:{self.normalized_path}"


@dataclass(frozen=True)
class ApiTraceCandidate:
    """Immutable DTO representing an API contract traceability link (LOCK-TRACE-04)."""
    source_project_key: str
    target_project_key: str
    subject_entity_key: str
    predicate: ApiTracePredicate
    normalized_endpoint: str
    relation_kind: RelationKind = RelationKind.STATIC
    confidence: Decimal = Decimal("1.00000")
    resolution_status: ResolutionStatus = ResolutionStatus.RESOLVED
    object_entity_key: str = ""
    candidate_discriminator: str = "default"
    occurrences: tuple[SourceOccurrence, ...] = field(default_factory=tuple)
    source_file_rel_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def relation_key(self) -> str:
        """Deterministic global key for API traceability relation (LOCK-TRACE-04)."""
        pred_val = self.predicate.value if isinstance(self.predicate, Enum) else str(self.predicate)
        kind_val = self.relation_kind.value if isinstance(self.relation_kind, Enum) else str(self.relation_kind)
        return (
            f"RELATION:TRACE:"
            f"{self.source_project_key}:"
            f"{self.target_project_key}:"
            f"{self.subject_entity_key}:"
            f"{pred_val}:"
            f"{self.normalized_endpoint}:"
            f"{kind_val}:"
            f"{self.candidate_discriminator}"
        )
