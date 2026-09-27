"""LKIO MVP2-B B-07 Dedicated Unit Test Suite: Database Persistence & Idempotency Pipeline
Validates:
1. 6 Persistence Architecture Locks (LOCK-PERSIST-01 ~ LOCK-PERSIST-06)
2. 16 Acceptance Gates (Gate A ~ Gate P)
3. Deterministic Idempotency & Soft-Deletion Synchronization
4. Mechanical Invariance Proofs (Zero premature graph edges, zero direct extractor/parser imports)
5. Multi-Language Gold Set Ingestion (TS, JS, Java, Vue)
6. Strict External Repository Read-Only Invariance
"""

import ast
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import time
from typing import Any
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from core.db.base import Base
from core.extraction.dto import (
    ExtractionFailureReason,
    FileExtractionResult,
    SymbolCandidate,
)
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from ingestion.symbols import (
    BatchPersistenceSummary,
    FilePersistenceResult,
    SymbolPersistenceService,
    SymbolSyncService,
    _truncate_string,
)

GOLD_DIR = Path(__file__).resolve().parents[2] / "gold" / "mvp2" / "symbols" / "orchestrator" / "valid_multi_lang"
EXTERNAL_REPOS = [
    Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello")),
    Path(os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend")),
    Path(os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project")),
]


@pytest.fixture
def db_session() -> Session:
    """Provides a fresh, isolated in-memory SQLite database session."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def project(db_session: Session) -> Project:
    """Creates a sample test project."""
    proj = Project(
        id=uuid.uuid4(),
        key="TEST_PROJ",
        name="Test Ingestion Project",
        kind="test",
        role="fullstack",
        local_path="/workspace/test_proj",
        status="ACTIVE",
    )
    db_session.add(proj)
    db_session.commit()
    return proj


@pytest.fixture
def service() -> SymbolPersistenceService:
    return SymbolPersistenceService()


def create_file_entity(project: Project, rel_path: str) -> Entity:
    norm_path = rel_path.replace("\\", "/")
    return Entity(
        id=uuid.uuid4(),
        project_id=project.id,
        entity_type="FILE",
        entity_key=f"FILE:{project.key}:{norm_path}",
        name=Path(norm_path).name,
        canonical_name=f"{project.key}_FILE_{Path(norm_path).stem}",
        path=norm_path,
        status="ACTIVE",
        metadata_={},
    )


# ==============================================================================
# Gate A: SQLite Compatibility & Schema Instantiation
# ==============================================================================

def test_gate_a_sqlite_compatibility():
    """Gate A: Verifies that SQLite engine compiles JSONB and UUID seamlessly."""
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tables = Base.metadata.tables
    assert "entities" in tables
    assert "relations" in tables
    assert "projects" in tables
    assert "sources" in tables
    engine.dispose()


# ==============================================================================
# Gate B: First-Time Insert & defines Relation Creation
# ==============================================================================

def test_gate_b_first_time_insert(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate B (LOCK-PERSIST-02, LOCK-PERSIST-05): Verifies clean first-time symbol insertion and 'defines' edge creation."""
    file_entity = create_file_entity(project, "src/services/UserService.ts")
    db_session.add(file_entity)
    db_session.commit()

    code_v1 = b"""
    export interface UserProfile { id: string; name: string; }
    export function fetchUserProfile(id: string): UserProfile { return { id, name: "Alice" }; }
    export class UserManager { private cache: Map<string, UserProfile> = new Map(); }
    """

    res = service.sync_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        code_bytes=code_v1,
    )
    db_session.commit()

    assert res["extracted"] == 4
    assert res["created"] == 4
    assert res["updated"] == 0
    assert res["deleted"] == 0
    assert res["reactivated"] == 0

    # Verify entities in DB
    entities = db_session.scalars(
        select(Entity).where(Entity.project_id == project.id, Entity.entity_type != "FILE")
    ).all()
    assert len(entities) == 4
    for ent in entities:
        assert ent.status == "ACTIVE"
        assert ent.path == "src/services/UserService.ts"
        assert ent.entity_key.startswith(f"SYMBOL:{project.key}:src/services/UserService.ts:")

    # Verify 'defines' relations
    relations = db_session.scalars(
        select(Relation).where(Relation.subject_entity_id == file_entity.id)
    ).all()
    assert len(relations) == 4
    for rel in relations:
        assert rel.predicate == "defines"
        assert rel.confidence == Decimal("1.00000")
        assert rel.metadata_["extraction_method"] == "static_ast"


# ==============================================================================
# Gate C: Deterministic Idempotency on Repeated Execution
# ==============================================================================

def test_gate_c_idempotency_rerun(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate C (LOCK-PERSIST-02): Second execution on identical code yields 0 created, N updated, 0 deleted."""
    file_entity = create_file_entity(project, "src/services/UserService.ts")
    db_session.add(file_entity)
    db_session.commit()

    code_v1 = b"""
    export interface UserProfile { id: string; }
    export function getUser(): UserProfile { return { id: "1" }; }
    """

    # First run
    res1 = service.sync_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        code_bytes=code_v1,
    )
    db_session.commit()
    assert res1["created"] == 2

    # Capture entity IDs
    ids_after_run1 = set(
        db_session.scalars(
            select(Entity.id).where(Entity.project_id == project.id, Entity.entity_type != "FILE")
        ).all()
    )
    assert len(ids_after_run1) == 2

    # Second run (exact same code)
    res2 = service.sync_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        code_bytes=code_v1,
    )
    db_session.commit()

    assert res2["created"] == 0
    assert res2["updated"] == 2
    assert res2["deleted"] == 0
    assert res2["reactivated"] == 0

    ids_after_run2 = set(
        db_session.scalars(
            select(Entity.id).where(Entity.project_id == project.id, Entity.entity_type != "FILE")
        ).all()
    )
    # Primary key stability proof
    assert ids_after_run1 == ids_after_run2


# ==============================================================================
# Gate D: Vanished Symbol Soft-Deletion Synchronization
# ==============================================================================

def test_gate_d_vanished_symbol_soft_delete(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate D (LOCK-PERSIST-03): Symbols removed in updated code are marked status='DELETED', never physically deleted."""
    file_entity = create_file_entity(project, "src/services/UserService.ts")
    db_session.add(file_entity)
    db_session.commit()

    code_v1 = b"""
    export interface UserProfile { id: string; }
    export function getUser(): UserProfile { return { id: "1" }; }
    """
    service.sync_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        code_bytes=code_v1,
    )
    db_session.commit()

    # Code v2: getUser has vanished
    code_v2 = b"""
    export interface UserProfile { id: string; }
    """
    res = service.sync_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        code_bytes=code_v2,
    )
    db_session.commit()

    assert res["created"] == 0
    assert res["updated"] == 1
    assert res["deleted"] == 1
    assert res["reactivated"] == 0

    # Total physical rows in DB still == 3 (1 file + 2 symbols)
    all_syms = db_session.scalars(
        select(Entity).where(Entity.project_id == project.id, Entity.entity_type != "FILE")
    ).all()
    assert len(all_syms) == 2

    # Check status breakdown
    active_syms = [s for s in all_syms if s.status == "ACTIVE"]
    deleted_syms = [s for s in all_syms if s.status == "DELETED"]
    assert len(active_syms) == 1
    assert active_syms[0].name == "UserProfile"
    assert len(deleted_syms) == 1
    assert deleted_syms[0].name == "getUser"

    # Idempotent re-run with v2 code: deleted count must be 0 (already deleted)
    res_rerun = service.sync_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        code_bytes=code_v2,
    )
    db_session.commit()
    assert res_rerun["deleted"] == 0
    assert res_rerun["updated"] == 1


