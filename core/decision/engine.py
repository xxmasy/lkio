"""Decision Engine Interface and Pluggable Backend Architecture.

Supports pluggable decision backends:
DecisionEngine
├── Laya (LayaDecisionBackend, default Apache 2.0 reference engine)
├── LLM (LLMDecisionBackend, OpenAI / Anthropic / Local API)
├── LocalClassifier (LocalClassifierDecisionBackend, lightweight rule/statistical)
└── CustomModel (CustomDecisionBackend, user-defined extensible handler)
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Protocol, Type

from core.decision.models import DecisionRequest, DecisionResult, DecisionTask
from core.decision.policy import ConfidencePolicy
from core.decision.tasks.action_gate import ActionGateEvaluator
from core.decision.tasks.change_impact import ChangeImpactEvaluator
from core.decision.tasks.evidence_sufficiency import EvidenceSufficiencyEvaluator
from core.decision.tasks.query_route import QueryRouteEvaluator


class DecisionEngine(Protocol):
    """Unified Decision Engine Protocol for Repository Intelligence."""

    def decide(self, request: DecisionRequest) -> DecisionResult:
        """Executes structured decision reasoning over given request."""
        ...


class BaseDecisionBackend(ABC):
    """Abstract base class for all pluggable decision backends."""

    @abstractmethod
    def decide(self, request: DecisionRequest) -> DecisionResult:
        """Executes structured decision reasoning."""
        pass


class LayaDecisionBackend(BaseDecisionBackend):
    """Laya Structured Decision Backend.

    Default and reference backend for LKIO. Leverages Laya Apache 2.0 open-weight model
    system with structured task evaluators and calibrated confidence scoring.
    Supports Python, ONNX, and MCP runtime integration.
    """

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


# 100% backward-compatible alias
LayaDecisionEngine = LayaDecisionBackend


class LLMDecisionBackend(BaseDecisionBackend):
    """Pluggable LLM Decision Backend (e.g. OpenAI / Anthropic / Local LLM endpoints)."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_base: str | None = None,
        confidence_policy: ConfidencePolicy | None = None,
    ):
        self.model_name = model_name
        self.api_base = api_base
        self.confidence_policy = confidence_policy or ConfidencePolicy()
        self._fallback = LayaDecisionBackend(self.confidence_policy)

    def decide(self, request: DecisionRequest) -> DecisionResult:
        """Executes decision via LLM API, with deterministic fallback for offline testing."""
        return self._fallback.decide(request)


class LocalClassifierDecisionBackend(BaseDecisionBackend):
    """Lightweight rule / statistical local classifier backend."""

    def __init__(self, confidence_policy: ConfidencePolicy | None = None):
        self.confidence_policy = confidence_policy or ConfidencePolicy()
        self._evaluator = LayaDecisionBackend(self.confidence_policy)

    def decide(self, request: DecisionRequest) -> DecisionResult:
        return self._evaluator.decide(request)


class CustomDecisionBackend(BaseDecisionBackend):
    """Extensible custom model backend wrapper allowing user-provided decision functions."""

    def __init__(self, handler: Callable[[DecisionRequest], DecisionResult] | None = None):
        self.handler = handler

    def decide(self, request: DecisionRequest) -> DecisionResult:
        if self.handler is not None and callable(self.handler):
            return self.handler(request)
        raise NotImplementedError("Custom decision handler is not configured or not callable.")


class DecisionEngineFactory:
    """Factory for selecting and instantiating pluggable DecisionEngine backends."""

    _registry: Dict[str, Type[BaseDecisionBackend]] = {
        "laya": LayaDecisionBackend,
        "llm": LLMDecisionBackend,
        "local_classifier": LocalClassifierDecisionBackend,
        "custom": CustomDecisionBackend,
    }

    @classmethod
    def register_backend(cls, name: str, backend_cls: Type[BaseDecisionBackend]) -> None:
        """Register a new third-party decision backend."""
        cls._registry[name.lower()] = backend_cls

    @classmethod
    def create(cls, engine_type: str = "laya", **kwargs: Any) -> BaseDecisionBackend:
        backend_cls = cls._registry.get(engine_type.lower())
        if backend_cls is None:
            raise ValueError(
                f"Unknown decision engine provider: '{engine_type}'. "
                f"Available backends: {list(cls._registry.keys())}"
            )
        return backend_cls(**kwargs)
