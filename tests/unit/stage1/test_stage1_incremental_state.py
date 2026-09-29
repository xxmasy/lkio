"""Unit and Concurrency tests for Stage 1: Real-time Incremental Indexing & Repository State Engine.
Conforms to docs/LKIO_持续基础设施演进开发规范.md Section 3 (Stage 1 Gate 1).
"""

import threading
import time
import pytest
from core.indexing.change_detector import ChangeClassification, ChangeDetector
from core.indexing.equivalence_oracle import EquivalenceOracle
from core.indexing.pipeline import IncrementalIndexingPipeline, PipelineEvent
from core.indexing.relation_delta import RelationshipDeltaEngine
from core.indexing.symbol_delta import SymbolDeltaEngine, SymbolDeltaType
from core.state.snapshot import SnapshotManager, SnapshotStatus


def test_stage1_change_detector():
    old_files = {
        "src/LeadService.java": "public class LeadService { public void process() {} }",
        "src/OldFile.java": "public class OldFile {}",
    }
    new_files = {
        "src/LeadService.java": "public class LeadService {\n    // added comment\n    public void process() {}\n}",
        "src/NewFile.java": "public class NewFile {}",
    }

    diffs = ChangeDetector.detect_from_memory(old_files, new_files)
    diff_map = {d.file_path: d for d in diffs}

    assert "src/NewFile.java" in diff_map
    assert diff_map["src/NewFile.java"].change_type == ChangeClassification.ADDED

    assert "src/OldFile.java" in diff_map
    assert diff_map["src/OldFile.java"].change_type == ChangeClassification.DELETED

    assert "src/LeadService.java" in diff_map
    assert diff_map["src/LeadService.java"].change_type == ChangeClassification.MODIFIED
    assert diff_map["src/LeadService.java"].is_format_or_comment_only is True


def test_stage1_symbol_delta_and_signature_change():
    old_code = """
    public class OrderService {
        public void submitOrder(String orderId) {}
        public void cancelOrder(String orderId) {}
    }
    """
    new_code = """
    public class OrderService {
        public void submitOrder(String orderId, boolean notifyUser) {}
        public void refundOrder(String orderId) {}
    }
    """

    deltas = SymbolDeltaEngine.compute_file_symbol_delta("src/OrderService.java", old_code, new_code)
    delta_map = {d.symbol_name: d for d in deltas}

    assert "cancelOrder" in delta_map
    assert delta_map["cancelOrder"].delta_type == SymbolDeltaType.SYMBOL_DELETED

    assert "refundOrder" in delta_map
    assert delta_map["refundOrder"].delta_type == SymbolDeltaType.SYMBOL_ADDED

    assert "submitOrder" in delta_map
    assert delta_map["submitOrder"].delta_type == SymbolDeltaType.SIGNATURE_CHANGED


def test_stage1_incremental_pipeline_and_equivalence():
    repo_id = "test-repo"
    mgr = SnapshotManager(repo_id=repo_id, initial_commit="c0")
    pipeline = IncrementalIndexingPipeline(mgr)

    # Initial state
    files_v1 = {
        "src/A.java": "public class A { public void doA() {} }",
        "src/B.java": "public class B { public void doB() {} }",
    }
    diffs_v1 = ChangeDetector.detect_from_memory({}, files_v1)
    audit_v1 = pipeline.apply_incremental_update("c1", diffs_v1)
    assert audit_v1.status == "SUCCESS"
    assert mgr.get_current_snapshot().metadata.commit_id == "c1"

    # Version 2 state: Modify A (change signature), Delete B, Add C
    files_v2 = {
        "src/A.java": "public class A { public void doA(int count) {} }",
        "src/C.java": "public class C { public void doC() {} }",
    }
    diffs_v2 = ChangeDetector.detect_from_memory(files_v1, files_v2)
    audit_v2 = pipeline.apply_incremental_update("c2", diffs_v2)

    assert audit_v2.status == "SUCCESS"
    assert audit_v2.stale_edge_rate == 0.0
    current_snap = mgr.get_current_snapshot()
    assert current_snap.metadata.commit_id == "c2"

    # Verify semantic equivalence against clean Full Rebuild
    full_rebuilt_snap = EquivalenceOracle.full_rebuild(repo_id, files_v2, commit_id="c2")
    report = EquivalenceOracle.verify_equivalence(current_snap, full_rebuilt_snap)

    assert report.is_equivalent is True
    assert report.entity_match_rate == 1.0
    assert report.edge_match_rate == 1.0
    assert report.stale_edge_rate == 0.0
    assert len(report.discrepancies) == 0


