"""Unit tests for Stage 2 Multi-Repository Reasoning, Identity, Contracts, and Impact.
Conforms to docs/LKIO_持续基础设施演进开发规范.md Section 4 (Stage 2 Gate).
"""

import pytest
from core.multirepo.models import (
    ApiContract,
    ApiEndpoint,
    CrossRepoEdge,
    DtoFieldLineage,
    EvidenceLevel,
    ScopedEntityKey,
)
from core.multirepo.api_matcher import ApiContractMatcher
from core.multirepo.dto_matcher import DtoContractMatcher
from core.multirepo.impact import (
    CrossRepoImpactAnalyzer,
    CrossRepoImpactNode,
    CrossRepoImpactResult,
)


def test_scoped_entity_key():
    key = ScopedEntityKey(
        repo_id="backend-service",
        snapshot_id="snap_123456",
        entity_id="src/controller/LeadController.java#getLeadById",
    )
    assert str(key) == "backend-service@snap_123456::src/controller/LeadController.java#getLeadById"
    assert key.repo_id == "backend-service"
    assert key.snapshot_id == "snap_123456"
    assert key.entity_id == "src/controller/LeadController.java#getLeadById"


def test_api_contract_matcher_extraction_and_matching():
    frontend_code = """
    import axios from 'axios';

    export async function fetchDailyMetrics(params) {
        return axios.get('/api/v1/lead/daily-metrics', { params });
    }

    export async function createLead(data) {
        return apiClient.post('/api/v1/lead/create', data);
    }
    """

    backend_code = """
    package com.example.lead.controller;

    @RestController
    @RequestMapping("/api/v1/lead")
    public class LeadController {

        @GetMapping("/daily-metrics")
        public ResponseEntity<DailyMetricsDTO> getDailyMetrics() {
            return ResponseEntity.ok(leadService.getDailyMetrics());
        }

        @PostMapping("/create")
        public ResponseEntity<Void> createLeadRecord(@RequestBody LeadCreateDTO dto) {
            leadService.create(dto);
            return ResponseEntity.ok().build();
        }
    }
    """

    fe_endpoints = ApiContractMatcher.extract_frontend_endpoints(
        repo_id="repo-fe",
        file_path="src/api/lead.ts",
        code=frontend_code,
    )
    assert len(fe_endpoints) == 2
    assert fe_endpoints[0].http_method == "GET"
    assert fe_endpoints[0].path == "/api/v1/lead/daily-metrics"
    assert fe_endpoints[1].http_method == "POST"
    assert fe_endpoints[1].path == "/api/v1/lead/create"

    be_endpoints = ApiContractMatcher.extract_backend_endpoints(
        repo_id="repo-be",
        file_path="src/controller/LeadController.java",
        code=backend_code,
    )
    assert len(be_endpoints) == 2
    assert be_endpoints[0].http_method == "GET"
    assert be_endpoints[0].path == "/api/v1/lead/daily-metrics"
    assert be_endpoints[0].symbol_name == "getDailyMetrics"
    assert be_endpoints[1].http_method == "POST"
    assert be_endpoints[1].path == "/api/v1/lead/create"
    assert be_endpoints[1].symbol_name == "createLeadRecord"

    # Match contracts
    contracts = ApiContractMatcher.match_contracts(fe_endpoints, be_endpoints)
    assert len(contracts) == 2

    c0 = contracts[0]
    assert c0.evidence_level == EvidenceLevel.EXACT
    assert c0.confidence == 1.0
    assert c0.matched_path == "/api/v1/lead/daily-metrics"

    # Convert to cross repo edges
    edges = ApiContractMatcher.to_cross_repo_edges(contracts)
    assert len(edges) == 2
    assert edges[0].edge_type == "API_CALLS"
    assert edges[0].source_repo == "repo-fe"
    assert edges[0].target_repo == "repo-be"
    assert edges[0].evidence_level == EvidenceLevel.EXACT


def test_dto_contract_matcher():
    ts_code = """
    export interface LeadMetricsDTO {
        leadCount: number;
        conversionRate: number;
        regionName: string;
        isQualified?: boolean;
    }
    """

    java_code = """
    package com.example.lead.dto;

    public class LeadMetricsDTO {
        private Integer leadCount;
        private BigDecimal conversionRate;
        private String regionName;
        private Boolean isQualified;
        private Long internalId;
    }
    """

    lineages = DtoContractMatcher.match_dto_lineage(
        frontend_uri="repo://repo-fe/src/types/lead.ts#LeadMetricsDTO",
        frontend_code=ts_code,
        backend_uri="repo://repo-be/src/dto/LeadMetricsDTO.java#LeadMetricsDTO",
        backend_code=java_code,
    )

    field_map = {l.frontend_field: l for l in lineages}
    assert "leadCount" in field_map
    assert "conversionRate" in field_map
    assert "regionName" in field_map
    assert "isQualified" in field_map
    assert "internalId" not in field_map  # Not present in TS
    assert field_map["regionName"].backend_type == "String"


