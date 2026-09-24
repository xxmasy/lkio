"""Integration tests for Ingestion and Project Snapshot APIs
"""

import sys
from pathlib import Path
from starlette.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from apps.api.main import app

client = TestClient(app)


def test_project_snapshot_and_runs():
    # 1. Query HELLO_FE snapshot
    resp = client.get("/api/v1/projects/HELLO_FE/snapshot")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    snap = body["data"]
    assert snap is not None
    assert snap["head"] is not None
    assert snap["file_count"] > 100
    assert snap["directory_count"] > 10
    assert len(snap["frameworks"]) >= 3
    # Check framework structure
    fw_names = [f["name"] for f in snap["frameworks"]]
    assert "Vue" in fw_names
    assert "Element Plus" in fw_names

    # 2. Query HELLO_FE scan runs
    runs_resp = client.get("/api/v1/projects/HELLO_FE/scan-runs?limit=10")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()["data"]
    assert len(runs) >= 1
    assert runs[0]["status"] in ["COMPLETED", "RUNNING"]
    assert runs[0]["head_after"] is not None


def test_project_dependencies_and_frameworks():
    # 1. Query dependencies
    dep_resp = client.get("/api/v1/projects/HELLO_FE/dependencies")
    assert dep_resp.status_code == 200
    deps = dep_resp.json()["data"]
    assert len(deps) >= 20
    dep_names = [d["name"] for d in deps]
    assert "vue" in dep_names
    assert "element-plus" in dep_names
    assert "axios" in dep_names

    # 2. Query frameworks
    fw_resp = client.get("/api/v1/projects/HELLO_FE/frameworks")
    assert fw_resp.status_code == 200
    fws = fw_resp.json()["data"]
    assert len(fws) >= 3
    for fw in fws:
        assert fw["confidence"] >= 0.9
        assert fw["method"] == "package_manifest"
        assert len(fw["evidence"]) > 0


def test_trigger_single_scan():
    # Trigger scan on HELLO_FE
    scan_resp = client.post("/api/v1/projects/HELLO_FE/scan")
    assert scan_resp.status_code == 200
    run_data = scan_resp.json()["data"]
    assert run_data["status"] == "COMPLETED"
    assert run_data["files_seen"] > 100
    # Idempotency: entities created should be 0 on rescan
    assert run_data["entities_created"] == 0
