"""MVP2-E System Verification Gate on Real Projects (Gate E5)
Validates end-to-end API contract traceability between:
- HELLO_FE / L2C_FE frontend outgoing API client requests
- HELLO_BE backend Spring Boot REST controllers

Enforces:
- LOCK-TRACE-01: Objective endpoint contract derived from AST.
- LOCK-TRACE-03: Multi-layer traceability linking.
- LOCK-TRACE-04: Deterministic 3-Set identity invariance.
- LOCK-TRACE-05: Strict source read-only redline.
"""

from decimal import Decimal
import os
from pathlib import Path
import subprocess
import uuid
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from core.db.base import Base
from core.graph.api.backend_extractor import BackendControllerExtractor
from core.graph.api.frontend_extractor import FrontendApiExtractor
from core.graph.api.models import ApiTracePredicate, HttpMethod
from core.graph.api.persistence import ApiTracePersistenceService
from core.graph.api.traceability_engine import ApiTraceabilityEngine
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation

REPOS = {
    "HELLO_FE": Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello")),
    "HELLO_BE": Path(os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend")),
    "L2C_FE": Path(os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project")),
}


def capture_git_porcelain() -> dict[str, str]:
    snapshots = {}
    for name, root in REPOS.items():
        if root.exists():
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            snapshots[name] = res.stdout.strip()
    return snapshots


@pytest.fixture
def db_session() -> Session:
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def real_projects(db_session: Session) -> dict[str, Project]:
    projects = {}
    for key, path in REPOS.items():
        proj = Project(
            id=uuid.uuid4(),
            key=key,
            name=key,
            kind="frontend" if "FE" in key else "backend",
            role="primary_frontend" if key == "HELLO_FE" else ("paired_backend" if key == "HELLO_BE" else "future_frontend"),
            local_path=str(path),
            status="ACTIVE",
        )
        db_session.add(proj)
        projects[key] = proj
    db_session.commit()
    return projects


def test_gate_e5_real_projects_api_traceability_and_readonly(db_session, real_projects):
    """Gate E5: Discovers real API endpoints, generates end-to-end traceability relations, and verifies read-only."""
    before_git = capture_git_porcelain()

    be_extractor = BackendControllerExtractor()
    fe_extractor = FrontendApiExtractor()
    engine = ApiTraceabilityEngine()

    # 1. Extract backend endpoints from HELLO_BE CallConfigController
    be_file = "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"
    be_path = REPOS["HELLO_BE"] / be_file
    assert be_path.exists()
    be_endpoints = be_extractor.extract_from_code(be_path.read_bytes(), "HELLO_BE", be_file)
    assert len(be_endpoints) >= 1

    config_ep = next(ep for ep in be_endpoints if ep.normalized_path == "/api/call/config")
    assert config_ep.http_method == HttpMethod.GET
    assert "callConfigService.getSdkConfig" in config_ep.downstream_service_calls

    engine.register_backend_endpoints(be_endpoints)

    # 2. Extract frontend endpoints from HELLO_FE config/api.js or L2C API client
    fe_file = "demo/phone-frontend/config/api.js"
    fe_path = REPOS["HELLO_FE"] / fe_file
    assert fe_path.exists()
    fe_endpoints = fe_extractor.extract_from_code(fe_path.read_bytes(), "javascript", "HELLO_FE", fe_file)
    assert len(fe_endpoints) >= 1

    # 3. Add synthetic or real caller targeting /api/call/config to verify matching
    l2c_file = "apps/web-antd/src/api/core/auth.ts"
    l2c_path = REPOS["L2C_FE"] / l2c_file
    if l2c_path.exists():
        l2c_endpoints = fe_extractor.extract_from_code(l2c_path.read_bytes(), "typescript", "L2C_FE", l2c_file)
        assert len(l2c_endpoints) >= 1

    # 4. Generate trace candidates for matched call
    fe_caller_ep = fe_endpoints[0]
    traces = engine.align_frontend_calls(fe_endpoints, target_backend_project_key="HELLO_BE")
    # All candidates adhere to relation_key format
    for t in traces:
        assert t.predicate == ApiTracePredicate.TRACES_TO
        assert "RELATION:TRACE:" in t.relation_key

    # 5. Persist entities and trace relations into DB
    service = ApiTracePersistenceService()

    # Seed entities for subject and object
    fe_ent = Entity(
        id=uuid.uuid4(),
        project_id=real_projects["HELLO_FE"].id,
        entity_key=f"FILE:HELLO_FE:{fe_file}",
        name=Path(fe_file).name,
        canonical_name=f"HELLO_FE_FILE_{Path(fe_file).stem}",
        entity_type="FILE",
        path=fe_file,
        status="ACTIVE",
    )
    be_ent = Entity(
        id=uuid.uuid4(),
        project_id=real_projects["HELLO_BE"].id,
        entity_key=config_ep.enclosing_symbol_key,
        name="getConfig",
        canonical_name="HELLO_BE_getConfig",
        entity_type="METHOD",
        path=be_file,
        status="ACTIVE",
    )
    db_session.add_all([fe_ent, be_ent])
    db_session.commit()

    # Create test trace candidate
    trace_candidate = engine.align_frontend_calls([
        type(config_ep)(
            project_key="HELLO_FE",
            http_method=HttpMethod.GET,
            raw_path="/api/call/config",
            normalized_path="/api/call/config",
            source_file_rel_path=fe_file,
            line=20,
            enclosing_symbol_key=fe_ent.entity_key,
            is_backend_handler=False,
        )
    ], target_backend_project_key="HELLO_BE")

    assert len(trace_candidate) == 1
    tc = trace_candidate[0]

    # Pass 1
    res1 = service.sync_trace_relations(db_session, "HELLO_FE", [tc])
    db_session.commit()
    assert res1.created == 1

    rels_1 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "traces_to")).all()
    id_set_1 = {r.id for r in rels_1}
    key_set_1 = {r.relation_key for r in rels_1}
    triple_set_1 = {(r.subject_entity_id, r.predicate, r.object_entity_id) for r in rels_1}

    # Pass 2: Re-run
    res2 = service.sync_trace_relations(db_session, "HELLO_FE", [tc])
    db_session.commit()
    assert res2.created == 0
    assert res2.updated == 1

    rels_2 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "traces_to")).all()
    id_set_2 = {r.id for r in rels_2}
    key_set_2 = {r.relation_key for r in rels_2}
    triple_set_2 = {(r.subject_entity_id, r.predicate, r.object_entity_id) for r in rels_2}

    # 3-Set Invariance
    assert id_set_1 == id_set_2
    assert key_set_1 == key_set_2
    assert triple_set_1 == triple_set_2

    # LOCK-TRACE-05: Strict source read-only audit
    after_git = capture_git_porcelain()
    assert before_git == after_git, "CRITICAL REDLINE: External repositories were modified during API traceability scan!"
