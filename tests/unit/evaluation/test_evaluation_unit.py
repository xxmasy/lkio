"""Unit tests for MVP8 Evaluation, Calibration & Outcome Loop.
Strictly verifies Baseline Section 35 & 36 requirements:
- 600 Benchmark cases with proper distributions (Gold, Boundary, Abstain, Conflict)
- 4 Manifests with SHA-256 integrity and lineage isolation
- 9 Evaluation metrics (Accuracy, Macro-F1, Brier, ECE, NLL, Confusion Matrix, Abstain, FPR, FNR)
- Confidence Calibration and ECE minimization
- Outcome Loop causal feedback and dynamic policy weight adaptation
"""

import json
from pathlib import Path
import pytest
from core.decision.models import ActionGateDecision, ChangeImpactLevel, DecisionTask, QueryRouteDestination
from core.decision.policy import ConfidencePolicy
from core.evaluation.calibration import ConfidenceCalibrator
from core.evaluation.dataset import BenchmarkDatasetManager
from core.evaluation.metrics import MetricsCalculator
from core.evaluation.models import (
    ActualOutcomeType,
    CasePrediction,
    DatasetSplit,
    EvaluationCase,
    EvaluationCaseType,
    LabelSource,
)
from core.evaluation.outcome_loop import OutcomeFeedback, OutcomeLearningLoop
from core.evaluation.runner import EvaluationRunner


def test_models_and_decision_request_conversion():
    """Verifies EvaluationCase data model and conversion to DecisionRequest."""
    manager = BenchmarkDatasetManager()
    schema = manager.get_standard_label_schema()

    assert len(schema.tasks) == 4
    for task_name, info in schema.tasks.items():
        assert len(info["options"]) > 0

    case = EvaluationCase(
        case_id="case_test_001",
        task=DecisionTask.ACTION_GATE,
        case_type=EvaluationCaseType.GOLD,
        split=DatasetSplit.TRAIN,
        label_source=LabelSource.HUMAN_VERIFIED,
        project_scope=["HELLO_FE"],
        question={"options": ["AUTO", "REVIEW", "ESCALATE", "REJECT"]},
        expected=ActionGateDecision.REJECT.value,
        created_at="2026-09-26T20:00:00Z",
    )
    req = case.to_decision_request()
    assert req.task == DecisionTask.ACTION_GATE
    assert req.metadata["case_id"] == "case_test_001"
    assert req.metadata["split"] == "TRAIN"


def test_benchmark_dataset_generation_and_distributions():
    """Verifies generation of >= 600 benchmark cases across the 4 required types (Section 35.1)."""
    manager = BenchmarkDatasetManager()
    cases = manager.generate_benchmark_suite()

    assert len(cases) == 600

    gold_cases = [c for c in cases if c.case_type == EvaluationCaseType.GOLD]
    boundary_cases = [c for c in cases if c.case_type == EvaluationCaseType.BOUNDARY]
    abstain_cases = [c for c in cases if c.case_type == EvaluationCaseType.ABSTAIN]
    conflict_cases = [c for c in cases if c.case_type == EvaluationCaseType.CONFLICT]

    assert len(gold_cases) == 300
    assert len(boundary_cases) == 100
    assert len(abstain_cases) == 100
    assert len(conflict_cases) == 100

    # Verify task coverage
    tasks_represented = {c.task for c in cases}
    assert tasks_represented == {
        DecisionTask.CHANGE_IMPACT,
        DecisionTask.EVIDENCE_SUFFICIENCY,
        DecisionTask.QUERY_ROUTE,
        DecisionTask.ACTION_GATE,
    }


def test_temporal_split_isolation_and_no_leakage():
    """Verifies temporal split isolation without case leakage across train/val/test (Section 36)."""
    manager = BenchmarkDatasetManager()
    cases = manager.generate_benchmark_suite()

    train_cases = [c for c in cases if c.split == DatasetSplit.TRAIN]
    val_cases = [c for c in cases if c.split == DatasetSplit.VALIDATION]
    test_cases = [c for c in cases if c.split == DatasetSplit.TEST]

    assert len(train_cases) == 360  # 60%
    assert len(val_cases) == 120    # 20%
    assert len(test_cases) == 120   # 20%

    train_ids = {c.case_id for c in train_cases}
    val_ids = {c.case_id for c in val_cases}
    test_ids = {c.case_id for c in test_cases}

    # Strict isolation: 0 set intersections
    assert len(train_ids & val_ids) == 0
    assert len(train_ids & test_ids) == 0
    assert len(val_ids & test_ids) == 0


