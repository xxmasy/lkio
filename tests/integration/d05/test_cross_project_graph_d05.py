"""MVP2-D System Verification Gate on Real Projects (Gate D5)
Validates cross-project dependency discovery and relation persistence across:
- HELLO_FE (Vue / TS frontend)
- HELLO_BE (Java Spring Boot backend)
- L2C_FE (Vue 3 monorepo with apps and packages)

Enforces:
- LOCK-CROSS-04: Grounded evidence from real repository manifests.
- LOCK-CROSS-05: 3-Set identity invariance on real projects.
- LOCK-CROSS-06: Strict source read-only redline.
"""

from decimal import Decimal
from pathlib import Path
import subprocess
import uuid
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from core.db.base import Base
from core.graph.cross.manifest import CrossProjectManifestRegistry
from core.graph.cross.models import CrossProjectPredicate
from core.graph.cross.persistence import CrossProjectPersistenceService
from core.graph.cross.resolver import CrossProjectDependencyResolver
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation

REPOS = {
    "HELLO_FE": Path("C:/WorkSpace/hello"),
    "HELLO_BE": Path("C:/WorkSpace/hello-backend"),
    "L2C_FE": Path("C:/WorkSpace/L2C project"),
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


def test_gate_d5_real_projects_cross_manifest_discovery_and_readonly(db_session, real_projects):
    """Gate D5: Scans real manifests across all 3 projects, creates cross-project edges, and audits read-only redline."""
    before_git = capture_git_porcelain()

    registry = CrossProjectManifestRegistry()

    # 1. Scan manifests in all three repositories
    hello_fe_manifests = registry.scan_project_manifests("HELLO_FE", REPOS["HELLO_FE"])
    hello_be_manifests = registry.scan_project_manifests("HELLO_BE", REPOS["HELLO_BE"])
    l2c_manifests = registry.scan_project_manifests("L2C_FE", REPOS["L2C_FE"])

    assert len(hello_be_manifests) >= 1  # pom.xml
    assert len(l2c_manifests) >= 5  # root + apps + packages in monorepo

    # Check Java BE POM
    pom = next(m for m in hello_be_manifests if m.ecosystem == "maven")
    assert "haha" in pom.package_name.lower()

    # Check L2C packages
    package_names = {m.package_name for m in l2c_manifests}
    assert any("@vben" in name for name in package_names)

    # 2. Resolve cross-project / monorepo dependencies
    resolver = CrossProjectDependencyResolver(registry)
    deps = resolver.resolve_manifest_dependencies()
    # In L2C monorepo or across projects, apps depend on packages
    # Check that candidates have valid keys
    for d in deps:
        assert d.predicate == CrossProjectPredicate.DEPENDS_ON
        assert "RELATION:CROSS:" in d.relation_key

    # 3. Seed entities for manifests to test persistence
    service = CrossProjectPersistenceService()
    for m in (hello_fe_manifests + hello_be_manifests + l2c_manifests):
        proj = real_projects[m.project_key]
        ent = Entity(
            id=uuid.uuid4(),
            project_id=proj.id,
            entity_key=f"FILE:{m.project_key}:{m.manifest_rel_path}",
            name=Path(m.manifest_rel_path).name,
            canonical_name=f"{m.project_key}_FILE_{Path(m.manifest_rel_path).stem}",
            entity_type="FILE",
            path=m.manifest_rel_path,
            status="ACTIVE",
        )
        db_session.add(ent)
    db_session.commit()

    # Pass 1: Persist cross relations
    res1 = service.persist_cross_relations(db_session, deps)
    db_session.commit()
    assert res1.created == len(deps)

    rels_1 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "depends_on")).all()
    id_set_1 = {r.id for r in rels_1}
    key_set_1 = {r.relation_key for r in rels_1}
    triple_set_1 = {(r.subject_entity_id, r.predicate, r.object_entity_id) for r in rels_1}

    # Pass 2: Re-run
    res2 = service.persist_cross_relations(db_session, deps)
    db_session.commit()
    assert res2.created == 0
    assert res2.updated == len(deps)

    rels_2 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "depends_on")).all()
    id_set_2 = {r.id for r in rels_2}
    key_set_2 = {r.relation_key for r in rels_2}
    triple_set_2 = {(r.subject_entity_id, r.predicate, r.object_entity_id) for r in rels_2}

    # 3-Set Invariance
    assert id_set_1 == id_set_2
    assert key_set_1 == key_set_2
    assert triple_set_1 == triple_set_2

    # LOCK-CROSS-06: Strict source read-only audit
    after_git = capture_git_porcelain()
    assert before_git == after_git, "CRITICAL REDLINE: External repositories were modified during cross-project scan!"
