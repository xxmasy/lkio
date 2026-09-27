"""Unit tests for Stage 4 Agent Closed-Loop Feedback & Governance.
Conforms to docs/LKIO_持续基础设施演进开发规范.md Section 6 (Final Gate).
"""

import pytest
from core.agent_loop import (
    AgentRefactoringLoop,
    AgentTask,
    DecisionGovernanceEngine,
    GovernanceChoice,
    GovernanceRisk,
    PostChangeValidation,
    PreChangeEvidence,
)
from core.sdk import LKIO


@pytest.fixture
def agent_loop():
    sdk = LKIO(default_repo_id="test-agent-repo")
    return AgentRefactoringLoop(repo_id="test-agent-repo", sdk=sdk)


def test_stage4_pre_change_evidence_collection(agent_loop):
    task = AgentTask(
        task_id="TASK-001",
        requirement="Optimize Daily Metrics calculation query",
        target_entity="repo://test-agent-repo/src/service/MetricService.java#calculate",
        declared_scope=["repo://test-agent-repo/src/service/MetricService.java#calculate"],
        business_criticality="NORMAL",
    )

    evidence = agent_loop.collect_pre_change_evidence(task)
    assert evidence.target_entity == task.target_entity
    assert len(evidence.references) >= 2
    assert len(evidence.dependencies) > 0
    assert len(evidence.history) > 0
    assert len(evidence.direct_impact) > 0


def test_stage4_successful_safe_refactoring_flow(agent_loop):
    task = AgentTask(
        task_id="TASK-002",
        requirement="Add log statement in helper method",
        target_entity="src/Helper.java",
        declared_scope=[
            "src/Helper.java",
            "CONTROLLER:HELLO_BE:LeadController",
            "REPOSITORY:HELLO_BE:MetricsRepo",
        ],
        business_criticality="LOW",
    )

    old_files = {"src/Helper.java": "public class Helper { public void log() {} }"}
    new_files = {"src/Helper.java": "public class Helper { public void log() { System.out.println('ok'); } }"}

    audit = agent_loop.execute_workflow(
        task=task,
        old_files=old_files,
        new_files=new_files,
        commit_id="c_step_1",
        test_runner=lambda: True,  # Tests pass
    )

    assert audit.step_count == 7
    assert audit.completed_successfully is True
    assert audit.governance.choice == GovernanceChoice.ALLOW
    assert audit.governance.risk == GovernanceRisk.LOW
    assert audit.governance.requires_human_signoff is False
    assert audit.post_validation.test_passed is True
    assert audit.post_validation.snapshot_id


def test_stage4_regression_detection_blocks_execution(agent_loop):
    task = AgentTask(
        task_id="TASK-003",
        requirement="Refactor Billing Engine",
        target_entity="src/Billing.java",
        declared_scope=["src/Billing.java"],
        business_criticality="NORMAL",
    )

    old_files = {"src/Billing.java": "public class Billing { public double bill() { return 10.0; } }"}
    new_files = {"src/Billing.java": "public class Billing { public double bill() { return -1.0; } }"}

    # Simulate failing test suite
    audit = agent_loop.execute_workflow(
        task=task,
        old_files=old_files,
        new_files=new_files,
        commit_id="c_step_bad",
        test_runner=lambda: False,
    )

    assert audit.completed_successfully is False
    assert audit.governance.choice == GovernanceChoice.BLOCK
    assert audit.governance.risk == GovernanceRisk.HIGH
    assert audit.governance.policy == "ZERO_REGRESSION_POLICY"
    assert audit.post_validation.test_passed is False
    assert audit.post_validation.regression_detected is True


def test_stage4_high_risk_confidence_does_not_equal_permission(agent_loop):
    """Verifies Section 6.8: High criticality tasks ALWAYS require human review,
    even with high model confidence."""
    task = AgentTask(
        task_id="TASK-004",
        requirement="Upgrade Core Payment Authorization Logic",
        target_entity="src/PaymentAuth.java",
        declared_scope=[
            "src/PaymentAuth.java",
            "CONTROLLER:HELLO_BE:LeadController",
            "REPOSITORY:HELLO_BE:MetricsRepo",
        ],
        business_criticality="HIGH",  # High business criticality
    )

    old_files = {"src/PaymentAuth.java": "public class PaymentAuth { public void auth() {} }"}
    new_files = {"src/PaymentAuth.java": "public class PaymentAuth { public void auth() { /* secure */ } }"}

    audit = agent_loop.execute_workflow(
        task=task,
        old_files=old_files,
        new_files=new_files,
        commit_id="c_step_pay",
        test_runner=lambda: True,
    )

    # Even though tests pass and confidence is high, it MUST require human signoff
    assert audit.governance.choice == GovernanceChoice.REVIEW
    assert audit.governance.requires_human_signoff is True
    assert audit.governance.policy == "MANDATORY_HUMAN_SIGNOFF_FOR_HIGH_RISK"


def test_stage4_scope_deviation_on_critical_component_blocks():
    """Undeclared blast radius on a CRITICAL component results in BLOCK."""
    task = AgentTask(
        task_id="TASK-005",
        requirement="Refactor Database Core Driver",
        target_entity="src/DBDriver.java",
        declared_scope=["src/DBDriver.java"],
        business_criticality="CRITICAL",
    )

    pre_evidence = PreChangeEvidence(
        target_entity="src/DBDriver.java",
        risk_level="MEDIUM",
    )

    post_validation = PostChangeValidation(
        snapshot_id="snap_123",
        actual_impact=["src/DBDriver.java", "src/UnexpectedConsumer.java"],
        undeclared_impact=["src/UnexpectedConsumer.java"],
        scope_deviation=True,
        test_passed=True,
    )

    res = DecisionGovernanceEngine.evaluate(
        task=task,
        pre_evidence=pre_evidence,
        post_validation=post_validation,
        calibrated_confidence=0.98,
    )

    assert res.choice == GovernanceChoice.BLOCK
    assert res.policy == "CRITICAL_SCOPE_STRICT_BLOCK"
    assert res.risk == GovernanceRisk.HIGH
