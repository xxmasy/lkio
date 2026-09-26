"""Outcome Learning Loop & Feedback Engine for MVP8.
Strictly implements Baseline Section 35 & 36:
- Records runtime execution outcomes and human reviews with causal evidence
- Updates historical accuracy statistics across decision tasks
- Dynamically calibrates ConfidencePolicy weights based on empirical outcomes
- Permanent No-Write Guarantee (updates policy/metrics, never touches source code)
"""

import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from core.decision.models import DecisionTask
from core.decision.policy import ConfidencePolicy
from core.evaluation.models import ActualOutcomeType


class OutcomeFeedback(BaseModel):
    """Structured feedback payload binding actual outcome with causal evidence (Redline 4)."""
    feedback_id: str
    decision_id: str
    task: DecisionTask
    predicted_decision: str
    predicted_confidence: float
    actual_outcome: ActualOutcomeType
    is_correct: bool
    evidence_ref: str = Field(
        ...,
        description="Mandatory causal evidence reference (e.g. Git Commit SHA, CI test run ID, review note)",
    )
    domain_scope: str = "DEFAULT"
    human_notes: str = ""
    timestamp: str = ""


class TaskAccuracyProfile(BaseModel):
    """Historical accuracy profile for a specific decision task."""
    task: DecisionTask
    total_feedback_count: int = 0
    verified_count: int = 0
    regression_count: int = 0
    override_count: int = 0
    empirical_accuracy: float = 1.0


class PolicyAdaptationRecord(BaseModel):
    """Audit record tracking policy weight adjustments from outcome feedback."""
    adaptation_id: str
    task: DecisionTask
    previous_weights: dict[str, float]
    updated_weights: dict[str, float]
    triggering_feedback_id: str
    rationale: str
    timestamp: str


class OutcomeLearningLoop:
    """Manages the continuous feedback and policy calibration loop."""

    def __init__(
        self,
        history_file: Path | str = "data/evaluation/outcome_history.json",
        confidence_policy: ConfidencePolicy | None = None,
    ):
        self.history_file = Path(history_file)
        self.confidence_policy = confidence_policy or ConfidencePolicy()
        self.feedback_records: list[OutcomeFeedback] = []
        self.adaptation_history: list[PolicyAdaptationRecord] = []
        self._load_history()

    def _load_history(self) -> None:
        """Loads historical feedback records from disk if present."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.feedback_records = [OutcomeFeedback(**item) for item in data.get("feedbacks", [])]
            except Exception:
                self.feedback_records = []

    def _persist_history(self) -> None:
        """Persists feedback records to disk."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0",
            "feedbacks": [f.model_dump() for f in self.feedback_records],
        }
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record_outcome(self, feedback: OutcomeFeedback) -> TaskAccuracyProfile:
        """Records a new outcome feedback, recalculates accuracy, and updates policy."""
        # Redline validation: must have causal evidence reference
        if not feedback.evidence_ref or len(feedback.evidence_ref.strip()) == 0:
            raise ValueError("Outcome feedback rejected: missing mandatory causal evidence_ref (Redline 4)")

        self.feedback_records.append(feedback)
        self._persist_history()

        profile = self.get_task_profile(feedback.task)
        self._adapt_policy_weights(feedback.task, profile, feedback.feedback_id)
        return profile

    def get_task_profile(self, task: DecisionTask) -> TaskAccuracyProfile:
        """Calculates current empirical accuracy profile for a specific task."""
        task_feedbacks = [f for f in self.feedback_records if f.task == task]
        if not task_feedbacks:
            return TaskAccuracyProfile(
                task=task,
                total_feedback_count=0,
                verified_count=0,
                regression_count=0,
                override_count=0,
                empirical_accuracy=1.0,
            )

        total = len(task_feedbacks)
        verified = sum(1 for f in task_feedbacks if f.is_correct)
        regressions = sum(1 for f in task_feedbacks if not f.is_correct and "REGRESSION" in f.actual_outcome.value)
        overrides = sum(1 for f in task_feedbacks if f.actual_outcome == ActualOutcomeType.HUMAN_OVERRIDDEN)
        acc = round(verified / total, 4)

        return TaskAccuracyProfile(
            task=task,
            total_feedback_count=total,
            verified_count=verified,
            regression_count=regressions,
            override_count=overrides,
            empirical_accuracy=acc,
        )

    def _adapt_policy_weights(
        self,
        task: DecisionTask,
        profile: TaskAccuracyProfile,
        trigger_id: str,
    ) -> None:
        """Dynamically adjusts ConfidencePolicy weights based on observed empirical accuracy."""
        prev = {
            "w_m": self.confidence_policy.w_m,
            "w_e": self.confidence_policy.w_e,
            "w_g": self.confidence_policy.w_g,
            "w_h": self.confidence_policy.w_h,
        }

        # If we have at least 5 feedback samples, adapt weights
        if profile.total_feedback_count >= 5:
            if profile.empirical_accuracy >= 0.90:
                # High historical accuracy -> reward historical weight w_h, reduce model weight w_m
                new_wh = min(0.25, round(0.10 + (profile.empirical_accuracy - 0.80) * 0.5, 3))
                diff = new_wh - self.confidence_policy.w_h
                new_wm = max(0.20, round(self.confidence_policy.w_m - diff, 3))
                rationale = f"High empirical accuracy ({profile.empirical_accuracy:.2%}): increased history weight"
            else:
                # Regressions observed -> prioritize explicit evidence w_e, reduce model intuition w_m
                new_we = min(0.50, round(self.confidence_policy.w_e + 0.10, 3))
                diff = new_we - self.confidence_policy.w_e
                new_wm = max(0.20, round(self.confidence_policy.w_m - diff, 3))
                new_wh = self.confidence_policy.w_h
                rationale = f"Regressions detected ({profile.regression_count} regressions): tightened evidence requirement"

            # Apply normalized updates
            total_w = new_wm + (new_we if 'new_we' in locals() else self.confidence_policy.w_e) + self.confidence_policy.w_g + (new_wh if 'new_wh' in locals() else self.confidence_policy.w_h)
            self.confidence_policy.w_m = round(new_wm / total_w, 3)
            if 'new_we' in locals():
                self.confidence_policy.w_e = round(new_we / total_w, 3)
            if 'new_wh' in locals():
                self.confidence_policy.w_h = round(new_wh / total_w, 3)

            updated = {
                "w_m": self.confidence_policy.w_m,
                "w_e": self.confidence_policy.w_e,
                "w_g": self.confidence_policy.w_g,
                "w_h": self.confidence_policy.w_h,
            }

            self.adaptation_history.append(
                PolicyAdaptationRecord(
                    adaptation_id=f"adapt_{len(self.adaptation_history)+1:04d}",
                    task=task,
                    previous_weights=prev,
                    updated_weights=updated,
                    triggering_feedback_id=trigger_id,
                    rationale=rationale,
                    timestamp="2026-09-26T20:30:00Z",
                )
            )
