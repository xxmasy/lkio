"""Integration & Unit Tests for LKIO API v1
"""

import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from apps.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert "data" in body
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] == "connected"
    assert body["data"]["pgvector_version"] == "0.8.6"
    assert "request_id" in body["meta"]


def test_overview_endpoint():
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    data = body["data"]
    assert data["project_count"] >= 3
    assert data["frontend_count"] >= 2
    assert data["backend_count"] >= 1
    assert data["entity_count"] >= 9
    assert data["relation_count"] >= 7
    assert data["source_count"] >= 3


def test_projects_endpoints():
    # 1. List projects
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    projects = body["data"]
    keys = [p["key"] for p in projects]
    assert "HELLO_FE" in keys
    assert "HELLO_BE" in keys
    assert "L2C_FE" in keys

    # 2. Get project by key
    p_resp = client.get("/api/v1/projects/HELLO_FE")
    assert p_resp.status_code == 200
    p_body = p_resp.json()["data"]
    assert p_body["key"] == "HELLO_FE"
    assert p_body["role"] == "primary_frontend"
    assert p_body["entity_count"] >= 3
    assert "HELLO_BE" in p_body["related_projects"]

    # 3. Conflict on duplicate project creation
    dup_resp = client.post(
        "/api/v1/projects",
        json={
            "key": "HELLO_FE",
            "name": "hello",
            "kind": "frontend",
            "role": "primary_frontend",
            "local_path": "/workspace/hello",
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "conflict"


def test_entities_endpoints():
    response = client.get("/api/v1/entities?limit=20")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert len(body["data"]) >= 9

    # Filter by entity_type
    proj_entities = client.get("/api/v1/entities?entity_type=PROJECT").json()["data"]
    assert len(proj_entities) >= 3

    # Get specific entity
    e_resp = client.get("/api/v1/entities/PROJECT:HELLO_FE")
    assert e_resp.status_code == 200
    assert e_resp.json()["data"]["name"] == "hello"


def test_relations_endpoints():
    response = client.get("/api/v1/relations")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert len(body["data"]) >= 7

    # Filter by predicate
    paired_rels = client.get("/api/v1/relations?predicate=paired_with").json()["data"]
    assert len(paired_rels) >= 1


def test_graph_endpoints():
    # 1. Project graph
    p_graph_resp = client.get("/api/v1/graph/projects/HELLO_FE")
    assert p_graph_resp.status_code == 200
    g_body = p_graph_resp.json()["data"]
    nodes = g_body["nodes"]
    edges = g_body["edges"]

    # Cytoscape element structure checks
    assert len(nodes) >= 3
    assert len(edges) >= 2
    for node in nodes:
        assert "id" in node["data"]
        assert "label" in node["data"]
        assert "entity_type" in node["data"]
    for edge in edges:
        assert "source" in edge["data"]
        assert "target" in edge["data"]
        assert "predicate" in edge["data"]

    # 2. Neighbors graph
    n_resp = client.get("/api/v1/graph/entities/PROJECT:HELLO_FE/neighbors")
    assert n_resp.status_code == 200
    n_body = n_resp.json()["data"]
    assert len(n_body["nodes"]) >= 2

    # 3. Overview graph
    o_resp = client.get("/api/v1/graph/overview")
    assert o_resp.status_code == 200
    o_body = o_resp.json()["data"]
    assert len(o_body["nodes"]) >= 9
    assert len(o_body["edges"]) >= 7


def test_error_handling():
    # 1. 404 not_found
    resp_404 = client.get("/api/v1/projects/NON_EXISTENT_KEY")
    assert resp_404.status_code == 404
    b_404 = resp_404.json()
    assert b_404["data"] is None
    assert b_404["error"]["code"] == "not_found"
    assert "request_id" in b_404["meta"]

    # 2. 400 validation_error
    resp_400 = client.post(
        "/api/v1/projects",
        json={"name": "missing_required_fields"},
    )
    assert resp_400.status_code == 400
    b_400 = resp_400.json()
    assert b_400["data"] is None
    assert b_400["error"]["code"] == "validation_error"

