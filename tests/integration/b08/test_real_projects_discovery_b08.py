"""B-08 Layer 1 Tests: Real Project File Discovery & Language Routing (Gate A, Gate B)
Validates:
- Gate A: Discovery of 4,603 supported source files across HELLO_FE, HELLO_BE, L2C_FE.
- Gate B: 100% deterministic routing accuracy across TS, TSX, JS, Java, and Vue.
"""

from pathlib import Path
import pytest

from core.extraction.orchestrator import SymbolExtractionOrchestrator
from tests.integration.b08.conftest import REPOS, discover_supported_files


def test_gate_a_real_projects_discovery():
    """Gate A: Safe directory scanning discovers all 4,603 supported source files without pollution."""
    discovered = {}
    for name, root in REPOS.items():
        assert root.exists(), f"Repository path missing: {root}"
        files = discover_supported_files(root)
        discovered[name] = files
        assert len(files) > 0, f"No files discovered for {name}"

    assert len(discovered["HELLO_FE"]) >= 1050
    assert len(discovered["HELLO_BE"]) >= 1900
    assert len(discovered["L2C_FE"]) >= 1500

    total_files = sum(len(f) for f in discovered.values())
    assert total_files >= 4500

    # Verify no pruned directories leaked in
    forbidden_tokens = {"node_modules", "target", "dist", ".git", ".idea", ".vscode"}
    for name, files in discovered.items():
        for f in files:
            parts = set(f.parts)
            leakage = parts.intersection(forbidden_tokens)
            assert not leakage, f"Pruned directory leaked in {name}: {f}"


def test_gate_b_real_language_routing_accuracy():
    """Gate B: 100% of discovered real source files are accurately recognized and routed."""
    orchestrator = SymbolExtractionOrchestrator()
    language_census = {}

    for name, root in REPOS.items():
        files = discover_supported_files(root)
        for f in files:
            assert orchestrator.is_supported(f) is True, f"Supported file deemed unsupported: {f}"
            lang = orchestrator.detect_language(f)
            assert lang in {"typescript", "tsx", "javascript", "jsx", "java", "vue"}, f"Unexpected language '{lang}' for {f}"
            language_census[lang] = language_census.get(lang, 0) + 1

    # Check language counts
    assert language_census["java"] >= 1900
    assert language_census["vue"] >= 1300
    assert language_census["typescript"] >= 800
    assert language_census["javascript"] >= 400
    assert language_census["tsx"] >= 30
    assert sum(language_census.values()) >= 4500

