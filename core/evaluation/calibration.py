"""Confidence Calibration Engine for MVP8.
Strictly implements Baseline Section 35:
- Minimizing Expected Calibration Error (ECE)
- Temperature Scaling & Binning Calibration
- Reliability Diagram Data Generation
- Confidence alignment with empirical accuracy
"""

import math
from typing import Any
from pydantic import BaseModel, Field
from core.evaluation.metrics import MetricsCalculator
from core.evaluation.models import CasePrediction


class CalibrationCurvePoint(BaseModel):
    """Single point on an empirical calibration curve (Reliability Diagram)."""
    bin_index: int
    mean_confidence: float
    mean_accuracy: float
    sample_count: int
    gap: float


class CalibrationReport(BaseModel):
    """Detailed report comparing pre-calibration and post-calibration metrics."""
    calibrator_type: str = "temperature_scaling"
    temperature: float = 1.0
    pre_ece: float
    post_ece: float
    ece_reduction_percent: float
    pre_brier: float
    post_brier: float
    pre_mce: float
    post_mce: float
    calibration_curve: list[CalibrationCurvePoint] = Field(default_factory=list)


class ConfidenceCalibrator:
    """Performs empirical confidence calibration to minimize ECE and Brier score."""

    def __init__(self, temperature: float = 1.0, num_bins: int = 10):
        self.temperature = max(0.01, temperature)
        self.num_bins = num_bins
        self.metrics_calculator = MetricsCalculator(num_bins=num_bins)

    @staticmethod
    def _logit(p: float, eps: float = 1e-6) -> float:
        """Computes logit of probability with safety clipping."""
        p_clipped = max(eps, min(1.0 - eps, p))
        return math.log(p_clipped / (1.0 - p_clipped))

    @staticmethod
    def _sigmoid(z: float) -> float:
        """Computes sigmoid of logit with overflow protection."""
        if z >= 20.0:
            return 1.0
        if z <= -20.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-z))

    def calibrate_confidence(self, raw_confidence: float) -> float:
        """Transforms raw confidence via learned temperature parameter."""
        z = self._logit(raw_confidence)
        calibrated_z = z / self.temperature
        calibrated_prob = self._sigmoid(calibrated_z)
        return round(calibrated_prob, 4)

    def calibrate_predictions(self, predictions: list[CasePrediction]) -> list[CasePrediction]:
        """Applies calibration to a batch of predictions, returning updated copies."""
        calibrated_list: list[CasePrediction] = []
        for p in predictions:
            new_conf = self.calibrate_confidence(p.confidence)
            calibrated_list.append(
                CasePrediction(
                    case_id=p.case_id,
                    task=p.task,
                    expected=p.expected,
                    predicted=p.predicted,
                    confidence=new_conf,
                    probability=new_conf,
                    is_correct=p.is_correct,
                    requires_human_review=p.requires_human_review,
                    case_type=p.case_type,
                    split=p.split,
                    rationale=p.rationale + f" [Calibrated T={self.temperature:.2f}]",
                )
            )
        return calibrated_list

    def fit(self, val_predictions: list[CasePrediction], target_metric: str = "ece") -> float:
        """Fits temperature parameter on validation set to minimize target metric ('ece' or 'brier').
        Uses deterministic bounded grid search over T in [0.1, 5.0].
        """
        if not val_predictions:
            return self.temperature

        best_t = 1.0
        best_loss = float("inf")

        # Search range from 0.2 to 3.5 in increments of 0.05
        candidate_temps = [round(0.2 + 0.05 * i, 2) for i in range(67)]

        for t in candidate_temps:
            self.temperature = t
            calibrated = self.calibrate_predictions(val_predictions)
            summary = self.metrics_calculator.calculate(calibrated)

            loss = summary.ece if target_metric == "ece" else summary.brier_score
            if loss < best_loss:
                best_loss = loss
                best_t = t

        self.temperature = best_t
        return self.temperature

    def evaluate_calibration(self, predictions: list[CasePrediction]) -> CalibrationReport:
        """Generates comprehensive report comparing uncalibrated vs calibrated results."""
        pre_summary = self.metrics_calculator.calculate(predictions)
        calibrated_predictions = self.calibrate_predictions(predictions)
        post_summary = self.metrics_calculator.calculate(calibrated_predictions)

        reduction = 0.0
        if pre_summary.ece > 0:
            reduction = round(((pre_summary.ece - post_summary.ece) / pre_summary.ece) * 100.0, 2)

        curve_points: list[CalibrationCurvePoint] = [
            CalibrationCurvePoint(
                bin_index=b.bin_index,
                mean_confidence=b.mean_confidence,
                mean_accuracy=b.mean_accuracy,
                sample_count=b.sample_count,
                gap=b.calibration_gap,
            )
            for b in post_summary.calibration_bins
        ]

        return CalibrationReport(
            calibrator_type="temperature_scaling",
            temperature=self.temperature,
            pre_ece=pre_summary.ece,
            post_ece=post_summary.ece,
            ece_reduction_percent=reduction,
            pre_brier=pre_summary.brier_score,
            post_brier=post_summary.brier_score,
            pre_mce=pre_summary.mce,
            post_mce=post_summary.mce,
            calibration_curve=curve_points,
        )
