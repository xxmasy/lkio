"""Integration Tests for Symbol Synchronization and Database Persistence
Validates:
1. Atomic file symbol sync & 'defines' relations creation.
2. Soft deletion of vanished symbols on incremental sync.
3. Idempotent upsert behavior (0 extra inserts on re-run).
4. Project-level symbol ingestion smoke test on real project.
"""

from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from core.db.session import SessionLocal
from core.models.entity import Entity
from core.models.project import Project
from core.models.relation import Relation
from ingestion.symbols import SymbolSyncService


def test_file_symbol_sync_and_idempotency():
    try:
        db = SessionLocal()
        proj = db.scalars(select(Project).where(Project.status == "ACTIVE")).first()
    except Exception as e:
        pytest.skip(f"PostgreSQL database not available: {e}")
    if not proj:
        pytest.skip("No ACTIVE project found in database")
    try:


        file_entity = Entity(
            id=uuid.uuid4(),
            project_id=proj.id,
            entity_type="FILE",
            entity_key=f"FILE:{proj.key}:test_mock/SampleService.ts",
            name="SampleService.ts",
            canonical_name=f"{proj.key}_FILE_SampleService",
            path="test_mock/SampleService.ts",
            status="ACTIVE",
            metadata_={},
        )
        db.add(file_entity)
        db.commit()

        sync_service = SymbolSyncService()

        # 2. First sync with 2 symbols (1 interface, 1 hook)
        code_v1 = b"""
export interface Config { timeout: number; }
export function useConfigHook(): Config { return { timeout: 1000 }; }
"""
        res1 = sync_service.sync_file_symbols(
            db=db,
            project_id=proj.id,
            project_key=proj.key,
            file_entity=file_entity,
            code_bytes=code_v1,
        )
        db.commit()

        assert res1["extracted"] == 2
        assert res1["created"] == 2
        assert res1["deleted"] == 0

        # Verify symbols and relations exist in DB
        syms_v1 = db.scalars(
            select(Entity).where(
                Entity.project_id == proj.id,
                Entity.path == "test_mock/SampleService.ts",
                Entity.entity_type != "FILE",
                Entity.status == "ACTIVE",
            )
        ).all()
        assert len(syms_v1) == 2

        relations_v1 = db.scalars(
            select(Relation).where(
                Relation.subject_entity_id == file_entity.id,
                Relation.predicate == "defines",
            )
        ).all()
        assert len(relations_v1) == 2

        # 3. Second sync with identical code (Idempotency test)
        res2 = sync_service.sync_file_symbols(
            db=db,
            project_id=proj.id,
            project_key=proj.key,
            file_entity=file_entity,
            code_bytes=code_v1,
        )
        db.commit()

        assert res2["created"] == 0
        assert res2["updated"] == 2
        assert res2["deleted"] == 0

        # 4. Third sync with vanished symbol (Soft delete test)
        code_v2 = b"""
export interface Config { timeout: number; }
"""
        res3 = sync_service.sync_file_symbols(
            db=db,
            project_id=proj.id,
            project_key=proj.key,
            file_entity=file_entity,
            code_bytes=code_v2,
        )
        db.commit()

        assert res3["created"] == 0
        assert res3["deleted"] == 1

        # Check that useConfigHook is marked deleted, NOT physically removed
        deleted_sym = db.scalars(
            select(Entity).where(
                Entity.project_id == proj.id,
                Entity.name == "useConfigHook",
            )
        ).first()
        assert deleted_sym is not None
        assert deleted_sym.status == "deleted"

    finally:
        # Cleanup mock entities and relations
        db.rollback()
        mock_entities = db.scalars(
            select(Entity).where(Entity.path == "test_mock/SampleService.ts")
        ).all()
        for e in mock_entities:
            db.delete(e)
        db.commit()
        db.close()


def test_real_project_symbols_smoke():
    """Runs symbol extraction on HELLO_BE (Spring Boot Java project)."""
    try:
        db = SessionLocal()
        proj = db.scalars(select(Project).where(Project.key == "HELLO_BE")).first()
    except Exception as e:
        pytest.skip(f"PostgreSQL database not available: {e}")
    if not proj:
        pytest.skip("HELLO_BE not registered")
    try:

        sync_service = SymbolSyncService()
        stats = sync_service.sync_project_symbols("HELLO_BE", db=db, limit=10)

        assert stats["supported_files"] > 0
        assert stats["total_symbols_extracted"] > 0
        assert stats["created"] + stats["updated"] > 0

        # Check sample Java method in DB
        sample_method = db.scalars(
            select(Entity).where(
                Entity.project_id == proj.id,
                Entity.entity_type == "METHOD",
                Entity.status == "ACTIVE",
            )
        ).first()
        assert sample_method is not None
        assert sample_method.metadata_["base_symbol_type"] == "METHOD"
        assert sample_method.metadata_["signature_discriminator"] is not None

        # Verify defines relation
        rel = db.scalars(
            select(Relation).where(
                Relation.object_entity_id == sample_method.id,
                Relation.predicate == "defines",
            )
        ).first()
        assert rel is not None
        assert rel.confidence == Decimal("1.00000")

    finally:
        db.close()
