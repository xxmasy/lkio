"""C-08 Relation Lifecycle, Soft-Delete & Idempotency Pipeline Tests
Validates:
- Gate Y: Soft-delete synchronization (vanished relations marked DELETED, never physically deleted)
- Gate Z: Reactivation state machine (DELETED relations resurrected to ACTIVE upon reappearance)
- Gate AA: Double-scan 3-set identity invariance (id_set, key_set, triple_set bit-for-bit identical)
- Protection of MVP2-B 'defines' relations from soft-delete
"""

from decimal import Decimal
import uuid
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from core.db.base import Base
from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)
from core.graph.persistence import RelationPersistenceService
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation


@pytest.fixture
def db_session() -> Session:
    """Provides a fresh in-memory SQLite database session."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_setup(db_session: Session):
    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        key="TEST_PROJ",
        name="Test Project",
        kind="backend",
        role="paired_backend",
        local_path="/path/to/test",
    )
    db_session.add(project)

    file_entity = Entity(
        id=uuid.uuid4(),
        project_id=project_id,
        entity_key="FILE:TEST_PROJ:src/OrderService.java",
        name="OrderService.java",
        canonical_name="OrderService.java",
        entity_type="FILE",
        path="src/OrderService.java",
        status="ACTIVE",
    )
    db_session.add(file_entity)

    class_entity = Entity(
        id=uuid.uuid4(),
        project_id=project_id,
        entity_key="SYMBOL:TEST_PROJ:src/OrderService.java:CLASS:OrderService:e3b0c44298fc1c14",
        name="OrderService",
        canonical_name="OrderService",
        entity_type="CLASS",
        path="src/OrderService.java",
        status="ACTIVE",
    )
    db_session.add(class_entity)

    # Add a B-07 'defines' relation
    defines_rel = Relation(
        id=uuid.uuid4(),
        relation_key="RELATION:DEFINES:test",
        subject_entity_id=file_entity.id,
        predicate="defines",
        object_entity_id=class_entity.id,
        status="ACTIVE",
    )
    db_session.add(defines_rel)

    db_session.commit()
    return {
        "project_id": project_id,
        "project_key": "TEST_PROJ",
        "file_entity": file_entity,
        "class_entity": class_entity,
        "defines_rel": defines_rel,
    }


def test_gate_y_soft_delete_synchronization(db_session, test_setup):
    """Gate Y: Relations vanished from source are marked DELETED, never physically deleted."""
    service = RelationPersistenceService()
    file_entity = test_setup["file_entity"]
    proj_id = test_setup["project_id"]
    proj_key = test_setup["project_key"]

    cand_import_a = RelationCandidate(
        project_key=proj_key,
        subject_entity_key=file_entity.entity_key,
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="com.example.util.Logger",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=1, column=0),),
        source_file_rel_path="src/OrderService.java",
    )
    cand_import_b = RelationCandidate(
        project_key=proj_key,
        subject_entity_key=file_entity.entity_key,
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="com.example.util.Config",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=2, column=0),),
        source_file_rel_path="src/OrderService.java",
    )

    # Step 1: Initial sync with both imports A and B
    res1 = service.sync_file_relations(db_session, proj_id, proj_key, file_entity, [cand_import_a, cand_import_b])
    assert res1.created == 2

    rels = db_session.scalars(sa.select(Relation).where(Relation.predicate == "imports")).all()
    assert len(rels) == 2
    assert all(r.status == "ACTIVE" for r in rels)

    # Step 2: Second sync where import B has vanished (removed from code)
    res2 = service.sync_file_relations(db_session, proj_id, proj_key, file_entity, [cand_import_a])
    assert res2.deleted == 1

    # Invariant: Physical count remains 2 (zero physical DELETE)
    all_imports = db_session.scalars(sa.select(Relation).where(Relation.predicate == "imports")).all()
    assert len(all_imports) == 2

    rel_a = next(r for r in all_imports if r.raw_target == "com.example.util.Logger")
    rel_b = next(r for r in all_imports if r.raw_target == "com.example.util.Config")
    assert rel_a.status == "ACTIVE"
    assert rel_b.status == "DELETED"

    # Invariant: MVP2-B 'defines' relation remains untouched and ACTIVE
    defines_rel = db_session.scalar(sa.select(Relation).where(Relation.predicate == "defines"))
    assert defines_rel.status == "ACTIVE"


def test_gate_z_reactivation_state_machine(db_session, test_setup):
    """Gate Z: A soft-deleted relation is resurrected to ACTIVE upon reappearing."""
    service = RelationPersistenceService()
    file_entity = test_setup["file_entity"]
    proj_id = test_setup["project_id"]
    proj_key = test_setup["project_key"]

    cand = RelationCandidate(
        project_key=proj_key,
        subject_entity_key=file_entity.entity_key,
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="com.example.util.Logger",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=1, column=0),),
        source_file_rel_path="src/OrderService.java",
    )

    # 1. Initial create
    service.sync_file_relations(db_session, proj_id, proj_key, file_entity, [cand])
    rel = db_session.scalars(sa.select(Relation).where(Relation.relation_key == cand.relation_key)).one()
    orig_id = rel.id
    assert rel.status == "ACTIVE"

    # 2. Vanished (soft-deleted)
    service.sync_file_relations(db_session, proj_id, proj_key, file_entity, [])
    db_session.refresh(rel)
    assert rel.status == "DELETED"

    # 3. Reappeared -> Reactivated
    res = service.sync_file_relations(db_session, proj_id, proj_key, file_entity, [cand])
    db_session.refresh(rel)
    assert rel.status == "ACTIVE"
    assert rel.id == orig_id
    assert res.reactivated == 1


def test_gate_aa_double_scan_3set_identity_invariance(db_session, test_setup):
    """Gate AA: Double scan yields 100% identical id_set, key_set, and triple_set (LOCK-GRAPH-02, LOCK-GRAPH-10)."""
    service = RelationPersistenceService()
    file_entity = test_setup["file_entity"]
    class_entity = test_setup["class_entity"]
    proj_id = test_setup["project_id"]
    proj_key = test_setup["project_key"]

    candidates = [
        RelationCandidate(
            project_key=proj_key,
            subject_entity_key=file_entity.entity_key,
            predicate=RelationPredicate.IMPORTS,
            normalized_raw_target="com.example.service.BaseService",
            relation_kind=RelationKind.STATIC,
            confidence=Decimal("1.00000"),
            resolution_status=ResolutionStatus.UNRESOLVED,
            occurrences=(SourceOccurrence(line=3, column=0),),
            source_file_rel_path="src/OrderService.java",
        ),
        RelationCandidate(
            project_key=proj_key,
            subject_entity_key=class_entity.entity_key,
            predicate=RelationPredicate.EXTENDS,
            normalized_raw_target="BaseService",
            relation_kind=RelationKind.STATIC,
            confidence=Decimal("1.00000"),
            resolution_status=ResolutionStatus.UNRESOLVED,
            occurrences=(SourceOccurrence(line=7, column=35),),
            source_file_rel_path="src/OrderService.java",
        ),
        RelationCandidate(
            project_key=proj_key,
            subject_entity_key=class_entity.entity_key,
            predicate=RelationPredicate.CALLS,
            normalized_raw_target="super.init",
            relation_kind=RelationKind.STATIC,
            confidence=Decimal("1.00000"),
            resolution_status=ResolutionStatus.UNRESOLVED,
            occurrences=(SourceOccurrence(line=12, column=8),),
            source_file_rel_path="src/OrderService.java",
        ),
    ]

    # Pass 1
    res1 = service.sync_file_relations(db_session, proj_id, proj_key, file_entity, candidates)
    assert res1.created == 3

    rels_pass1 = db_session.scalars(
        sa.select(Relation).where(Relation.predicate != "defines")
    ).all()
    id_set_1 = {r.id for r in rels_pass1}
    key_set_1 = {r.relation_key for r in rels_pass1}
    triple_set_1 = {(r.subject_entity_id, r.predicate, r.raw_target) for r in rels_pass1}

    # Pass 2: Re-run with exact same input
    res2 = service.sync_file_relations(db_session, proj_id, proj_key, file_entity, candidates)
    assert res2.created == 0
    assert res2.updated == 3
    assert res2.deleted == 0

    rels_pass2 = db_session.scalars(
        sa.select(Relation).where(Relation.predicate != "defines")
    ).all()
    id_set_2 = {r.id for r in rels_pass2}
    key_set_2 = {r.relation_key for r in rels_pass2}
    triple_set_2 = {(r.subject_entity_id, r.predicate, r.raw_target) for r in rels_pass2}

    # Verify 3-Set Invariance
    assert id_set_1 == id_set_2
    assert key_set_1 == key_set_2
    assert triple_set_1 == triple_set_2
