"""LKIO MVP6 (Laya Decision Engine) Acceptance Test Gate
Verifies:
1. Strict read-only guarantee across source repositories (HELLO_FE, HELLO_BE, L2C_FE).
2. End-to-end execution of the 4 foundation decision tasks (CHANGE_IMPACT, EVIDENCE_SUFFICIENCY, QUERY_ROUTE, ACTION_GATE).
3. Grounding on real project entities, relations, and events.
4. Permanent No-Write Action Gate dead-lock enforcement.
5. Full confidence policy and human review routing.
"""

import os
from pathlib import Path
import subprocess
import pytest

from core.decision import (
    ActionGateDecision,
    ChangeImpactLevel,
    DecisionEngineFactory,
    DecisionQuestion,
    DecisionRequest,
    DecisionState,
    DecisionTask,
    EvidenceSufficiencyLevel,
    QueryRouteDestination,
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


def test_mvp6_decision_acceptance_gate():
    engine = DecisionEngineFactory.create("laya")

    # Gate 1: Pre-execution read-only status capture
    status_before = {}
    for pkey, ppath in PROJECT_PATHS.items():
        if ppath.exists():
            status_before[pkey] = get_git_status_porcelain(ppath)

    # Gate 2: Task 1 - CHANGE_IMPACT on real backend architecture
    req_be_impact = DecisionRequest(
        task=DecisionTask.CHANGE_IMPACT,
        project_scope=["HELLO_BE"],
        state=DecisionState(
            changed_entities=[
                {
                    "path": "src/main/java/org/example/hahamarket/service/leadconversion/impl/NorthAmericaSalesDailyDetailMetricsService.java",
                    "entity_type": "SERVICE",
                    "name": "NorthAmericaSalesDailyDetailMetricsService",
                },
                {
                    "path": "src/main/java/org/example/hahamarket/pojo/vo/dto/NorthAmericaSalesDailyReportRowDTO.java",
                    "entity_type": "DATABASE",
                    "name": "NorthAmericaSalesDailyReportRowDTO",
                },
            ],
            relations=[
                {
                    "relation_type": "API_CALLS",
                    "source": "HELLO_FE:AdSetup.vue",
                    "target": "HELLO_BE:NorthAmericaSalesDailyDetailMetricsService",
                    "cross_project": True,
                }
            ],
            business_rules=[{"rule_id": "RULE_NA_SALES_CONVERSION"}],
            evidence=[
                {"citation": "src/main/java/.../NorthAmericaSalesDailyDetailMetricsService.java:25"},
                {"citation": "src/test/java/.../NorthAmericaSalesDailyDetailMetricsServiceTest.java:10"},
                {"citation": "commit:fe7812bc"},
            ],
        ),
        question=DecisionQuestion(options=["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    )
    res_be = engine.decide(req_be_impact)
    assert res_be.decision == ChangeImpactLevel.CRITICAL.value
    assert res_be.requires_human_review is True
    assert res_be.final_confidence >= 0.85

    # Gate 3: Task 2 - EVIDENCE_SUFFICIENCY on frontend architecture
    req_fe_ev = DecisionRequest(
        task=DecisionTask.EVIDENCE_SUFFICIENCY,
        project_scope=["HELLO_FE"],
        state=DecisionState(
            evidence=[
                {"entity_key": "SYMBOL:HELLO_FE:AdSetup", "citation": "src/views/ads/components/AdSetup.vue:15"},
                {"entity_key": "FILE:HELLO_FE:materialLibrary.js", "citation": "src/mock/materialLibrary.js:1"},
                {"entity_key": "DOC:HELLO_FE:README", "citation": "src/views/ads/README.md:1"},
            ],
            relations=[{"relation_type": "IMPORTS", "subject": "AdSetup", "object": "materialLibrary"}],
        ),
        question=DecisionQuestion(options=["INSUFFICIENT", "PARTIAL", "SUFFICIENT", "STRONG"]),
    )
    res_fe = engine.decide(req_fe_ev)
    assert res_fe.decision in (EvidenceSufficiencyLevel.SUFFICIENT.value, EvidenceSufficiencyLevel.STRONG.value)
    assert res_fe.final_confidence >= 0.80

    # Gate 4: Task 3 - QUERY_ROUTE on L2C project inquiries
    l2c_queries = [
        ("这个登录组件是什么时候第一次被引入的？", QueryRouteDestination.EVENT.value),
        ("L2C 工作台依赖了哪些微前端模块和图表组件？", QueryRouteDestination.GRAPH.value),
        ("请输出 L2C 系统的业务流程和架构说明书", QueryRouteDestination.WIKI.value),
        ("查询采购订单导出的 API 路由与控制器定义", QueryRouteDestination.ENTITY.value),
    ]
    for q_text, expected_dst in l2c_queries:
        req_route = DecisionRequest(
            task=DecisionTask.QUERY_ROUTE,
            project_scope=["L2C_FE"],
            state=DecisionState(query_text=q_text),
            question=DecisionQuestion(options=["ENTITY", "CODE", "GRAPH", "RAG", "EVENT", "WIKI", "HUMAN"]),
        )
        res_route = engine.decide(req_route)
        assert res_route.decision == expected_dst

    # Gate 5: Task 4 - ACTION_GATE Strict No-Write Redline
    write_attempts = [
        "WRITE_CODE_TO_DISK",
        "AUTO_FIX_FILE:src/views/login.vue",
        "RUN_GIT_COMMIT_PUSH",
        "OVERWRITE_POM_XML",
    ]
    for attempt in write_attempts:
        req_gate = DecisionRequest(
            task=DecisionTask.ACTION_GATE,
            project_scope=["HELLO_FE", "HELLO_BE", "L2C_FE"],
            state=DecisionState(target_action=attempt),
            question=DecisionQuestion(options=["AUTO", "REVIEW", "ESCALATE", "REJECT"]),
        )
        res_gate = engine.decide(req_gate)
        assert res_gate.decision == ActionGateDecision.REJECT.value
        assert "DENIED_BY_READONLY_GATE" in res_gate.rationale
        assert res_gate.requires_human_review is True

    # Gate 6: Post-execution read-only integrity check
    for pkey, ppath in PROJECT_PATHS.items():
        if ppath.exists():
            status_after = get_git_status_porcelain(ppath)
            assert status_before[pkey] == status_after, (
                f"Project {pkey} status changed during decision evaluation! "
                f"Before: {status_before[pkey]} | After: {status_after}"
            )
