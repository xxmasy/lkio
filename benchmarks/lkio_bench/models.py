"""Pydantic Models and Data Structures for LKIO-Bench v1.0.
Defines specifications, ground truth schemas, and metric reports across all 15 evaluation layers.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class BenchmarkSplit(str, Enum):
    """The 4 Isolated Splits mandated by LKIO-Bench Section 2."""
    DEV = "DEV"                    # 60% development set
    CALIBRATION = "CALIBRATION"    # 20% calibration set (temperature scaling only)
    TEST = "TEST"                  # 20% standard test set
    BLIND_TEST = "BLIND_TEST"      # Completely blind evaluation set (hidden from system & developer)


# ---------------------------------------------------------
# Layer Metric Models (Layers 1 to 15)
# ---------------------------------------------------------

class SemanticRetrievalMetrics(BaseModel):
    """Layer 1: Semantic Retrieval Metrics."""
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_10: float


class SymbolRetrievalMetrics(BaseModel):
    """Layer 2: Symbol Retrieval (AST core benchmark)."""
    symbol_recall_at_1: float
    symbol_recall_at_5: float
    file_recall_at_5: float
    line_recall: float


class DependencyRetrievalMetrics(BaseModel):
    """Layer 3: Multi-hop Dependency Retrieval."""
    hop1_recall: float
    hop2_recall: float
    hop3_recall: float
    overall_hop_recall: float


class CycleSafetyMetrics(BaseModel):
    """Layer 4: Cycle Safety (5 complex topologies)."""
    termination_rate: float = 1.0
    duplicate_expansion: int = 0
    max_depth_violation: int = 0
    passed_cases_count: int = 5
    total_cases_count: int = 5


class ShortestHopMetrics(BaseModel):
    """Layer 5: Shortest-Hop Preservation."""
    shortest_hop_accuracy: float = 1.0
    total_cases: int
    correct_cases: int


class DepthBoundaryMetrics(BaseModel):
    """Layer 6: Depth Boundary Invariants."""
    depth_violation_count: int = 0
    tested_boundaries: list[int] = Field(default_factory=lambda: [1, 2, 3, 5])
    passed_all: bool = True


class TemporalGitMetrics(BaseModel):
    """Layer 7: Temporal Git Reasoning."""
    commit_identification_accuracy: float
    temporal_precision: float
    temporal_recall: float
    change_attribution_accuracy: float


class HistoricalStateMetrics(BaseModel):
    """Layer 8: Historical State Reconstruction."""
    historical_dependency_accuracy: float
    state_reconstruction_fidelity: float


class ImpactAnalysisMetrics(BaseModel):
    """Layer 9: Impact Analysis Breakdown."""
    direct_f1: float
    indirect_f1: float
    potential_f1: float
    overall_impact_f1: float
    overall_precision: float
    overall_recall: float


class FalsePositiveImpactMetrics(BaseModel):
    """Layer 10: False Positive Impact (Anti Over-Propagation)."""
    impact_precision: float
    impact_recall: float
    impact_f1: float
    over_propagation_rate: float


class MultiPathEvidenceMetrics(BaseModel):
    """Layer 11: Multi-Path Evidence Accumulation."""
    evidence_recall: float
    evidence_precision: float
    shortest_hop_accuracy: float


class CrossStackMetrics(BaseModel):
    """Layer 12: Cross-Frontend/Backend Reasoning."""
    cross_layer_recall: float
    cross_layer_precision: float
    cross_stack_f1: float


class CalibrationBinDetail(BaseModel):
    bin_index: int
    lower_bound: float
    upper_bound: float
    confidence: float
    accuracy: float
    count: int


class DecisionLayerMetrics(BaseModel):
    """Layer 13: Decision Layer Evaluation."""
    accuracy: float
    macro_f1: float
    micro_f1: float
    precision: float
    recall: float
    brier_score: float
    nll: float
    ece: float
    reliability_diagram: list[CalibrationBinDetail] = Field(default_factory=list)


class CalibrationAblationMetrics(BaseModel):
    """Layer 14: Calibration Ablation (No Calibration vs Temperature Scaling)."""
    uncalibrated_ece: float
    uncalibrated_brier: float
    calibrated_ece: float
    calibrated_brier: float
    ece_reduction_percent: float
    parameter_source_split: str = "CALIBRATION_ONLY"


class AblationRow(BaseModel):
    """Row in the Master Comparison Table (Layer 15 & Section 18)."""
    system: str
    recall_at_10: float | str
    impact_f1: float | str
    temporal_acc: float | str
    decision_acc: float | str
    macro_f1: float | str
    ece: float | str


class AblationMasterTable(BaseModel):
    """Master Comparison Table across all 8 Baselines (Section 18)."""
    columns: list[str] = [
        "System", "Recall@10", "Impact F1", "Temporal Acc", "Decision Acc", "Macro-F1", "ECE"
    ]
    rows: list[AblationRow] = Field(default_factory=list)
    honest_loss_notes: list[str] = Field(default_factory=list)


class IncrementalCorrectnessMetrics(BaseModel):
    """Layer 16: Incremental Correctness (14 metrics, Stage 1 Section 3.9)."""
    add_file_rate: float
    delete_file_rate: float
    modify_file_rate: float
    rename_file_rate: float
    add_symbol_rate: float
    delete_symbol_rate: float
    modify_symbol_rate: float
    rename_symbol_rate: float
    signature_change_rate: float
    add_edge_rate: float
    delete_edge_rate: float
    stale_edge_rate: float
    query_during_update_downtime: float
    rollback_success_rate: float
    semantic_equivalence_rate: float


class IncrementalPerformanceMetrics(BaseModel):
    """Layer 17: Incremental Performance Benchmark (Stage 1 Section 3.9)."""
    one_file_p95_ms: float
    five_files_p95_ms: float
    twenty_files_p95_ms: float
    hundred_files_p95_ms: float
    full_rebuild_ms: float
    average_speedup: float


# ---------------------------------------------------------
# Overall Suite Models
# ---------------------------------------------------------

class LayerEvaluationResult(BaseModel):
    """Result for an individual evaluation layer."""
    layer_id: int
    layer_name: str
    sample_count: int
    metrics: dict[str, Any]
    status: str = "PASSED"
    notes: str = ""


class LKIOBenchSuiteResult(BaseModel):
    """Full execution report of LKIO-Bench v1.0."""
    benchmark_name: str = "LKIO-Bench v1.0"
    repository_snapshot: str = "HELLO_FE + HELLO_BE + L2C_FE"
    timestamp: str
    split_statistics: dict[str, int]
    layer_results: list[LayerEvaluationResult] = Field(default_factory=list)
    master_table: AblationMasterTable