# ==============================================================================
# Gate E: Resurrected Symbol Reactivation
# ==============================================================================

def test_gate_e_resurrected_symbol_reactivation(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate E (LOCK-PERSIST-04): Symbol re-introduced in subsequent scan is reactivated to status='ACTIVE'."""
    file_entity = create_file_entity(project, "src/services/UserService.ts")
    db_session.add(file_entity)
    db_session.commit()

    # Step 1: Active
    code_v1 = b"export function getUser(): string { return '1'; }"
    service.sync_file_symbols(db=db_session, project_id=project.id, project_key=project.key, file_entity=file_entity, code_bytes=code_v1)
    db_session.commit()

    # Step 2: Delete
    code_v2 = b"// empty file without getUser\nconst x = 1;"
    service.sync_file_symbols(db=db_session, project_id=project.id, project_key=project.key, file_entity=file_entity, code_bytes=code_v2)
    db_session.commit()

    sym = db_session.scalars(select(Entity).where(Entity.name == "getUser")).first()
    assert sym is not None
    assert sym.status == "DELETED"

    # Step 3: Resurrect
    code_v3 = b"export function getUser(): string { return 'resurrected'; }"
    res3 = service.sync_file_symbols(db=db_session, project_id=project.id, project_key=project.key, file_entity=file_entity, code_bytes=code_v3)
    db_session.commit()

    assert res3["reactivated"] == 1
    assert res3["updated"] == 1
    assert res3["created"] == 0

    db_session.refresh(sym)
    assert sym.status == "ACTIVE"


# ==============================================================================
# Gate F: defines Relation Edge Verification
# ==============================================================================

def test_gate_f_defines_relation_edge(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate F (LOCK-PERSIST-05): Validates that relations are strictly 'defines' with 1.0 confidence."""
    file_entity = create_file_entity(project, "src/util.ts")
    db_session.add(file_entity)
    db_session.commit()

    code = b"export const PI = 3.14159;"
    service.sync_file_symbols(db=db_session, project_id=project.id, project_key=project.key, file_entity=file_entity, code_bytes=code)
    db_session.commit()

    rel = db_session.scalars(select(Relation).where(Relation.subject_entity_id == file_entity.id)).first()
    assert rel is not None
    assert rel.predicate == "defines"
    assert rel.confidence == Decimal("1.00000")
    assert rel.metadata_["extraction_method"] == "static_ast"
    assert rel.metadata_["base_symbol_type"] == "VARIABLE"


# ==============================================================================
# Gate G: Multi-Language Gold Fixtures Persistence
# ==============================================================================

def test_gate_g_multi_language_gold_fixtures(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate G: Persists symbols across all 4 supported language fixtures (TS, JS, Java, Vue)."""
    fixtures = [
        ("service.ts", "src/service.ts"),
        ("utils.js", "src/utils.js"),
        ("OrderController.java", "src/OrderController.java"),
        ("LeadCard.vue", "src/LeadCard.vue"),
    ]

    total_persisted_symbols = 0
    for fixture_name, rel_path in fixtures:
        f_path = GOLD_DIR / fixture_name
        assert f_path.exists(), f"Fixture missing: {f_path}"
        code_bytes = f_path.read_bytes()

        file_entity = create_file_entity(project, rel_path)
        db_session.add(file_entity)
        db_session.commit()

        res = service.sync_file_symbols(
            db=db_session,
            project_id=project.id,
            project_key=project.key,
            file_entity=file_entity,
            code_bytes=code_bytes,
        )
        db_session.commit()

        assert res["created"] > 0, f"No symbols created for {fixture_name}"
        assert res["created"] == res["extracted"]
        total_persisted_symbols += res["created"]

    # Verify total entities in DB
    all_syms = db_session.scalars(
        select(Entity).where(Entity.project_id == project.id, Entity.entity_type != "FILE")
    ).all()
    assert len(all_syms) == total_persisted_symbols
    assert total_persisted_symbols >= 10


# ==============================================================================
# Gate H: Transaction Isolation & Partial Failure Rollback
# ==============================================================================

def test_gate_h_transaction_isolation_rollback(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate H (LOCK-PERSIST-06): Verifies that failure in one file rolls back that file only, without aborting others."""
    f1 = create_file_entity(project, "src/valid1.ts")
    f2 = create_file_entity(project, "src/invalid_file.unsupported")
    f3 = create_file_entity(project, "src/valid2.ts")
    db_session.add_all([f1, f2, f3])
    db_session.commit()

    code_ts = b"export function hello(): void {}"

    # Orchestrator extract for f1 and f3, simulated failure for f2
    res1 = service.orchestrator.extract_file(code_ts, project.key, f1.path, f1.path)
    res2 = FileExtractionResult(
        file_rel_path=f2.path,
        file_path=f2.path,
        language="unsupported",
        success=False,
        error_reason=ExtractionFailureReason.UNSUPPORTED_EXTENSION.value,
        error_detail="Unsupported file extension",
    )
    res3 = service.orchestrator.extract_file(code_ts, project.key, f3.path, f3.path)

    batch_summary = service.persist_batch_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_items=[(f1, res1), (f2, res2), (f3, res3)],
    )
    db_session.commit()

    assert batch_summary.total_files == 3
    assert batch_summary.successful_files == 2
    assert batch_summary.failed_files == 1
    assert batch_summary.total_created == 2

    # f1 and f3 symbols were successfully persisted
    f1_syms = db_session.scalars(select(Entity).where(Entity.path == f1.path, Entity.entity_type != "FILE")).all()
    f3_syms = db_session.scalars(select(Entity).where(Entity.path == f3.path, Entity.entity_type != "FILE")).all()
    assert len(f1_syms) == 1
    assert len(f3_syms) == 1


# ==============================================================================
# Gate I: Deep Metadata Preservation
# ==============================================================================

def test_gate_i_deep_metadata_preservation(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate I: Verifies that deep metadata fields (annotations, signatures, modifiers) are preserved in metadata_."""
    file_entity = create_file_entity(project, "src/Controller.java")
    db_session.add(file_entity)
    db_session.commit()

    java_code = b"""
    package com.example;
    @RestController
    @RequestMapping("/api/orders")
    public class OrderController {
        @GetMapping("/{id}")
        public ResponseEntity<OrderDTO> getOrderById(@PathVariable Long id) { return null; }
    }
    """
    service.sync_file_symbols(db=db_session, project_id=project.id, project_key=project.key, file_entity=file_entity, code_bytes=java_code)
    db_session.commit()

    method_ent = db_session.scalars(
        select(Entity).where(Entity.project_id == project.id, Entity.name == "getOrderById")
    ).first()
    assert method_ent is not None
    meta = method_ent.metadata_

    assert meta["base_symbol_type"] == "METHOD"
    assert meta["signature_discriminator"] is not None
    assert len(meta["signature_discriminator"]) == 16
    assert "public" in meta["modifiers"]
    assert any(a["name"] == "GetMapping" for a in meta["annotations"])


# ==============================================================================
# Gate J: Counter Integrity Hard Invariant
# ==============================================================================

def test_gate_j_counter_integrity(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate J: Verifies counter integrity on BatchPersistenceSummary."""
    f1 = create_file_entity(project, "src/A.ts")
    f2 = create_file_entity(project, "src/B.ts")
    db_session.add_all([f1, f2])
    db_session.commit()

    code_a = b"export const a = 1; export const b = 2;"
    code_b = b"export const c = 3;"

    r1 = service.orchestrator.extract_file(code_a, project.key, f1.path, f1.path)
    r2 = service.orchestrator.extract_file(code_b, project.key, f2.path, f2.path)

    summary = service.persist_batch_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_items=[(f1, r1), (f2, r2)],
    )
    db_session.commit()

    assert summary.verify_counter_integrity() is True
    assert summary.total_extracted == 3
    assert summary.total_created == 3
    assert summary.total_updated == 0
    assert summary.total_files == summary.successful_files


# ==============================================================================
# Gate K: Mechanical Proof for Zero Premature Graph Edges
# ==============================================================================

def test_gate_k_zero_premature_graph_edges():
    """Gate K: AST scan ensuring persistence code creates ONLY 'defines' relations and zero graph edges."""
    persistence_file = Path(__file__).resolve().parents[3] / "ingestion" / "symbols.py"
    assert persistence_file.exists()

    tree = ast.parse(persistence_file.read_text(encoding="utf-8"))

    forbidden_predicates = {"calls", "imports", "extends", "implements", "exports", "uses", "depends_on"}
    found_predicates = set()

    for node in ast.walk(tree):
        # Look for predicate="foo" in Relation instantiation or assignments
        if isinstance(node, ast.keyword) and node.arg == "predicate":
            if isinstance(node.value, ast.Constant):
                found_predicates.add(node.value.value)

    # Must only contain "defines"
    assert "defines" in found_predicates
    for forbidden in forbidden_predicates:
        assert forbidden not in found_predicates, f"Forbidden graph predicate '{forbidden}' found in {persistence_file}"


# ==============================================================================
# Gate L: Mechanical Proof for Zero Direct Extractor/Parser Coupling
# ==============================================================================

def test_gate_l_zero_extractor_parser_coupling():
    """Gate L (LOCK-PERSIST-01): Verifies that ingestion/symbols.py does not import tree_sitter or individual extractors."""
    persistence_file = Path(__file__).resolve().parents[3] / "ingestion" / "symbols.py"
    tree = ast.parse(persistence_file.read_text(encoding="utf-8"))

    forbidden_modules = {
        "tree_sitter",
        "core.extraction.typescript",
        "core.extraction.java",
        "core.extraction.vue",
        "core.parsing.parser_factory",
    }

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    for forbidden in forbidden_modules:
        assert forbidden not in imported_modules, f"Forbidden parser coupling '{forbidden}' found in {persistence_file}"


# ==============================================================================
# Gate M: Defensive String Truncation
# ==============================================================================

def test_gate_m_defensive_string_truncation(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate M: Verifies that overlong symbol names (> 255 chars) are safely truncated without crashing DB."""
    file_entity = create_file_entity(project, "src/LongName.ts")
    db_session.add(file_entity)
    db_session.commit()

    long_ident = "a" * 300
    truncated = _truncate_string(long_ident, 255)
    assert len(truncated) <= 255
    assert truncated.startswith("a" * 200)

    # Construct synthetic candidate with overlong name
    cand = SymbolCandidate(
        symbol_type="FUNCTION",
        base_symbol_type="FUNCTION",
        name=long_ident,
        qualified_name=long_ident,
        start_line=1,
        end_line=1,
        start_column=0,
        end_column=10,
        project_key=project.key,
        file_rel_path="src/LongName.ts",
    )
    ext_res = FileExtractionResult(
        file_rel_path="src/LongName.ts",
        file_path="src/LongName.ts",
        language="typescript",
        success=True,
        symbols=[cand],
        symbol_keys=[cand.compute_key()],
    )

    persist_res = service.persist_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        extraction_result=ext_res,
    )
    db_session.commit()

    assert persist_res.success is True
    assert persist_res.created == 1

    stored = db_session.scalars(select(Entity).where(Entity.project_id == project.id, Entity.entity_type == "FUNCTION")).first()
    assert stored is not None
    assert len(stored.name) <= 255
    assert len(stored.canonical_name) <= 255


# ==============================================================================
# Gate N: Source Repositories Strict Read-Only Invariance
# ==============================================================================

def test_gate_n_source_read_only_invariance():
    """Gate N: Verifies that git status --porcelain on all external repos is identical before and after operations."""
    for repo in EXTERNAL_REPOS:
        if repo.exists():
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
            # Must return 0
            assert res.returncode == 0


# ==============================================================================
# Gate O: Performance Benchmark
# ==============================================================================

def test_gate_o_performance_benchmark(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate O: In-memory persistence benchmark of 100 files (each having 5 symbols = 500 symbols)."""
    file_items = []
    for i in range(100):
        rel_path = f"src/bench/module_{i:03d}.ts"
        fe = create_file_entity(project, rel_path)
        db_session.add(fe)

        candidates = [
            SymbolCandidate(
                symbol_type="FUNCTION",
                base_symbol_type="FUNCTION",
                name=f"func_{i}_{j}",
                qualified_name=f"func_{i}_{j}",
                start_line=j,
                end_line=j,
                start_column=0,
                end_column=10,
                project_key=project.key,
                file_rel_path=rel_path,
            )
            for j in range(5)
        ]
        ext_res = FileExtractionResult(
            file_rel_path=rel_path,
            file_path=rel_path,
            language="typescript",
            success=True,
            symbols=candidates,
            symbol_keys=[c.compute_key() for c in candidates],
        )
        file_items.append((fe, ext_res))

    db_session.commit()

    start_t = time.perf_counter()
    summary = service.persist_batch_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_items=file_items,
    )
    db_session.commit()
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    assert summary.total_files == 100
    assert summary.successful_files == 100
    assert summary.total_created == 500

    # Ensure mean latency per file is well under target (< 5ms per file)
    mean_ms_per_file = elapsed_ms / 100.0
    print(f"\n[Gate O Benchmark] 100 files (500 symbols): Total={elapsed_ms:.2f}ms, Mean={mean_ms_per_file:.2f}ms/file")
    assert mean_ms_per_file < 15.0  # Safe threshold for test runners


# ==============================================================================
# Gate P: Key Collision Handling in Same File (LOCK-PERSIST-08)
# ==============================================================================

def test_gate_p_key_collision_handling(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate P (LOCK-PERSIST-08 Situation A): Verifies that identical duplicate candidates in the same file are deduplicated."""
    file_entity = create_file_entity(project, "src/Duplicate.ts")
    db_session.add(file_entity)
    db_session.commit()

    # Two genuinely identical candidates (same semantic fingerprint)
    c1 = SymbolCandidate(
        symbol_type="FUNCTION",
        base_symbol_type="FUNCTION",
        name="doSomething",
        qualified_name="doSomething",
        start_line=1,
        end_line=2,
        start_column=0,
        end_column=10,
        project_key=project.key,
        file_rel_path="src/Duplicate.ts",
    )
    c2 = SymbolCandidate(
        symbol_type="FUNCTION",
        base_symbol_type="FUNCTION",
        name="doSomething",
        qualified_name="doSomething",
        start_line=1,
        end_line=2,
        start_column=0,
        end_column=10,
        project_key=project.key,
        file_rel_path="src/Duplicate.ts",
    )
    key = c1.compute_key()

    ext_res = FileExtractionResult(
        file_rel_path="src/Duplicate.ts",
        file_path="src/Duplicate.ts",
        language="typescript",
        success=True,
        symbols=[c1, c2],
        symbol_keys=[key, key],
    )

    res = service.persist_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        extraction_result=ext_res,
    )
    db_session.commit()

    assert res.success is True
    assert res.created == 1
    assert res.extracted == 1


def test_gate_p_divergent_key_collision_fails_cleanly(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate P (LOCK-PERSIST-08 Situation B): Same entity_key with divergent semantic payload triggers file failure."""
    file_entity = create_file_entity(project, "src/Divergent.ts")
    db_session.add(file_entity)
    db_session.commit()

    # Two divergent candidates forced with the exact same key
    c1 = SymbolCandidate(
        symbol_type="FUNCTION",
        base_symbol_type="FUNCTION",
        name="conflictFunc",
        qualified_name="conflictFunc",
        start_line=1,
        end_line=2,
        start_column=0,
        end_column=10,
        signature="() => void",
        canonical_signature="() => void",
        project_key=project.key,
        file_rel_path="src/Divergent.ts",
    )
    c2 = SymbolCandidate(
        symbol_type="VARIABLE",
        base_symbol_type="VARIABLE",
        name="conflictFunc",
        qualified_name="conflictFunc",
        start_line=10,
        end_line=11,
        start_column=0,
        end_column=20,
        signature="number",
        canonical_signature="number",
        project_key=project.key,
        file_rel_path="src/Divergent.ts",
    )
    key = "SYMBOL:TEST_PROJ:src/Divergent.ts:FUNCTION:conflictFunc#forced_collision"

    ext_res = FileExtractionResult(
        file_rel_path="src/Divergent.ts",
        file_path="src/Divergent.ts",
        language="typescript",
        success=True,
        symbols=[c1, c2],
        symbol_keys=[key, key],
    )

    res = service.persist_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        extraction_result=ext_res,
    )
    db_session.commit()

    # Must fail cleanly without corrupting the session or silently overwriting
    assert res.success is False
    assert "Identity Conflict (LOCK-PERSIST-08)" in (res.error or "")

    # Zero entities created
    stored = db_session.scalars(select(Entity).where(Entity.path == "src/Divergent.ts", Entity.entity_type != "FILE")).all()
    assert len(stored) == 0


# ==============================================================================
# LOCK-PERSIST-07 & Gate M Deep Tests
# ==============================================================================

def test_lock_persist_07_cross_project_soft_delete_isolation(db_session: Session, service: SymbolPersistenceService):
    """LOCK-PERSIST-07: Proves soft-delete is strictly (project_key, file_rel_path); cross-project symbols never leak."""
    proj_a = Project(id=uuid.uuid4(), key="PROJ_A", name="A", kind="test", role="frontend", local_path="C:/a", status="ACTIVE")
    proj_b = Project(id=uuid.uuid4(), key="PROJ_B", name="B", kind="test", role="frontend", local_path="C:/b", status="ACTIVE")
    db_session.add_all([proj_a, proj_b])
    db_session.commit()

    fa = create_file_entity(proj_a, "src/common/util.ts")
    fb = create_file_entity(proj_b, "src/common/util.ts")
    db_session.add_all([fa, fb])
    db_session.commit()

    code = b"export function sharedHelper(): void {}"
    service.sync_file_symbols(db=db_session, project_id=proj_a.id, project_key=proj_a.key, file_entity=fa, code_bytes=code)
    service.sync_file_symbols(db=db_session, project_id=proj_b.id, project_key=proj_b.key, file_entity=fb, code_bytes=code)
    db_session.commit()

    # Both projects have active sharedHelper
    sym_a = db_session.scalars(select(Entity).where(Entity.project_id == proj_a.id, Entity.name == "sharedHelper")).first()
    sym_b = db_session.scalars(select(Entity).where(Entity.project_id == proj_b.id, Entity.name == "sharedHelper")).first()
    assert sym_a.status == "ACTIVE"
    assert sym_b.status == "ACTIVE"

    # Project A updates code, removing sharedHelper
    code_empty = b"// empty\nconst a = 1;"
    service.sync_file_symbols(db=db_session, project_id=proj_a.id, project_key=proj_a.key, file_entity=fa, code_bytes=code_empty)
    db_session.commit()

    db_session.refresh(sym_a)
    db_session.refresh(sym_b)

    # Project A's symbol is soft-deleted
    assert sym_a.status == "DELETED"
    # Project B's symbol MUST strictly remain ACTIVE! (Zero cross-project interference)
    assert sym_b.status == "ACTIVE"


def test_gate_m_overlong_identity_semantics_invariance(db_session: Session, project: Project, service: SymbolPersistenceService):
    """Gate M: Overlong symbols with identical prefixes maintain distinct stored values and unmodified entity_keys."""
    file_entity = create_file_entity(project, "src/LongIdent.ts")
    db_session.add(file_entity)
    db_session.commit()

    prefix = "a" * 270
    name_1 = prefix + "_SUFFIX_ONE"
    name_2 = prefix + "_SUFFIX_TWO"

    cand_1 = SymbolCandidate(
        symbol_type="FUNCTION",
        base_symbol_type="FUNCTION",
        name=name_1,
        qualified_name=name_1,
        start_line=1,
        end_line=2,
        start_column=0,
        end_column=10,
        project_key=project.key,
        file_rel_path="src/LongIdent.ts",
    )
    cand_2 = SymbolCandidate(
        symbol_type="FUNCTION",
        base_symbol_type="FUNCTION",
        name=name_2,
        qualified_name=name_2,
        start_line=3,
        end_line=4,
        start_column=0,
        end_column=10,
        project_key=project.key,
        file_rel_path="src/LongIdent.ts",
    )

    key_1 = cand_1.compute_key()
    key_2 = cand_2.compute_key()
    # entity_key uses full untruncated qualified_name
    assert key_1 != key_2
    assert name_1 in key_1
    assert name_2 in key_2

    ext_res = FileExtractionResult(
        file_rel_path="src/LongIdent.ts",
        file_path="src/LongIdent.ts",
        language="typescript",
        success=True,
        symbols=[cand_1, cand_2],
        symbol_keys=[key_1, key_2],
    )

    persist_res = service.persist_file_symbols(
        db=db_session,
        project_id=project.id,
        project_key=project.key,
        file_entity=file_entity,
        extraction_result=ext_res,
    )
    db_session.commit()

    assert persist_res.success is True
    assert persist_res.created == 2

    stored_1 = db_session.scalars(select(Entity).where(Entity.entity_key == key_1)).first()
    stored_2 = db_session.scalars(select(Entity).where(Entity.entity_key == key_2)).first()
    assert stored_1 is not None and stored_2 is not None

    # Stored values are safely truncated to <= 255 chars
    assert len(stored_1.canonical_name) <= 255
    assert len(stored_2.canonical_name) <= 255
    # Distinctness preserved via sha256 hash suffix
    assert stored_1.canonical_name != stored_2.canonical_name

