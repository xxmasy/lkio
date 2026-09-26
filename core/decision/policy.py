"""Confidence Policy & Action Gate Enforcement for MVP6
Strictly implements Baseline Section 32:
- Confidence tier evaluation ([< 0.65, 0.65-0.85, 0.85-0.95, >= 0.95])
- Weighted multi-source confidence calculation (model + evidence + graph + history)
- Permanent No-Write Action Gate Redline across MVP0~MVP6
"""

from typing import Any
from core.decision.models import ActionGateDecision, DecisionRequest, DecisionResult


class ConfidencePolicy:
    """Calculates explainable final confidence and human review requirements."""

    def __init__(
        self,
        weight_model: float = 0.35,
        weight_evidence: float = 0.35,
        weight_graph: float = 0.20,
        weight_history: float = 0.10,
    ):
        self.w_m = weight_model
        self.w_e = weight_evidence
        self.w_g = weight_graph
        self.w_h = weight_history

    def calculate_final_confidence(
        self,
        model_conf: float,
        evidence_conf: float,
        graph_conf: float,
        historical_acc: float,
    ) -> float:
        """Weighted confidence computation as defined in Baseline Section 31 & 32."""
        raw_score = (
            self.w_m * model_conf
            + self.w_e * evidence_conf
            + self.w_g * graph_conf
            + self.w_h * historical_acc
        )
        return round(min(1.0, max(0.0, raw_score)), 4)

    def evaluate_tier(self, final_confidence: float) -> tuple[str, bool]:
        """Maps final_confidence to policy tier and human review requirement.
        Returns: (tier_recommendation, requires_human_review)
        """
        if final_confidence < 0.65:
            return "HUMAN", True
        elif final_confidence < 0.85:
            return "REVIEW", True
        elif final_confidence < 0.95:
            return "SECOND_CHECK", True
        else:
            return "POLICY_APPROVED", False


class ActionGatePolicy:
    """Enforces No-Write gate and execution authorization policies."""

    MUTATIVE_ACTION_KEYWORDS = {
        "write", "modify", "delete", "create", "overwrite",
        "update", "commit", "push", "checkout", "patch",
        "fix", "repair", "refactor", "apply", "replace", "save",
        "rm", "remove", "drop", "truncate", "destroy", "revert"
    }

    def __init__(self, confidence_policy: ConfidencePolicy | None = None):
        self.confidence_policy = confidence_policy or ConfidencePolicy()

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        """Evaluates an ACTION_GATE request with strict permanent No-Write enforcement."""
        target_action = str(request.state.target_action or "").lower().strip()

        # Check if the requested action attempts to mutate code / source projects
        is_mutative = any(kw in target_action for kw in self.MUTATIVE_ACTION_KEYWORDS)

        if is_mutative:
            # Permanent Redline: MVP0~MVP6 strictly forbids any write-back to source repositories
            return DecisionResult(
                decision=ActionGateDecision.REJECT.value,
                probability=1.0,
                model_confidence=1.0,
                evidence_confidence=1.0,
                graph_confidence=1.0,
                historical_accuracy=1.0,
                final_confidence=1.0,
                requires_human_review=True,
                model_version="laya-action-gate-v1",
                policy_version="no-write-redline-v1",
                rationale="DENIED_BY_READONLY_GATE: Mutative actions on source repositories are permanently forbidden across MVP0~MVP6.",
                action_recommendation="REJECT",
            )

        # For read-only actions, evaluate evidence sufficiency and confidence
        evidence_count = len(request.state.evidence)
        entities_count = len(request.state.changed_entities)

        model_conf = 0.90 if evidence_count > 0 else 0.60
        evidence_conf = min(1.0, 0.5 + evidence_count * 0.1)
        graph_conf = min(1.0, 0.6 + len(request.state.relations) * 0.1)
        hist_acc = 0.95

        final_conf = self.confidence_policy.calculate_final_confidence(
            model_conf=model_conf,
            evidence_conf=evidence_conf,
            graph_conf=graph_conf,
            historical_acc=hist_acc,
        )

        tier, requires_review = self.confidence_policy.evaluate_tier(final_conf)

        if final_conf >= 0.85:
            decision = ActionGateDecision.AUTO.value
        elif final_conf >= 0.65:
            decision = ActionGateDecision.REVIEW.value
        else:
            decision = ActionGateDecision.ESCALATE.value

        return DecisionResult(
            decision=decision,
            probability=final_conf,
            model_confidence=model_conf,
            evidence_confidence=evidence_conf,
            graph_confidence=graph_conf,
            historical_accuracy=hist_acc,
            final_confidence=final_conf,
            requires_human_review=requires_review,
            model_version="laya-action-gate-v1",
            policy_version="action-gate-v1",
            rationale=f"Read-only action '{request.state.target_action or 'READ'}' authorized under tier {tier}.",
            action_recommendation=tier,
        )
