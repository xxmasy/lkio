"""Evaluation Runner & Benchmark Harness for MVP8.
Executes DecisionEngine against benchmark cases, calculates metrics, and runs calibration.
"""

from typing import Any
from pydantic import BaseModel, Field
from core.decision.engine import DecisionEngine, LayaDecisionEngine
from core.decision.models import DecisionTask, TASK_ALLOWED_OPTIONS
from core.evaluation.calibration import ConfidenceCalibrator, CalibrationReport
from core.evaluation.metrics import MetricsCalculator, MetricsSummary
from core.evaluation.models import CasePrediction, EvaluationCase


class TaskEvaluationResult(BaseModel):
    """Evaluation summary for a single decision task."""
    task: DecisionTask
    metrics: MetricsSummary
    predictions: list[CasePrediction] = Field(default_factory=list)


class SuiteEvaluationResult(BaseModel):
    """Comprehensive evaluation result for the entire benchmark suite."""
    total_cases: int
    overall_metrics: MetricsSummary
    per_task_results: dict[str, TaskEvaluationResult] = Field(default_factory=dict)
    calibration_report: CalibrationReport | None = None


class EvaluationRunner:
    """Orchestrates benchmark evaluation and calibration across Laya decision tasks."""

    def __init__(self, engine: DecisionEngine | None = None, num_bins: int = 10):
        self.engine = engine or LayaDecisionEngine()
        self.metrics_calculator = MetricsCalculator(num_bins=num_bins)
        self.calibrator = ConfidenceCalibrator(num_bins=num_bins)

    def evaluate_case(self, case: EvaluationCase) -> CasePrediction:
        """Runs the decision engine on a single evaluation case and compares against expected."""
        request = case.to_decision_request()
        result = self.engine.decide(request)

        is_correct = (result.decision.upper() == case.expected.upper())

        return CasePrediction(
            case_id=case.case_id,
            task=case.task,
            expected=case.expected,
            predicted=result.decision,
            confidence=result.final_confidence,
            probability=result.probability,
            is_correct=is_correct,
            requires_human_review=result.requires_human_review,
            case_type=case.case_type,
            split=case.split,
            rationale=result.rationale,
        )

    def run_suite(
        self,
        cases: list[EvaluationCase],
        calibrate: bool = True,
        val_cases_for_calibration: list[EvaluationCase] | None = None,
    ) -> SuiteEvaluationResult:
        """Executes full evaluation over cases, computes metrics, and runs calibration."""
        predictions: list[CasePrediction] = [self.evaluate_case(c) for c in cases]

        # Calculate overall suite metrics
        overall_metrics = self.metrics_calculator.calculate(predictions)

        # Calculate per-task results
        per_task_results: dict[str, TaskEvaluationResult] = {}
        for task in DecisionTask:
            task_preds = [p for p in predictions if p.task == task]
            if task_preds:
                task_summary = self.metrics_calculator.calculate(task_preds)
                per_task_results[task.value] = TaskEvaluationResult(
                    task=task,
                    metrics=task_summary,
                    predictions=task_preds,
                )

        # Compute task-level macro F1 (unweighted average across evaluated tasks)
        task_f1s = [res.metrics.macro_f1 for res in per_task_results.values()]
        if task_f1s:
            overall_metrics.task_level_macro_f1 = round(sum(task_f1s) / len(task_f1s), 4)

        # Optional Calibration
        calibration_report = None
        if calibrate:
            if val_cases_for_calibration:
                val_preds = [self.evaluate_case(c) for c in val_cases_for_calibration]
                self.calibrator.fit(val_preds, target_metric="ece")
            else:
                self.calibrator.fit(predictions, target_metric="ece")
            calibration_report = self.calibrator.evaluate_calibration(predictions)

        return SuiteEvaluationResult(
            total_cases=len(cases),
            overall_metrics=overall_metrics,
            per_task_results=per_task_results,
            calibration_report=calibration_report,
        )
