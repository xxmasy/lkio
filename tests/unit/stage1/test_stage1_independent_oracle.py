"""Unit tests for Stage 1 Hard Gate G1.8: Independent Oracle.
Verifies that Incremental State Engine matches clean-room Canonical Graph without self-referential bias.
"""

import pytest
from core.indexing.change_detector import ChangeDetector
from core.indexing.independent_oracle import IndependentOracle
from core.indexing.pipeline import IncrementalIndexingPipeline
from core.state.snapshot import SnapshotEdge, SnapshotManager


def test_g1_8_independent_oracle_clean_room_verification():
    repo_id = "oracle-test-repo"
    mgr = SnapshotManager(repo_id=repo_id, initial_commit="c0")
    pipeline = IncrementalIndexingPipeline(mgr)

    # Initial state (c1): 2 files with classes and methods
    files_v1 = {
        "src/OrderService.java": (
            "public class OrderService {\n"
            "    public void createOrder(String itemId) {}\n"
            "    public void cancelOrder(String orderId) {}\n"
            "}\n"
        ),
        "src/PaymentService.java": (
            "public class PaymentService {\n"
            "    public void processPayment(double amount) {}\n"
            "}\n"
        ),
    }

    # Step 1: Initial load
    diffs_v1 = ChangeDetector.detect_from_memory({}, files_v1)
    pipeline.apply_incremental_update("c1", diffs_v1)
    snap_v1 = mgr.get_current_snapshot()

    canonical_v1 = IndependentOracle.build_canonical_graph(repo_id, files_v1)
    audit_v1 = IndependentOracle.audit_snapshot_against_canonical(snap_v1, canonical_v1)
    assert audit_v1.passed is True
    assert audit_v1.node_recall == 1.0
    assert audit_v1.node_precision == 1.0
    assert audit_v1.stale_edges_count == 0

    # Step 2: Incremental mutation (c2):
    # - Add UserReport.java
    # - Delete PaymentService.java
    # - Modify OrderService.java (remove cancelOrder, add refundOrder)
    files_v2 = {
        "src/OrderService.java": (
            "public class OrderService {\n"
            "    public void createOrder(String itemId) {}\n"
            "    public void refundOrder(String orderId, double amt) {}\n"
            "}\n"
        ),
        "src/UserReport.java": (
            "public class UserReport {\n"
            "    public void exportStats() {}\n"
            "}\n"
        ),
    }

    diffs_v2 = ChangeDetector.detect_from_memory(files_v1, files_v2)
    pipeline.apply_incremental_update("c2", diffs_v2)
    snap_v2 = mgr.get_current_snapshot()

    # Step 3: Independent Canonical extraction on files_v2
    canonical_v2 = IndependentOracle.build_canonical_graph(repo_id, files_v2)
    audit_v2 = IndependentOracle.audit_snapshot_against_canonical(snap_v2, canonical_v2)

    assert audit_v2.passed is True
    assert audit_v2.node_recall == 1.0
    assert audit_v2.node_precision == 1.0
    assert audit_v2.edge_recall == 1.0
    assert audit_v2.edge_precision == 1.0
    assert audit_v2.stale_edges_count == 0
    assert len(audit_v2.discrepancies) == 0


def test_g1_8_independent_oracle_detects_injected_discrepancy():
    repo_id = "discrepancy-repo"
    mgr = SnapshotManager(repo_id=repo_id, initial_commit="c0")
    snap = mgr.get_current_snapshot()

    files = {"src/A.java": "public class A { public void run() {} }"}
    canonical = IndependentOracle.build_canonical_graph(repo_id, files)

    # Inject dangling stale edge into snapshot
    snap.add_edge(
        SnapshotEdge(
            edge_key="edge://repo://discrepancy-repo/src/Ghost.java->CONTAINS->ghostMethod",
            source_key="repo://discrepancy-repo/src/Ghost.java",
            predicate="CONTAINS",
            target_key="ghostMethod",
        )
    )

    audit = IndependentOracle.audit_snapshot_against_canonical(snap, canonical)
    assert audit.passed is False
    assert audit.stale_edges_count > 0
    assert any("Stale dangling edge" in d for d in audit.discrepancies)
