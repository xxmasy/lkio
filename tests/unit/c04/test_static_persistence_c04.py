"""C-04 Static Relations Persistence & Occurrence Dedup Tests
Validates:
- Gate M: Occurrence merging (multiple occurrences merged into single relation candidate and JSONB)
- Gate N: Entity resolution (subject_entity_key resolved to subject_entity_id, strict check)
- Gate O: Idempotent double-save (identical row counts, zero duplicates, stable IDs)
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
from core.graph.persistence import RelationPersistenceService, merge_relation_candidates
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation


@pytest.fixture
def db_session() -> Session:
    """Provides a clean in-memory SQLite DB session."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_data(db_session: Session):
    """Seeds test project and entities."""
    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        key="TEST_PROJ",
        name="Test Project",
        kind="frontend",
        role="primary_frontend",
        local_path="/path/to/test",
    )
    db_session.add(project)

    file_entity = Entity(
        id=uuid.uuid4(),
        project_id=project_id,
        entity_key="FILE:TEST_PROJ:src/service/UserService.ts",
        name="UserService.ts",
        canonical_name="UserService.ts",
        entity_type="FILE",
        path="src/service/UserService.ts",
        status="ACTIVE",
    )
    db_session.add(file_entity)

    class_entity = Entity(
        id=uuid.uuid4(),
        project_id=project_id,
        entity_key="SYMBOL:TEST_PROJ:src/service/UserService.ts:CLASS:UserService:e3b0c44298fc1c14",
        name="UserService",
        canonical_name="UserService",
        entity_type="CLASS",
        path="src/service/UserService.ts",
        status="ACTIVE",
    )
    db_session.add(class_entity)

    dep_file_entity = Entity(
        id=uuid.uuid4(),
        project_id=project_id,
        entity_key="FILE:TEST_PROJ:src/utils/logger.ts",
        name="logger.ts",
        canonical_name="logger.ts",
        entity_type="FILE",
        path="src/utils/logger.ts",
        status="ACTIVE",
    )
    db_session.add(dep_file_entity)

    db_session.commit()
    return {
        "project_id": project_id,
        "project_key": "TEST_PROJ",
        "file_entity": file_entity,
        "class_entity": class_entity,
        "dep_file_entity": dep_file_entity,
    }


def test_gate_m_occurrence_merging(seed_data):
    """Gate M: Multiple occurrences for the same relation merge into single candidate."""
    cand1 = RelationCandidate(
        project_key="TEST_PROJ",
        subject_entity_key="FILE:TEST_PROJ:src/service/UserService.ts",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="./logger",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=5, column=0),),
        source_file_rel_path="src/service/UserService.ts",
    )
    cand2 = RelationCandidate(
        project_key="TEST_PROJ",
        subject_entity_key="FILE:TEST_PROJ:src/service/UserService.ts",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="./logger",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=12, column=4),),
        source_file_rel_path="src/service/UserService.ts",
    )

    merged = merge_relation_candidates([cand1, cand2])
    assert len(merged) == 1
    assert len(merged[0].occurrences) == 2
    assert merged[0].occurrences[0].line == 5
    assert merged[0].occurrences[1].line == 12


