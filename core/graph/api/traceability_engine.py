"""API Contract Alignment & Traceability Engine (E-03)
Aligns frontend API client calls with backend Spring Boot controller endpoints,
producing end-to-end contract traceability relations.

Enforces:
- LOCK-TRACE-01: Objective path and method matching.
- LOCK-TRACE-02: Normalized path alignment.
- LOCK-TRACE-03: Multi-layer traceability linking.
"""

from decimal import Decimal
import logging
from typing import Any

from core.graph.api.models import (
    ApiEndpoint,
    ApiTraceCandidate,
    ApiTracePredicate,
    HttpMethod,
)
from core.graph.models import RelationKind, ResolutionStatus, SourceOccurrence

logger = logging.getLogger(__name__)


class ApiTraceabilityEngine:
    """Matches frontend HTTP request calls with backend controller handlers."""

    def __init__(self):
        # Maps (method, normalized_path) -> list[ApiEndpoint]
        self.backend_handlers: dict[tuple[str, str], list[ApiEndpoint]] = {}
        self.all_backend_endpoints: list[ApiEndpoint] = []

    def register_backend_endpoints(self, endpoints: list[ApiEndpoint]):
        """Indexes backend endpoints for fast lookup."""
        for ep in endpoints:
            self.all_backend_endpoints.append(ep)
            key = (ep.http_method.value, ep.normalized_path)
            self.backend_handlers.setdefault(key, []).append(ep)
            if ep.http_method != HttpMethod.ANY:
                any_key = (HttpMethod.ANY.value, ep.normalized_path)
                self.backend_handlers.setdefault(any_key, []).append(ep)

    def align_frontend_calls(
        self,
        frontend_endpoints: list[ApiEndpoint],
        target_backend_project_key: str,
    ) -> list[ApiTraceCandidate]:
        """Aligns frontend outgoing calls with registered backend endpoints."""
        trace_candidates: list[ApiTraceCandidate] = []

        for fe in frontend_endpoints:
            matched_backend, confidence = self._find_matching_backend(fe)

            if matched_backend:
                ep_str = f"{fe.http_method.value}:{fe.normalized_path}"
                kind = RelationKind.STATIC if confidence == Decimal("1.00000") else RelationKind.INFERRED

                cand = ApiTraceCandidate(
                    source_project_key=fe.project_key,
                    target_project_key=target_backend_project_key,
                    subject_entity_key=fe.enclosing_symbol_key,
                    predicate=ApiTracePredicate.TRACES_TO,
                    normalized_endpoint=ep_str,
                    relation_kind=kind,
                    confidence=confidence,
                    resolution_status=ResolutionStatus.RESOLVED,
                    object_entity_key=matched_backend.enclosing_symbol_key,
                    candidate_discriminator=f"trace_{fe.http_method.value}",
                    occurrences=(SourceOccurrence(line=fe.line, column=0),),
                    source_file_rel_path=fe.source_file_rel_path,
                    metadata={
                        "http_method": fe.http_method.value,
                        "request_path": fe.raw_path,
                        "matched_backend_path": matched_backend.raw_path,
                        "controller_file": matched_backend.source_file_rel_path,
                        "downstream_services": list(matched_backend.downstream_service_calls),
                    },
                )
                trace_candidates.append(cand)

        return trace_candidates

    def _find_matching_backend(self, fe: ApiEndpoint) -> tuple[ApiEndpoint | None, Decimal]:
        """Finds best matching backend endpoint for frontend call."""
        norm_path = fe.normalized_path
        method_val = fe.http_method.value

        # 1. Exact match on method and path
        exact_key = (method_val, norm_path)
        if exact_key in self.backend_handlers:
            return self.backend_handlers[exact_key][0], Decimal("1.00000")

        # 2. Match with ANY method
        any_key = (HttpMethod.ANY.value, norm_path)
        if any_key in self.backend_handlers:
            return self.backend_handlers[any_key][0], Decimal("1.00000")

        # 3. Match stripping common '/api' or '/crm' prefix if frontend or backend differed
        stripped_path = norm_path
        if norm_path.startswith("/api/"):
            stripped_path = norm_path[4:]  # '/call/config'
        elif norm_path.startswith("/crm/"):
            stripped_path = norm_path[4:]

        for be in self.all_backend_endpoints:
            be_stripped = be.normalized_path
            if be_stripped.startswith("/api/"):
                be_stripped = be_stripped[4:]
            elif be_stripped.startswith("/crm/"):
                be_stripped = be_stripped[4:]

            if stripped_path == be_stripped:
                if be.http_method in {fe.http_method, HttpMethod.ANY} or fe.http_method == HttpMethod.ANY:
                    return be, Decimal("0.95000")

        # 4. Parameterized path matching (e.g. /users/123 -> /users/{param})
        # Check if segment count matches
        fe_segments = [s for s in norm_path.split("/") if s]
        for be in self.all_backend_endpoints:
            be_segments = [s for s in be.normalized_path.split("/") if s]
            if len(fe_segments) == len(be_segments):
                match = True
                for f_seg, b_seg in zip(fe_segments, be_segments):
                    if b_seg == "{param}":
                        continue
                    if f_seg != b_seg:
                        match = False
                        break
                if match:
                    if be.http_method in {fe.http_method, HttpMethod.ANY} or fe.http_method == HttpMethod.ANY:
                        return be, Decimal("0.90000")

        return None, Decimal("0.00000")
