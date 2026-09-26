"""B-08 Layer 3 Tests: Real Projects Lifecycle Audit, Conflict Rejection & Truncation (Gate K, L, M)
Validates:
- Gate K: Three-stage counter integrity audit and 6-tuple failure traceability.
- Gate L: Identity conflict rejection on real pipeline (100% inheriting B-07 LOCK-PERSIST-08).
- Gate M: Real code overlong symbol storage truncation with absolute identity semantics preservation.
"""

from decimal import Decimal
from pathlib import Path
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.extraction.dto import FileExtractionResult, SymbolCandidate
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.models.entity import Entity
from core.models.project import Project
from ingestion.symbols import BatchPersistenceSummary, SymbolPersistenceService
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


def test_gate_k_three_stage_counter_integrity_and_traceability(
    b08_db: Session,
    b08_projects: dict[str, Project],
    service: SymbolPersistenceService,
):
    """Gate K (LOCK-VERIFY-05): Verifies 3-stage counter integrity and 6-tuple failure traceability on real batch."""
    proj = b08_projects["HELLO_BE"]

    real_batch_files = [
        "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java",
        "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallRecordController.java",
    ]

    discovered_files = []
    file_entities = []
    for rel in real_batch_files:
        fe = create_file_entity(proj, rel)
        b08_db.add(fe)
        file_entities.append(fe)
        code_bytes = (REPOS["HELLO_BE"] / rel).read_bytes()
        discovered_files.append((code_bytes, rel, rel))

    # Add 1 unsupported file to exercise discovery/routing stage counter
    unsupported_rel = "config/application.yml"
    discovered_files.append((b"spring:\n  profiles: active", unsupported_rel, unsupported_rel))
    fe_unsupported = create_file_entity(proj, unsupported_rel)
    b08_db.add(fe_unsupported)
    file_entities.append(fe_unsupported)
    b08_db.commit()

    # Stage 1: Extraction Batch
    extraction_summary = service.orchestrator.extract_batch(discovered_files, proj.key)
    assert extraction_summary.verify_counter_integrity() is True
    # Formula 1: total_files == successful_files + failed_files + unsupported_files
    assert extraction_summary.total_files == (
        extraction_summary.successful_files + extraction_summary.failed_files + extraction_summary.unsupported_files
    )
    assert extraction_summary.unsupported_files == 1
    assert extraction_summary.successful_files == 2

    # Verify failure traceability on unsupported item
    failed_trace = [
        {
            "project": proj.key,
            "file_rel_path": r.file_rel_path,
            "language": r.language,
            "failure_stage": "extraction_routing",
            "failure_reason": r.error_reason,
            "error_detail": r.error_detail,
        }
        for r in extraction_summary.results
        if not r.success
    ]
    assert len(failed_trace) == 1
    assert failed_trace[0]["failure_reason"] == "unsupported_extension"
    assert failed_trace[0]["language"] == "unsupported"

    # Stage 2 & 3: Persistence Batch
    file_items = list(zip(file_entities, extraction_summary.results))
    persist_summary = service.persist_batch_symbols(
        db=b08_db,
        project_id=proj.id,
        project_key=proj.key,
        file_items=file_items,
    )
    b08_db.commit()

    assert persist_summary.verify_counter_integrity() is True
    # Formula 2: successful_extracted == successful_persisted + failed_persisted
    assert extraction_summary.successful_files == persist_summary.successful_files
    # Formula 3: total_extracted == created + updated
    assert persist_summary.total_extracted == (persist_summary.total_created + persist_summary.total_updated)
    assert persist_summary.total_created > 0
    assert persist_summary.total_updated == 0