def test_gate_n_entity_resolution_and_persistence(db_session, seed_data):
    """Gate N: Subject and object entity key resolution to entity IDs."""
    service = RelationPersistenceService(strict_subjects=True)

    cand = RelationCandidate(
        project_key="TEST_PROJ",
        subject_entity_key=seed_data["file_entity"].entity_key,
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="./logger",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.RESOLVED,
        occurrences=(SourceOccurrence(line=2, column=0),),
        object_entity_key=seed_data["dep_file_entity"].entity_key,
        source_file_rel_path="src/service/UserService.ts",
    )

    result = service.persist_relations(
        db=db_session,
        project_id=seed_data["project_id"],
        project_key=seed_data["project_key"],
        candidates=[cand],
    )

    assert result.created == 1
    assert result.unique_edges == 1
    assert result.unresolved_subjects == 0

    # Query DB
    rel = db_session.scalars(sa.select(Relation).where(Relation.relation_key == cand.relation_key)).one()
    assert rel.subject_entity_id == seed_data["file_entity"].id
    assert rel.object_entity_id == seed_data["dep_file_entity"].id
    assert rel.predicate == "imports"
    assert rel.resolution_status == "RESOLVED"
    assert rel.status == "ACTIVE"
    assert len(rel.occurrences) == 1
    assert rel.occurrences[0]["line"] == 2

    # Test strict mode failure on missing subject
    bad_cand = RelationCandidate(
        project_key="TEST_PROJ",
        subject_entity_key="FILE:TEST_PROJ:src/nonexistent.ts",
        predicate=RelationPredicate.IMPORTS,
        normalized_raw_target="./foo",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=1, column=0),),
        source_file_rel_path="src/nonexistent.ts",
    )
    with pytest.raises(ValueError, match="Relational Integrity Violation"):
        service.persist_relations(
            db=db_session,
            project_id=seed_data["project_id"],
            project_key=seed_data["project_key"],
            candidates=[bad_cand],
        )


def test_gate_o_idempotent_double_save(db_session, seed_data):
    """Gate O: Idempotent double save preserves exact row count, IDs, and merges occurrences."""
    service = RelationPersistenceService()

    cand1 = RelationCandidate(
        project_key="TEST_PROJ",
        subject_entity_key=seed_data["class_entity"].entity_key,
        predicate=RelationPredicate.EXTENDS,
        normalized_raw_target="BaseService",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=10, column=25),),
        source_file_rel_path="src/service/UserService.ts",
    )

    # Pass 1: Initial save
    res1 = service.persist_relations(
        db=db_session,
        project_id=seed_data["project_id"],
        project_key=seed_data["project_key"],
        candidates=[cand1],
    )
    assert res1.created == 1
    assert res1.updated == 0

    rel_pass1 = db_session.scalars(sa.select(Relation).where(Relation.relation_key == cand1.relation_key)).one()
    orig_id = rel_pass1.id

    # Pass 2: Re-save exact same candidate
    res2 = service.persist_relations(
        db=db_session,
        project_id=seed_data["project_id"],
        project_key=seed_data["project_key"],
        candidates=[cand1],
    )
    assert res2.created == 0
    assert res2.updated == 1

    rel_pass2 = db_session.scalars(sa.select(Relation).where(Relation.relation_key == cand1.relation_key)).one()
    assert rel_pass2.id == orig_id  # Stable UUID primary key

    # Pass 3: Re-save with additional occurrence site
    cand2 = RelationCandidate(
        project_key="TEST_PROJ",
        subject_entity_key=seed_data["class_entity"].entity_key,
        predicate=RelationPredicate.EXTENDS,
        normalized_raw_target="BaseService",
        relation_kind=RelationKind.STATIC,
        confidence=Decimal("1.00000"),
        resolution_status=ResolutionStatus.UNRESOLVED,
        occurrences=(SourceOccurrence(line=20, column=0),),
        source_file_rel_path="src/service/UserService.ts",
    )
    res3 = service.persist_relations(
        db=db_session,
        project_id=seed_data["project_id"],
        project_key=seed_data["project_key"],
        candidates=[cand2],
    )
    assert res3.created == 0
    assert res3.updated == 1

    rel_pass3 = db_session.scalars(sa.select(Relation).where(Relation.relation_key == cand1.relation_key)).one()
    assert rel_pass3.id == orig_id
    assert len(rel_pass3.occurrences) == 2
    assert [o["line"] for o in rel_pass3.occurrences] == [10, 20]

    # Verify total DB count of relations is strictly 1
    total_count = db_session.scalar(sa.select(sa.func.count(Relation.id)))
    assert total_count == 1
