"""Unit tests for Wiki Models and Lifecycle State Machine."""

from core.models.wiki import StandardWikiSection, WikiSection, WikiSectionStatus
from core.wiki.models import WikiSectionDTO


def test_standard_wiki_sections_completeness():
    # Exactly 13 fixed sections required by baseline
    sections = list(StandardWikiSection)
    assert len(sections) == 13

    expected = {
        "project_overview",
        "architecture",
        "frontend",
        "backend",
        "api",
        "database",
        "business_domain",
        "business_process",
        "business_rules",
        "dependencies",
        "recent_changes",
        "known_risks",
        "open_decisions",
    }
    assert {s.value for s in sections} == expected


def test_wiki_section_lifecycle_transitions():
    sec = WikiSection(
        project_key="HELLO_FE",
        section_key="WIKI:HELLO_FE:api",
        section_name=StandardWikiSection.API.value,
        title="API Contracts",
        content="## API Content",
        status=WikiSectionStatus.GENERATED.value,
    )
    assert sec.status == WikiSectionStatus.GENERATED.value

    # Transition: GENERATED -> VERIFIED
    sec.mark_verified()
    assert sec.status == WikiSectionStatus.VERIFIED.value
    assert sec.verified_at is not None

    # Transition: VERIFIED -> STALE
    sec.mark_stale()
    assert sec.status == WikiSectionStatus.STALE.value

    # Transition: STALE -> CONFLICTED
    sec.mark_conflicted()
    assert sec.status == WikiSectionStatus.CONFLICTED.value


def test_wiki_section_dto_key():
    dto = WikiSectionDTO(
        project_key="L2C_FE",
        section_name=StandardWikiSection.FRONTEND,
        title="Frontend Architecture",
        content="Vue 3 + Vite",
    )
    assert dto.section_key == "WIKI:L2C_FE:frontend"