def test_manifest_saving_and_checksum_integrity(tmp_path: Path):
    """Verifies generation of 4 manifests and SHA-256 tamper-proof verification."""
    manager = BenchmarkDatasetManager(data_dir=tmp_path)
    cases = manager.generate_benchmark_suite()

    files = manager.save_dataset_and_manifests(cases)

    assert (tmp_path / "label_schema.json").exists()
    assert (tmp_path / "training_manifest.json").exists()
    assert (tmp_path / "validation_manifest.json").exists()
    assert (tmp_path / "test_manifest.json").exists()

    # Load and verify test split
    loaded_test = manager.load_dataset(DatasetSplit.TEST)
    assert len(loaded_test) == 120

    # Tampering test: modify test dataset and ensure validation fails
    test_file = tmp_path / "test_cases.json"
    with open(test_file, "a", encoding="utf-8") as f:
        f.write(" ")

    with pytest.raises(ValueError, match="Dataset integrity verification failed"):
        manager.load_dataset(DatasetSplit.TEST)


def test_metrics_calculator_all_nine_metrics():
    """Verifies that all 9 metrics in Baseline Section 35.4 are accurately computed."""
    calc = MetricsCalculator(num_bins=5)

    preds = [
        CasePrediction(
            case_id="c1",
            task=DecisionTask.ACTION_GATE,
            expected="AUTO",
            predicted="AUTO",
            confidence=0.90,
            probability=0.90,
            is_correct=True,
            requires_human_review=False,
            case_type=EvaluationCaseType.GOLD,
            split=DatasetSplit.TEST,
        ),
        CasePrediction(
            case_id="c2",
            task=DecisionTask.ACTION_GATE,
            expected="REJECT",
            predicted="REJECT",
            confidence=0.95,
            probability=0.95,
            is_correct=True,
            requires_human_review=True,
            case_type=EvaluationCaseType.GOLD,
            split=DatasetSplit.TEST,
        ),
        CasePrediction(
            case_id="c3",
            task=DecisionTask.ACTION_GATE,
            expected="AUTO",
            predicted="REVIEW",
            confidence=0.60,
            probability=0.60,
            is_correct=False,
            requires_human_review=True,
            case_type=EvaluationCaseType.BOUNDARY,
            split=DatasetSplit.TEST,
        ),
        CasePrediction(
            case_id="c4",
            task=DecisionTask.ACTION_GATE,
            expected="REJECT",
            predicted="AUTO",
            confidence=0.85,
            probability=0.85,
            is_correct=False,
            requires_human_review=False,
            case_type=EvaluationCaseType.CONFLICT,
            split=DatasetSplit.TEST,
        ),
    ]

    metrics = calc.calculate(preds, classes=["AUTO", "REVIEW", "REJECT"])

    # 1. Accuracy (2/4 = 0.50)
    assert metrics.accuracy == 0.50
    # 2. Macro-F1 (class-level)
    assert 0.0 <= metrics.macro_f1 <= 1.0
    assert metrics.class_level_macro_f1 == metrics.macro_f1
    assert "AUTO" in metrics.per_class_precision
    assert "AUTO" in metrics.per_class_recall
    # 3. Brier Score
    assert metrics.brier_score > 0.0
    # 4. ECE
    assert 0.0 <= metrics.ece <= 1.0
    # 5. NLL
    assert metrics.nll > 0.0
    # 6. Confusion Matrix
    assert "AUTO" in metrics.confusion_matrix
    assert metrics.confusion_matrix["AUTO"]["AUTO"] == 1
    # 7. Abstain Rate & Cases
    assert metrics.abstain_rate == 0.50
    assert metrics.abstain_cases == 2
    assert metrics.non_abstain_cases == 2
    # 8. Actionable False Positive Rate & False Negative Rate
    assert metrics.actionable_fpr == 1.0
    assert metrics.actionable_fnr == 0.0

    # Test 100% Abstain scenario: Actionable metrics must be None
    all_abstain_preds = [
        CasePrediction(
            case_id="ab1",
            task=DecisionTask.ACTION_GATE,
            expected="REJECT",
            predicted="REJECT",
            confidence=0.95,
            probability=0.95,
            is_correct=True,
            requires_human_review=True,
            case_type=EvaluationCaseType.ABSTAIN,
            split=DatasetSplit.TEST,
        )
    ]
    all_ab_metrics = calc.calculate(all_abstain_preds, classes=["AUTO", "REJECT"])
    assert all_ab_metrics.abstain_rate == 1.0
    assert all_ab_metrics.abstain_cases == 1
    assert all_ab_metrics.non_abstain_cases == 0
    assert all_ab_metrics.actionable_accuracy is None
    assert all_ab_metrics.actionable_fpr is None
    assert all_ab_metrics.actionable_fnr is None
    assert "Actionable decision coverage is 0" in all_ab_metrics.safety_metric_note


