"""MVP2-E API End-to-End Contract Traceability Unit Tests (Gates E1 ~ E4)
Validates:
- Gate E1: Frontend API client call and route constant extraction
- Gate E2: Backend Spring Boot Controller route and downstream service extraction
- Gate E3: API contract alignment and full-chain traceability generation
- Gate E4: Traceability persistence, soft-delete, and double-pass 3-Set invariance
"""

from decimal import Decimal
import uuid
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from core.db.base import Base
from core.graph.api.backend_extractor import BackendControllerExtractor
from core.graph.api.frontend_extractor import FrontendApiExtractor
from core.graph.api.models import (
    ApiEndpoint,
    ApiTraceCandidate,
    ApiTracePredicate,
    HttpMethod,
    normalize_api_path,
)
from core.graph.api.persistence import ApiTracePersistenceService
from core.graph.api.traceability_engine import ApiTraceabilityEngine
from core.graph.models import RelationKind, ResolutionStatus, SourceOccurrence
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation


@pytest.fixture
def db_session() -> Session:
    """Isolated in-memory SQLite DB session."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_gate_e1_frontend_api_extractor():
    """Gate E1: Extracts outgoing API calls and route constants from TS and Vue SFC."""
    fe_code = b"""
import { requestClient } from '#/api/request';

export function getProfile(userId: string) {
    return requestClient.get('/api/users/' + userId);
}

export function login(data: any) {
    return requestClient.post('/api/auth/login', data);
}

export const API_PATHS = {
    RECORD_UPLOAD: '/api/call/record/upload'
};
"""
    extractor = FrontendApiExtractor()
    endpoints = extractor.extract_from_code(
        code_bytes=fe_code,
        language="typescript",
        project_key="TEST_FE",
        file_rel_path="src/api/auth.ts",
    )

    paths = {ep.normalized_path for ep in endpoints}
    assert "/api/auth/login" in paths
    assert "/api/call/record/upload" in paths

    login_ep = next(ep for ep in endpoints if ep.normalized_path == "/api/auth/login")
    assert login_ep.http_method == HttpMethod.POST
    assert login_ep.is_backend_handler is False
    assert "src/api/auth.ts" in login_ep.source_file_rel_path


def test_gate_e2_backend_controller_extractor():
    """Gate E2: Extracts Spring Boot controller routes, HTTP methods, and service calls."""
    be_code = b"""
package org.example.controller;

import org.springframework.web.bind.annotation.*;
import org.example.service.OrderService;

@RestController
@RequestMapping("/api/orders")
public class OrderController {
    private final OrderService orderService;

    @GetMapping("/config")
    public OrderConfig getConfig() {
        return orderService.getSystemConfig();
    }

