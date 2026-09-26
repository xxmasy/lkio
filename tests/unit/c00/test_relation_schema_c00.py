"""C-00 Schema & Relation Contract Tests
Validates:
- Gate A: Relation model with nullable object_entity_id, relation_kind, resolution_status, raw_target, occurrences
- Gate B: relation_key TEXT UNIQUE enforcement
- Gate C: Backward compatibility with MVP2-B defines relations (auto-generating relation_key when omitted)
"""

import uuid
from decimal import Decimal
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from core.db.base import Base
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation


@pytest.fixture
def c00_db():
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_gate_a_relation_schema_contract(c00_db):
    """Gate A: Verify relation model supports nullable object_entity_id and new fields."""
    proj = Project(
        id=uuid.uuid4(),
        key="TEST_PROJ",
        name="Test",
        kind="repo",
        role="frontend",
        local_path="/tmp",
        status="ACTIVE",
    )
    c00_db.add(proj)
    c00_db.commit()

    file_ent = Entity(
        id=uuid.uuid4(),
        project_id=proj.id,
        entity_type="FILE",
        entity_key="FILE:TEST_PROJ:src/main.ts",
        name="main.ts",
        canonical_name="TEST_PROJ_FILE_main",
        path="src/main.ts",
        status="ACTIVE",
    )
    c00_db.add(file_ent)
    c00_db.commit()

    # Unresolved relation with object_entity_id=None
    rel_unresolved = Relation(
        id=uuid.uuid4(),
        relation_key="RELATION:TEST_PROJ:FILE:TEST_PROJ:src/main.ts:imports:lodash/cloneDeep:STATIC:default",
        subject_entity_id=file_ent.id,
        predicate="imports",
        object_entity_id=None,
        relation_kind="STATIC",
        resolution_status="UNRESOLVED",
        raw_target="lodash/cloneDeep",
        status="ACTIVE",
        confidence=Decimal("1.00000"),
        occurrences=[{"line": 1, "column": 0}],
        metadata_={"is_type_only": False},
    )
    c00_db.add(rel_unresolved)
    c00_db.commit()

    saved = c00_db.scalar(sa.select(Relation).where(Relation.id == rel_unresolved.id))
    assert saved is not None
    assert saved.object_entity_id is None
    assert saved.resolution_status == "UNRESOLVED"
    assert saved.relation_kind == "STATIC"
    assert saved.raw_target == "lodash/cloneDeep"
    assert saved.occurrences == [{"line": 1, "column": 0}]
    assert saved.confidence == Decimal("1.00000")


def test_gate_b_relation_key_unique_enforcement(c00_db):
    """Gate B: Verify relation_key uniqueness is strictly enforced by the database."""
    proj = Project(id=uuid.uuid4(), key="TEST_P", name="Test", kind="repo", role="be", local_path="/tmp")
    c00_db.add(proj)
    c00_db.commit()

    fe = Entity(
        id=uuid.uuid4(),
        project_id=proj.id,
        entity_type="FILE",
        entity_key="FILE:TEST_P:App.java",
        name="App.java",
        canonical_name="App",
    )
    c00_db.add(fe)
    c00_db.commit()

    rel1 = Relation(
        id=uuid.uuid4(),
        relation_key="RELATION:TEST_P:FILE:TEST_P:App.java:imports:com.foo.Bar:STATIC:default",
        subject_entity_id=fe.id,
        predicate="imports",
        object_entity_id=None,
        raw_target="com.foo.Bar",
    )
    c00_db.add(rel1)
    c00_db.commit()

    # Attempt duplicate relation_key
    rel2 = Relation(
        id=uuid.uuid4(),
        relation_key="RELATION:TEST_P:FILE:TEST_P:App.java:imports:com.foo.Bar:STATIC:default",
        subject_entity_id=fe.id,
        predicate="imports",
        object_entity_id=None,
        raw_target="com.foo.Bar",
    )
    c00_db.add(rel2)
    with pytest.raises(sa.exc.IntegrityError):
        c00_db.commit()
    c00_db.rollback()


def test_gate_c_backward_compatibility_with_b07(c00_db):
    """Gate C: Backward compatibility: B-07 defines relations auto-generate relation_key if omitted."""
    proj = Project(id=uuid.uuid4(), key="P", name="P", kind="repo", role="fe", local_path="/tmp")
    c00_db.add(proj)
    c00_db.commit()

    fe = Entity(id=uuid.uuid4(), project_id=proj.id, entity_type="FILE", entity_key="FILE:P:f.ts", name="f.ts", canonical_name="f")
    se = Entity(id=uuid.uuid4(), project_id=proj.id, entity_type="FUNCTION", entity_key="SYMBOL:P:f.ts:FUNCTION:fn:1234", name="fn", canonical_name="fn")
    c00_db.add_all([fe, se])
    c00_db.commit()

    # Create relation without passing relation_key or occurrences (like B-07 does)
    rel = Relation(
        id=uuid.uuid4(),
        subject_entity_id=fe.id,
        predicate="defines",
        object_entity_id=se.id,
        confidence=Decimal("1.00000"),
        metadata_={"extraction_method": "static_ast"},
    )
    c00_db.add(rel)
    c00_db.commit()

    saved = c00_db.scalar(sa.select(Relation).where(Relation.id == rel.id))
    assert saved is not None
    assert saved.relation_key.startswith(f"RELATION:{fe.id}:defines:{se.id}")
    assert saved.relation_kind == "STATIC"
    assert saved.resolution_status == "RESOLVED"
    assert saved.occurrences == []
