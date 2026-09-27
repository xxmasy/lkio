"""Decision Governance Engine (Stage 4 Section 6.7 & 6.8).

Enforces production safety invariants:
- Confidence != Permission (High confidence cannot bypass high risk)
- Zero-tolerance for detected regressions
- Bounded scope deviation enforcement
- Multi-tier human sign-off policies
"""

from typing import Any, Dict, List
from core.agent_loop.models import (
    AgentTask,
    DecisionGovernanceResult,
    GovernanceChoice,
    GovernanceRisk,
    PostChangeValidation,
    PreChangeEvidence,
)


class DecisionGovernanceEngine:
    """Evaluates multi-factor repository evidence to produce binding governance verdicts."""

    @classmethod
    def evaluate(
        cls,
        task: AgentTask,
        pre_evidence: PreChangeEvidence,
        post_validation: PostChangeValidation,
        calibrated_confidence: float = 0.90,
    ) -> DecisionGovernanceResult:
        import math
        reasons: List[str] = []
        evidence: List[Dict[str, Any]] = []

        # 0.1 Model Output Anomaly Check
        if math.isnan(calibrated_confidence) or calibrated_confidence < 0.0 or calibrated_confidence > 1.0:
            reasons.append(f"Model output anomaly detected: invalid confidence value {calibrated_confidence}")
            evidence.append({"rule": "MODEL_ANOMALY_GATE", "confidence": calibrated_confidence})
            return DecisionGovernanceResult(
                choice=GovernanceChoice.BLOCK,
                score=0.0,
                confidence=0.0,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.HIGH,
                policy="ANOMALOUS_MODEL_OUTPUT_BLOCK",
                requires_human_signoff=True,
            )

        # 0.2 Evidence Completeness Check
        if pre_evidence is None or (
            not pre_evidence.references and not pre_evidence.dependencies and not pre_evidence.direct_impact
        ):
            reasons.append("Evidence missing: foundational repository graph paths and impact data are absent.")
            evidence.append({"rule": "EVIDENCE_COMPLETENESS", "status": "MISSING"})
            return DecisionGovernanceResult(
                choice=GovernanceChoice.BLOCK,
                score=0.15,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.HIGH,
                policy="INSUFFICIENT_EVIDENCE_BLOCK",
                requires_human_signoff=True,
            )

        # 0.3 Incomplete Topology / Orphan Entity Check
        if task.target_entity.startswith("unknown://") or task.target_entity in ("ORPHAN", "UNKNOWN"):
            reasons.append("Incomplete topology: target entity is not indexed in canonical repository graph.")
            evidence.append({"rule": "TOPOLOGY_COMPLETENESS", "target": task.target_entity})
            return DecisionGovernanceResult(
                choice=GovernanceChoice.BLOCK,
                score=0.20,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.HIGH,
                policy="INCOMPLETE_TOPOLOGY_BLOCK",
                requires_human_signoff=True,
            )

        # 0.4 Out-of-Distribution (OOD) Domain Shift Check
        if task.business_criticality == "UNKNOWN_OOD" or "OOD" in task.task_id:
            reasons.append("Out-of-distribution scenario detected; automated reasoning deferred to human triage.")
            evidence.append({"rule": "OOD_GATE", "task_id": task.task_id})
            return DecisionGovernanceResult(
                choice=GovernanceChoice.REVIEW,
                score=0.50,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.MEDIUM,
                policy="OUT_OF_DISTRIBUTION_HUMAN_TRIAGE",
                requires_human_signoff=True,
            )

        # 1. Hard Invariant: Regression Gate
        if not post_validation.test_passed or post_validation.regression_detected:
            reasons.append(
                f"Regression detected: {post_validation.regression_details or 'Automated tests failed'}"
            )
            evidence.append({"rule": "REGRESSION_GATE", "passed": False})
            return DecisionGovernanceResult(
                choice=GovernanceChoice.BLOCK,
                score=0.10,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.HIGH,
                policy="ZERO_REGRESSION_POLICY",
                requires_human_signoff=True,
            )

        # 2. Scope Deviation Check
        if post_validation.scope_deviation and post_validation.undeclared_impact:
            reasons.append(
                f"Undeclared impact blast radius detected: {post_validation.undeclared_impact}"
            )
            evidence.append(
                {"rule": "SCOPE_CONTAINMENT", "undeclared": post_validation.undeclared_impact}
            )

            # High criticality tasks cannot silently expand impact scope
            if task.business_criticality in ("HIGH", "CRITICAL"):
                reasons.append("Scope deviation on HIGH/CRITICAL business component is strictly blocked.")
                return DecisionGovernanceResult(
                    choice=GovernanceChoice.BLOCK,
                    score=0.25,
                    confidence=calibrated_confidence,
                    evidence=evidence,
                    reasons=reasons,
                    risk=GovernanceRisk.HIGH,
                    policy="CRITICAL_SCOPE_STRICT_BLOCK",
                    requires_human_signoff=True,
                )

        # 3. High Risk & Business Criticality Policy (Section 6.8: Confidence != Permission)
        is_high_risk = (
            task.business_criticality in ("HIGH", "CRITICAL")
            or pre_evidence.risk_level == "HIGH"
            or post_validation.scope_deviation
        )

        if is_high_risk:
            reasons.append(
                "High business criticality or broad blast radius requires human sign-off regardless of model confidence."
            )
            evidence.append(
                {
                    "rule": "HIGH_RISK_HUMAN_GOVERNANCE",
                    "criticality": task.business_criticality,
                    "confidence": calibrated_confidence,
                }
            )
            return DecisionGovernanceResult(
                choice=GovernanceChoice.REVIEW,
                score=0.75,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.HIGH,
                policy="MANDATORY_HUMAN_SIGNOFF_FOR_HIGH_RISK",
                requires_human_signoff=True,
            )

        # 4. Standard Low / Medium Risk Policies
        evidence.append({"rule": "EVIDENCE_COMPLETENESS", "status": "VERIFIED"})

        allow_threshold = 0.75 if task.business_criticality == "LOW" else 0.85

        if calibrated_confidence >= allow_threshold:
            reasons.append("All regression tests passed with zero undeclared impact and high evidence confidence.")
            return DecisionGovernanceResult(
                choice=GovernanceChoice.ALLOW,
                score=0.95,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.LOW,
                policy="AUTOMATED_ALLOW_SAFE_CHANGE",
                requires_human_signoff=False,
            )
        elif calibrated_confidence >= 0.65:
            reasons.append("Moderate confidence requires engineer peer review.")
            return DecisionGovernanceResult(
                choice=GovernanceChoice.REVIEW,
                score=0.72,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.MEDIUM,
                policy="MODERATE_CONFIDENCE_PEER_REVIEW",
                requires_human_signoff=True,
            )
        else:
            reasons.append("Low evidence confidence or insufficient test assertions.")
            return DecisionGovernanceResult(
                choice=GovernanceChoice.BLOCK,
                score=0.35,
                confidence=calibrated_confidence,
                evidence=evidence,
                reasons=reasons,
                risk=GovernanceRisk.MEDIUM,
                policy="INSUFFICIENT_EVIDENCE_BLOCK",
                requires_human_signoff=True,
            )
