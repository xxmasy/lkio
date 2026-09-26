"""Ground Truth Test Suite Generator for LKIO-Bench v1.0.
Constructs realistic, uncontaminated evaluation cases for all 15 benchmark layers.
Ground truth targets correspond to real entities and relationships across:
- HELLO_FE (Vue 3, Pinia, Axios, Lead components)
- HELLO_BE (Spring Boot, NorthAmericaSalesDailyReport, LeadController, MetricsService)
- L2C_FE (Enterprise marketing dashboard, mock APIs)
"""

from typing import Any
from benchmarks.lkio_bench.models import BenchmarkSplit


class GroundTruthSuite:
    """Provides ground-truth datasets for each of the 15 evaluation layers."""

    @staticmethod
    def get_layer01_semantic_cases() -> list[dict[str, Any]]:
        """Layer 1: Semantic Retrieval Test Cases."""
        return [
            {
                "id": "sem_001",
                "query": "Where is the business logic for calculating North America Sales Daily detail metrics?",
                "gold_files": [
                    "src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyDetailMetricsService.java",
                    "src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyReportServiceImpl.java",
                ],
                "split": BenchmarkSplit.TEST.value,
            },
            {
                "id": "sem_002",
                "query": "Facebook lead conversion webhook ingestion and normalize handler",
                "gold_files": [
                    "src/main/java/org/example/hahamarket/controller/LeadController.java",
                    "src/main/java/org/example/hahamarket/service/LeadService.java",
                ],
                "split": BenchmarkSplit.TEST.value,
            },
            {
                "id": "sem_003",
                "query": "Frontend lead marketing form and conversion UI view",
                "gold_files": [
                    "src/views/ads/components/AdSetup.vue",
                    "src/api/leadApi.ts",
                ],
                "split": BenchmarkSplit.TEST.value,
            },
            {
                "id": "sem_004",
                "query": "L2C enterprise marketing cockpit analytics and dashboard",
                "gold_files": [
                    "apps/web-ele/src/views/dashboard/cockpit/index.vue",
                    "apps/web-ele/src/router/routes/modules/marketing.ts",
                ],
                "split": BenchmarkSplit.TEST.value,
            },
        ]

    @staticmethod
    def get_layer02_symbol_cases() -> list[dict[str, Any]]:
        """Layer 2: Symbol Retrieval (AST core benchmark)."""
        return [
            {
                "id": "sym_001",
                "query": "Which DTO represents the North America sales daily report row fields?",
                "gold_symbol": "NorthAmericaSalesDailyReportRowDTO",
                "gold_file": "NorthAmericaSalesDailyReportRowDTO.java",
                "split": BenchmarkSplit.TEST.value,
            },
            {
                "id": "sym_002",
                "query": "Which service method computes conversion rates and aggregates daily call metrics?",
                "gold_symbol": "calculateDailyDetailMetrics",
                "gold_file": "NorthAmericaSalesDailyDetailMetricsService.java",
                "split": BenchmarkSplit.TEST.value,
            },
            {
                "id": "sym_003",
                "query": "Which frontend API client function sends lead conversion query requests?",
                "gold_symbol": "fetchLeadConversionList",
                "gold_file": "leadApi.ts",
                "split": BenchmarkSplit.TEST.value,
            },
        ]

    @staticmethod
    def get_layer03_dependency_cases() -> list[dict[str, Any]]:
        """Layer 3: Multi-hop Dependency Retrieval Ground Truth."""
        return [
            {
                "id": "dep_001",
                "seed": "SERVICE:HELLO_BE:MetricsService",
                "gold_hop1": ["CONTROLLER:HELLO_BE:LeadController", "REPOSITORY:HELLO_BE:MetricsRepo"],
                "gold_hop2": ["API:HELLO_FE:leadApi", "TABLE:HELLO_BE:daily_metrics"],
                "gold_hop3": ["COMP:HELLO_FE:AdSetup", "STORE:HELLO_FE:leadStore"],
                "split": BenchmarkSplit.TEST.value,
            }
        ]

    @staticmethod
    def get_layer04_cycle_safety_fixtures() -> list[dict[str, Any]]:
        """Layer 4: Five Cycle Topologies mandated by Section 6:
        - Case A: Simple Cycle (A -> B -> C -> A)
        - Case B: Inner Cycle (A -> B -> C, C -> D -> B)
        - Case C: Multi-cycle (A -> B -> C -> A, A -> D -> E -> D)
        - Case D: Cycle + Bypass (A -> B -> C -> D, B -> E, D -> F -> E)
        - Case E: Cross-layer Cycle (Frontend -> API -> Service -> Repo -> Frontend)
        """
        return [
            {
                "id": "case_a_simple",
                "name": "Case A: Simple Cycle",
                "seed": "A",
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                    {"subject_key": "C", "object_key": "A"},
                ],
                "expected_nodes": {"B", "C"},
            },
            {
                "id": "case_b_inner",
                "name": "Case B: Inner Cycle",
                "seed": "A",
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                    {"subject_key": "C", "object_key": "D"},
                    {"subject_key": "D", "object_key": "B"},
                ],
                "expected_nodes": {"B", "C", "D"},
            },
            {
                "id": "case_c_multi",
                "name": "Case C: Multi-cycle",
                "seed": "A",
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                    {"subject_key": "C", "object_key": "A"},
                    {"subject_key": "A", "object_key": "D"},
                    {"subject_key": "D", "object_key": "E"},
                    {"subject_key": "E", "object_key": "D"},
                ],
                "expected_nodes": {"B", "C", "D", "E"},
            },
            {
                "id": "case_d_bypass",
                "name": "Case D: Cycle + Bypass",
                "seed": "A",
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                    {"subject_key": "C", "object_key": "D"},
                    {"subject_key": "D", "object_key": "C"},
                    {"subject_key": "B", "object_key": "E"},
                    {"subject_key": "D", "object_key": "F"},
                    {"subject_key": "F", "object_key": "E"},
                ],
                "expected_nodes": {"B", "C", "D", "E"},
            },
            {
                "id": "case_e_cross_layer",
                "name": "Case E: Cross-layer Cycle",
                "seed": "FE_View",
                "relations": [
                    {"subject_key": "FE_View", "object_key": "API_Client"},
                    {"subject_key": "API_Client", "object_key": "BE_Controller"},
                    {"subject_key": "BE_Controller", "object_key": "BE_Service"},
                    {"subject_key": "BE_Service", "object_key": "BE_Repo"},
                    {"subject_key": "BE_Repo", "object_key": "FE_View"},
                ],
                "expected_nodes": {"API_Client", "BE_Controller", "BE_Service"},
            },
        ]

    @staticmethod
    def get_layer05_shortest_hop_fixtures() -> list[dict[str, Any]]:
        """Layer 5: Shortest-Hop Preservation Topologies (Section 7)."""
        return [
            {
                "id": "sh_01",
                "seed": "A",
                "target": "D",
                "expected_hop": 2,
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                    {"subject_key": "C", "object_key": "D"},
                    {"subject_key": "A", "object_key": "X"},
                    {"subject_key": "X", "object_key": "D"},
                ],
            },
            {
                "id": "sh_02",
                "seed": "A",
                "target": "D",
                "expected_hop": 2,
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                    {"subject_key": "C", "object_key": "D"},
                    {"subject_key": "A", "object_key": "X"},
                    {"subject_key": "X", "object_key": "Y"},
                    {"subject_key": "Y", "object_key": "D"},
                    {"subject_key": "A", "object_key": "M"},
                    {"subject_key": "M", "object_key": "D"},
                ],
            },
            {
                "id": "sh_03",
                "seed": "A",
                "target": "D",
                "expected_hop": 2,
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                    {"subject_key": "A", "object_key": "X"},
                    {"subject_key": "X", "object_key": "D"},
                    {"subject_key": "A", "object_key": "M"},
                    {"subject_key": "M", "object_key": "N"},
                    {"subject_key": "N", "object_key": "D"},
                    {"subject_key": "A", "object_key": "P"},
                    {"subject_key": "P", "object_key": "Q"},
                    {"subject_key": "Q", "object_key": "R"},
                    {"subject_key": "R", "object_key": "D"},
                ],
            },
        ]

    @staticmethod
    def get_layer06_depth_boundary_fixture() -> dict[str, Any]:
        """Layer 6: Depth Boundary Fixture (Section 8)."""
        return {
            "seed": "N0",
            "chain": ["N0", "N1", "N2", "N3", "N4", "N5"],
            "relations": [
                {"subject_key": f"N{i}", "object_key": f"N{i+1}"} for i in range(5)
            ],
            "boundaries": [1, 2, 3, 5],
        }

    @staticmethod
    def get_layer07_temporal_git_cases() -> list[dict[str, Any]]:
        """Layer 7: Temporal Git Reasoning Cases (Section 9)."""
        return [
            {
                "id": "temp_001",
                "query_type": "COMMIT_IDENTIFICATION",
                "target_relation": "NorthAmericaSalesDailyReportRowDTO --> NorthAmericaSalesDailyDetailMetricsService",
                "expected_commit": "83b1069",
                "description": "When was the North America sales metric DTO first wired to MetricsService?",
            },
            {
                "id": "temp_002",
                "query_type": "FUNCTION_ADJUSTMENT",
                "symbol": "calculateDailyDetailMetrics",
                "expected_commit": "83b1069",
                "change_type": "MODIFIED",
            },
            {
                "id": "temp_003",
                "query_type": "RECENT_STRUCTURAL_DIFF",
                "module": "leadconversion",
                "commits_window": 5,
                "expected_symbols": ["NorthAmericaSalesDailyDetailMetricsService", "NorthAmericaSalesDailyReportServiceImpl"],
            },
        ]

    @staticmethod
    def get_layer08_historical_state_cases() -> list[dict[str, Any]]:
        """Layer 8: Historical State Reconstruction Cases (Section 10)."""
        return [
            {
                "id": "hist_001",
                "commit_tag": "Commit_V1_Snapshot",
                "subject": "MetricsService",
                "object": "LeadController",
                "expected_dependent": True,
            },
            {
                "id": "hist_002",
                "commit_tag": "Commit_Initial_Bootstrap",
                "subject": "MetricsService",
                "object": "L2C_Cockpit",
                "expected_dependent": False,
            },
        ]

    @staticmethod
    def get_layer09_impact_analysis_cases() -> list[dict[str, Any]]:
        """Layer 9: Impact Analysis Cases (Section 11)."""
        return [
            {
                "id": "imp_001",
                "modified_entity": "SERVICE:HELLO_BE:MetricsService",
                "gold_direct": ["CONTROLLER:HELLO_BE:LeadController", "REPOSITORY:HELLO_BE:MetricsRepo"],
                "gold_indirect": ["API:HELLO_FE:leadApi"],
                "gold_potential": ["COMP:HELLO_FE:AdSetup"],
            }
        ]

    @staticmethod
    def get_layer10_false_positive_cases() -> list[dict[str, Any]]:
        """Layer 10: False Positive Impact (Anti Over-Propagation) Cases (Section 12)."""
        return [
            {
                "id": "fp_001",
                "seed": "A",
                "true_affected": ["B", "C"],
                "unrelated_distractors": ["X", "Y", "Z", "W"],
                "relations": [
                    {"subject_key": "A", "object_key": "B"},
                    {"subject_key": "B", "object_key": "C"},
                ],
            }
        ]

    @staticmethod
    def get_layer11_multipath_evidence_cases() -> list[dict[str, Any]]:
        """Layer 11: Multi-Path Evidence Accumulation Cases (Section 13)."""
        return [
            {
                "id": "mpe_001",
                "seed": "A",
                "target": "D",
                "expected_hop": 2,
                "expected_evidence_sources": ["CALLS", "IMPORTS"],
                "relations": [
                    {"subject_key": "A", "object_key": "B", "relation_type": "CALLS"},
                    {"subject_key": "B", "object_key": "D", "relation_type": "CALLS"},
                    {"subject_key": "A", "object_key": "C", "relation_type": "IMPORTS"},
                    {"subject_key": "C", "object_key": "D", "relation_type": "IMPORTS"},
                ],
            }
        ]

    @staticmethod
    def get_layer12_cross_stack_cases() -> list[dict[str, Any]]:
        """Layer 12: Cross-Frontend/Backend Reasoning (Section 14)."""
        return [
            {
                "id": "cross_001",
                "frontend_mutation": "COMP:HELLO_FE:AdSetup",
                "gold_frontend_chain": ["COMP:HELLO_FE:AdSetup", "STORE:HELLO_FE:leadStore", "API:HELLO_FE:leadApi"],
                "gold_backend_chain": [
                    "CONTROLLER:HELLO_BE:LeadController",
                    "SERVICE:HELLO_BE:LeadService",
                    "DTO:HELLO_BE:LeadDTO",
                    "REPOSITORY:HELLO_BE:LeadRepository",
                ],
            }
        ]
