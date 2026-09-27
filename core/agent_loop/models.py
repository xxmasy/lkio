"""Agent Closed-Loop Feedback & Governance Models (Stage 4 Section 6.2 - 6.8).

Implements:
- AgentTask: Refactoring / modification task specification
- PreChangeEvidence: Graph facts established prior to modification
- PostChangeValidation: Incremental re-index and topology diff verification
- DecisionGovernanceResult: Production policy enforcement (Confidence != Permission)
- WorkflowAuditTrail: End-to-end evidence record
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GovernanceChoice(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class GovernanceRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AgentTask(BaseModel):
    task_id: str
    requirement: str
    target_entity: str
    declared_scope: List[str] = Field(default_factory=list)
    business_criticality: str = "NORMAL"  # LOW, NORMAL, HIGH, CRITICAL


class PreChangeEvidence(BaseModel):
    target_entity: str
    references: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    direct_impact: List[str] = Field(default_factory=list)
    indirect_impact: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"


class PostChangeValidation(BaseModel):
    snapshot_id: str
    files_changed: List[str] = Field(default_factory=list)
    symbols_changed: List[str] = Field(default_factory=list)
    new_edges: List[str] = Field(default_factory=list)
    deleted_edges: List[str] = Field(default_factory=list)
    actual_impact: List[str] = Field(default_factory=list)
    undeclared_impact: List[str] = Field(default_factory=list)
    scope_deviation: bool = False
    test_passed: bool = True
    regression_detected: bool = False
    regression_details: Optional[str] = None


class DecisionGovernanceResult(BaseModel):
    choice: GovernanceChoice
    score: float
    confidence: float
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    risk: GovernanceRisk
    policy: str
    requires_human_signoff: bool = False


class WorkflowAuditTrail(BaseModel):
    task_id: str
    step_count: int
    pre_evidence: PreChangeEvidence
    post_validation: PostChangeValidation
    governance: DecisionGovernanceResult
    latency_ms: float
    completed_successfully: bool
