"""B-08 Layer 3 Tests: Real Projects End-to-End Persistence & Double-Pass Idempotency (Gate G, H, I, J)
Validates:
- Gate G: End-to-end extraction and persistence of real-project files into Knowledge Core.
- Gate H: Mathematical Double-Pass Idempotency Proof (N = Pass 1 ACTIVE count; ID, Key, Defines Edge 3-set identity).
- Gate I: Real code soft-deletion and resurrection in temporary verification workspace (LOCK-VERIFY-02).
- Gate J: Multi-project co-existence and physical isolation in the same database session.
"""

from decimal import Decimal
from pathlib import Path
import shutil
from typing import Any
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from ingestion.symbols import SymbolPersistenceService
from tests.integration.b08.conftest import REPOS


@pytest.fixture
def service() -> SymbolPersistenceService:
    return SymbolPersistenceService()


def create_file_entity(project: Project, rel_path: str) -> Entity:
    norm = rel_path.replace("\\", "/")
    return Entity(
        id=uuid.uuid4(),
        project_id=project.id,
        entity_type="FILE",
        entity_key=f"FILE:{project.key}:{norm}",
        name=Path(norm).name,
        canonical_name=f"{project.key}_FILE_{Path(norm).stem}",
        path=norm,
        status="ACTIVE",
        metadata_={},
    )


def test_gate_g_real_code_end_to_end_persistence(b08_db: Session, b08_projects: dict[str, Project], service: SymbolPersistenceService):
    """Gate G: Real files from HELLO_FE, HELLO_BE, L2C_FE are persisted with 1.0 confidence defines edges."""
    cases = [
        ("HELLO_FE", "demo/phone-frontend/components/TwilioCall.vue"),
        ("HELLO_BE", "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"),
        ("L2C_FE", "apps/web-antd/src/layouts/basic.vue"),
    ]

    total_created = 0
    for proj_key, rel_path in cases:
        proj = b08_projects[proj_key]
        full_path = REPOS[proj_key] / rel_path
        code_bytes = full_path.read_bytes()

        fe = create_file_entity(proj, rel_path)
        b08_db.add(fe)
        b08_db.commit()

        res = service.sync_file_symbols(
            db=b08_db,
            project_id=proj.id,
            project_key=proj.key,
            file_entity=fe,
            code_bytes=code_bytes,
        )
        b08_db.commit()

        assert res["created"] > 0
        assert res["created"] == res["extracted"]
        total_created += res["created"]

        # Verify defines relations exist
        rels = b08_db.scalars(select(Relation).where(Relation.subject_entity_id == fe.id)).all()
        assert len(rels) == res["created"]
        for r in rels:
            assert r.predicate == "defines"
            assert r.confidence == Decimal("1.00000")
            assert r.metadata_["extraction_method"] == "static_ast"

    assert total_created >= 25


def test_gate_h_double_pass_idempotency_proof(b08_db: Session, b08_projects: dict[str, Project], service: SymbolPersistenceService):
    """Gate H (LOCK-VERIFY-03): Mathematical Two-Pass Idempotency Proof on Real Code.
    Pass 2 must satisfy:
    1. created == 0, deleted == 0, updated == N (where N = Pass 1 ACTIVE count)
    2. entity_id_set(pass1) == entity_id_set(pass2)
    3. entity_key_set(pass1) == entity_key_set(pass2)
    4. defines_edge_set(pass1) == defines_edge_set(pass2)
    """
    proj = b08_projects["HELLO_BE"]
    test_files = [
        "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java",
        "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallRecordController.java",
    ]

    file_entities = []
    file_bytes_map = {}
    for rel in test_files:
        fe = create_file_entity(proj, rel)
        b08_db.add(fe)
        file_entities.append(fe)
        file_bytes_map[rel] = (REPOS["HELLO_BE"] / rel).read_bytes()
    b08_db.commit()

    # ========================== PASS 1 ==========================
    pass1_created = 0
    for fe in file_entities:
        res1 = service.sync_file_symbols(
            db=b08_db,
            project_id=proj.id,
            project_key=proj.key,
            file_entity=fe,
            code_bytes=file_bytes_map[fe.path],
        )
        pass1_created += res1["created"]
    b08_db.commit()

    assert pass1_created > 0

    # Capture Snapshot S1
    active_syms_pass1 = b08_db.scalars(
        select(Entity).where(Entity.project_id == proj.id, Entity.entity_type != "FILE", Entity.status == "ACTIVE")
    ).all()
    N = len(active_syms_pass1)
    assert N == pass1_created

    id_set_pass1 = {s.id for s in active_syms_pass1}
    key_set_pass1 = {s.entity_key for s in active_syms_pass1}

    edges_pass1 = b08_db.scalars(
        select(Relation).where(Relation.predicate == "defines")
    ).all()
    edge_set_pass1 = {(e.subject_entity_id, e.predicate, e.object_entity_id) for e in edges_pass1}

    # ========================== PASS 2 ==========================
    pass2_created = 0
    pass2_updated = 0
    pass2_deleted = 0
    pass2_reactivated = 0

    for fe in file_entities:
        res2 = service.sync_file_symbols(
            db=b08_db,
            project_id=proj.id,
            project_key=proj.key,
            file_entity=fe,
            code_bytes=file_bytes_map[fe.path],
        )
        pass2_created += res2["created"]
        pass2_updated += res2["updated"]
        pass2_deleted += res2["deleted"]
        pass2_reactivated += res2["reactivated"]
    b08_db.commit()

    # Assert Counter Invariants
    assert pass2_created == 0, "Pass 2 created new entities violating idempotency!"
    assert pass2_deleted == 0, "Pass 2 falsely marked symbols deleted!"
    assert pass2_reactivated == 0, "Pass 2 falsely reactivated symbols!"
    assert pass2_updated == N, f"Pass 2 updated count ({pass2_updated}) does not match Pass 1 ACTIVE count ({N})!"

    # Capture Snapshot S2
    active_syms_pass2 = b08_db.scalars(
        select(Entity).where(Entity.project_id == proj.id, Entity.entity_type != "FILE", Entity.status == "ACTIVE")
    ).all()
    id_set_pass2 = {s.id for s in active_syms_pass2}
    key_set_pass2 = {s.entity_key for s in active_syms_pass2}

    edges_pass2 = b08_db.scalars(
        select(Relation).where(Relation.predicate == "defines")
    ).all()
    edge_set_pass2 = {(e.subject_entity_id, e.predicate, e.object_entity_id) for e in edges_pass2}

    # Mathematical 3-Set Invariance Proof
    assert id_set_pass1 == id_set_pass2, "Entity ID set mutated between Pass 1 and Pass 2!"
    assert key_set_pass1 == key_set_pass2, "Entity Key set mutated between Pass 1 and Pass 2!"
    assert edge_set_pass1 == edge_set_pass2, "Defines relation edge set mutated between Pass 1 and Pass 2!"


