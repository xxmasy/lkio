"""LKIO MVP7 (Impact Analysis Engine) Acceptance Test Gate
Verifies:
1. Strict read-only guarantee across source repositories (HELLO_FE, HELLO_BE, L2C_FE).
2. Multi-hop traversal across 1-hop (DIRECT), 2-hop (INDIRECT), and 3-hop (POTENTIAL).
3. Cross-project full-stack propagation (Database -> Service -> Controller -> API Client -> Frontend Page).
4. Shortest path & critical path evidence generation.
5. Actionable Human Review Flow generation.
"""

import os
from pathlib import Path
import subprocess
import pytest

from core.impact import (
    EvidenceKind,
    ImpactAnalysisEngine,
    ImpactHopLevel,
)

PROJECT_PATHS = {
    "HELLO_FE": Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello")),
    "HELLO_BE": Path(os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend")),
    "L2C_FE": Path(os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project")),
}


def get_git_status_porcelain(repo_path: Path) -> str:
    if not repo_path.exists():
        return ""
    res = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    return res.stdout.strip()


def test_mvp7_impact_acceptance_gate():
    engine = ImpactAnalysisEngine()

    # Gate 1: Source Project Strict Read-Only Verification (Pre-scan)
    status_before = {}
    for pkey, ppath in PROJECT_PATHS.items():
        if ppath.exists():
            status_before[pkey] = get_git_status_porcelain(ppath)

    # Gate 2: Construct Real Project Full-Stack Topology
    entities = {
        # Frontend HELLO_FE
        "PAGE:HELLO_FE:AdSetup": {
            "name": "AdSetup.vue",
            "entity_type": "PAGE",
            "project_key": "HELLO_FE",
            "path": "src/views/ads/components/AdSetup.vue",
        },
        "API:HELLO_FE:leadApi": {
            "name": "leadApi.ts",
            "entity_type": "API",
            "project_key": "HELLO_FE",
            "path": "src/api/leadApi.ts",
        },
        # Backend HELLO_BE
        "CONTROLLER:HELLO_BE:LeadController": {
            "name": "NorthAmericaSalesDailyReportController",
            "entity_type": "CONTROLLER",
            "project_key": "HELLO_BE",
            "path": "src/main/java/org/example/hahamarket/controller/NorthAmericaSalesDailyReportController.java",
        },
        "SERVICE:HELLO_BE:MetricsService": {
            "name": "NorthAmericaSalesDailyDetailMetricsService",
            "entity_type": "SERVICE",
            "project_key": "HELLO_BE",
            "path": "src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyDetailMetricsService.java",
        },
        "DB:HELLO_BE:ReportDTO": {
            "name": "NorthAmericaSalesDailyReportRowDTO",
            "entity_type": "DATABASE",
            "project_key": "HELLO_BE",
            "path": "src/main/java/org/example/hahamarket/pojo/vo/dto/NorthAmericaSalesDailyReportRowDTO.java",
        },
        # Frontend L2C_FE
        "PAGE:L2C_FE:Login": {
            "name": "login.vue",
            "entity_type": "PAGE",
            "project_key": "L2C_FE",
            "path": "apps/web-ele/src/views/_core/authentication/login.vue",
        },
        "API:L2C_FE:AuthApi": {
            "name": "auth.ts",
            "entity_type": "API",
            "project_key": "L2C_FE",
            "path": "apps/web-ele/src/api/core/auth.ts",
        },
    }

    relations = [
        # HELLO_FE internal
        {"subject_key": "PAGE:HELLO_FE:AdSetup", "object_key": "API:HELLO_FE:leadApi", "relation_type": "IMPORTS", "confidence": 1.0},
        # Cross-project API call: HELLO_FE -> HELLO_BE
        {"subject_key": "API:HELLO_FE:leadApi", "object_key": "CONTROLLER:HELLO_BE:LeadController", "relation_type": "API_CALLS", "confidence": 0.95},
        # HELLO_BE internal call
        {"subject_key": "CONTROLLER:HELLO_BE:LeadController", "object_key": "SERVICE:HELLO_BE:MetricsService", "relation_type": "CALLS", "confidence": 1.0},
        # HELLO_BE service -> DB mapping
        {"subject_key": "SERVICE:HELLO_BE:MetricsService", "object_key": "DB:HELLO_BE:ReportDTO", "relation_type": "QUERIES", "confidence": 1.0},
        # L2C_FE internal
        {"subject_key": "PAGE:L2C_FE:Login", "object_key": "API:L2C_FE:AuthApi", "relation_type": "IMPORTS", "confidence": 1.0},
    ]

    # Gate 3: Upstream Full-Stack Impact Propagation
    # When backend DB DTO changes, analyze all affected callers
    report = engine.analyze_impact(
        seed_keys=["DB:HELLO_BE:ReportDTO"],
        entities_by_key=entities,
        relations=relations,
        direction="both",
    )

    # Verify Multi-hop classifications
    node_map = {n.entity_key: n for n in report.affected_nodes}

    # 1-hop DIRECT: Service
    assert "SERVICE:HELLO_BE:MetricsService" in node_map
    assert node_map["SERVICE:HELLO_BE:MetricsService"].hop == 1
    assert node_map["SERVICE:HELLO_BE:MetricsService"].level == ImpactHopLevel.DIRECT

    # 2-hop INDIRECT: Controller
    assert "CONTROLLER:HELLO_BE:LeadController" in node_map
    assert node_map["CONTROLLER:HELLO_BE:LeadController"].hop == 2
    assert node_map["CONTROLLER:HELLO_BE:LeadController"].level == ImpactHopLevel.INDIRECT

    # 3-hop POTENTIAL: Cross-project API client in HELLO_FE
    assert "API:HELLO_FE:leadApi" in node_map
    assert node_map["API:HELLO_FE:leadApi"].hop == 3
    assert node_map["API:HELLO_FE:leadApi"].level == ImpactHopLevel.POTENTIAL

    # Gate 4: Cross-Project Propagation & Full-Stack Categories
    assert "HELLO_BE" in report.affected_projects
    assert "HELLO_FE" in report.affected_projects
    assert "L2C_FE" not in report.affected_projects  # L2C is isolated
    assert len(report.affected_apis) >= 1
    assert len(report.affected_services) >= 1
    assert report.overall_impact_level in ("HIGH", "CRITICAL")
    assert report.requires_human_review is True

    # Gate 5: Shortest & Critical Path
    assert report.shortest_path is not None
    assert report.critical_path is not None
    assert report.critical_path.hops >= 3
    assert "-->" in report.critical_path.description

    # Gate 6: Actionable Human Review Flow Generation
    checklist = engine.generate_review_checklist(report)
    assert checklist["status"] == "REQUIRES_HUMAN_REVIEW"
    assert checklist["scope"]["total_affected_entities"] >= 3
    assert len(checklist["recommended_actions"]) >= 2

    # Gate 7: Source Project Strict Read-Only Verification (Post-scan)
    for pkey, ppath in PROJECT_PATHS.items():
        if ppath.exists():
            status_after = get_git_status_porcelain(ppath)
            assert status_before[pkey] == status_after, (
                f"Project {pkey} was modified during impact analysis! "
                f"Before: {status_before[pkey]} | After: {status_after}"
            )
