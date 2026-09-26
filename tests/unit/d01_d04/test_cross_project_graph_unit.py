"""MVP2-D Cross-Project Graph Unit Tests (Gates D1 ~ D4)
Validates:
- Gate D1: Package & Module manifest discovery (package.json and pom.xml)
- Gate D2: Manifest dependency resolution (depends_on) and cross-module import resolution (cross_imports)
- Gate D3: Shared contract reference linking with calibrated confidence (references_contract)
- Gate D4: Cross-project relation persistence, soft-delete, and double-pass 3-set invariance
"""

from decimal import Decimal
from pathlib import Path
import tempfile
import uuid
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from core.db.base import Base
from core.graph.cross.contract_linker import CrossProjectContractLinker
from core.graph.cross.manifest import CrossProjectManifestRegistry
from core.graph.cross.models import (
    CrossProjectCandidate,
    CrossProjectPredicate,
    DeclaredDependency,
    PackageManifest,
)
from core.graph.cross.persistence import CrossProjectPersistenceService
from core.graph.cross.resolver import CrossProjectDependencyResolver
from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)
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


def test_gate_d1_manifest_discovery_and_registration():
    """Gate D1: Discovers and registers package.json and pom.xml manifests."""
    registry = CrossProjectManifestRegistry()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create a package.json
        pkg_json = root / "package.json"
        pkg_json.write_text("""{
            "name": "@myorg/core",
            "version": "1.2.0",
            "dependencies": {
                "lodash": "^4.17.21"
            },
            "devDependencies": {
                "typescript": "^5.0.0"
            },
            "workspaces": ["packages/*"]
        }""", encoding="utf-8")

        # Create a pom.xml
        pom_xml = root / "pom.xml"
        pom_xml.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
            <groupId>com.example</groupId>
            <artifactId>service-backend</artifactId>
            <version>2.0.0</version>
            <dependencies>
                <dependency>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-starter-web</artifactId>
                    <version>3.2.0</version>
                </dependency>
            </dependencies>
        </project>""", encoding="utf-8")

        manifests = registry.scan_project_manifests("TEST_PROJ", root)
        assert len(manifests) == 2

        npm_manifest = next(m for m in manifests if m.ecosystem == "npm")
        assert npm_manifest.package_name == "@myorg/core"
        assert npm_manifest.package_version == "1.2.0"
        assert len(npm_manifest.dependencies) == 2
        assert npm_manifest.workspaces == ("packages/*",)

        maven_manifest = next(m for m in manifests if m.ecosystem == "maven")
        assert maven_manifest.package_name == "com.example:service-backend"
        assert maven_manifest.package_version == "2.0.0"
        assert len(maven_manifest.dependencies) == 1


def test_gate_d2_cross_dependencies_and_imports_resolution():
    """Gate D2: Resolves depends_on across projects and cross_imports from unresolvable imports."""
    registry = CrossProjectManifestRegistry()

    # Project A provides @org/shared-lib
    manifest_a = PackageManifest(
        project_key="PROJ_A",
        manifest_rel_path="packages/shared/package.json",
        package_name="@org/shared-lib",
        package_version="1.0.0",
        ecosystem="npm",
    )
    registry.register_manifest(manifest_a)

    # Project B depends on @org/shared-lib
    manifest_b = PackageManifest(
        project_key="PROJ_B",
        manifest_rel_path="apps/web/package.json",
        package_name="@org/web-app",
        package_version="1.0.0",
        ecosystem="npm",
        dependencies=(
            DeclaredDependency(
                name="@org/shared-lib",
                version_constraint="^1.0.0",
                dependency_type="production",
                manifest_rel_path="apps/web/package.json",
            ),
        ),
    )
    registry.register_manifest(manifest_b)

    resolver = CrossProjectDependencyResolver(registry)

    # 1. Resolve manifest dependencies (depends_on)
    deps = resolver.resolve_manifest_dependencies()
    assert len(deps) == 1
    dep = deps[0]
    assert dep.source_project_key == "PROJ_B"
    assert dep.target_project_key == "PROJ_A"
    assert dep.predicate == CrossProjectPredicate.DEPENDS_ON
    assert dep.normalized_raw_target == "@org/shared-lib"
    assert dep.object_entity_key == "FILE:PROJ_A:packages/shared/package.json"

    # 2. Resolve cross imports (cross_imports)
    intra_unresolved_cand = RelationCandidate(
        project_key="PROJ_B",
        subject_entity_key="FILE:PROJ_B:apps/web/src/main.ts",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="@org/shared-lib/utils",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=2, column=0),),
        source_file_rel_path="apps/web/src/main.ts",
    )

    cross_imports = resolver.resolve_cross_imports([intra_unresolved_cand])
    assert len(cross_imports) == 1
    ci = cross_imports[0]
    assert ci.source_project_key == "PROJ_B"
    assert ci.target_project_key == "PROJ_A"
    assert ci.predicate == CrossProjectPredicate.CROSS_IMPORTS
    assert ci.normalized_raw_target == "@org/shared-lib/utils"


def test_gate_d3_cross_project_contract_linker():
    """Gate D3: Links consumer contract references to provider entity with calibrated confidence."""
    linker = CrossProjectContractLinker()
    linker.register_contract_provider(
        project_key="BACKEND",
        contract_name="OrderDTO",
        entity_key="SYMBOL:BACKEND:src/dto/OrderDTO.java:CLASS:OrderDTO:e3b0c44298fc1c14",
        file_rel_path="src/dto/OrderDTO.java",
    )

    references = [
        {
            "contract_name": "OrderDTO",
            "subject_key": "FILE:FRONTEND:src/api/order.ts",
            "file_rel_path": "src/api/order.ts",
            "occurrences": (SourceOccurrence(line=5, column=10),),
        }
    ]

    cands = linker.link_contract_references("FRONTEND", references)
    assert len(cands) == 1
    c = cands[0]
    assert c.source_project_key == "FRONTEND"
    assert c.target_project_key == "BACKEND"
    assert c.predicate == CrossProjectPredicate.REFERENCES_CONTRACT
    assert c.confidence == Decimal("0.85000")
    assert c.relation_kind == RelationKind.INFERRED
    assert c.object_entity_key == "SYMBOL:BACKEND:src/dto/OrderDTO.java:CLASS:OrderDTO:e3b0c44298fc1c14"


def test_gate_d4_cross_project_persistence_and_invariance(db_session: Session):
    """Gate D4: Persists cross-project relations, performs soft-delete, and proves 3-Set invariance."""
    proj_a = Project(
        id=uuid.uuid4(),
        key="PROJ_A",
        name="Project A",
        kind="frontend",
        role="primary_frontend",
        local_path="/path/a",
    )
    proj_b = Project(
        id=uuid.uuid4(),
        key="PROJ_B",
        name="Project B",
        kind="backend",
        role="paired_backend",
        local_path="/path/b",
    )
    db_session.add_all([proj_a, proj_b])

    ent_a = Entity(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        entity_key="FILE:PROJ_A:src/client.ts",
        name="client.ts",
        canonical_name="PROJ_A_FILE_client",
        entity_type="FILE",
        path="src/client.ts",
        status="ACTIVE",
    )
    ent_b = Entity(
        id=uuid.uuid4(),
        project_id=proj_b.id,
        entity_key="FILE:PROJ_B:src/api.java",
        name="api.java",
        canonical_name="PROJ_B_FILE_api",
        entity_type="FILE",
        path="src/api.java",
        status="ACTIVE",
    )
    db_session.add_all([ent_a, ent_b])
    db_session.commit()

    service = CrossProjectPersistenceService(strict_entities=True)

    cand1 = CrossProjectCandidate(
        source_project_key="PROJ_A",
        target_project_key="PROJ_B",
        subject_entity_key=ent_a.entity_key,
        predicate=CrossProjectPredicate.CROSS_IMPORTS,
        normalized_raw_target="com.example.api",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.RESOLVED,
        object_entity_key=ent_b.entity_key,
        candidate_discriminator="default",
        source_file_rel_path="src/client.ts",
    )

    # Pass 1
    res1 = service.sync_cross_relations(db_session, "PROJ_A", [cand1])
    assert res1.created == 1

    rels_1 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "cross_imports")).all()
    assert len(rels_1) == 1
    assert rels_1[0].subject_entity_id == ent_a.id
    assert rels_1[0].object_entity_id == ent_b.id
    assert rels_1[0].status == "ACTIVE"

    id_set_1 = {r.id for r in rels_1}
    key_set_1 = {r.relation_key for r in rels_1}
    triple_set_1 = {(r.subject_entity_id, r.predicate, r.object_entity_id) for r in rels_1}

    # Pass 2: Re-sync identical candidate
    res2 = service.sync_cross_relations(db_session, "PROJ_A", [cand1])
    assert res2.created == 0
    assert res2.updated == 1
    assert res2.deleted == 0

    rels_2 = db_session.scalars(sa.select(Relation).where(Relation.predicate == "cross_imports")).all()
    id_set_2 = {r.id for r in rels_2}
    key_set_2 = {r.relation_key for r in rels_2}
    triple_set_2 = {(r.subject_entity_id, r.predicate, r.object_entity_id) for r in rels_2}

    # Prove 3-Set Invariance
    assert id_set_1 == id_set_2
    assert key_set_1 == key_set_2
    assert triple_set_1 == triple_set_2

    # Step 3: Vanished relation -> Soft delete
    res3 = service.sync_cross_relations(db_session, "PROJ_A", [])
    assert res3.deleted == 1

    rel_after = db_session.scalar(sa.select(Relation).where(Relation.relation_key == cand1.relation_key))
    assert rel_after.status == "DELETED"
    assert rel_after.id in id_set_1
