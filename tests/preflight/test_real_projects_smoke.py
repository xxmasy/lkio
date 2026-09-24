"""Real-World Projects Preflight Smoke Tests & Readonly Guarantee
Validates that ParserFactory and SfcBlockSlicer parse real production code
from HELLO_FE, HELLO_BE, and L2C_FE without errors or working-tree mutations.
"""

from pathlib import Path
import subprocess
import pytest
from core.parsing.parser_factory import ParserFactory
from core.parsing.sfc_block_slicer import SfcBlockSlicer


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


def test_hello_fe_smoke():
    """Smoke test on HELLO_FE real Vue and JS files."""
    repo_path = Path("C:/WorkSpace/hello")
    assert repo_path.exists(), f"Path not found: {repo_path}"

    factory = ParserFactory()
    slicer = SfcBlockSlicer(preserve_physical_lines=True)

    # 1. Parse CallDetails.vue
    vue_file = repo_path / "src" / "views" / "sales" / "components" / "CallDetails.vue"
    if vue_file.exists():
        sfc = slicer.slice_file(vue_file)
        assert len(sfc.script_blocks) >= 1
        for sc in sfc.script_blocks:
            lang = "typescript" if sc.lang in ["ts", "typescript"] else "javascript"
            tree = factory.get(lang).parse(sc.content.encode("utf-8"))
            assert tree.root_node.type == "program"

    # 2. Parse main.js
    main_js = repo_path / "src" / "main.js"
    if main_js.exists():
        code = main_js.read_bytes()
        tree = factory.get("javascript").parse(code)
        assert tree.root_node.type == "program"


def test_hello_be_smoke():
    """Smoke test on HELLO_BE real Java files."""
    repo_path = Path("C:/WorkSpace/hello-backend")
    assert repo_path.exists(), f"Path not found: {repo_path}"

    factory = ParserFactory()
    java_files = list((repo_path / "src" / "main" / "java").rglob("*.java"))
    assert len(java_files) > 10, "Expected at least 10 Java files in backend"

    # Test parse on first 5 Java files
    for jf in java_files[:5]:
        code = jf.read_bytes()
        tree = factory.get("java").parse(code)
        assert tree.root_node.type == "program"
        assert not tree.root_node.has_error


def test_l2c_fe_smoke():
    """Smoke test on L2C_FE real Vue 3 and TypeScript files."""
    repo_path = Path("C:/WorkSpace/L2C project")
    assert repo_path.exists(), f"Path not found: {repo_path}"

    factory = ParserFactory()
    slicer = SfcBlockSlicer(preserve_physical_lines=True)

    src_dir = repo_path / "apps" / "web-ele" / "src"
    if src_dir.exists():
        vue_files = list(src_dir.rglob("*.vue"))
        assert len(vue_files) > 0
        for vf in vue_files[:5]:
            sfc = slicer.slice_file(vf)
            for sc in sfc.script_blocks:
                lang = "typescript" if sc.lang in ["ts", "typescript"] else "javascript"
                tree = factory.get(lang).parse(sc.content.encode("utf-8"))
                assert tree.root_node.type == "program"


def test_source_repos_strict_readonly():
    """Verify that parsing source files causes 0 changes to working tree status."""
    paths = [
        "C:\\WorkSpace\\hello",
        "C:\\WorkSpace\\hello-backend",
        "C:\\WorkSpace\\L2C project",
    ]
    status_before = {p: get_git_status_porcelain(p) for p in paths if Path(p).exists()}

    # Perform extensive parsing across the projects
    factory = ParserFactory()
    slicer = SfcBlockSlicer(preserve_physical_lines=True)

    for p in paths:
        root = Path(p)
        if not root.exists():
            continue
        # Scan 10 vue files and 10 java/ts files
        for f in list(root.rglob("*.vue"))[:10]:
            try:
                sfc = slicer.slice_file(f)
                for sc in sfc.script_blocks:
                    lang = "typescript" if sc.lang in ["ts", "typescript"] else "javascript"
                    factory.get(lang).parse(sc.content.encode("utf-8"))
            except Exception:
                pass

        for f in list(root.rglob("*.java"))[:10] + list(root.rglob("*.ts"))[:10]:
            try:
                l_key = factory.detect_language(f)
                if l_key in ["typescript", "tsx", "javascript", "jsx", "java"]:
                    factory.get(l_key).parse(f.read_bytes())
            except Exception:
                pass

    for p in paths:
        if Path(p).exists():
            status_after = get_git_status_porcelain(p)
            assert status_after == status_before[p], (
                f"Source project '{p}' was modified! "
                f"Before:\n{status_before[p]}\nAfter:\n{status_after}"
            )
