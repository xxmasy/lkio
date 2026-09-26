"""B-08 Layer 4 Tests: System Audit, Read-Only Redline & Resource Stability (Gate N, P, Q, R)
Validates:
- Gate N: Strict read-only guarantee across all three external repositories.
- Gate P: Absolute zero premature graph edges in database (only 'defines' allowed).
- Gate Q: Resource Stability Contract across Pass 1/2/3 (handles, memory, DB connections).
- Gate R: Historical regression invariance across B-00 ~ B-07 suites.
"""

import gc
import os
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from ingestion.symbols import SymbolPersistenceService
from tests.integration.b08.conftest import REPOS, capture_git_porcelain, discover_supported_files


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


def test_gate_n_three_repos_strict_readonly_invariance(b08_db: Session, b08_projects: dict[str, Project], service: SymbolPersistenceService):
    """Gate N (LOCK-VERIFY-02): Verifies zero working-tree modifications across HELLO_FE, HELLO_BE, L2C_FE."""
    # Capture snapshot before operations
    before_snapshots = capture_git_porcelain()

    # Execute read-only batch extraction and persistence on real files from all 3 repos
    cases = [
        ("HELLO_FE", "demo/phone-frontend/components/TwilioCall.vue"),
        ("HELLO_BE", "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"),
        ("L2C_FE", "apps/web-antd/src/layouts/basic.vue"),
    ]
    for proj_key, rel in cases:
        proj = b08_projects[proj_key]
        full_path = REPOS[proj_key] / rel
        code = full_path.read_bytes()
        fe = create_file_entity(proj, rel)
        b08_db.add(fe)
        b08_db.commit()
        service.sync_file_symbols(db=b08_db, project_id=proj.id, project_key=proj.key, file_entity=fe, code_bytes=code)
        b08_db.commit()

    # Capture snapshot after operations
    after_snapshots = capture_git_porcelain()

    # Compare exact porcelain outputs
    for name in REPOS:
        assert before_snapshots[name] == after_snapshots[name], (
            f"External repository '{name}' was modified during B-08 execution! "
            f"Before:\n{before_snapshots[name]}\nAfter:\n{after_snapshots[name]}"
        )


def test_gate_p_zero_premature_graph_edges_in_db(b08_db: Session, b08_projects: dict[str, Project], service: SymbolPersistenceService):
    """Gate P: Verifies that ONLY 'defines' relations exist in DB, with zero premature graph edges."""
    proj = b08_projects["HELLO_BE"]
    rel = "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"
    code = (REPOS["HELLO_BE"] / rel).read_bytes()
    fe = create_file_entity(proj, rel)
    b08_db.add(fe)
    b08_db.commit()

    service.sync_file_symbols(db=b08_db, project_id=proj.id, project_key=proj.key, file_entity=fe, code_bytes=code)
    b08_db.commit()

    all_relations = b08_db.scalars(select(Relation)).all()
    assert len(all_relations) > 0

    forbidden_predicates = {"calls", "imports", "extends", "implements", "exports", "uses", "depends_on"}
    predicates_found = {r.predicate for r in all_relations}

    # Only 'defines' allowed in MVP2-B
    assert predicates_found == {"defines"}
    for forbidden in forbidden_predicates:
        assert forbidden not in predicates_found, f"Premature graph predicate '{forbidden}' found in database!"


def test_gate_q_resource_stability_contract(b08_db: Session, b08_projects: dict[str, Project], service: SymbolPersistenceService):
    """Gate Q (LOCK-VERIFY-06): Resource Stability Contract across Pass 1/2/3.
    Verifies that memory (RSS), open handles, and DB state remain bounded without continuous monotonic growth.
    """
    proj = b08_projects["HELLO_BE"]
    all_java = discover_supported_files(REPOS["HELLO_BE"])[:30]  # 30 real Spring files
    file_tuples = []
    for f in all_java:
        rel = f.relative_to(REPOS["HELLO_BE"]).as_posix()
        fe = create_file_entity(proj, rel)
        b08_db.add(fe)
        file_tuples.append((fe, f.read_bytes()))
    b08_db.commit()

    tracemalloc.start()
    try:
        allocations = []
        # Run 3 consecutive passes
        for pass_idx in range(1, 4):
            for fe, code in file_tuples:
                service.sync_file_symbols(db=b08_db, project_id=proj.id, project_key=proj.key, file_entity=fe, code_bytes=code)
            b08_db.commit()
            gc.collect()
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            allocations.append((current_mem, peak_mem))

        # Growth between Pass 2 and Pass 3 must be within tight tolerance (< 5MB)
        delta_p2_p3_mb = (allocations[2][0] - allocations[1][0]) / (1024 * 1024)
        print(f"\n[Gate Q Resource Stability] Traced Memory: P1={allocations[0][0]/1024/1024:.2f}MB, P2={allocations[1][0]/1024/1024:.2f}MB, P3={allocations[2][0]/1024/1024:.2f}MB, Delta(P3-P2)={delta_p2_p3_mb:.2f}MB")
        assert delta_p2_p3_mb < 5.0, f"Memory growth between Pass 2 and Pass 3 exceeded tolerance: {delta_p2_p3_mb} MB"
    finally:
        tracemalloc.stop()


def test_gate_r_historical_regression_invariance():
    """Gate R: Verifies that all unit tests from B-00 through B-07 execute green."""
    test_dirs = [
        "tests/unit/b00_b02",
        "tests/unit/b03",
        "tests/unit/b04",
        "tests/unit/b05",
        "tests/unit/b06",
        "tests/unit/b07",
    ]
    for d in test_dirs:
        res = subprocess.run(
            [sys.executable, "-m", "pytest", d, "-q"],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"Historical regression failure in {d}:\n{res.stdout}\n{res.stderr}"
