"""Pydantic Models and DTOs for MVP6 Laya Decision Engine
Implements Baseline Section 29, 30, and 31.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DecisionTask(str, Enum):
    """The 4 Foundation Decision Tasks mandated by Baseline Section 29.2."""
    CHANGE_IMPACT = "CHANGE_IMPACT"
    EVIDENCE_SUFFICIENCY = "EVIDENCE_SUFFICIENCY"
    QUERY_ROUTE = "QUERY_ROUTE"
    ACTION_GATE = "ACTION_GATE"


class ChangeImpactLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceSufficiencyLevel(str, Enum):
    INSUFFICIENT = "INSUFFICIENT"
    PARTIAL = "PARTIAL"
    SUFFICIENT = "SUFFICIENT"
    STRONG = "STRONG"


class QueryRouteDestination(str, Enum):
    ENTITY = "ENTITY"
    CODE = "CODE"
    GRAPH = "GRAPH"
    RAG = "RAG"
    EVENT = "EVENT"
    WIKI = "WIKI"
    HUMAN = "HUMAN"


class ActionGateDecision(str, Enum):
    AUTO = "AUTO"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"
    REJECT = "REJECT"


TASK_ALLOWED_OPTIONS: dict[DecisionTask, list[str]] = {
    DecisionTask.CHANGE_IMPACT: [e.value for e in ChangeImpactLevel],
    DecisionTask.EVIDENCE_SUFFICIENCY: [e.value for e in EvidenceSufficiencyLevel],
    DecisionTask.QUERY_ROUTE: [e.value for e in QueryRouteDestination],
    DecisionTask.ACTION_GATE: [e.value for e in ActionGateDecision],
}


class DecisionQuestion(BaseModel):
    """Specifies the decision choice question and options."""
    type: str = "choice"
    options: list[str] = Field(default_factory=list)


class DecisionState(BaseModel):
    """Structured knowledge state input to the Decision Engine (Baseline Section 30).
    Laya consumes strictly structured state, never raw unbounded filesystem dumps.
    """
    changed_entities: list[dict[str, Any]] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    business_rules: list[dict[str, Any]] = Field(default_factory=list)
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    query_text: str | None = None
    target_action: str | None = None  # e.g., "READ_CODE", "WRITE_FILE", "UPDATE_CONFIG"
    extra: dict[str, Any] = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    """Standard request payload for LKIO DecisionEngine (Baseline Section 30)."""
    task: DecisionTask
    project_scope: list[str] = Field(default_factory=list)
    state: DecisionState = Field(default_factory=DecisionState)
    question: DecisionQuestion
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionResult(BaseModel):
    """Standard decision output from LKIO DecisionEngine (Baseline Section 31)."""
    decision: str
    probability: float
    model_confidence: float
    evidence_confidence: float
    graph_confidence: float
    historical_accuracy: float
    final_confidence: float
    requires_human_review: bool
    model_version: str = "laya-typed-decisions"
    policy_version: str = "impact-v1"
    rationale: str = ""
    action_recommendation: str = ""