def test_confidence_calibration_ece_minimization():
    """Verifies that Temperature Scaling fits and minimizes ECE on overconfident predictions."""
    # Synthetic overconfident predictions: predicted confidence ~ 0.95, but accuracy is ~ 50%
    preds = []
    for i in range(50):
        is_corr = (i % 2 == 0)
        preds.append(
            CasePrediction(
                case_id=f"c_{i}",
                task=DecisionTask.CHANGE_IMPACT,
                expected="HIGH" if is_corr else "LOW",
                predicted="HIGH",
                confidence=0.92,
                probability=0.92,
                is_correct=is_corr,
                requires_human_review=False,
                case_type=EvaluationCaseType.GOLD,
                split=DatasetSplit.VALIDATION,
            )
        )

    calibrator = ConfidenceCalibrator(num_bins=10)
    raw_summary = calibrator.metrics_calculator.calculate(preds)
    # Raw ECE should be high because confidence (0.92) is far from accuracy (0.50)
    assert raw_summary.ece > 0.30

    best_temp = calibrator.fit(preds, target_metric="ece")
    # Temperature should have increased (T > 1.0) to soften/moderate the overconfident scores
    assert best_temp > 1.0

    report = calibrator.evaluate_calibration(preds)
    assert report.post_ece < report.pre_ece
    assert report.ece_reduction_percent > 0.0
    assert len(report.calibration_curve) == 10


def test_outcome_learning_loop_causal_feedback_and_adaptation(tmp_path: Path):
    """Verifies OutcomeLearningLoop enforces causal evidence (Redline 4) and adapts policy weights."""
    policy = ConfidencePolicy(weight_model=0.35, weight_evidence=0.35, weight_graph=0.20, weight_history=0.10)
    loop = OutcomeLearningLoop(history_file=tmp_path / "outcomes.json", confidence_policy=policy)

    # 1. Missing evidence_ref must be rejected
    with pytest.raises(ValueError, match="missing mandatory causal evidence_ref"):
        loop.record_outcome(
            OutcomeFeedback(
                feedback_id="fb_001",
                decision_id="dec_001",
                task=DecisionTask.CHANGE_IMPACT,
                predicted_decision="LOW",
                predicted_confidence=0.80,
                actual_outcome=ActualOutcomeType.OUTCOME_VERIFIED,
                is_correct=True,
                evidence_ref="",  # Violates Redline 4
            )
        )

    # 2. Feed 5 consecutive high-quality verified outcomes with valid causal git commit evidence
    for i in range(5):
        loop.record_outcome(
            OutcomeFeedback(
                feedback_id=f"fb_{i+1:03d}",
                decision_id=f"dec_{i+1:03d}",
                task=DecisionTask.CHANGE_IMPACT,
                predicted_decision="HIGH",
                predicted_confidence=0.88,
                actual_outcome=ActualOutcomeType.OUTCOME_VERIFIED,
                is_correct=True,
                evidence_ref=f"commit_sha_83b106{i}",
            )
        )

    profile = loop.get_task_profile(DecisionTask.CHANGE_IMPACT)
    assert profile.total_feedback_count == 5
    assert profile.empirical_accuracy == 1.0

    # Policy should adapt: historical weight w_h should increase
    assert loop.confidence_policy.w_h >= 0.15
    assert len(loop.adaptation_history) > 0


def test_evaluation_runner_pipeline():
    """Verifies EvaluationRunner executing LayaDecisionEngine over benchmark cases."""
    manager = BenchmarkDatasetManager()
    cases = manager.generate_benchmark_suite()
    sample_cases = cases[:20]  # Fast sample

    runner = EvaluationRunner()
    result = runner.run_suite(sample_cases, calibrate=True)

    assert result.total_cases == 20
    assert result.overall_metrics.accuracy >= 0.0
    assert len(result.per_task_results) > 0
    assert result.calibration_report is not None
