"""Decision Governance Stress & Adversarial Test Suite (Stage 4 Section 6.8).

Proves the overarching invariant:
    Confidence != Permission
    Confidence -> Risk -> Policy -> Permission
Guarantees that high model confidence never bypasses high risk, tests failures,
scope deviations, anomalous outputs, missing evidence, or out-of-distribution shifts.
"""

import math
import pytest
from core.agent_loop.governance import DecisionGovernanceEngine
from core.agent_loop.models import (
    AgentTask,
    GovernanceChoice,
    GovernanceRisk,
    PostChangeValidation,
    PreChangeEvidence,
)


@pytest.fixture
def base_evidence():
    return PreChangeEvidence(
        target_entity="repo://repo/src/Service.java#run",
        references=[{"source": "Controller"}],
        dependencies=[{"dep": "Repo"}],
        direct_impact=["Service", "Controller"],
        risk_level="LOW",
    )


def test_high_confidence_high_risk_requires_human_signoff(base_evidence):
    """Scenario 1: High confidence (0.999) + High risk (Critical payment logic).
    Confidence CANNOT grant permission. Must require human sign-off.
    """
    task = AgentTask(
        task_id="STRESS-001",
        requirement="Alter core settlement payment rules",
        target_entity="repo://repo/src/Settlement.java#pay",
        declared_scope=["repo://repo/src/Settlement.java#pay", "Service", "Controller"],
        business_criticality="CRITICAL",
    )

    post_val = PostChangeValidation(
        snapshot_id="snap_1",
        actual_impact=["Service", "Controller"],
        test_passed=True,
    )

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=base_evidence,
        post_validation=post_val,
        calibrated_confidence=0.999,
    )

    assert res.choice == GovernanceChoice.REVIEW
    assert res.requires_human_signoff is True
    assert res.risk == GovernanceRisk.HIGH
    assert res.policy == "MANDATORY_HUMAN_SIGNOFF_FOR_HIGH_RISK"


def test_low_confidence_low_risk_routes_to_peer_review(base_evidence):
    """Scenario 2: Low confidence (0.68) + Low risk.
    Must require human peer review rather than automated allow.
    """
    task = AgentTask(
        task_id="STRESS-002",
        requirement="Tweak formatting log message",
        target_entity="repo://repo/src/Service.java#run",
        declared_scope=["repo://repo/src/Service.java#run", "Service", "Controller"],
        business_criticality="LOW",
    )

    post_val = PostChangeValidation(
        snapshot_id="snap_1",
        actual_impact=["Service", "Controller"],
        test_passed=True,
    )

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=base_evidence,
        post_validation=post_val,
        calibrated_confidence=0.68,
    )

    assert res.choice == GovernanceChoice.REVIEW
    assert res.requires_human_signoff is True
    assert res.policy == "MODERATE_CONFIDENCE_PEER_REVIEW"


def test_high_confidence_wrong_judgment_intercepted_by_regression_gate(base_evidence):
    """Scenario 3: Model is extremely confident (0.99) that the change is benign,
    but automated test suite failed. Regression Gate MUST intercept and BLOCK.
    """
    task = AgentTask(
        task_id="STRESS-003",
        requirement="Refactor algorithm",
        target_entity="repo://repo/src/Service.java#run",
        declared_scope=["repo://repo/src/Service.java#run", "Service", "Controller"],
        business_criticality="NORMAL",
    )

    post_val = PostChangeValidation(
        snapshot_id="snap_1",
        test_passed=False,
        regression_detected=True,
        regression_details="Unit test assertion failed on edge case -1",
    )

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=base_evidence,
        post_validation=post_val,
        calibrated_confidence=0.99,
    )

    assert res.choice == GovernanceChoice.BLOCK
    assert res.policy == "ZERO_REGRESSION_POLICY"
    assert "Regression detected" in res.reasons[0]


