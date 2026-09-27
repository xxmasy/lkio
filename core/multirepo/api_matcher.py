"""API Contract Matcher across Multi-Repo Boundaries (Stage 2 Section 4.4 & 4.5).

Extracts route endpoints from frontend client calls and backend controllers,
producing graded cross-repo API_CALLS edges.
"""

import re
from typing import Dict, List, Optional, Tuple
from core.multirepo.models import ApiContract, ApiEndpoint, CrossRepoEdge, EvidenceLevel


class ApiContractMatcher:
    """Discovers and establishes cross-repository contracts between Frontend APIs and Backend Controllers."""

    @classmethod
    def extract_frontend_endpoints(cls, repo_id: str, file_path: str, code: str) -> List[ApiEndpoint]:
        """Extracts Axios/fetch route invocations from frontend code."""
        endpoints = []
        # Pattern 1: axios.get('/api/...'), request.post(`/api/...${id}`), axios.get('/api/users/' + id)
        p1 = re.finditer(
            r"(?:axios|apiClient|http|request)\.(get|post|put|delete)\s*\(\s*[`'\"]([^`'\"]+)[`'\"](?:\s*\+\s*[A-Za-z0-9_]+)?",
            code,
            re.IGNORECASE,
        )
        for m in p1:
            method = m.group(1).upper()
            raw_path = m.group(2).strip()
            # If string concatenation was present, or path ended with trailing slash before param
            if "+" in m.group(0):
                raw_path = raw_path.rstrip("/") + "/{id}"
            # Normalize JS template syntax ${id} -> {id}
            raw_path = re.sub(r"\$\{[^}]+\}", "{id}", raw_path)
            line_no = code[: m.start()].count("\n") + 1
            norm_p = cls._normalize_path(raw_path)
            endpoints.append(
                ApiEndpoint(
                    repo_id=repo_id,
                    file_path=file_path,
                    http_method=method,
                    path=norm_p,
                    symbol_name=f"client_{method}_{norm_p.split('/')[-1]}",
                    line_no=line_no,
                )
            )

        # Pattern 2: url: '/api/...', method: 'GET'
        p2 = re.finditer(r"url:\s*[`'\"]([^`'\"]+)[`'\"].*?method:\s*[`'\"]([^`'\"]+)[`'\"]", code, re.DOTALL | re.IGNORECASE)
        for m in p2:
            raw_path = m.group(1).strip()
            raw_path = re.sub(r"\$\{[^}]+\}", "{id}", raw_path)
            method = m.group(2).upper()
            line_no = code[: m.start()].count("\n") + 1
            norm_p = cls._normalize_path(raw_path)
            endpoints.append(
                ApiEndpoint(
                    repo_id=repo_id,
                    file_path=file_path,
                    http_method=method,
                    path=norm_p,
                    symbol_name=f"client_{method}_{norm_p.split('/')[-1]}",
                    line_no=line_no,
                )
            )

        return endpoints

    @classmethod
    def extract_backend_endpoints(cls, repo_id: str, file_path: str, code: str) -> List[ApiEndpoint]:
        """Extracts Spring Boot route annotations from Java controllers."""
        endpoints = []
        # Base controller path if any
        base_path = ""
        base_match = re.search(r"@RequestMapping\s*\(\s*(?:value\s*=\s*)?['\"]([^'\"]+)['\"]", code)
        if base_match:
            base_path = base_match.group(1).strip()

        # Method level routes
        mapping_pattern = re.finditer(
            r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?['\"]?([^'\"\)]*)['\"]?",
            code,
        )
        for m in mapping_pattern:
            if base_match and m.start() == base_match.start():
                # Skip the class-level @RequestMapping annotation
                continue
            annotation = m.group(1)
            sub_path = m.group(2).strip()
            full_path = cls._normalize_path(f"{base_path}/{sub_path}")

            method = "GET"
            if annotation == "PostMapping":
                method = "POST"
            elif annotation == "PutMapping":
                method = "PUT"
            elif annotation == "DeleteMapping":
                method = "DELETE"
            elif annotation == "RequestMapping":
                method = "GET"

            # Search method name following annotation
            snippet = code[m.end() : m.end() + 200]
            func_m = re.search(r"(?:public\s+)?[A-Za-z0-9_<>[\]]+\s+([A-Za-z0-9_]+)\s*\(", snippet)
            func_name = func_m.group(1) if func_m else "handleRequest"
            line_no = code[: m.start()].count("\n") + 1

            endpoints.append(
                ApiEndpoint(
                    repo_id=repo_id,
                    file_path=file_path,
                    http_method=method,
                    path=full_path,
                    symbol_name=func_name,
                    line_no=line_no,
                )
            )

        return endpoints

    @classmethod
    def match_contracts(
        cls,
        frontend_endpoints: List[ApiEndpoint],
        backend_endpoints: List[ApiEndpoint],
    ) -> List[ApiContract]:
        """Matches endpoints across repositories and assigns graded evidence levels."""
        contracts = []
        for fe in frontend_endpoints:
            for be in backend_endpoints:
                level, conf = cls._evaluate_match(fe, be)
                if level != EvidenceLevel.UNKNOWN:
                    contract_id = f"contract::{fe.repo_id}::{be.repo_id}::{fe.path}"
                    contracts.append(
                        ApiContract(
                            contract_id=contract_id,
                            frontend_endpoint=fe,
                            backend_endpoint=be,
                            evidence_level=level,
                            confidence=conf,
                            matched_path=be.path,
                        )
                    )
        return contracts

    @classmethod
    def to_cross_repo_edges(cls, contracts: List[ApiContract]) -> List[CrossRepoEdge]:
        """Transforms API contracts into persistent CrossRepoEdges."""
        edges = []
        for c in contracts:
            src_uri = f"repo://{c.frontend_endpoint.repo_id}/{c.frontend_endpoint.file_path}#{c.frontend_endpoint.symbol_name}"
            tgt_uri = f"repo://{c.backend_endpoint.repo_id}/{c.backend_endpoint.file_path}#{c.backend_endpoint.symbol_name}"
            edge_key = f"edge://{src_uri}->API_CALLS->{tgt_uri}"

            edges.append(
                CrossRepoEdge(
                    edge_key=edge_key,
                    source_repo=c.frontend_endpoint.repo_id,
                    source_snapshot="current",
                    source_entity=src_uri,
                    edge_type="API_CALLS",
                    target_repo=c.backend_endpoint.repo_id,
                    target_snapshot="current",
                    target_entity=tgt_uri,
                    evidence_level=c.evidence_level,
                    confidence=c.confidence,
                    evidence=[
                        {
                            "type": "API_CONTRACT",
                            "method": c.backend_endpoint.http_method,
                            "path": c.matched_path,
                        }
                    ],
                )
            )
        return edges

    @classmethod
    def _evaluate_match(cls, fe: ApiEndpoint, be: ApiEndpoint) -> Tuple[EvidenceLevel, float]:
        # Path equivalence with variable normalization e.g. /users/1 vs /users/{id}
        norm_fe = re.sub(r"/[0-9]+", "/{id}", fe.path)
        norm_be = re.sub(r"/[0-9]+", "/{id}", be.path)

        if norm_fe == norm_be:
            if fe.http_method == be.http_method:
                return EvidenceLevel.EXACT, 1.0
            return EvidenceLevel.STRONG, 0.90

        # Gateway prefix stripping: remove /api, /api/v1, /api/v2
        gw_prefix = re.compile(r"^/api(?:/v\d+)?")
        strip_fe = gw_prefix.sub("", norm_fe)
        strip_be = gw_prefix.sub("", norm_be)

        if strip_fe and strip_fe == strip_be:
            if fe.http_method == be.http_method:
                return EvidenceLevel.STRONG, 0.90
            return EvidenceLevel.HEURISTIC, 0.75

        # Strict multi-segment suffix matching: requires at least 2 common business path segments
        fe_segs = [s for s in norm_fe.split("/") if s and not s.startswith("{")]
        be_segs = [s for s in norm_be.split("/") if s and not s.startswith("{")]
        if len(fe_segs) >= 2 and len(be_segs) >= 2:
            min_common = min(len(fe_segs), len(be_segs))
            if min_common >= 2 and fe_segs[-2:] == be_segs[-2:]:
                if fe.http_method == be.http_method:
                    return EvidenceLevel.HEURISTIC, 0.70
                return EvidenceLevel.HEURISTIC, 0.60

        return EvidenceLevel.UNKNOWN, 0.0

    @staticmethod
    def _normalize_path(path: str) -> str:
        clean = path.strip()
        if not clean.startswith("/"):
            clean = "/" + clean
        return re.sub(r"/+", "/", clean).rstrip("/")
