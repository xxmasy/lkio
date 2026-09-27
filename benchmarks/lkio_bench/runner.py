"""Unified Benchmark Runner for LKIO-Bench v1.0.
Executes all 15 evaluation layers, computes ablation metrics, and generates Master Table.
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from benchmarks.lkio_bench.dataset.manifests import LKIOBenchManifestManager
from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator
from benchmarks.lkio_bench.models import (
    BenchmarkSplit,
    LKIOBenchSuiteResult,
)


class LKIOBenchRunner:
    """Executes the complete LKIO-Bench v1.0 suite across all 15 layers."""

    def __init__(self, output_dir: Path | str = "docs/benchmarks"):
        self.output_dir = Path(output_dir)
        self.manifest_manager = LKIOBenchManifestManager()
        self.layer_evaluator = LKIOBenchLayerEvaluator()

    def run_all_layers(self) -> LKIOBenchSuiteResult:
        """Executes all 15 layers sequentially and compiles comprehensive results."""
        results = []

        # Layer 1: Semantic Retrieval
        results.append(self.layer_evaluator.evaluate_layer01_semantic())

        # Layer 2: Symbol Retrieval
        results.append(self.layer_evaluator.evaluate_layer02_symbol())

        # Layer 3: Dependency Retrieval
        results.append(self.layer_evaluator.evaluate_layer03_dependency())

        # Layer 4: Cycle Safety
        results.append(self.layer_evaluator.evaluate_layer04_cycle_safety())

        # Layer 5: Shortest-Hop Preservation
        results.append(self.layer_evaluator.evaluate_layer05_shortest_hop())

        # Layer 6: Depth Boundary
        results.append(self.layer_evaluator.evaluate_layer06_depth_boundary())

        # Layer 7: Temporal Git Reasoning
        results.append(self.layer_evaluator.evaluate_layer07_temporal_git())

        # Layer 8: Historical State Reconstruction
        results.append(self.layer_evaluator.evaluate_layer08_historical_state())

        # Layer 9: Impact Analysis
        results.append(self.layer_evaluator.evaluate_layer09_impact_analysis())

        # Layer 10: False Positive Impact
        results.append(self.layer_evaluator.evaluate_layer10_fp_impact())

        # Layer 11: Multi-Path Evidence
        results.append(self.layer_evaluator.evaluate_layer11_multipath_evidence())

        # Layer 12: Cross-Frontend/Backend Reasoning
        results.append(self.layer_evaluator.evaluate_layer12_cross_stack())

        # Layer 13: Decision Layer
        results.append(self.layer_evaluator.evaluate_layer13_decision_layer())

        # Layer 14: Calibration Ablation
        results.append(self.layer_evaluator.evaluate_layer14_calibration_ablation())

        # Layer 15: Ablation Study
        layer15_res, master_table = self.layer_evaluator.evaluate_layer15_ablation_study()
        results.append(layer15_res)

        # Layer 16: Incremental Correctness (Stage 1 Section 3.9)
        results.append(self.layer_evaluator.evaluate_layer16_incremental_correctness())

        # Layer 17: Incremental Performance Benchmark (Stage 1 Section 3.9)
        results.append(self.layer_evaluator.evaluate_layer17_incremental_performance())

        suite_result = LKIOBenchSuiteResult(
            benchmark_name="LKIO-Bench v1.0",
            repository_snapshot="HELLO_FE (Vue) + HELLO_BE (Spring Boot) + L2C_FE",
            timestamp=datetime.now().isoformat(),
            split_statistics={
                BenchmarkSplit.DEV.value: 360,
                BenchmarkSplit.CALIBRATION.value: 120,
                BenchmarkSplit.TEST.value: 120,
                BenchmarkSplit.BLIND_TEST.value: 120,
            },
            layer_results=results,
            master_table=master_table,
        )

        self._export_markdown_report(suite_result)
        return suite_result

    def _export_markdown_report(self, suite: LKIOBenchSuiteResult) -> Path:
        """Exports full report with Master Table to docs/benchmarks/."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_file = self.output_dir / "lkio_bench_v1_report.md"

        lines = [
            "# LKIO-Bench v1.0: 权威性能与消融评测总报告",
            "",
            "> **评测套件**：**LKIO-Bench v1.0**  ",
            f"> **评测时间**：`{suite.timestamp}`  ",
            f"> **评测代码库**：`{suite.repository_snapshot}`  ",
            "> **核心准则**：将‘系统能不能跑’与‘系统到底比什么强’彻底解耦，覆盖 15 层纵深指标，如实呈现优势与缺陷。",
            "",
            "---",
            "",
            "## 一、全系统 8 大基线消融对比主表 (Section 18 Master Table)",
            "",
            "| System | Recall@10 | Impact F1 | Temporal Acc | Decision Acc | Macro-F1 | ECE |",
            "|---|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for row in suite.master_table.rows:
            lines.append(
                f"| **{row.system}** | {row.recall_at_10} | {row.impact_f1} | {row.temporal_acc} | {row.decision_acc} | {row.macro_f1} | {row.ece} |"
            )

        lines.extend([
            "",
            "### 🛑 真实劣势与诚实保留原则 (Honest Loss Disclosures)",
            "",
        ])
        for note in suite.master_table.honest_loss_notes:
            lines.append(f"- **{note}**")

        lines.extend([
            "",
            "---",
            "",
            "## 二、15 层基准评测详细结果统计 (Layers 1 ~ 15)",
            "",
        ])

        for layer in suite.layer_results:
            lines.append(f"### Layer {layer.layer_id}: {layer.layer_name}")
            lines.append(f"- **测试样本量**：{layer.sample_count}")
            lines.append(f"- **验证状态**：`{layer.status}`")
            lines.append("```json")
            import json
            lines.append(json.dumps(layer.metrics, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return report_file
