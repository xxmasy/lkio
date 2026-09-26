"""Evidence Sufficiency Evaluator for MVP6 Laya Decision Engine
Evaluates sufficiency across ["INSUFFICIENT", "PARTIAL", "SUFFICIENT", "STRONG"].
"""

from core.decision.models import (
    DecisionRequest,
    DecisionResult,
    EvidenceSufficiencyLevel,
)
from core.decision.policy import ConfidencePolicy


class EvidenceSufficiencyEvaluator:
    """Evaluates whether the collected evidence grounding is sufficient to justify a decision."""

    def __init__(self, confidence_policy: ConfidencePolicy | None = None):
        self.policy = confidence_policy or ConfidencePolicy()

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        evidence = request.state.evidence
        relations = request.state.relations
        ev_count = len(evidence)

        # Check for citation validity
        cited_keys = sum(1 for e in evidence if e.get("entity_key") or e.get("citation"))

        if ev_count == 0:
            decision = EvidenceSufficiencyLevel.INSUFFICIENT.value
            prob = 0.96
            model_conf = 0.95
            ev_conf = 0.10
        elif ev_count < 3 or cited_keys == 0:
            decision = EvidenceSufficiencyLevel.PARTIAL.value
            prob = 0.85
            model_conf = 0.85
            ev_conf = 0.60
        elif ev_count >= 3 and len(relations) >= 2:
            decision = EvidenceSufficiencyLevel.STRONG.value
            prob = 0.92
            model_conf = 0.90
            ev_conf = 0.95
        else:
            decision = EvidenceSufficiencyLevel.SUFFICIENT.value
            prob = 0.88
            model_conf = 0.88
            ev_conf = 0.80

        graph_conf = min(1.0, 0.5 + len(relations) * 0.15)
        hist_acc = 0.90

        final_conf = self.policy.calculate_final_confidence(
            model_conf=model_conf,
            evidence_conf=ev_conf,
            graph_conf=graph_conf,
            historical_acc=hist_acc,
        )

        tier, requires_review = self.policy.evaluate_tier(final_conf)
        if decision in (EvidenceSufficiencyLevel.INSUFFICIENT.value, EvidenceSufficiencyLevel.PARTIAL.value):
            requires_review = True

        return DecisionResult(
            decision=decision,
            probability=prob,
            model_confidence=model_conf,
            evidence_confidence=ev_conf,
            graph_confidence=graph_conf,
            historical_accuracy=hist_acc,
            final_confidence=final_conf,
            requires_human_review=requires_review,
            model_version="laya-evidence-v1",
            policy_version="evidence-eval-v1",
            rationale=f"Evaluated {ev_count} evidence items ({cited_keys} citations) and {len(relations)} relations.",
            action_recommendation=tier,
        )