def test_test_passed_but_impact_breached_critical_scope(base_evidence):
    """Scenario 4: Tests pass, but impact blast radius breaches into undeclared critical entity."""
    task = AgentTask(
        task_id="STRESS-004",
        requirement="Add internal metric",
        target_entity="repo://repo/src/Service.java#run",
        declared_scope=["repo://repo/src/Service.java#run"],
        business_criticality="CRITICAL",
    )

    post_val = PostChangeValidation(
        snapshot_id="snap_1",
        actual_impact=["repo://repo/src/Service.java#run", "repo://billing/BillingEngine"],
        undeclared_impact=["repo://billing/BillingEngine"],
        scope_deviation=True,
        test_passed=True,
    )

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=base_evidence,
        post_validation=post_val,
        calibrated_confidence=0.95,
    )

    assert res.choice == GovernanceChoice.BLOCK
    assert res.policy == "CRITICAL_SCOPE_STRICT_BLOCK"


def test_unknown_out_of_distribution_scenario():
    """Scenario 5: Out-of-Distribution (OOD) task type."""
    task = AgentTask(
        task_id="STRESS-OOD-005",
        requirement="Deploy unverified binary plugin",
        target_entity="repo://repo/plugin.so",
        business_criticality="UNKNOWN_OOD",
    )

    evidence = PreChangeEvidence(
        target_entity="repo://repo/plugin.so",
        references=[{"source": "Loader"}],
        risk_level="MEDIUM",
    )
    post_val = PostChangeValidation(snapshot_id="snap_1", test_passed=True)

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=evidence,
        post_validation=post_val,
        calibrated_confidence=0.90,
    )

    assert res.choice == GovernanceChoice.REVIEW
    assert res.policy == "OUT_OF_DISTRIBUTION_HUMAN_TRIAGE"


def test_model_output_anomaly_blocked(base_evidence):
    """Scenario 6: Model outputs NaN, negative, or > 1.0 confidence."""
    task = AgentTask(
        task_id="STRESS-006",
        requirement="Minor fix",
        target_entity="repo://repo/src/Service.java#run",
    )
    post_val = PostChangeValidation(snapshot_id="snap_1", test_passed=True)

    for bad_conf in [float("nan"), -0.5, 1.5]:
        res = DecisionGovernanceEngine.evaluate(
            task=task,
            pre_evidence=base_evidence,
            post_validation=post_val,
            calibrated_confidence=bad_conf,
        )
        assert res.choice == GovernanceChoice.BLOCK
        assert res.policy == "ANOMALOUS_MODEL_OUTPUT_BLOCK"


def test_evidence_missing_blocked():
    """Scenario 7: Pre-change evidence is empty (no references, deps, or impact graph)."""
    task = AgentTask(
        task_id="STRESS-007",
        requirement="Refactor method",
        target_entity="repo://repo/src/Service.java#run",
    )
    empty_evidence = PreChangeEvidence(target_entity="repo://repo/src/Service.java#run")
    post_val = PostChangeValidation(snapshot_id="snap_1", test_passed=True)

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=empty_evidence,
        post_validation=post_val,
        calibrated_confidence=0.95,
    )

    assert res.choice == GovernanceChoice.BLOCK
    assert res.policy == "INSUFFICIENT_EVIDENCE_BLOCK"


def test_incomplete_topology_orphan_blocked(base_evidence):
    """Scenario 8: Target entity is an orphan or unknown namespace."""
    task = AgentTask(
        task_id="STRESS-008",
        requirement="Refactor ghost file",
        target_entity="unknown://repo/phantom.js",
    )
    post_val = PostChangeValidation(snapshot_id="snap_1", test_passed=True)

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=base_evidence,
        post_validation=post_val,
        calibrated_confidence=0.90,
    )

    assert res.choice == GovernanceChoice.BLOCK
    assert res.policy == "INCOMPLETE_TOPOLOGY_BLOCK"
