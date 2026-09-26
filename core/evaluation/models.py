"""Pydantic Models and DTOs for MVP8 Evaluation, Calibration & Learning Loop.
Strictly implements Baseline Section 35 (Dataset, Metrics, Schema) and Section 36 (Training Policy).
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from core.decision.models import DecisionQuestion, DecisionRequest, DecisionState, DecisionTask


class EvaluationCaseType(str, Enum):
    """Four foundational case types mandated by Baseline Section 35.1."""
    GOLD = "GOLD"
    BOUNDARY = "BOUNDARY"
    ABSTAIN = "ABSTAIN"
    CONFLICT = "CONFLICT"


class DatasetSplit(str, Enum):
    """Temporal or lineage isolated splits mandated by Baseline Section 36."""
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"


class LabelSource(str, Enum):
    """Authoritative sources of truth for ground truth labels (Baseline Section 35.2)."""
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    GIT_HISTORY = "GIT_HISTORY"
    KNOWN_BUG = "KNOWN_BUG"
    DEPLOYMENT_RESULT = "DEPLOYMENT_RESULT"
    INCIDENT_POSTMORTEM = "INCIDENT_POSTMORTEM"
    IMPACT_REVIEW = "IMPACT_REVIEW"
    AGENT_PROPOSAL = "AGENT_PROPOSAL"
    AUTOMATED_TEST = "AUTOMATED_TEST"


class ActualOutcomeType(str, Enum):
    """Runtime outcome observed after decision execution (Baseline Section 35.3)."""
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"
    FRONTEND_REGRESSION = "FRONTEND_REGRESSION"
    BACKEND_REGRESSION = "BACKEND_REGRESSION"
    API_CONTRACT_BROKEN = "API_CONTRACT_BROKEN"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    HUMAN_OVERRIDDEN = "HUMAN_OVERRIDDEN"
    TEST_PASSED = "TEST_PASSED"
    SAFE_ABSTAIN = "SAFE_ABSTAIN"


class EvaluationCase(BaseModel):
    """Individual benchmark evaluation case matching Baseline Section 35.3."""
    case_id: str
    task: DecisionTask
    case_type: EvaluationCaseType
    split: DatasetSplit
    label_source: LabelSource
    project_scope: list[str] = Field(default_factory=list)
    state: DecisionState = Field(default_factory=DecisionState)
    question: DecisionQuestion
    expected: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    actual_outcome: str | None = None
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_decision_request(self) -> DecisionRequest:
        """Converts benchmark case into standard Laya DecisionRequest."""
        return DecisionRequest(
            task=self.task,
            project_scope=self.project_scope,
            state=self.state,
            question=self.question,
            metadata={
                "case_id": self.case_id,
                "case_type": self.case_type.value,
                "split": self.split.value,
                "label_source": self.label_source.value,
                **self.metadata,
            },
        )


class LabelSchema(BaseModel):
    """Standardized label schema across the 4 decision tasks (Baseline Section 36)."""
    version: str = "1.0.0"
    tasks: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ManifestMetadata(BaseModel):
    """Metadata specification for train/validation/test manifests (Baseline Section 36)."""
    manifest_type: DatasetSplit
    version: str = "1.0.0"
    total_cases: int
    task_distribution: dict[str, int] = Field(default_factory=dict)
    case_type_distribution: dict[str, int] = Field(default_factory=dict)
    project_distribution: dict[str, int] = Field(default_factory=dict)
    case_ids: list[str] = Field(default_factory=list)
    checksum_sha256: str = ""
    created_at: str = ""
    description: str = ""


class CasePrediction(BaseModel):
    """Evaluation result for a single case."""
    case_id: str
    task: DecisionTask
    expected: str
    predicted: str
    confidence: float
    probability: float
    is_correct: bool
    requires_human_review: bool
    case_type: EvaluationCaseType
    split: DatasetSplit
    rationale: str = ""
