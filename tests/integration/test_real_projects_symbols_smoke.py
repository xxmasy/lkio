"""Real Projects Symbol Extraction Smoke Tests & Strict Read-Only Verification
Validates:
1. Symbol extraction on real production files from HELLO_FE, HELLO_BE, L2C_FE.
2. Inviolable Red Line 1: Git status --porcelain unchanged across all 3 source projects.
3. No hallucinated/fake business data (AST is structural fact).
"""

import os
from pathlib import Path
import subprocess
import pytest
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.parsing.models import SymbolType


def get_git_status_porcelain(repo_path: str) -> str:
    """Invokes Git CLI to get exact working tree porcelain output with warmed-up stat cache."""
    subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def safe_walk_files(base_path: Path, extensions: tuple[str, ...], limit: int = 10) -> list[Path]:
    """Safely walks directory while pruning node_modules, .git, dist, target, build."""
    found = []
    for root_dir, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".pnpm", "dist", "target", "build", ".venv"}]
        for f in files:
            if f.endswith(extensions):
                found.append(Path(root_dir) / f)
                if len(found) >= limit:
                    return found
    return found


def test_hello_fe_real_symbols():
    repo = Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello"))
    if not repo.exists():
        pytest.skip("HELLO_FE not found")

    orchestrator = SymbolExtractionOrchestrator()
    sample_files = safe_walk_files(repo / "src", (".vue", ".js", ".ts"), limit=5)
    assert len(sample_files) > 0

    all_symbols = []
    for f in sample_files:
        code = f.read_bytes()
        rel_path = str(f.relative_to(repo)).replace("\\", "/")
        res = orchestrator.extract_file_symbols(
            code_bytes=code,
            project_key="HELLO_FE",
            file_path=str(f),
            file_rel_path=rel_path,
        )
        all_symbols.extend(res)

    assert len(all_symbols) > 0
    types = {cand.symbol_type for _, cand in all_symbols}
    assert any(t in types for t in ["COMPONENT", "FUNCTION", "VARIABLE", "METHOD"])


def test_hello_be_real_symbols():
    repo = Path(os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend"))
    if not repo.exists():
        pytest.skip("HELLO_BE not found")

    orchestrator = SymbolExtractionOrchestrator()
    sample_files = safe_walk_files(repo / "src" / "main" / "java", (".java",), limit=5)
    assert len(sample_files) > 0

    all_symbols = []
    for f in sample_files:
        code = f.read_bytes()
        rel_path = str(f.relative_to(repo)).replace("\\", "/")
        res = orchestrator.extract_file_symbols(
            code_bytes=code,
            project_key="HELLO_BE",
            file_path=str(f),
            file_rel_path=rel_path,
        )
        all_symbols.extend(res)

    assert len(all_symbols) > 0
    types = {cand.symbol_type for _, cand in all_symbols}
    assert "CLASS" in types or "INTERFACE" in types
    assert "METHOD" in types


def test_l2c_fe_real_symbols():
    repo = Path(os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project"))
    if not repo.exists():
        pytest.skip("L2C_FE not found")

    orchestrator = SymbolExtractionOrchestrator()
    sample_files = safe_walk_files(repo / "apps" / "web-ele" / "src", (".vue", ".ts"), limit=5)
    assert len(sample_files) > 0

    all_symbols = []
    for f in sample_files:
        code = f.read_bytes()
        rel_path = str(f.relative_to(repo)).replace("\\", "/")
        res = orchestrator.extract_file_symbols(
            code_bytes=code,
            project_key="L2C_FE",
            file_path=str(f),
            file_rel_path=rel_path,
        )
        all_symbols.extend(res)

    assert len(all_symbols) > 0


def test_source_repositories_strict_readonly_after_symbols():
    """Verify that scanning real project files for symbol extraction causes 0 modifications."""
    paths = [
        os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello"),
        os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend"),
        os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project"),
    ]
    status_before = {p: get_git_status_porcelain(p) for p in paths if Path(p).exists()}

    orchestrator = SymbolExtractionOrchestrator()
    for p in paths:
        root = Path(p)
        if not root.exists():
            continue

        sample_files = safe_walk_files(root, (".vue", ".java", ".ts", ".js"), limit=15)
        for f in sample_files:
            try:
                code = f.read_bytes()
                rel_path = str(f.relative_to(root)).replace("\\", "/")
                orchestrator.extract_file_symbols(
                    code_bytes=code,
                    project_key="BENCHMARK",
                    file_path=str(f),
                    file_rel_path=rel_path,
                )
            except Exception:
                pass

    for p in paths:
        if Path(p).exists():
            status_after = get_git_status_porcelain(p)
            assert status_after == status_before[p], (
                f"Source project '{p}' was modified during symbol extraction! "
                f"Before:\n{status_before[p]}\nAfter:\n{status_after}"
            )
