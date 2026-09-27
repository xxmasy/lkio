"""LKIO MVP2-A - Tree-sitter & Vue SFC Preflight Test Suite
Validates:
1. Tree-sitter exact pinned versions and grammar ABI initialization.
2. TS, TSX, JS, Java AST parsing capabilities.
3. Vue SFC Slicer with 100% physical line alignment.
4. Real-world parser smoke testing across HELLO_FE, HELLO_BE, and L2C_FE.
5. Strict read-only guarantee across source repositories.
"""

from pathlib import Path
import os
import subprocess
import pytest
from ingestion.code.dto import LanguageType
from ingestion.code.parsers.factory import PARSER_BUNDLE_VERSION, ParserFactory
from ingestion.code.parsers.vue_sfc import SfcBlockSlicer


def get_git_status_porcelain(repo_path: str) -> str:
    """Invokes Git CLI to get exact working tree porcelain output."""
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


def test_treesitter_exact_pin_and_abi():
    """Verify exact pinned versions match the MVP2 Preflight Lock."""
    assert PARSER_BUNDLE_VERSION["tree_sitter"] == "0.25.2"
    assert PARSER_BUNDLE_VERSION["tree_sitter_javascript"] == "0.25.0"
    assert PARSER_BUNDLE_VERSION["tree_sitter_typescript"] == "0.23.2"
    assert PARSER_BUNDLE_VERSION["tree_sitter_java"] == "0.23.5"

    factory = ParserFactory()
    # Verify languages initialize cleanly without ABI mismatches
    assert factory.get_language(LanguageType.JAVASCRIPT) is not None
    assert factory.get_language(LanguageType.TYPESCRIPT) is not None
    assert factory.get_language(LanguageType.TSX) is not None
    assert factory.get_language(LanguageType.JAVA) is not None


def test_parse_snippets_basic():
    """Verify basic AST generation on synthetic snippets."""
    factory = ParserFactory()

    # 1. TypeScript
    ts_code = "interface User { id: string; name: string; }\nfunction getUser(): User { return { id: '1', name: 'Alice' }; }"
    ts_tree = factory.parse_source(ts_code, LanguageType.TYPESCRIPT)
    assert ts_tree.root_node.type == "program"
    assert not ts_tree.root_node.has_error

    # 2. TSX
    tsx_code = "const App = () => <div><h1>Hello LKIO</h1></div>;"
    tsx_tree = factory.parse_source(tsx_code, LanguageType.TSX)
    assert tsx_tree.root_node.type == "program"
    assert not tsx_tree.root_node.has_error

    # 3. Java
    java_code = "package com.example;\npublic class LeadController {\n  public String getLead() { return \"lead\"; }\n}"
    java_tree = factory.parse_source(java_code, LanguageType.JAVA)
    assert java_tree.root_node.type == "program"
    assert not java_tree.root_node.has_error


def test_vue_sfc_slicing_and_line_preservation():
    """Verify Vue SFC Slicer preserves exact physical file line numbers."""
    vue_content = """<template>
  <div class="user-box">
    <ElButton @click="handleClick">Submit</ElButton>
    <el-table :data="tableData" v-model="selectedRow"></el-table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
function handleClick() {
  count.value++
}
</script>

<style scoped>
.user-box { color: red; }
</style>
"""
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file("test_component.vue", content=vue_content)

    assert res.template_block is not None
    assert len(res.script_blocks) == 1
    assert len(res.style_blocks) == 1

    # Template checks
    assert "ElButton" in res.component_references
    assert "el-table" in res.component_references
    assert "click->handleClick" in res.event_bindings

    # Script line alignment check
    script = res.script_blocks[0]
    assert script.lang == "ts"
    assert script.is_setup is True
    # The <script setup> tag opens on line 8, closes on line 15
    assert script.start_line == 8
    assert script.end_line == 15

    # Parse script content with TypeScript parser
    factory = ParserFactory()
    tree = factory.parse_source(script.content, LanguageType.TYPESCRIPT)
    assert tree.root_node.type == "program"

    # Find the function_declaration node and verify its line number matches physical line
    func_node = None
    for child in tree.root_node.children:
        if child.type == "function_declaration":
            func_node = child
            break

    assert func_node is not None, "function_declaration not found in script AST"
    # In vue_content, 'function handleClick()' is on line 12 (1-based)
    # Tree-sitter row is 0-based, so row + 1 should equal 12!
    assert func_node.start_point.row + 1 == 12, (
        f"Line mismatch: expected line 12, got {func_node.start_point.row + 1}"
    )