def test_stage1_rollback_after_failed_validation():
    repo_id = "test-repo"
    mgr = SnapshotManager(repo_id=repo_id, initial_commit="c0")
    pipeline = IncrementalIndexingPipeline(mgr)

    # Seed baseline commit
    files_v1 = {"src/A.java": "public class A {}"}
    pipeline.apply_incremental_update("c1", ChangeDetector.detect_from_memory({}, files_v1))
    snapshot_before = mgr.get_current_snapshot()
    assert snapshot_before.metadata.commit_id == "c1"

    # Attempt faulty update with forced validation failure
    files_v2 = {"src/A.java": "public class A { public void broken() {} }"}
    diffs = ChangeDetector.detect_from_memory(files_v1, files_v2)
    audit_fail = pipeline.apply_incremental_update("c2_faulty", diffs, force_fail_validation=True)

    assert "FAILED" in audit_fail.status
    assert PipelineEvent.ROLLBACK_COMPLETED.value in audit_fail.events

    # Verify rollback: current snapshot remains 100% untouched
    snapshot_after = mgr.get_current_snapshot()
    assert snapshot_after.metadata.snapshot_id == snapshot_before.metadata.snapshot_id
    assert snapshot_after.metadata.commit_id == "c1"


def test_stage1_concurrency_zero_downtime():
    repo_id = "test-repo"
    mgr = SnapshotManager(repo_id=repo_id, initial_commit="c0")
    pipeline = IncrementalIndexingPipeline(mgr)

    files_init = {"src/A.java": "public class A {}"}
    pipeline.apply_incremental_update("c1", ChangeDetector.detect_from_memory({}, files_init))

    stop_readers = False
    read_results = []
    read_errors = []

    def reader_loop():
        while not stop_readers:
            try:
                snap = mgr.get_current_snapshot()
                assert snap.metadata.status == SnapshotStatus.PUBLISHED
                # Ensure no reader ever sees an empty or corrupt entity table
                assert len(snap.entities) > 0
                read_results.append(snap.metadata.commit_id)
            except Exception as e:
                read_errors.append(str(e))
            time.sleep(0.001)

    # Launch 5 concurrent readers
    threads = [threading.Thread(target=reader_loop) for _ in range(5)]
    for t in threads:
        t.start()

    # Writer executes multiple incremental updates
    for i in range(2, 6):
        files_next = {
            "src/A.java": f"public class A {{ public void step{i}() {{}} }}",
            f"src/File{i}.java": f"public class File{i} {{}}",
        }
        diffs = ChangeDetector.detect_from_memory(files_init, files_next)
        pipeline.apply_incremental_update(f"c{i}", diffs)
        files_init = files_next
        time.sleep(0.005)

    stop_readers = True
    for t in threads:
        t.join()

    assert len(read_errors) == 0
    assert len(read_results) > 10
    # Current snapshot must be c5
    assert mgr.get_current_snapshot().metadata.commit_id == "c5"


def test_stage1_snapshot_retention_policy():
    mgr = SnapshotManager(repo_id="retention-repo", initial_commit="c0", max_history_snapshots=5)
    pipeline = IncrementalIndexingPipeline(mgr)

    files_curr = {"src/Main.java": "public class Main {}"}
    base_snap_id = mgr.get_current_snapshot().metadata.snapshot_id

    # Apply 20 consecutive commits
    for i in range(1, 21):
        files_next = {"src/Main.java": f"public class Main {{ int v = {i}; }}"}
        diffs = ChangeDetector.detect_from_memory(files_curr, files_next)
        pipeline.apply_incremental_update(f"c{i}", diffs)
        files_curr = files_next

    # History count should be capped at max_history_snapshots + 1 (base snapshot)
    assert mgr.history_count == 6
    # Base snapshot must always be preserved
    assert mgr.get_snapshot(base_snap_id) is not None
    # Latest snapshot must be current
    assert mgr.get_current_snapshot().metadata.commit_id == "c20"
    # Older intermediate snapshots (e.g. c1) must have been safely pruned
    assert mgr.get_snapshot("snap_c1") is None

