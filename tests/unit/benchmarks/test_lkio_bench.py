"""Automated Test Suite for LKIO-Bench v1.0.
Verifies all 18 sections:
- 4-split manifest isolation
- All 15 evaluation layers
- Master comparison table across 8 baselines
"""

from pathlib import Path
import pytest
from benchmarks.lkio_bench.dataset.manifests import LKIOBenchManifestManager
from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator
from benchmarks.lkio_bench.models import BenchmarkSplit
from benchmarks.lkio_bench.runner import LKIOBenchRunner


def test_split_manifests_integrity(tmp_path: Path):
    """Verifies 4-split manifest generation and SHA-256 validation (Section 2)."""
    manager = LKIOBenchManifestManager(storage_dir=tmp_path)
    sample_data = [{"id": f"c_{i}", "val": i} for i in range(10)]

    data_file, manifest_file = manager.save_split_data(BenchmarkSplit.TEST, sample_data)
    assert data_file.exists()
    assert manifest_file.exists()
    assert manager.verify_split_integrity(BenchmarkSplit.TEST) is True

    # Tampering test
    with open(data_file, "a") as f:
        f.write(" ")
    assert manager.verify_split_integrity(BenchmarkSplit.TEST) is False


def test_all_fifteen_layers_execution():
    """Verifies that all 15 evaluation layers produce valid mathematical results."""
    evaluator = LKIOBenchLayerEvaluator()

    # Layer 1: Semantic
    l1 = evaluator.evaluate_layer01_semantic()
    assert l1.layer_id == 1
    assert l1.metrics["recall_at_10"] >= 0.80
    assert l1.metrics["mrr"] > 0.0

    # Layer 2: Symbol (AST)
    l2 = evaluator.evaluate_layer02_symbol()
    assert l2.layer_id == 2
    assert l2.metrics["symbol_recall_at_1"] == 1.0

    # Layer 3: Dependency
    l3 = evaluator.evaluate_layer03_dependency()
    assert l3.layer_id == 3
    assert l3.metrics["overall_hop_recall"] == 1.0

    # Layer 4: Cycle Safety (5 cases)
    l4 = evaluator.evaluate_layer04_cycle_safety()
    assert l4.layer_id == 4
    assert l4.metrics["passed_cases_count"] == 5
    assert l4.metrics["max_depth_violation"] == 0

    # Layer 5: Shortest-Hop
    l5 = evaluator.evaluate_layer05_shortest_hop()
    assert l5.layer_id == 5
    assert l5.metrics["shortest_hop_accuracy"] == 1.0

    # Layer 6: Depth Boundary
    l6 = evaluator.evaluate_layer06_depth_boundary()
    assert l6.layer_id == 6
    assert l6.metrics["passed_all"] is True

    # Layer 7: Temporal Git
    l7 = evaluator.evaluate_layer07_temporal_git()
    assert l7.layer_id == 7
    assert l7.metrics["commit_identification_accuracy"] == 1.0

    # Layer 8: Historical State
    l8 = evaluator.evaluate_layer08_historical_state()
    assert l8.layer_id == 8
    assert l8.metrics["historical_dependency_accuracy"] == 1.0

    # Layer 9: Impact Analysis
    l9 = evaluator.evaluate_layer09_impact_analysis()
    assert l9.layer_id == 9
    assert l9.metrics["overall_impact_f1"] == 1.0

    # Layer 10: False Positive Impact
    l10 = evaluator.evaluate_layer10_fp_impact()
    assert l10.layer_id == 10
    assert l10.metrics["impact_precision"] == 1.0
    assert l10.metrics["over_propagation_rate"] == 0.0

    # Layer 11: Multi-Path Evidence
    l11 = evaluator.evaluate_layer11_multipath_evidence()
    assert l11.layer_id == 11
    assert l11.metrics["evidence_recall"] == 1.0
    assert l11.metrics["shortest_hop_accuracy"] == 1.0

    # Layer 12: Cross-Stack
    l12 = evaluator.evaluate_layer12_cross_stack()
    assert l12.layer_id == 12
    assert l12.metrics["cross_stack_f1"] == 1.0

    # Layer 13: Decision Layer
    l13 = evaluator.evaluate_layer13_decision_layer()
    assert l13.layer_id == 13
    assert l13.metrics["accuracy"] >= 0.80

    # Layer 14: Calibration Ablation
    l14 = evaluator.evaluate_layer14_calibration_ablation()
    assert l14.layer_id == 14
    assert l14.metrics["calibrated_ece"] < l14.metrics["uncalibrated_ece"]
    assert l14.metrics["parameter_source_split"] == "CALIBRATION_ONLY"

    # Layer 15: Ablation Study
    l15, table = evaluator.evaluate_layer15_ablation_study()
    assert l15.layer_id == 15
    assert len(table.rows) == 8


def test_runner_and_master_table_generation(tmp_path: Path):
    """Verifies that LKIOBenchRunner generates the 15 layers and Markdown report with Section 18 Table."""
    runner = LKIOBenchRunner(output_dir=tmp_path)
    suite = runner.run_all_layers()

    assert suite.benchmark_name == "LKIO-Bench v1.0"
    assert len(suite.layer_results) == 15
    assert len(suite.master_table.rows) == 8

    # Verify honest loss is recorded
    assert len(suite.master_table.honest_loss_notes) >= 2

    # Check Markdown report file
    report_file = tmp_path / "lkio_bench_v1_report.md"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "LKIO-Bench v1.0" in content
    assert "Vector RAG" in content
    assert "Hybrid + Reranker" in content
    assert "Full LKIO" in content
