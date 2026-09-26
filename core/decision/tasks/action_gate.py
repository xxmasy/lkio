"""Action Gate Evaluator for MVP6 Laya Decision Engine
Enforces the Action Gate Policy and permanent No-Write constraints.
"""

from core.decision.models import DecisionRequest, DecisionResult
from core.decision.policy import ActionGatePolicy, ConfidencePolicy


class ActionGateEvaluator:
    """Evaluates action requests against security policies and read-only boundaries."""

    def __init__(self, confidence_policy: ConfidencePolicy | None = None):
        self.policy = ActionGatePolicy(confidence_policy=confidence_policy)

    def evaluate(self, request: DecisionRequest) -> DecisionResult:
        return self.policy.evaluate(request)
