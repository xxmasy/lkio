"""Change Impact Evaluator for MVP6 Laya Decision Engine
Evaluates impact level across ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"].
"""

from core.decision.models import (
    ChangeImpactLevel,
    DecisionRequest,
    DecisionResult,
)
from core.decision.policy import ConfidencePolicy


class ChangeImpactEvaluator:
    """Evaluates the ripple impact of code and architectural changes."""

    def __init__(self, confidence_policy: ConfidencePolicy | None = None):
        self.policy = confidence_policy or ConfidencePolicy()

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        state = request.state
        changed_entities = state.changed_entities
        relations = state.relations
        business_rules = state.business_rules

        if not changed_entities:
            # No entities changed
            final_conf = 0.95
            tier, requires_review = self.policy.evaluate_tier(final_conf)
            return DecisionResult(
                decision=ChangeImpactLevel.NONE.value,
                probability=0.98,
                model_confidence=0.95,
                evidence_confidence=0.95,
                graph_confidence=0.95,
                historical_accuracy=0.95,
                final_confidence=final_conf,
                requires_human_review=requires_review,
                model_version="laya-impact-v1",
                policy_version="impact-eval-v1",
                rationale="Zero changed entities detected in scope.",
                action_recommendation=tier,
            )

        # Check for critical architectural impacts: Database tables, cross-project API contracts, auth
        has_db_change = any(
            "model" in str(e.get("path", "")).lower()
            or "entity" in str(e.get("path", "")).lower()
            or e.get("entity_type") in ("DATABASE", "TABLE", "SCHEMA")
            for e in changed_entities
        )

        has_api_or_controller_change = any(
            "controller" in str(e.get("path", "")).lower()
            or "api" in str(e.get("path", "")).lower()
            or e.get("entity_type") in ("API", "CONTROLLER", "ENDPOINT")
            for e in changed_entities
        )

        has_cross_project_relation = any(
            r.get("relation_type") == "API_CALLS" or r.get("cross_project") is True
            for r in relations
        )

        affected_rules_count = len(business_rules)
        total_relations_count = len(relations)

        # Classify impact level
        if (has_db_change and has_api_or_controller_change) or (has_cross_project_relation and affected_rules_count > 0):
            decision = ChangeImpactLevel.CRITICAL.value
            prob = 0.92
        elif has_api_or_controller_change or has_cross_project_relation or affected_rules_count > 0:
            decision = ChangeImpactLevel.HIGH.value
            prob = 0.88
        elif total_relations_count > 3 or len(changed_entities) > 3:
            decision = ChangeImpactLevel.MEDIUM.value
            prob = 0.85
        else:
            decision = ChangeImpactLevel.LOW.value
            prob = 0.89

        model_conf = prob
        evidence_conf = min(1.0, 0.70 + len(state.evidence) * 0.06)
        graph_conf = min(1.0, 0.65 + total_relations_count * 0.05)
        hist_acc = 0.90

        final_conf = self.policy.calculate_final_confidence(
            model_conf=model_conf,
            evidence_conf=evidence_conf,
            graph_conf=graph_conf,
            historical_acc=hist_acc,
        )

        tier, requires_review = self.policy.evaluate_tier(final_conf)
        # CRITICAL and HIGH always trigger human review
        if decision in (ChangeImpactLevel.CRITICAL.value, ChangeImpactLevel.HIGH.value):
            requires_review = True

        return DecisionResult(
            decision=decision,
            probability=prob,
            model_confidence=model_conf,
            evidence_confidence=evidence_conf,
            graph_confidence=graph_conf,
            historical_accuracy=hist_acc,
            final_confidence=final_conf,
            requires_human_review=requires_review,
            model_version="laya-impact-v1",
            policy_version="impact-eval-v1",
            rationale=(
                f"Evaluated {len(changed_entities)} changed entities with {total_relations_count} relations. "
                f"DB change: {has_db_change}, API/Controller change: {has_api_or_controller_change}, "
                f"Cross-project: {has_cross_project_relation}."
            ),
            action_recommendation=tier,
        )
