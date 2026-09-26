"""Decision Engine Interface and Laya Decision Engine Implementation
Implements Baseline Section 29:
- DecisionEngine(Protocol)
- LayaDecisionEngine(DecisionEngine)
- DecisionEngineFactory
"""

from typing import Protocol
from core.decision.models import DecisionRequest, DecisionResult, DecisionTask
from core.decision.policy import ConfidencePolicy
from core.decision.tasks.action_gate import ActionGateEvaluator
from core.decision.tasks.change_impact import ChangeImpactEvaluator
from core.decision.tasks.evidence_sufficiency import EvidenceSufficiencyEvaluator
from core.decision.tasks.query_route import QueryRouteEvaluator


class DecisionEngine(Protocol):
    """Unified Decision Engine Interface mandated by Baseline Section 29.1."""

    def decide(self, request: DecisionRequest) -> DecisionResult:
        """Executes structured decision reasoning over given request."""
        ...


class LayaDecisionEngine:
    """Core Laya Structured Decision Engine implementation (Baseline Section 29.1 & 29.2)."""

    def __init__(self, confidence_policy: ConfidencePolicy | None = None):
        self.confidence_policy = confidence_policy or ConfidencePolicy()
        self.change_impact_evaluator = ChangeImpactEvaluator(self.confidence_policy)
        self.evidence_evaluator = EvidenceSufficiencyEvaluator(self.confidence_policy)
        self.query_route_evaluator = QueryRouteEvaluator(self.confidence_policy)
        self.action_gate_evaluator = ActionGateEvaluator(self.confidence_policy)

    def decide(self, request: DecisionRequest) -> DecisionResult:
        """Dispatches request to specialized evaluator based on task type."""
        task = request.task

        if task == DecisionTask.CHANGE_IMPACT:
            return self.change_impact_evaluator.evaluate(request)
        elif task == DecisionTask.EVIDENCE_SUFFICIENCY:
            return self.evidence_evaluator.evaluate(request)
        elif task == DecisionTask.QUERY_ROUTE:
            return self.query_route_evaluator.evaluate(request)
        elif task == DecisionTask.ACTION_GATE:
            return self.action_gate_evaluator.evaluate(request)
        else:
            raise ValueError(f"Unsupported decision task: {task}")


class DecisionEngineFactory:
    """Factory for selecting and instantiating DecisionEngine providers."""

    @staticmethod
    def create(engine_type: str = "laya", **kwargs) -> DecisionEngine:
        if engine_type.lower() == "laya":
            return LayaDecisionEngine(**kwargs)
        raise ValueError(f"Unknown decision engine provider: {engine_type}")
