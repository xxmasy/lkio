"""Unit tests for WikiPipeline (Full generation, Incremental update, and Persistence)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db.base import Base
from core.models.wiki import StandardWikiSection, WikiSection, WikiSectionStatus
from core.rag.builder import RAGIndexHub
from core.rag.engine import RAGEngine
from core.wiki.pipeline import WikiPipeline


def test_pipeline_generate_and_incremental():
    hub = RAGIndexHub(dimension=32)
    hub.index_entity(
        entity_key="SYMBOL:HELLO_FE:api/order.ts",
        name="order.ts",
        canonical_name="api/order.ts",
        project_key="HELLO_FE",
        entity_type="MODULE",
        file_path="src/api/order.ts",
        start_line=1,
        end_line=50,
        docstring="API client for HTTP endpoints",
    )
    hub.index_entity(
        entity_key="SYMBOL:HELLO_FE:model/Order.ts",
        name="OrderModel",
        canonical_name="model/Order.ts:OrderModel",
        project_key="HELLO_FE",
        entity_type="CLASS",
        file_path="src/model/Order.ts",
        start_line=1,
        end_line=30,
        docstring="Database schema and entity definitions for orders",
    )
    engine = RAGEngine(index_hub=hub)
    pipeline = WikiPipeline()

    # 1. Full Generation
    all_sections = pipeline.generate_full_wiki(project_key="HELLO_FE", engine=engine)
    assert len(all_sections) == 13
    assert {s.section_name for s in all_sections} == set(StandardWikiSection)

    # 2. Incremental Regeneration: Modify only src/api/order.ts
    regen_sections, stale_names = pipeline.regenerate_stale_sections(
        project_key="HELLO_FE",
        modified_files=["src/api/order.ts"],
        engine=engine,
        existing_sections=all_sections,
    )

    assert len(regen_sections) == 13
    # Stale sections should include API, ARCHITECTURE, RECENT_CHANGES
    assert StandardWikiSection.API in stale_names
    assert StandardWikiSection.RECENT_CHANGES in stale_names
    assert StandardWikiSection.DATABASE not in stale_names

    # Check that non-stale sections were preserved
    preserved_db = next(s for s in regen_sections if s.section_name == StandardWikiSection.DATABASE)
    original_db = next(s for s in all_sections if s.section_name == StandardWikiSection.DATABASE)
    assert preserved_db.content == original_db.content


def test_pipeline_persistence_idempotency():
    # Setup in-memory SQLite engine
    engine_sqlite = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine_sqlite)
    SessionTest = sessionmaker(bind=engine_sqlite)
    session = SessionTest()

    hub = RAGIndexHub(dimension=32)
    rag_engine = RAGEngine(index_hub=hub)
    pipeline = WikiPipeline()

    sections = pipeline.generate_full_wiki(project_key="HELLO_BE", engine=rag_engine)

    # Pass 1: Initial Insert
    res1 = pipeline.persist_sections(db=session, sections=sections)
    assert res1["created"] == 13
    assert res1["updated"] == 0
    assert session.query(WikiSection).count() == 13

    # Pass 2: Idempotent Re-sync
    res2 = pipeline.persist_sections(db=session, sections=sections)
    assert res2["created"] == 0
    assert res2["updated"] == 13
    assert session.query(WikiSection).count() == 13