def test_gate_i_real_code_soft_delete_and_resurrection(
    b08_db: Session,
    b08_projects: dict[str, Project],
    service: SymbolPersistenceService,
    temp_workspace: Path,
):
    """Gate I (LOCK-VERIFY-02 + Gate I): Real code mutation drill in Temporary Verification Workspace.
    Proves ACTIVE -> DELETED -> ACTIVE lifecycle on real AST without touching original repository.
    """
    proj = b08_projects["HELLO_BE"]
    source_rel = "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"
    real_source_path = REPOS["HELLO_BE"] / source_rel
    assert real_source_path.exists()

    # Step 0: Clone real file into temporary verification workspace
    temp_target_path = temp_workspace / "CallConfigController.java"
    shutil.copy2(real_source_path, temp_target_path)
    file_entity = create_file_entity(proj, "temp/CallConfigController.java")
    b08_db.add(file_entity)
    b08_db.commit()

    # Step 1: Initial Scan (Pass 1) -> ACTIVE
    code_v1 = temp_target_path.read_bytes()
    res1 = service.sync_file_symbols(db=b08_db, project_id=proj.id, project_key=proj.key, file_entity=file_entity, code_bytes=code_v1)
    b08_db.commit()
    assert res1["created"] >= 3

    target_method = b08_db.scalars(
        select(Entity).where(Entity.project_id == proj.id, Entity.path == file_entity.path, Entity.name == "getConfig")
    ).first()
    assert target_method is not None
    assert target_method.status == "ACTIVE"

    # Step 2: Simulate deletion of getConfig in temp workspace
    code_v1_text = code_v1.decode("utf-8")
    assert "getConfig()" in code_v1_text
    code_v2_text = code_v1_text.replace("getConfig()", "_removed_getConfig()")
    code_v2 = code_v2_text.encode("utf-8")
    temp_target_path.write_bytes(code_v2)

    res2 = service.sync_file_symbols(db=b08_db, project_id=proj.id, project_key=proj.key, file_entity=file_entity, code_bytes=code_v2)
    b08_db.commit()

    assert res2["deleted"] == 1
    b08_db.refresh(target_method)
    assert target_method.status == "DELETED"

    # Step 3: Restore getConfig in temp workspace (Resurrection)
    temp_target_path.write_bytes(code_v1)
    res3 = service.sync_file_symbols(db=b08_db, project_id=proj.id, project_key=proj.key, file_entity=file_entity, code_bytes=code_v1)
    b08_db.commit()

    assert res3["reactivated"] == 1
    b08_db.refresh(target_method)
    assert target_method.status == "ACTIVE"


def test_gate_j_multi_project_physical_isolation(b08_db: Session, b08_projects: dict[str, Project], service: SymbolPersistenceService):
    """Gate J (LOCK-VERIFY-04): Co-persistence of all 3 real projects into same DB proves zero cross-project leakage."""
    cases = [
        ("HELLO_FE", "demo/phone-frontend/components/TwilioCall.vue"),
        ("HELLO_BE", "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"),
        ("L2C_FE", "apps/web-antd/src/layouts/basic.vue"),
    ]

    for proj_key, rel in cases:
        proj = b08_projects[proj_key]
        code = (REPOS[proj_key] / rel).read_bytes()
        fe = create_file_entity(proj, rel)
        b08_db.add(fe)
        b08_db.commit()
        service.sync_file_symbols(db=b08_db, project_id=proj.id, project_key=proj.key, file_entity=fe, code_bytes=code)
        b08_db.commit()

    # Query counts per project
    counts = {}
    for key, proj in b08_projects.items():
        syms = b08_db.scalars(select(Entity).where(Entity.project_id == proj.id, Entity.entity_type != "FILE")).all()
        counts[key] = len(syms)
        # All keys must strictly start with their respective project_key
        for s in syms:
            assert s.entity_key.startswith(f"SYMBOL:{key}:")

    assert counts["HELLO_FE"] >= 5
    assert counts["HELLO_BE"] >= 3
    assert counts["L2C_FE"] >= 10

    # Ensure no defines relation crosses project boundaries
    rels = b08_db.scalars(select(Relation)).all()
    for r in rels:
        subj = b08_db.get(Entity, r.subject_entity_id)
        obj = b08_db.get(Entity, r.object_entity_id)
        assert subj.project_id == obj.project_id, "defines edge crossed project boundaries!"