def test_smoke_real_source_projects():
    """Smoke test Tree-sitter parsers against real code files from the three projects."""
    factory = ParserFactory()
    slicer = SfcBlockSlicer(preserve_physical_lines=True)

    # 1. HELLO_FE: Vue and TS/JS
    hello_vue = Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello")) / "src/views/sales/components/CallDetails.vue"
    if hello_vue.exists():
        sfc_res = slicer.slice_file(hello_vue)
        assert len(sfc_res.script_blocks) >= 1
        for sc in sfc_res.script_blocks:
            l_type = LanguageType.TYPESCRIPT if sc.lang in ["ts", "typescript"] else LanguageType.JAVASCRIPT
            tree = factory.parse_source(sc.content, l_type)
            assert tree.root_node.type == "program"

    hello_js = Path(os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello")) / "src/main.js"
    if hello_js.exists():
        code = hello_js.read_text(encoding="utf-8", errors="replace")
        tree = factory.parse_source(code, LanguageType.JAVASCRIPT)
        assert tree.root_node.type == "program"

    # 2. HELLO_BE: Java
    backend_java_dir = Path(os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend")) / "src/main/java"
    if backend_java_dir.exists():
        java_files = list(backend_java_dir.rglob("*.java"))
        assert len(java_files) > 0
        sample_java = java_files[0]
        code = sample_java.read_text(encoding="utf-8", errors="replace")
        tree = factory.parse_source(code, LanguageType.JAVA)
        assert tree.root_node.type == "program"
        assert not tree.root_node.has_error

    # 3. L2C_FE: Vue and TS
    l2c_dir = Path(os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project")) / "apps/web-ele/src"
    if l2c_dir.exists():
        vue_files = list(l2c_dir.rglob("*.vue"))
        if vue_files:
            sfc_res = slicer.slice_file(vue_files[0])
            for sc in sfc_res.script_blocks:
                l_type = LanguageType.TYPESCRIPT if sc.lang in ["ts", "typescript"] else LanguageType.JAVASCRIPT
                tree = factory.parse_source(sc.content, l_type)
                assert tree.root_node.type == "program"


def test_readonly_integrity_preflight():
    """Verify that Tree-sitter preflight checks do not touch or alter source projects."""
    paths = [
        os.environ.get("LKIO_TEST_HELLO_FE", "C:/WorkSpace/hello"),
        os.environ.get("LKIO_TEST_HELLO_BE", "C:/WorkSpace/hello-backend"),
        os.environ.get("LKIO_TEST_L2C_FE", "C:/WorkSpace/L2C project"),
    ]
    status_before = {p: get_git_status_porcelain(p) for p in paths if Path(p).exists()}

    # Run tests on files
    factory = ParserFactory()
    for p in paths:
        path_obj = Path(p)
        if not path_obj.exists():
            continue
        sample_files = []
        for root_dir, dirs, files in os.walk(path_obj):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".pnpm", "dist", "target", "build", ".venv"}]
            for f in files:
                if f.endswith((".vue", ".java", ".ts")):
                    sample_files.append(Path(root_dir) / f)
                    if len(sample_files) >= 5:
                        break
            if len(sample_files) >= 5:
                break

        for f in sample_files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                l_type = factory.detect_language(f)
                if l_type != LanguageType.UNKNOWN and l_type != LanguageType.VUE:
                    factory.parse_source(content, l_type)
            except Exception:
                pass

    # Verify status after
    for p in paths:
        if Path(p).exists():
            status_after = get_git_status_porcelain(p)
            assert status_after == status_before[p], f"Repository '{p}' was modified during preflight!"