    @PostMapping("/submit")
    public void submitOrder() {
        orderService.processOrder();
    }
}
"""
    extractor = BackendControllerExtractor()
    endpoints = extractor.extract_from_code(
        code_bytes=be_code,
        project_key="TEST_BE",
        file_rel_path="src/main/java/org/example/controller/OrderController.java",
    )

    assert len(endpoints) == 2

    get_ep = next(ep for ep in endpoints if ep.http_method == HttpMethod.GET)
    assert get_ep.normalized_path == "/api/orders/config"
    assert get_ep.is_backend_handler is True
    assert "orderService.getSystemConfig" in get_ep.downstream_service_calls

    post_ep = next(ep for ep in endpoints if ep.http_method == HttpMethod.POST)
    assert post_ep.normalized_path == "/api/orders/submit"
    assert "orderService.processOrder" in post_ep.downstream_service_calls


def test_gate_e3_api_traceability_alignment_engine():
    """Gate E3: Aligns frontend API calls with backend controller endpoints."""
    engine = ApiTraceabilityEngine()

    backend_ep = ApiEndpoint(
        project_key="TEST_BE",
        http_method=HttpMethod.POST,
        raw_path="/api/auth/login",
        normalized_path="/api/auth/login",
        source_file_rel_path="src/AuthController.java",
        line=25,
        enclosing_symbol_key="SYMBOL:TEST_BE:src/AuthController.java:METHOD:AuthController.login:e3b0c44298fc1c14",
        is_backend_handler=True,
        downstream_service_calls=("authService.authenticate",),
    )
    engine.register_backend_endpoints([backend_ep])

    frontend_ep = ApiEndpoint(
        project_key="TEST_FE",
        http_method=HttpMethod.POST,
        raw_path="/api/auth/login",
        normalized_path="/api/auth/login",
        source_file_rel_path="src/api/auth.ts",
        line=10,
        enclosing_symbol_key="SYMBOL:TEST_FE:src/api/auth.ts:FUNCTION:login:e3b0c44298fc1c14",
        is_backend_handler=False,
    )

    traces = engine.align_frontend_calls([frontend_ep], target_backend_project_key="TEST_BE")
    assert len(traces) == 1
    t = traces[0]

    assert t.source_project_key == "TEST_FE"
    assert t.target_project_key == "TEST_BE"
    assert t.predicate == ApiTracePredicate.TRACES_TO
    assert t.confidence == Decimal("1.00000")
    assert t.relation_kind == RelationKind.STATIC
    assert t.object_entity_key == backend_ep.enclosing_symbol_key
    assert "authService.authenticate" in t.metadata["downstream_services"]


def test_gate_e4_api_traceability_persistence_and_invariance(db_session: Session):
    """Gate E4: Persists API traceability links, executes soft-delete, and proves 3-Set invariance."""
    proj_fe = Project(
        id=uuid.uuid4(),
        key="TEST_FE",
        name="FE Project",
        kind="frontend",
        role="primary_frontend",
        local_path="/fe",
    )
    proj_be = Project(
        id=uuid.uuid4(),
        key="TEST_BE",
        name="BE Project",
        kind="backend",
        role="paired_backend",
        local_path="/be",
    )
    db_session.add_all([proj_fe, proj_be])

    fe_caller = Entity(
        id=uuid.uuid4(),
        project_id=proj_fe.id,
        entity_key="SYMBOL:TEST_FE:src/auth.ts:FUNCTION:login:e3b0c44298fc1c14",
        name="login",
        canonical_name="FE_login",
        entity_type="FUNCTION",
        path="src/auth.ts",
        status="ACTIVE",
    )
    be_controller = Entity(
        id=uuid.uuid4(),
        project_id=proj_be.id,
        entity_key="SYMBOL:TEST_BE:src/AuthController.java:METHOD:AuthController.login:e3b0c44298fc1c14",
        name="login",
        canonical_name="BE_login",
        entity_type="METHOD",
        path="src/AuthController.java",
        status="ACTIVE",
    )
    db_session.add_all([fe_caller, be_controller])
    db_session.commit()

    service = ApiTracePersistenceService(strict_entities=True)

    cand = ApiTraceCandidate(
        source_project_key="TEST_FE",
        target_project_key="TEST_BE",
        subject_entity_key=fe_caller.entity_key,
        predicate=ApiTracePredicate.TRACES_TO,
        normalized_endpoint="POST:/api/auth/login",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.RESOLVED,
        object_entity_key=be_controller.entity_key,
        candidate_discriminator="default",
        source_file_rel_path="src/auth.ts",
    )

    # Pass 1
    res1 = service.sync_trace_relations(db_session, "TEST_FE", [cand])
    assert res1.created == 1

    rels_1 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "traces_to")).all()
    assert len(rels_1) == 1
    assert rels_1[0].subject_entity_id == fe_caller.id
    assert rels_1[0].object_entity_id == be_controller.id

    id_set_1 = {r.id for r in rels_1}
    key_set_1 = {r.relation_key for r in rels_1}
    triple_set_1 = {(r.subject_entity_id, r.predicate, r.object_entity_id) for r in rels_1}

    # Pass 2: Re-run
    res2 = service.sync_trace_relations(db_session, "TEST_FE", [cand])
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

    # Step 3: Vanished -> Soft delete
    res3 = service.sync_trace_relations(db_session, "TEST_FE", [])
    assert res3.deleted == 1

    rel_after = db_session.scalar(sa.select(Relation).where(Relation.relation_key == cand.relation_key))
    assert rel_after.status == "DELETED"
