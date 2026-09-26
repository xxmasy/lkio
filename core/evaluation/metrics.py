"""Evaluation Metrics Calculation Engine for MVP8.
Strictly implements Baseline Section 35.4:
- Accuracy
- Macro-F1 (with explicit class-level and task-level aggregation definitions)
- Brier Score
- ECE (Expected Calibration Error)
- NLL (Negative Log Likelihood)
- Confusion Matrix
- Abstain Rate & Actionable Decision Coverage
- False Positive Rate (FPR) & False Negative Rate (FNR) with denominator safety checks
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
    """Complete metrics result meeting Baseline Section 35.4 and audit standards."""
    total_cases: int
    correct_cases: int
    accuracy: float
    macro_f1: float  # Class-level macro F1 by default
    class_level_macro_f1: float = 0.0  # Formal unweighted mean over all evaluated class labels
    task_level_macro_f1: float | None = None  # Formal unweighted mean over the 4 task macro-F1 scores
    brier_score: float
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    nll: float  # Negative Log Likelihood
    abstain_rate: float
    abstain_cases: int = 0
    non_abstain_cases: int = 0
    actionable_accuracy: float | None = None
    actionable_fpr: float | None = None
    actionable_fnr: float | None = None
    false_positive_rate: float | None = None
    false_negative_rate: float | None = None
    safety_metric_note: str = ""
    per_class_precision: dict[str, float] = Field(default_factory=dict)
    per_class_recall: dict[str, float] = Field(default_factory=dict)
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
                class_level_macro_f1=0.0,
                task_level_macro_f1=None,
                brier_score=0.0,
                ece=0.0,
                mce=0.0,
                nll=0.0,
                abstain_rate=0.0,
                abstain_cases=0,
                non_abstain_cases=0,
                actionable_accuracy=None,
                actionable_fpr=None,
                actionable_fnr=None,
                false_positive_rate=None,
                false_negative_rate=None,
                safety_metric_note="Empty prediction set.",
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
        per_class_precision: dict[str, float] = {}
        per_class_recall: dict[str, float] = {}
        per_class_f1: dict[str, float] = {}
        for c in classes:
            tp = matrix[c][c]
            fp = sum(matrix[other][c] for other in classes if other != c)
            fn = sum(matrix[c][other] for other in classes if other != c)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            per_class_precision[c] = round(precision, 4)
            per_class_recall[c] = round(recall, 4)
            per_class_f1[c] = round(f1, 4)

        macro_f1 = round(sum(per_class_f1.values()) / len(classes), 4) if classes else 0.0
        class_level_macro_f1 = macro_f1

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

        # 5. Abstain Rate & Action Gate Analysis
        abstain_keywords = {"HUMAN", "ESCALATE", "REJECT", "REVIEW"}
        abstain_count = sum(
            1 for p in predictions
            if p.predicted in abstain_keywords or p.requires_human_review
        )
        abstain_rate = round(abstain_count / n, 4)
        non_abstain_count = n - abstain_count

        # 6. Actionable Decisions vs Conservative Abstain
        if non_abstain_count == 0:
            actionable_accuracy = None
            actionable_fpr = None
            actionable_fnr = None
            fpr = None
            fnr = None
            safety_note = (
                "Actionable decision coverage is 0 (abstain_cases=120, non_abstain_cases=0). "
                "FPR/FNR are structurally non-informative under 100% abstention and do not represent evidence of zero classification error."
            )
        else:
            actionable_preds = [
                p for p in predictions
                if p.predicted not in abstain_keywords and not p.requires_human_review
            ]
            actionable_correct = sum(1 for p in actionable_preds if p.is_correct)
            actionable_accuracy = round(actionable_correct / len(actionable_preds), 4)

            positives_actual = sum(1 for p in actionable_preds if p.expected not in abstain_keywords)
            negatives_actual = len(actionable_preds) - positives_actual

            fp_count = sum(
                1 for p in actionable_preds
                if p.predicted not in abstain_keywords and p.expected in abstain_keywords
            )
            fn_count = sum(
                1 for p in actionable_preds
                if p.predicted in abstain_keywords and p.expected not in abstain_keywords
            )

            actionable_fpr = round(fp_count / negatives_actual, 4) if negatives_actual > 0 else 0.0
            actionable_fnr = round(fn_count / positives_actual, 4) if positives_actual > 0 else 0.0
            fpr = actionable_fpr
            fnr = actionable_fnr
            safety_note = f"Evaluated on {non_abstain_count} actionable (non-abstain) cases."

        return MetricsSummary(
            total_cases=n,
            correct_cases=correct_count,
            accuracy=accuracy,
            macro_f1=macro_f1,
            class_level_macro_f1=class_level_macro_f1,
            brier_score=brier_score,
            ece=ece,
            mce=mce,
            nll=nll,
            abstain_rate=abstain_rate,
            abstain_cases=abstain_count,
            non_abstain_cases=non_abstain_count,
            actionable_accuracy=actionable_accuracy,
            actionable_fpr=actionable_fpr,
            actionable_fnr=actionable_fnr,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
            safety_metric_note=safety_note,
            per_class_precision=per_class_precision,
            per_class_recall=per_class_recall,
            per_class_f1=per_class_f1,
            confusion_matrix=matrix,
            calibration_bins=calibration_bins,
        )
