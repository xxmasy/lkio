"""LKIO Core Evaluation Module (MVP8)
Baseline Section 35 & 36: Laya Evaluation, Calibration & Outcome Learning Loop
"""

from core.evaluation.calibration import CalibrationReport, ConfidenceCalibrator
from core.evaluation.dataset import BenchmarkDatasetManager
from core.evaluation.metrics import MetricsCalculator, MetricsSummary
from core.evaluation.models import (
    ActualOutcomeType,
    CasePrediction,
    DatasetSplit,
    EvaluationCase,
    EvaluationCaseType,
    LabelSchema,
    LabelSource,
    ManifestMetadata,
)
from core.evaluation.outcome_loop import OutcomeFeedback, OutcomeLearningLoop, TaskAccuracyProfile
from core.evaluation.runner import EvaluationRunner, SuiteEvaluationResult, TaskEvaluationResult

__all__ = [
    "ActualOutcomeType",
    "BenchmarkDatasetManager",
    "CalibrationReport",
    "CasePrediction",
    "ConfidenceCalibrator",
    "DatasetSplit",
    "EvaluationCase",
    "EvaluationCaseType",
    "EvaluationRunner",
    "LabelSchema",
    "LabelSource",
    "ManifestMetadata",
    "MetricsCalculator",
    "MetricsSummary",
    "OutcomeFeedback",
    "OutcomeLearningLoop",
    "SuiteEvaluationResult",
    "TaskAccuracyProfile",
    "TaskEvaluationResult",
]
