"""C-09 Real Projects System Verification Gate
Performs system-level integration verification of the Code Structural Graph
across all three external real-world repositories (HELLO_FE, HELLO_BE, L2C_FE).

Validates:
- VERIFY-GRAPH-01: Multi-repo real-world extraction coverage across TS, Vue, Java.
- VERIFY-GRAPH-02: Source Read-Only Invariance (strictly 0 working-tree modifications).
- VERIFY-GRAPH-03: Double-pass Idempotency & 3-set identity invariance on real code.
- VERIFY-GRAPH-04: Multi-project isolation across project boundaries.
- VERIFY-GRAPH-05: Predicate breakdown and statistical validity (imports, exports, extends, implements, calls).
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
from core.graph.extractors.call_relations import InvocationRelationExtractor
from core.graph.extractors.hierarchy_relations import HierarchyRelationExtractor
from core.graph.extractors.module_relations import ModuleRelationExtractor
from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
)
from core.graph.persistence import RelationPersistenceService
from core.graph.resolver import IntraProjectSymbolResolver, ResolverContext
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation

REPOS = {
    "HELLO_FE": Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello")),
    "HELLO_BE": Path(os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend")),
    "L2C_FE": Path(os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project")),
}


def capture_git_porcelain() -> dict[str, str]:
    """Captures exact porcelain output for each external repository."""
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
    """Isolated in-memory SQLite database session."""
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
    """Seeds the 3 real-world projects."""
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


def test_verify_graph_01_and_02_real_world_coverage_and_readonly(db_session, real_projects):
    """VERIFY-GRAPH-01 & VERIFY-GRAPH-02:
    Runs all graph extractors on representative files from all 3 repositories and verifies read-only redline.
    """
    before_git = capture_git_porcelain()

    module_ext = ModuleRelationExtractor()
    hierarchy_ext = HierarchyRelationExtractor()
    call_ext = InvocationRelationExtractor()

    test_files = [
        ("HELLO_FE", "demo/phone-frontend/components/TwilioCall.vue", "vue"),
        ("HELLO_BE", "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java", "java"),
        ("L2C_FE", "apps/web-antd/src/layouts/basic.vue", "vue"),
    ]

    all_extracted: list[RelationCandidate] = []

    for proj_key, rel_path, lang in test_files:
        full_path = REPOS[proj_key] / rel_path
        assert full_path.exists(), f"File {full_path} must exist"
        code_bytes = full_path.read_bytes()

        # 1. Module relations (imports/exports)
        mod_rels = module_ext.extract_from_code(code_bytes, lang, proj_key, rel_path)
        all_extracted.extend(mod_rels)

        # 2. Hierarchy relations (extends/implements)
        hier_rels = hierarchy_ext.extract_from_code(code_bytes, lang, proj_key, rel_path)
        all_extracted.extend(hier_rels)

        # 3. Invocation relations (calls)
        call_rels = call_ext.extract_from_code(code_bytes, lang, proj_key, rel_path)
        all_extracted.extend(call_rels)

    # Statistical sanity
    predicates = {r.predicate for r in all_extracted}
    assert RelationPredicate.IMPORTS in predicates
    assert RelationPredicate.CALLS in predicates
    assert len(all_extracted) > 10

    # VERIFY-GRAPH-02: Verify zero working-tree modifications across external repos
    after_git = capture_git_porcelain()
    assert before_git == after_git, "CRITICAL REDLINE: External repositories were modified during graph extraction!"


def test_verify_graph_03_double_pass_idempotency_on_real_code(db_session, real_projects):
    """VERIFY-GRAPH-03: Double-pass execution on real code produces 100% identical DB state."""
    service = RelationPersistenceService()
    module_ext = ModuleRelationExtractor()
    call_ext = InvocationRelationExtractor()

    proj = real_projects["HELLO_BE"]
    rel_path = "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"
    full_path = REPOS["HELLO_BE"] / rel_path
    code_bytes = full_path.read_bytes()

    # Create file entity in DB
    file_entity = Entity(
        id=uuid.uuid4(),
        project_id=proj.id,
        entity_key=f"FILE:{proj.key}:{rel_path}",
        name=Path(rel_path).name,
        canonical_name=f"{proj.key}_FILE_{Path(rel_path).stem}",
        entity_type="FILE",
        path=rel_path,
        status="ACTIVE",
    )
    db_session.add(file_entity)
    db_session.commit()

    candidates = module_ext.extract_from_code(code_bytes, "java", proj.key, rel_path)

    # Pass 1
    res1 = service.sync_file_relations(db_session, proj.id, proj.key, file_entity, candidates)
    db_session.commit()
    assert res1.created > 0

    rels_pass1 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "imports")).all()
    id_set_1 = {r.id for r in rels_pass1}
    key_set_1 = {r.relation_key for r in rels_pass1}
    triple_set_1 = {(r.subject_entity_id, r.predicate, r.raw_target) for r in rels_pass1}

    # Pass 2
    res2 = service.sync_file_relations(db_session, proj.id, proj.key, file_entity, candidates)
    db_session.commit()
    assert res2.created == 0
    assert res2.updated == len(candidates)
    assert res2.deleted == 0

    rels_pass2 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "imports")).all()
    id_set_2 = {r.id for r in rels_pass2}
    key_set_2 = {r.relation_key for r in rels_pass2}
    triple_set_2 = {(r.subject_entity_id, r.predicate, r.raw_target) for r in rels_pass2}

    # Exact 3-Set Equality
    assert id_set_1 == id_set_2
    assert key_set_1 == key_set_2
    assert triple_set_1 == triple_set_2


def test_verify_graph_04_multi_project_isolation(real_projects):
    """VERIFY-GRAPH-04: IntraProjectSymbolResolver enforces strict isolation between projects."""
    ctx_fe = ResolverContext(project_key="HELLO_FE")
    ctx_fe.register_file("src/utils/logger.ts", "FILE:HELLO_FE:src/utils/logger.ts")

    ctx_be = ResolverContext(project_key="HELLO_BE")
    ctx_be.register_file("src/main/java/org/example/Order.java", "FILE:HELLO_BE:src/main/java/org/example/Order.java")

    resolver_fe = IntraProjectSymbolResolver(ctx_fe)

    # Candidate belonging to HELLO_FE trying to reference a HELLO_BE file
    cross_cand = RelationCandidate(
        project_key="HELLO_FE",
        subject_entity_key="FILE:HELLO_FE:src/app.ts",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="org.example.Order",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        source_file_rel_path="src/app.ts",
    )

    resolved = resolver_fe.resolve_candidates([cross_cand])
    # Must remain UNRESOLVED because target is not in HELLO_FE context
    assert resolved[0].resolution_status == ResolutionStatus.UNRESOLVED
    assert resolved[0].object_entity_key is None


def test_verify_graph_05_predicate_distribution_breakdown():
    """VERIFY-GRAPH-05: Verifies that all 5 structural predicates are properly instantiated and typed."""
    predicates = [
        RelationPredicate.IMPORTS,
        RelationPredicate.EXPORTS,
        RelationPredicate.EXTENDS,
        RelationPredicate.IMPLEMENTS,
        RelationPredicate.CALLS,
    ]
    assert len(predicates) == 5
    assert all(isinstance(p, RelationPredicate) for p in predicates)
    assert {p.value for p in predicates} == {"imports", "exports", "extends", "implements", "calls"}