def test_cross_repo_impact_provenance_and_cycle_safety():
    """Tests cross-repository traversal with cyclic dependencies and verifies Invariants I1~I4."""
    # Graph Topology:
    # Service A (repo-be) -> Controller A (repo-be) -> API Contract -> Client A (repo-fe) -> Component A (repo-fe)
    # Plus a cycle back: Component A (repo-fe) -> Gateway (repo-gateway) -> Service A (repo-be)
    edges = [
        CrossRepoEdge(
            edge_key="e1",
            source_repo="repo-be",
            source_snapshot="s1",
            source_entity="repo://repo-be/src/service/MetricService.java#calculate",
            edge_type="CALLED_BY",
            target_repo="repo-be",
            target_snapshot="s1",
            target_entity="repo://repo-be/src/controller/MetricController.java#getMetrics",
        ),
        CrossRepoEdge(
            edge_key="e2",
            source_repo="repo-be",
            source_snapshot="s1",
            source_entity="repo://repo-be/src/controller/MetricController.java#getMetrics",
            edge_type="API_CONTRACT",
            target_repo="repo-fe",
            target_snapshot="s1",
            target_entity="repo://repo-fe/src/api/metricApi.ts#fetchMetrics",
        ),
        CrossRepoEdge(
            edge_key="e3",
            source_repo="repo-fe",
            source_snapshot="s1",
            source_entity="repo://repo-fe/src/api/metricApi.ts#fetchMetrics",
            edge_type="IMPORTED_BY",
            target_repo="repo-fe",
            target_snapshot="s1",
            target_entity="repo://repo-fe/src/views/MetricDashboard.vue#render",
        ),
        # Cycle edge: Component A -> Gateway
        CrossRepoEdge(
            edge_key="e4_cycle",
            source_repo="repo-fe",
            source_snapshot="s1",
            source_entity="repo://repo-fe/src/views/MetricDashboard.vue#render",
            edge_type="CALLS_GATEWAY",
            target_repo="repo-gateway",
            target_snapshot="s1",
            target_entity="repo://repo-gateway/src/routes.js#proxy",
        ),
        # Cycle back: Gateway -> Service A
        CrossRepoEdge(
            edge_key="e5_cycle_back",
            source_repo="repo-gateway",
            source_snapshot="s1",
            source_entity="repo://repo-gateway/src/routes.js#proxy",
            edge_type="ROUTES_TO",
            target_repo="repo-be",
            target_snapshot="s1",
            target_entity="repo://repo-be/src/service/MetricService.java#calculate",
        ),
        # Alternative path (2 hops) to MetricDashboard:
        CrossRepoEdge(
            edge_key="e6_alt",
            source_repo="repo-be",
            source_snapshot="s1",
            source_entity="repo://repo-be/src/service/MetricService.java#calculate",
            edge_type="DIRECT_EVENT",
            target_repo="repo-fe",
            target_snapshot="s1",
            target_entity="repo://repo-fe/src/views/MetricDashboard.vue#render",
        ),
    ]

    analyzer = CrossRepoImpactAnalyzer(max_depth=3)
    seed = "repo://repo-be/src/service/MetricService.java#calculate"

    result = analyzer.analyze_cross_repo_impact([seed], edges)

    # Invariant I1: Cycle safety (terminates, is_cycle_safe is True)
    assert result.is_cycle_safe is True

    # Invariant I3: Depth bound (no node > depth 3)
    assert result.depth_violation_count == 0
    for node in result.affected_nodes.values():
        assert node.depth <= 3

    # Invariant I4: Shortest hop preservation
    # Notice: MetricDashboard is reachable via 1-hop (e6_alt) and 3-hops (e1 -> e2 -> e3).
    dashboard_node = result.affected_nodes["repo://repo-fe/src/views/MetricDashboard.vue#render"]
    assert dashboard_node.depth == 1  # Shortest hop (1) retained!
    assert dashboard_node.impact_level == "DIRECT"
    # Evidence accumulation across both paths
    assert "e6_alt" in dashboard_node.evidence_sources

    # MetricController is 1 hop
    controller_node = result.affected_nodes["repo://repo-be/src/controller/MetricController.java#getMetrics"]
    assert controller_node.depth == 1
    assert controller_node.impact_level == "DIRECT"

    # fetchMetrics is 2 hops (via MetricController)
    fe_api_node = result.affected_nodes["repo://repo-fe/src/api/metricApi.ts#fetchMetrics"]
    assert fe_api_node.depth == 2
    assert fe_api_node.impact_level == "INDIRECT"


def test_api_contract_ambiguity_detection_and_candidate_ranking():
    fe_code = "export async function getUser() { return axios.get('/api/user'); }"
    fe_endpoints = ApiContractMatcher.extract_frontend_endpoints("fe-web", "src/api/user.ts", fe_code)

    # 3 backend services all declaring /api/user:
    # 1. user-service (primary)
    # 2. admin-service (competing)
    # 3. mock-service (penalized)
    be_user = ApiContractMatcher.extract_backend_endpoints(
        "user-service",
        "UserController.java",
        "@RestController\n@RequestMapping('/api')\npublic class UserController { @GetMapping('/user') public UserDTO get() {} }",
    )
    be_admin = ApiContractMatcher.extract_backend_endpoints(
        "admin-service",
        "AdminUserController.java",
        "@RestController\n@RequestMapping('/api')\npublic class AdminUserController { @GetMapping('/user') public UserDTO get() {} }",
    )
    be_mock = ApiContractMatcher.extract_backend_endpoints(
        "mock-service",
        "MockUserController.java",
        "@RestController\n@RequestMapping('/api')\npublic class MockUserController { @GetMapping('/user') public UserDTO get() {} }",
    )

    all_be = be_user + be_admin + be_mock
    ranked = ApiContractMatcher.match_ranked_contracts(fe_endpoints, all_be)

    assert len(ranked) == 1
    contract = ranked[0]
    assert len(contract.candidates) == 3

    # Ambiguity detection triggered due to competing user-service vs admin-service
    assert contract.is_ambiguous is True
    assert "Ambiguous contract mapping" in contract.ambiguity_details
    assert "user-service" in contract.ambiguity_details
    assert "admin-service" in contract.ambiguity_details

    # Mock service is ranked last due to penalty
    assert contract.candidates[-1].backend_endpoint.repo_id == "mock-service"
    assert "Penalized: mock repository" in contract.candidates[-1].evidence_rationale
    assert contract.candidates[-1].confidence < contract.candidates[0].confidence

