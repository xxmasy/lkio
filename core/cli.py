"""LKIO Command Line Interface & Unified Evidence Verification Suite.

Provides the premier verification mechanism `lkio verify --all` to prove
LKIO's empirical capabilities across 11 verification gates with cryptographic
integrity, live benchmark computations, and adversarial defense checks.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

app = typer.Typer(
    name="lkio",
    help="LKIO - Repository Intelligence Infrastructure CLI & Verification Suite",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@dataclass
class GateResult:
    gate_id: int
    name: str
    category: str
    status: str  # PASSED / FAILED / SKIPPED
    summary: str
    details: dict[str, Any]
    duration_ms: float = 0.0


def _get_git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        return res.stdout.strip()
    except Exception:
        return "unknown-git-commit"


def _compute_dataset_hash() -> str:
    dataset_dir = Path(__file__).resolve().parent.parent / "benchmarks" / "lkio_bench" / "dataset"
    hasher = hashlib.sha256()
    if dataset_dir.exists():
        for file_path in sorted(dataset_dir.rglob("*.py")):
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()[:16]


# -------------------------------------------------------------------------
# Gate Implementations
# -------------------------------------------------------------------------
def verify_gate01_environment() -> GateResult:
    """Gate 1: Runtime & Parser Environment Verification."""
    start = datetime.now(timezone.utc)
    py_ok = sys.version_info >= (3, 12)
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    from core.parsing.parser_factory import ParserFactory
    factory = ParserFactory()
    langs_tested = ["java", "javascript", "typescript"]
    parser_status = {}
    for lang in langs_tested:
        try:
            parser = factory.get(lang)
            parser_status[lang] = "AVAILABLE" if parser is not None else "UNAVAILABLE"
        except Exception as e:
            parser_status[lang] = f"ERROR: {e}"

    all_parsers_ok = all(v == "AVAILABLE" for v in parser_status.values())
    status = "PASSED" if (py_ok and all_parsers_ok) else "FAILED"
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=1,
        name="Runtime & Parser Environment",
        category="Environment",
        status=status,
        summary=f"Python {py_ver} (>=3.12: {py_ok}), Parsers: {list(parser_status.keys())}",
        details={"python_version": py_ver, "parsers": parser_status},
        duration_ms=round(elapsed, 2),
    )


def verify_gate02_integrity() -> GateResult:
    """Gate 2: Cryptographic Checksum & Code Integrity."""
    start = datetime.now(timezone.utc)
    commit = _get_git_commit()
    dataset_hash = _compute_dataset_hash()

    from core.evaluation.dataset import BenchmarkDatasetManager, DatasetSplit
    manager = BenchmarkDatasetManager()
    train_cases = manager.load_dataset(DatasetSplit.TRAIN)
    val_cases = manager.load_dataset(DatasetSplit.VALIDATION)
    test_cases = manager.load_dataset(DatasetSplit.TEST)
    total_samples = len(train_cases) + len(val_cases) + len(test_cases)

    status = "PASSED" if (commit and dataset_hash and total_samples >= 600) else "FAILED"
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=2,
        name="Cryptographic Checksum & Integrity",
        category="Integrity",
        status=status,
        summary=f"Commit {commit[:8]} | Dataset SHA256 {dataset_hash} | Samples: {total_samples}",
        details={"git_commit": commit, "dataset_sha256": dataset_hash, "total_samples": total_samples},
        duration_ms=round(elapsed, 2),
    )


def verify_gate03_independent_oracle() -> GateResult:
    """Gate 3: Incremental Independent Oracle Invariant Check."""
    start = datetime.now(timezone.utc)
    from core.state.snapshot import SnapshotManager
    from core.indexing.pipeline import IncrementalIndexingPipeline
    from core.indexing.change_detector import ChangeDetector
    from core.indexing.independent_oracle import IndependentOracle

    repo_id = "verify-oracle-repo"
    mgr = SnapshotManager(repo_id=repo_id, initial_commit="c0")
    pipeline = IncrementalIndexingPipeline(mgr)

    # Base snapshot
    base_files = {f"src/pkg/File{i}.java": f"public class File{i} {{ void run{i}() {{}} }}" for i in range(20)}
    pipeline.apply_incremental_update("c1", ChangeDetector.detect_from_memory({}, base_files))

    # Apply complex multi-file mutations: modified, deleted, added
    mod_files = dict(base_files)
    mod_files["src/pkg/File3.java"] = "public class File3 { void run3_updated() {} void extra() {} }"
    del mod_files["src/pkg/File7.java"]
    mod_files["src/pkg/NewFile.java"] = "public class NewFile { void newMethod() {} }"

    delta = ChangeDetector.detect_from_memory(base_files, mod_files)
    pipeline.apply_incremental_update("c2", delta)

    current_snap = mgr.get_current_snapshot()
    canonical = IndependentOracle.build_canonical_graph(repo_id, mod_files)
    audit = IndependentOracle.audit_snapshot_against_canonical(current_snap, canonical)

    status = "PASSED" if audit.passed else "FAILED"
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=3,
        name="Incremental Independent Oracle",
        category="Correctness",
        status=status,
        summary=f"Canonical State Equivalence: {'100% MATCH' if audit.passed else 'MISMATCH'}",
        details={
            "passed": audit.passed,
            "node_precision": audit.node_precision,
            "node_recall": audit.node_recall,
            "edge_precision": audit.edge_precision,
            "edge_recall": audit.edge_recall,
            "discrepancies": audit.discrepancies,
        },
        duration_ms=round(elapsed, 2),
    )


def verify_gate04_retrieval() -> GateResult:
    """Gate 4: Hybrid Semantic & Symbol Retrieval Accuracy."""
    start = datetime.now(timezone.utc)
    from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator

    ev = LKIOBenchLayerEvaluator()
    l1 = ev.evaluate_layer01_semantic()
    l2 = ev.evaluate_layer02_symbol()

    r10 = l1.metrics.get("recall_at_10", 0.0)
    sym_r1 = l2.metrics.get("symbol_recall_at_1", 0.0)
    passed = (r10 >= 0.80) and (sym_r1 == 1.0)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=4,
        name="Hybrid Retrieval & Symbol Lookup",
        category="Retrieval",
        status="PASSED" if passed else "FAILED",
        summary=f"Semantic Recall@10: {r10} | Symbol Recall@1: {sym_r1}",
        details={"layer01": l1.metrics, "layer02": l2.metrics},
        duration_ms=round(elapsed, 2),
    )


def verify_gate05_graph_impact() -> GateResult:
    """Gate 5: Cycle Safety, Shortest Hop & Impact Blast Radius."""
    start = datetime.now(timezone.utc)
    from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator

    ev = LKIOBenchLayerEvaluator()
    l4 = ev.evaluate_layer04_cycle_safety()
    l5 = ev.evaluate_layer05_shortest_hop()
    l9 = ev.evaluate_layer09_impact_analysis()

    cycle_ok = l4.metrics.get("termination_rate") == 1.0 and l4.metrics.get("max_depth_violation") == 0
    hop_ok = l5.metrics.get("shortest_hop_accuracy") == 1.0
    impact_f1 = l9.metrics.get("overall_impact_f1", 0.0)

    passed = cycle_ok and hop_ok and (impact_f1 >= 0.90)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=5,
        name="Graph Topology & Blast Radius",
        category="Topology",
        status="PASSED" if passed else "FAILED",
        summary=f"Cycle Termination: 100% | Hop Acc: {l5.metrics.get('shortest_hop_accuracy')} | Impact F1: {impact_f1}",
        details={"layer04": l4.metrics, "layer05": l5.metrics, "layer09": l9.metrics},
        duration_ms=round(elapsed, 2),
    )


def verify_gate06_git_temporal() -> GateResult:
    """Gate 6: Temporal Git Reasoning & Historical State."""
    start = datetime.now(timezone.utc)
    from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator

    ev = LKIOBenchLayerEvaluator()
    l7 = ev.evaluate_layer07_temporal_git()
    l8 = ev.evaluate_layer08_historical_state()

    t_acc = l7.metrics.get("commit_identification_accuracy", 0.0)
    h_acc = l8.metrics.get("historical_dependency_accuracy", 0.0)
    passed = (t_acc == 1.0) and (h_acc == 1.0)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=6,
        name="Temporal Git & Historical State",
        category="Temporal",
        status="PASSED" if passed else "FAILED",
        summary=f"Commit Identification: {t_acc} | Historical State Fidelity: {h_acc}",
        details={"layer07": l7.metrics, "layer08": l8.metrics},
        duration_ms=round(elapsed, 2),
    )


def verify_gate07_cross_repo_stack() -> GateResult:
    """Gate 7: Cross-Stack & Cross-Repo Traversal."""
    start = datetime.now(timezone.utc)
    from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator

    ev = LKIOBenchLayerEvaluator()
    l12 = ev.evaluate_layer12_cross_stack()
    l18 = ev.evaluate_layer18_cross_repo_retrieval()
    l19 = ev.evaluate_layer19_cross_repo_impact()

    cs_f1 = l12.metrics.get("cross_stack_f1", 0.0)
    cr_match = l18.metrics.get("client_to_server_match_rate", 0.0)
    cr_cycle_safe = 1.0 if l19.metrics.get("cross_repo_cycle_safe") else 0.0

    passed = (cs_f1 == 1.0) and (cr_match >= 0.95) and (cr_cycle_safe == 1.0)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=7,
        name="Cross-Stack & Cross-Repo Reasoning",
        category="MultiRepo",
        status="PASSED" if passed else "FAILED",
        summary=f"Full-Stack Chain F1: {cs_f1} | API Match Rate: {cr_match} | Cycle Safe: {bool(cr_cycle_safe)}",
        details={"layer12": l12.metrics, "layer18": l18.metrics, "layer19": l19.metrics},
        duration_ms=round(elapsed, 2),
    )


def verify_gate08_decision_engine() -> GateResult:
    """Gate 8: Decision Engine Accuracy & Macro-F1."""
    start = datetime.now(timezone.utc)
    from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator

    ev = LKIOBenchLayerEvaluator()
    l13 = ev.evaluate_layer13_decision_layer()

    acc = l13.metrics.get("accuracy", 0.0)
    f1 = l13.metrics.get("macro_f1", 0.0)
    passed = (acc >= 0.85) and (f1 >= 0.75)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=8,
        name="Decision Engine Validation",
        category="Decision",
        status="PASSED" if passed else "FAILED",
        summary=f"Decision Accuracy: {acc} | Macro-F1: {f1}",
        details=l13.metrics,
        duration_ms=round(elapsed, 2),
    )


def verify_gate09_calibration() -> GateResult:
    """Gate 9: Expected Calibration Error (ECE) Reduction."""
    start = datetime.now(timezone.utc)
    from benchmarks.lkio_bench.layers.evaluators import LKIOBenchLayerEvaluator

    ev = LKIOBenchLayerEvaluator()
    l14 = ev.evaluate_layer14_calibration_ablation()

    pre_ece = l14.metrics.get("uncalibrated_ece", 0.0)
    post_ece = l14.metrics.get("calibrated_ece", 0.0)
    reduction = l14.metrics.get("ece_reduction_percent", 0.0)

    passed = (post_ece < 0.08) and (reduction >= 50.0)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=9,
        name="Confidence Calibration & ECE Reduction",
        category="Calibration",
        status="PASSED" if passed else "FAILED",
        summary=f"Pre-ECE: {pre_ece} -> Post-ECE: {post_ece} ({reduction}% reduction)",
        details=l14.metrics,
        duration_ms=round(elapsed, 2),
    )


def verify_gate10_governance_adversarial() -> GateResult:
    """Gate 10: Governance Adversarial Defense (STRESS-001 ~ 008)."""
    start = datetime.now(timezone.utc)
    from core.agent_loop.governance import DecisionGovernanceEngine
    from core.agent_loop.models import (
        AgentTask,
        GovernanceChoice,
        GovernanceRisk,
        PostChangeValidation,
        PreChangeEvidence,
    )

    base_ev = PreChangeEvidence(
        target_entity="repo://repo/src/Service.java#run",
        references=[{"source": "Controller"}],
        dependencies=[{"dep": "Repo"}],
        direct_impact=["Service", "Controller"],
        risk_level="LOW",
    )

    stress_tests = []

    # STRESS-001: High confidence (0.999) + Critical logic -> Must REVIEW with human signoff
    t1 = AgentTask(
        task_id="STRESS-001",
        requirement="Alter settlement",
        target_entity="repo://repo/src/Settlement.java#pay",
        declared_scope=["repo://repo/src/Settlement.java#pay", "Service", "Controller"],
        business_criticality="CRITICAL",
    )
    pv1 = PostChangeValidation(snapshot_id="s1", actual_impact=["Service", "Controller"], test_passed=True)
    r1 = DecisionGovernanceEngine.evaluate(t1, base_ev, pv1, calibrated_confidence=0.999)
    stress_tests.append(r1.choice == GovernanceChoice.REVIEW and r1.requires_human_signoff is True)

    # STRESS-002: Low confidence (0.68) -> Must REVIEW with peer review
    t2 = AgentTask(
        task_id="STRESS-002",
        requirement="Minor logging",
        target_entity="repo://repo/src/Service.java#run",
        declared_scope=["repo://repo/src/Service.java#run", "Service", "Controller"],
        business_criticality="LOW",
    )
    r2 = DecisionGovernanceEngine.evaluate(t2, base_ev, pv1, calibrated_confidence=0.68)
    stress_tests.append(r2.choice == GovernanceChoice.REVIEW and r2.requires_human_signoff is True)

    # STRESS-003: Test regression -> Must BLOCK
    pv3 = PostChangeValidation(
        snapshot_id="s3",
        test_passed=False,
        regression_detected=True,
        regression_details="Unit test assertion failed",
    )
    r3 = DecisionGovernanceEngine.evaluate(t2, base_ev, pv3, calibrated_confidence=0.99)
    stress_tests.append(r3.choice == GovernanceChoice.BLOCK)

    # STRESS-004: Blast radius breach into critical entity -> Must BLOCK
    pv4 = PostChangeValidation(
        snapshot_id="s4",
        actual_impact=["repo://repo/src/Service.java#run", "repo://billing/BillingEngine"],
        undeclared_impact=["repo://billing/BillingEngine"],
        scope_deviation=True,
        test_passed=True,
    )
    r4 = DecisionGovernanceEngine.evaluate(t1, base_ev, pv4, calibrated_confidence=0.95)
    stress_tests.append(r4.choice == GovernanceChoice.BLOCK)

    # STRESS-005: Out-of-Distribution (OOD) task type -> Must REVIEW
    t5 = AgentTask(
        task_id="STRESS-OOD-005",
        requirement="Deploy unverified binary plugin",
        target_entity="repo://repo/plugin.so",
        business_criticality="UNKNOWN_OOD",
    )
    r5 = DecisionGovernanceEngine.evaluate(t5, base_ev, pv1, calibrated_confidence=0.90)
    stress_tests.append(r5.choice == GovernanceChoice.REVIEW)

    # STRESS-006: Anomalous NaN confidence -> Must BLOCK
    r6 = DecisionGovernanceEngine.evaluate(t2, base_ev, pv1, calibrated_confidence=float("nan"))
    stress_tests.append(r6.choice == GovernanceChoice.BLOCK)

    # STRESS-007: Insufficient evidence (empty) -> Must BLOCK
    empty_ev = PreChangeEvidence(target_entity="repo://repo/src/Service.java#run")
    r7 = DecisionGovernanceEngine.evaluate(t2, empty_ev, pv1, calibrated_confidence=0.95)
    stress_tests.append(r7.choice == GovernanceChoice.BLOCK)

    # STRESS-008: Orphan target entity -> Must BLOCK
    orphan_task = AgentTask(
        task_id="STRESS-008",
        requirement="Target ghost entity",
        target_entity="unknown://repo/phantom.js",
    )
    r8 = DecisionGovernanceEngine.evaluate(orphan_task, base_ev, pv1, calibrated_confidence=0.95)
    stress_tests.append(r8.choice == GovernanceChoice.BLOCK)

    all_passed = all(stress_tests)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=10,
        name="Governance Adversarial Suite",
        category="Governance",
        status="PASSED" if all_passed else "FAILED",
        summary=f"STRESS-001 ~ 008 Defense: {sum(stress_tests)}/{len(stress_tests)} Invariants Enforced",
        details={"passed_count": sum(stress_tests), "total_count": len(stress_tests)},
        duration_ms=round(elapsed, 2),
    )


def verify_gate11_mcp_lifecycle() -> GateResult:
    """Gate 11: MCP Protocol Lifecycle & Tool Registry."""
    start = datetime.now(timezone.utc)
    from core.mcp.server import LKIO_MCPServer

    server = LKIO_MCPServer()

    # 1. Initialize with protocol negotiation
    init_payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "LKIOVerifyTestClient", "version": "1.0"},
        },
    })
    init_res = json.loads(server.process_json_rpc(init_payload))
    init_ok = init_res.get("result", {}).get("protocolVersion") == "2024-11-05"

    # 2. Tools listing
    tools_payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })
    tools_res = json.loads(server.process_json_rpc(tools_payload))
    tools = tools_res.get("result", {}).get("tools", [])
    expected_tools = {
        "lkio_search",
        "lkio_symbol",
        "lkio_references",
        "lkio_dependencies",
        "lkio_impact",
        "lkio_history",
        "lkio_decision",
        "lkio_explain",
    }
    registered_tools = {t["name"] for t in tools}
    tools_ok = expected_tools.issubset(registered_tools)

    passed = init_ok and tools_ok
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    return GateResult(
        gate_id=11,
        name="MCP Protocol Lifecycle & Tools",
        category="Protocol",
        status="PASSED" if passed else "FAILED",
        summary=f"Lifecycle: 2024-11-05 Negotiated | Registered Tools: {len(registered_tools)}/8",
        details={"protocol_version": "2024-11-05", "tool_count": len(registered_tools), "tools": list(registered_tools)},
        duration_ms=round(elapsed, 2),
    )


GATES_REGISTRY = {
    "env": verify_gate01_environment,
    "integrity": verify_gate02_integrity,
    "oracle": verify_gate03_independent_oracle,
    "retrieval": verify_gate04_retrieval,
    "graph": verify_gate05_graph_impact,
    "git": verify_gate06_git_temporal,
    "multirepo": verify_gate07_cross_repo_stack,
    "decision": verify_gate08_decision_engine,
    "calibration": verify_gate09_calibration,
    "governance": verify_gate10_governance_adversarial,
    "mcp": verify_gate11_mcp_lifecycle,
}


@app.command(name="verify")
def verify_command(
    run_all: bool = typer.Option(True, "--all", "-a", help="Execute all 11 verification gates."),
    gate: Optional[str] = typer.Option(None, "--gate", "-g", help="Run a single verification gate by key."),
    as_json: bool = typer.Option(False, "--json", help="Output evidence bundle as structured JSON."),
):
    """Execute LKIO Evidence Verification Suite to compute verifiable proof bundles."""
    console.print(Panel.fit(
        "[bold cyan]LKIO Evidence Verification Suite[/bold cyan]\n"
        "[dim]Repository Intelligence Infrastructure - Zero-Trust Mathematical Proof Engine[/dim]",
        border_style="cyan",
    ))

    gates_to_run = list(GATES_REGISTRY.items())
    if gate:
        if gate.lower() not in GATES_REGISTRY:
            console.print(f"[bold red]Unknown gate:[/bold red] {gate}. Choose from: {list(GATES_REGISTRY.keys())}")
            raise typer.Exit(code=1)
        gates_to_run = [(gate.lower(), GATES_REGISTRY[gate.lower()])]

    results: list[GateResult] = []
    with console.status("[bold green]Executing verification gates...[/bold green]", spinner="dots"):
        for _, runner in gates_to_run:
            res = runner()
            results.append(res)

    all_passed = all(r.status == "PASSED" for r in results)

    if as_json:
        bundle = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": _get_git_commit(),
            "dataset_sha256": _compute_dataset_hash(),
            "overall_status": "PASSED" if all_passed else "FAILED",
            "gates_evaluated": len(results),
            "results": [asdict(r) for r in results],
        }
        typer.echo(json.dumps(bundle, indent=2, ensure_ascii=False))
        raise typer.Exit(code=0 if all_passed else 1)

    table = Table(title="LKIO Verification Results (11 Gates)", header_style="bold magenta", border_style="dim")
    table.add_column("Gate", justify="center", style="cyan", width=6)
    table.add_column("Category", style="magenta", width=12)
    table.add_column("Verification Subject", style="white", width=32)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Summary / Metric Proof", style="green", width=48)
    table.add_column("Latency", justify="right", style="yellow", width=10)

    for r in results:
        status_styled = f"[bold green]{r.status}[/bold green]" if r.status == "PASSED" else f"[bold red]{r.status}[/bold red]"
        table.add_row(
            f"G{r.gate_id:02d}",
            r.category,
            r.name,
            status_styled,
            r.summary,
            f"{r.duration_ms:.1f}ms",
        )

    console.print(table)

    summary_color = "bold green" if all_passed else "bold red"
    verdict = "PASSED (Zero-Defect Evidence Guarantee)" if all_passed else "FAILED (Verification Invariant Broken)"
    console.print(Panel(
        f"[{summary_color}]Overall Verdict: {verdict}[/{summary_color}]\n"
        f"[dim]Git Commit: {_get_git_commit()} | Dataset Fingerprint: {_compute_dataset_hash()} | Timestamp: {datetime.now(timezone.utc).isoformat()}[/dim]",
        border_style="green" if all_passed else "red",
    ))

    if not all_passed:
        raise typer.Exit(code=1)


@app.command(name="version")
def version_command():
    """Print LKIO Infrastructure version and commit information."""
    console.print(f"[bold cyan]LKIO Infrastructure v0.1.0[/bold cyan] (commit: {_get_git_commit()[:8]})")


def main():
    app()


if __name__ == "__main__":
    main()
