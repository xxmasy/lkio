"""Unit tests for StaleDetector (Entity/File Change -> Affected Wiki Sections)."""

from core.models.wiki import StandardWikiSection
from core.wiki.stale_detector import StaleDetector


def test_stale_detector_api_change():
    detector = StaleDetector()
    stale = detector.detect_stale_sections(modified_files=["src/api/order.ts"])

    assert StandardWikiSection.API in stale
    assert StandardWikiSection.ARCHITECTURE in stale
    assert StandardWikiSection.RECENT_CHANGES in stale
    assert StandardWikiSection.DATABASE not in stale


def test_stale_detector_service_change():
    detector = StaleDetector()
    stale = detector.detect_stale_sections(
        modified_files=["src/main/java/service/LeadAllocationService.java"]
    )

    assert StandardWikiSection.BACKEND in stale
    assert StandardWikiSection.BUSINESS_RULES in stale
    assert StandardWikiSection.BUSINESS_PROCESS in stale
    assert StandardWikiSection.RECENT_CHANGES in stale
    assert StandardWikiSection.FRONTEND not in stale


def test_stale_detector_vue_change():
    detector = StaleDetector()
    stale = detector.detect_stale_sections(
        modified_files=["apps/web-ele/src/views/dashboard/analytics/index.vue"]
    )

    assert StandardWikiSection.FRONTEND in stale
    assert StandardWikiSection.RECENT_CHANGES in stale
    assert StandardWikiSection.BACKEND not in stale


def test_stale_detector_manifest_change():
    detector = StaleDetector()
    stale = detector.detect_stale_sections(modified_files=["package.json"])

    assert StandardWikiSection.DEPENDENCIES in stale
    assert StandardWikiSection.ARCHITECTURE in stale


def test_stale_detector_evidence_intersection():
    detector = StaleDetector()
    existing_evidences = {
        StandardWikiSection.BUSINESS_DOMAIN: ["src/model/OrderDTO.java"],
        StandardWikiSection.FRONTEND: ["src/views/Home.vue"],
    }
    # Modifying OrderDTO.java should directly stale BUSINESS_DOMAIN
    stale = detector.detect_stale_sections(
        modified_files=["src/model/OrderDTO.java"],
        existing_section_evidences=existing_evidences,
    )
    assert StandardWikiSection.BUSINESS_DOMAIN in stale
    assert StandardWikiSection.FRONTEND not in stale
