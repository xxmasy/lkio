"""Unit tests for Stage 0 Baseline Freeze, Entity Identity, and Unified SDK Contract.
Conforms to docs/LKIO_持续基础设施演进开发规范.md Section 2 (Stage 0 Gate).
"""

import json
from pathlib import Path
import pytest
from core.identity import build_edge_key, build_entity_uri, parse_entity_uri
from core.sdk import LKIO


def test_stage0_baseline_manifests_and_metrics_frozen():
    base_dir = Path("benchmarks/baseline_v1")
    assert base_dir.exists()
    assert (base_dir / "README.md").exists()

    metrics_file = base_dir / "metrics.json"
    assert metrics_file.exists()
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert metrics["status"] == "FROZEN"
    assert "layers" in metrics
    assert len(metrics["layers"]) == 15
    assert len(metrics["master_table"]) == 8

    # Verify I1~I6 invariants are frozen
    invariants = metrics["invariants"]
    assert invariants["I1_Cycle_Safety"] is True
    assert invariants["I2_Seed_Isolation"] is True
    assert invariants["I3_Depth_Bound"] is True
    assert invariants["I4_Shortest_Hop_Preservation"] is True
    assert invariants["I5_Monotonic_Classification"] is True
    assert invariants["I6_Evidence_Accumulation"] is True


def test_stage0_entity_identity_namespace():
    uri = build_entity_uri("hello-be", "src/service/LeadService.java", "computeMetrics")
    assert uri == "repo://hello-be/src/service/LeadService.java#computeMetrics"

    parsed = parse_entity_uri(uri)
    assert parsed.repo_id == "hello-be"
    assert parsed.file_path == "src/service/LeadService.java"
    assert parsed.symbol_name == "computeMetrics"

    # Test file-only URI
    file_uri = build_entity_uri("hello-fe", "src/views/App.vue")
    assert file_uri == "repo://hello-fe/src/views/App.vue"
    parsed_file = parse_entity_uri(file_uri)
    assert parsed_file.symbol_name is None

    # Test edge key
    edge_key = build_edge_key(uri, "CALLS", "repo://hello-be/src/repo/LeadRepo.java")
    assert edge_key.startswith("edge://repo://hello-be/")

    with pytest.raises(ValueError):
        parse_entity_uri("invalid_uri_without_prefix")


def test_stage0_unified_sdk_nine_methods():
    lkio = LKIO(default_repo_id="test-repo")

    # 1. search
    res_search = lkio.search("North America Sales")
    assert len(res_search) > 0
    assert res_search[0].file_path

    # 2. symbol
    res_symbol = lkio.symbol("NorthAmericaSalesDailyReportRowDTO")
    assert len(res_symbol) > 0
    assert "DTO" in res_symbol[0].name

    # 3. references
    res_refs = lkio.references("repo://test-repo/src/service/LeadService.java#LeadService")
    assert len(res_refs) >= 2
    assert res_refs[0].reference_type in ("CALLS", "INVOKES")

    # 4. dependencies
    res_deps = lkio.dependencies("repo://test-repo/src/service/LeadService.java", depth=3)
    assert res_deps.seed
    assert len(res_deps.nodes) >= 2

    # 5. impact
    res_impact = lkio.impact(["SERVICE:HELLO_BE:MetricsService"], depth=3)
    assert len(res_impact.direct) > 0

    # 6. history
    res_hist = lkio.history("src/service/LeadService.java")
    assert len(res_hist) > 0
    assert res_hist[0].commit_id == "83b1069"

    # 7. snapshot
    res_snap = lkio.snapshot("83b1069abc")
    assert res_snap.snapshot_id.startswith("snap_")
    assert res_snap.status == "PUBLISHED"

    # 8. explain
    res_explain = lkio.explain("repo://test-repo/src/service/LeadService.java#LeadService")
    assert res_explain.role
    assert res_explain.summary

    # 9. decision
    res_dec = lkio.decision(
        "CHANGE_IMPACT",
        {
            "state": {"changed_entities": ["NorthAmericaSalesDailyDetailMetricsService"]},
            "question": {"options": ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        },
    )
    assert res_dec.decision in ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert 0.0 <= res_dec.confidence <= 1.0
