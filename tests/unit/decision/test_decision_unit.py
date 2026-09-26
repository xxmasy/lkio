"""Unit tests for MVP6 Laya Decision Engine in core/decision/
"""

import pytest
from core.decision import (
    ActionGateDecision,
    ChangeImpactLevel,
    ConfidencePolicy,
    DecisionEngineFactory,
    DecisionQuestion,
    DecisionRequest,
    DecisionState,
    DecisionTask,
    EvidenceSufficiencyLevel,
    LayaDecisionEngine,
    QueryRouteDestination,
)


def test_confidence_policy_tiers():
    policy = ConfidencePolicy()

    # Tier 1: < 0.65 -> HUMAN
    assert policy.evaluate_tier(0.50) == ("HUMAN", True)

    # Tier 2: 0.65 <= c < 0.85 -> REVIEW
    assert policy.evaluate_tier(0.70) == ("REVIEW", True)

    # Tier 3: 0.85 <= c < 0.95 -> SECOND_CHECK
    assert policy.evaluate_tier(0.90) == ("SECOND_CHECK", True)

    # Tier 4: >= 0.95 -> POLICY_APPROVED
    assert policy.evaluate_tier(0.96) == ("POLICY_APPROVED", False)


def test_action_gate_strict_no_write_redline():
    engine = LayaDecisionEngine()

    mutative_actions = [
        "WRITE_FILE",
        "modify src/App.vue",
        "delete table",
        "overwrite config.json",
        "git push origin master",
        "patch source code",
    ]

    for action in mutative_actions:
        req = DecisionRequest(
            task=DecisionTask.ACTION_GATE,
            project_scope=["HELLO_FE"],
            state=DecisionState(target_action=action),
            question=DecisionQuestion(options=["AUTO", "REVIEW", "ESCALATE", "REJECT"]),
        )
        res = engine.decide(req)
        assert res.decision == ActionGateDecision.REJECT.value
        assert "DENIED_BY_READONLY_GATE" in res.rationale
        assert res.requires_human_review is True
        assert res.final_confidence == 1.0


def test_action_gate_read_only_authorization():
    engine = LayaDecisionEngine()
    req = DecisionRequest(
        task=DecisionTask.ACTION_GATE,
        project_scope=["HELLO_BE"],
        state=DecisionState(
            target_action="READ_CODE",
            evidence=[{"entity_key": "ENT:1"}, {"entity_key": "ENT:2"}, {"entity_key": "ENT:3"}],
            relations=[{"relation_type": "CALLS"}, {"relation_type": "IMPORTS"}],
        ),
        question=DecisionQuestion(options=["AUTO", "REVIEW", "ESCALATE", "REJECT"]),
    )
    res = engine.decide(req)
    assert res.decision in (ActionGateDecision.AUTO.value, ActionGateDecision.REVIEW.value)
    assert res.final_confidence >= 0.80


def test_change_impact_evaluation():
    engine = LayaDecisionEngine()

    # Case 1: Empty changes -> NONE
    req_none = DecisionRequest(
        task=DecisionTask.CHANGE_IMPACT,
        project_scope=["HELLO_BE"],
        state=DecisionState(changed_entities=[]),
        question=DecisionQuestion(options=["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    )
    assert engine.decide(req_none).decision == ChangeImpactLevel.NONE.value

    # Case 2: Database and API change -> CRITICAL
    req_critical = DecisionRequest(
        task=DecisionTask.CHANGE_IMPACT,
        project_scope=["HELLO_BE"],
        state=DecisionState(
            changed_entities=[
                {"path": "src/models/UserModel.java", "entity_type": "DATABASE"},
                {"path": "src/controllers/UserController.java", "entity_type": "CONTROLLER"},
            ],
            relations=[{"relation_type": "API_CALLS", "cross_project": True}],
            business_rules=[{"rule_id": "RULE_AUTH"}],
        ),
        question=DecisionQuestion(options=["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    )
    res_crit = engine.decide(req_critical)
    assert res_crit.decision == ChangeImpactLevel.CRITICAL.value
    assert res_crit.requires_human_review is True


def test_evidence_sufficiency_evaluation():
    engine = LayaDecisionEngine()

    # Case 1: 0 evidence -> INSUFFICIENT
    req_insuf = DecisionRequest(
        task=DecisionTask.EVIDENCE_SUFFICIENCY,
        state=DecisionState(evidence=[]),
        question=DecisionQuestion(options=["INSUFFICIENT", "PARTIAL", "SUFFICIENT", "STRONG"]),
    )
    assert engine.decide(req_insuf).decision == EvidenceSufficiencyLevel.INSUFFICIENT.value

    # Case 2: Multi-evidence with citations and graph -> STRONG
    req_strong = DecisionRequest(
        task=DecisionTask.EVIDENCE_SUFFICIENCY,
        state=DecisionState(
            evidence=[
                {"entity_key": "K1", "citation": "src/App.vue:10"},
                {"entity_key": "K2", "citation": "src/api.ts:25"},
                {"entity_key": "K3", "citation": "src/store.ts:50"},
            ],
            relations=[{"relation_type": "CALLS"}, {"relation_type": "IMPORTS"}],
        ),
        question=DecisionQuestion(options=["INSUFFICIENT", "PARTIAL", "SUFFICIENT", "STRONG"]),
    )
    assert engine.decide(req_strong).decision == EvidenceSufficiencyLevel.STRONG.value


def test_query_route_evaluation():
    engine = LayaDecisionEngine()

    routes = [
        ("这个 API 是什么时候第一次出现的？", QueryRouteDestination.EVENT.value),
        ("LeadService 依赖了哪些下游类？", QueryRouteDestination.GRAPH.value),
        ("请总结整个工程的架构总览与业务规则", QueryRouteDestination.WIKI.value),
        ("UserController 定义在哪个文件？", QueryRouteDestination.ENTITY.value),
        ("如何排查用户登录超时的异常", QueryRouteDestination.RAG.value),
    ]

    for query, expected_route in routes:
        req = DecisionRequest(
            task=DecisionTask.QUERY_ROUTE,
            state=DecisionState(query_text=query),
            question=DecisionQuestion(options=["ENTITY", "CODE", "GRAPH", "RAG", "EVENT", "WIKI", "HUMAN"]),
        )
        res = engine.decide(req)
        assert res.decision == expected_route


def test_factory_creation():
    engine = DecisionEngineFactory.create("laya")
    assert isinstance(engine, LayaDecisionEngine)

    with pytest.raises(ValueError):
        DecisionEngineFactory.create("unsupported_engine")
