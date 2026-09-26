"""Evaluation Metrics Calculation Engine for MVP8.
Strictly implements Baseline Section 35.4:
- Accuracy
- Macro-F1
- Brier Score
- ECE (Expected Calibration Error)
- NLL (Negative Log Likelihood)
- Confusion Matrix
- Abstain Rate
- False Positive Rate (FPR)
- False Negative Rate (FNR)
"""

import math
from typing import Any
from pydantic import BaseModel, Field
from core.evaluation.models import CasePrediction


class CalibrationBin(BaseModel):
    """Details for a single confidence bin in ECE calculation."""
    bin_index: int
    lower_bound: float
    upper_bound: float
    sample_count: int
    mean_confidence: float
    mean_accuracy: float
    calibration_gap: float


class MetricsSummary(BaseModel):
    """Complete metrics result meeting Baseline Section 35.4."""
    total_cases: int
    correct_cases: int
    accuracy: float
    macro_f1: float
    brier_score: float
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    nll: float  # Negative Log Likelihood
    abstain_rate: float
    false_positive_rate: float
    false_negative_rate: float
    per_class_f1: dict[str, float] = Field(default_factory=dict)
    confusion_matrix: dict[str, dict[str, int]] = Field(default_factory=dict)
    calibration_bins: list[CalibrationBin] = Field(default_factory=list)


class MetricsCalculator:
    """Calculates all 9 standard evaluation metrics deterministically."""

    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins

    def calculate(self, predictions: list[CasePrediction], classes: list[str] | None = None) -> MetricsSummary:
        """Calculates full metrics summary for a list of predictions."""
        if not predictions:
            return MetricsSummary(
                total_cases=0,
                correct_cases=0,
                accuracy=0.0,
                macro_f1=0.0,
                brier_score=0.0,
                ece=0.0,
                mce=0.0,
                nll=0.0,
                abstain_rate=0.0,
                false_positive_rate=0.0,
                false_negative_rate=0.0,
            )

        n = len(predictions)
        correct_count = sum(1 for p in predictions if p.is_correct)
        accuracy = round(correct_count / n, 4)

        # Infer classes if not explicitly provided
        if not classes:
            class_set = set()
            for p in predictions:
                class_set.add(p.expected)
                class_set.add(p.predicted)
            classes = sorted(list(class_set))

        # 1. Confusion Matrix
        # matrix[actual][predicted] = count
        matrix: dict[str, dict[str, int]] = {c: {c2: 0 for c2 in classes} for c in classes}
        for p in predictions:
            exp = p.expected
            pred = p.predicted
            if exp in matrix and pred in matrix[exp]:
                matrix[exp][pred] += 1

        # 2. Per-Class Precision, Recall, F1 and Macro-F1
        per_class_f1: dict[str, float] = {}
        for c in classes:
            tp = matrix[c][c]
            fp = sum(matrix[other][c] for other in classes if other != c)
            fn = sum(matrix[c][other] for other in classes if other != c)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            per_class_f1[c] = round(f1, 4)

        macro_f1 = round(sum(per_class_f1.values()) / len(classes), 4) if classes else 0.0

        # 3. Brier Score & NLL (using top-1 prediction confidence and correctness)
        # Brier = (1/N) * sum((confidence - correctness)^2)
        brier_sum = 0.0
        nll_sum = 0.0
        eps = 1e-7

        for p in predictions:
            y = 1.0 if p.is_correct else 0.0
            conf = max(eps, min(1.0 - eps, p.confidence))
            brier_sum += (conf - y) ** 2
            # Log loss
            nll_sum += -(y * math.log(conf) + (1.0 - y) * math.log(1.0 - conf))

        brier_score = round(brier_sum / n, 4)
        nll = round(nll_sum / n, 4)

        # 4. ECE (Expected Calibration Error) with M equal-width bins
        bin_width = 1.0 / self.num_bins
        calibration_bins: list[CalibrationBin] = []
        ece_acc = 0.0
        max_gap = 0.0

        for b in range(self.num_bins):
            lower = b * bin_width
            upper = (b + 1) * bin_width
            # Samples in [lower, upper) or [lower, upper] for last bin
            if b == self.num_bins - 1:
                bin_preds = [p for p in predictions if lower <= p.confidence <= upper]
            else:
                bin_preds = [p for p in predictions if lower <= p.confidence < upper]

            count = len(bin_preds)
            if count > 0:
                mean_conf = sum(p.confidence for p in bin_preds) / count
                mean_acc = sum(1.0 for p in bin_preds if p.is_correct) / count
                gap = abs(mean_acc - mean_conf)
                ece_acc += (count / n) * gap
                max_gap = max(max_gap, gap)
            else:
                mean_conf = (lower + upper) / 2
                mean_acc = 0.0
                gap = 0.0

            calibration_bins.append(
                CalibrationBin(
                    bin_index=b,
                    lower_bound=round(lower, 2),
                    upper_bound=round(upper, 2),
                    sample_count=count,
                    mean_confidence=round(mean_conf, 4),
                    mean_accuracy=round(mean_acc, 4),
                    calibration_gap=round(gap, 4),
                )
            )

        ece = round(ece_acc, 4)
        mce = round(max_gap, 4)

        # 5. Abstain Rate
        abstain_keywords = {"HUMAN", "ESCALATE", "REJECT", "REVIEW"}
        abstain_count = sum(
            1 for p in predictions
            if p.predicted in abstain_keywords or p.requires_human_review
        )
        abstain_rate = round(abstain_count / n, 4)

        # 6. False Positive Rate & False Negative Rate
        # For critical actions / high impact cases
        # Define "Positive" as any actionable / non-abstain / critical decision
        # FP: Predicted Positive when actual was Negative (e.g., allowed mutative write or predicted LOW when it was CRITICAL)
        # FN: Predicted Negative when actual was Positive
        positives_actual = sum(1 for p in predictions if p.expected not in abstain_keywords)
        negatives_actual = n - positives_actual

        fp_count = sum(
            1 for p in predictions
            if p.predicted not in abstain_keywords and p.expected in abstain_keywords
        )
        fn_count = sum(
            1 for p in predictions
            if p.predicted in abstain_keywords and p.expected not in abstain_keywords
        )

        fpr = round(fp_count / negatives_actual, 4) if negatives_actual > 0 else 0.0
        fnr = round(fn_count / positives_actual, 4) if positives_actual > 0 else 0.0

        return MetricsSummary(
            total_cases=n,
            correct_cases=correct_count,
            accuracy=accuracy,
            macro_f1=macro_f1,
            brier_score=brier_score,
            ece=ece,
            mce=mce,
            nll=nll,
            abstain_rate=abstain_rate,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
            per_class_f1=per_class_f1,
            confusion_matrix=matrix,
            calibration_bins=calibration_bins,
        )