def test_gate_l_real_pipeline_identity_conflict_rejection(
    b08_db: Session,
    b08_projects: dict[str, Project],
    service: SymbolPersistenceService,
):
    """Gate L (LOCK-PERSIST-08): Proves real pipeline enforces identity conflict rejection without inventing new rules."""
    proj = b08_projects["HELLO_FE"]
    rel = "demo/phone-frontend/components/TwilioCall.vue"
    code = (REPOS["HELLO_FE"] / rel).read_bytes()
    fe = create_file_entity(proj, rel)
    b08_db.add(fe)
    b08_db.commit()

    # Pass 1: Normal extraction and persistence
    ext_res = service.orchestrator.extract_file(code, proj.key, rel, rel)
    assert ext_res.success is True
    assert len(ext_res.symbols) >= 5

    # Craft a collision using real candidate but with divergent payload
    real_cand = ext_res.symbols[0]
    conflict_cand = SymbolCandidate(
        symbol_type="INTERFACE" if real_cand.symbol_type != "INTERFACE" else "CLASS",
        base_symbol_type="INTERFACE" if real_cand.symbol_type != "INTERFACE" else "CLASS",
        name=real_cand.name,
        qualified_name=real_cand.qualified_name,
        start_line=real_cand.start_line + 50,
        end_line=real_cand.end_line + 50,
        start_column=0,
        end_column=20,
        project_key=proj.key,
        file_rel_path=rel,
    )

    collision_ext_res = FileExtractionResult(
        file_rel_path=rel,
        file_path=rel,
        language="vue",
        success=True,
        symbols=[real_cand, conflict_cand],
        symbol_keys=[real_cand.compute_key(), real_cand.compute_key()],  # Forced duplicate key with divergent payload
    )

    persist_res = service.persist_file_symbols(
        db=b08_db,
        project_id=proj.id,
        project_key=proj.key,
        file_entity=fe,
        extraction_result=collision_ext_res,
    )
    b08_db.commit()

    # Must reject with LOCK-PERSIST-08 Identity Conflict
    assert persist_res.success is False
    assert "Identity Conflict (LOCK-PERSIST-08)" in (persist_res.error or "")


def test_gate_m_real_code_overlong_symbol_safety(
    b08_db: Session,
    b08_projects: dict[str, Project],
    service: SymbolPersistenceService,
):
    """Gate M: Proves that real-style deeply-nested overlong symbols (> 255 chars) preserve entity_key semantics."""
    proj = b08_projects["HELLO_BE"]
    rel = "src/main/java/org/example/hahamarket/service/leadconversion/impl/EnterpriseOverlongDeeplyNestedService.java"
    fe = create_file_entity(proj, rel)
    b08_db.add(fe)
    b08_db.commit()

    # Real-style enterprise namespace prefix exceeding 255 characters
    deep_package = "org.example.hahamarket.service.leadconversion.deeply.nested.enterprise.architecture.layer.subsystem.domain.aggregate.specification.compliance.validator.subpackage"
    method_a = "validateNorthAmericaEnterpriseLeadConversionMetricsAgainstDailyTargetHistoricalRecordSpecification"
    method_b = "validateNorthAmericaEnterpriseLeadConversionMetricsAgainstWeeklyTargetHistoricalRecordSpecification"

    qual_a = f"{deep_package}.{method_a}"
    qual_b = f"{deep_package}.{method_b}"
    assert len(qual_a) > 255
    assert len(qual_b) > 255

    cand_a = SymbolCandidate(
        symbol_type="METHOD",
        base_symbol_type="METHOD",
        name=method_a,
        qualified_name=qual_a,
        start_line=10,
        end_line=25,
        start_column=4,
        end_column=5,
        project_key=proj.key,
        file_rel_path=rel,
    )
    cand_b = SymbolCandidate(
        symbol_type="METHOD",
        base_symbol_type="METHOD",
        name=method_b,
        qualified_name=qual_b,
        start_line=30,
        end_line=45,
        start_column=4,
        end_column=5,
        project_key=proj.key,
        file_rel_path=rel,
    )

    key_a = cand_a.compute_key()
    key_b = cand_b.compute_key()

    # 1. Identity preservation: entity_keys are distinct and untruncated
    assert key_a != key_b
    assert qual_a in key_a
    assert qual_b in key_b

    ext_res = FileExtractionResult(
        file_rel_path=rel,
        file_path=rel,
        language="java",
        success=True,
        symbols=[cand_a, cand_b],
        symbol_keys=[key_a, key_b],
    )

    persist_res = service.persist_file_symbols(
        db=b08_db,
        project_id=proj.id,
        project_key=proj.key,
        file_entity=fe,
        extraction_result=ext_res,
    )
    b08_db.commit()

    assert persist_res.success is True
    assert persist_res.created == 2

    # 2. Database column safety: stored canonical_name <= 255 chars and distinct
    stored_a = b08_db.scalars(select(Entity).where(Entity.entity_key == key_a)).first()
    stored_b = b08_db.scalars(select(Entity).where(Entity.entity_key == key_b)).first()
    assert stored_a is not None and stored_b is not None

    assert len(stored_a.canonical_name) <= 255
    assert len(stored_b.canonical_name) <= 255
    assert stored_a.canonical_name != stored_b.canonical_name
