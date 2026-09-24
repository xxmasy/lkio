"""Vue SFC Coordinate Gold Standard Test Suite (Lock 10)
Validates that SfcBlockSlicer preserves exact physical file line numbers
across all 8 gold test fixtures in tests/gold/mvp2/preflight/vue_coordinates/.
"""

from pathlib import Path
import pytest
from core.parsing.parser_factory import ParserFactory
from core.parsing.sfc_block_slicer import SfcBlockSlicer

GOLD_VUE_DIR = Path(__file__).resolve().parent.parent / "gold" / "mvp2" / "preflight" / "vue_coordinates"


def find_nodes_by_type(node, target_type: str, collected: list | None = None) -> list:
    """Helper to recursively find nodes of a specific type in an AST."""
    if collected is None:
        collected = []
    if node.type == target_type:
        collected.append(node)
    for child in node.children:
        find_nodes_by_type(child, target_type, collected)
    return collected


def test_01_options_api_coordinates():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "01-options-api.vue")

    assert len(res.script_blocks) == 1
    script = res.script_blocks[0]
    assert script.start_line == 7
    assert script.end_line == 21

    factory = ParserFactory()
    tree = factory.get("javascript").parse(script.content.encode("utf-8"))
    assert tree.root_node.type == "program"

    # In 01-options-api.vue, 'export default' is on line 8
    export_nodes = find_nodes_by_type(tree.root_node, "export_statement")
    assert len(export_nodes) >= 1
    assert export_nodes[0].start_point.row + 1 == 8

    # 'loadUser' method is on line 16
    method_nodes = find_nodes_by_type(tree.root_node, "method_definition")
    assert any(m.start_point.row + 1 == 16 for m in method_nodes)


def test_02_script_setup_coordinates():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "02-script-setup.vue")

    assert len(res.script_blocks) == 1
    script = res.script_blocks[0]
    assert script.is_setup is True
    assert script.start_line == 7
    assert script.end_line == 14

    factory = ParserFactory()
    tree = factory.get("javascript").parse(script.content.encode("utf-8"))

    # 'function increment()' is on line 11
    func_nodes = find_nodes_by_type(tree.root_node, "function_declaration")
    assert len(func_nodes) == 1
    assert func_nodes[0].start_point.row + 1 == 11


def test_03_script_ts_coordinates():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "03-script-ts.vue")

    assert len(res.script_blocks) == 1
    script = res.script_blocks[0]
    assert script.lang == "ts"
    assert script.start_line == 5
    assert script.end_line == 24

    factory = ParserFactory()
    tree = factory.get("typescript").parse(script.content.encode("utf-8"))

    # 'interface Props' is on line 8
    interface_nodes = find_nodes_by_type(tree.root_node, "interface_declaration")
    assert len(interface_nodes) == 1
    assert interface_nodes[0].start_point.row + 1 == 8

    # 'function getTitleLength(): number' is on line 18
    func_nodes = find_nodes_by_type(tree.root_node, "function_declaration")
    assert any(f.start_point.row + 1 == 18 for f in func_nodes)


def test_04_script_js_coordinates():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "04-script-js.vue")

    assert len(res.script_blocks) == 1
    script = res.script_blocks[0]
    assert script.start_line == 5
    assert script.end_line == 14

    factory = ParserFactory()
    tree = factory.get("javascript").parse(script.content.encode("utf-8"))
    export_nodes = find_nodes_by_type(tree.root_node, "export_statement")
    assert len(export_nodes) == 1
    assert export_nodes[0].start_point.row + 1 == 6


def test_05_multi_block_coordinates():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "05-multi-block.vue")

    # In Vue 3, both standard <script> and <script setup> can coexist
    assert len(res.script_blocks) == 2
    s1, s2 = res.script_blocks

    assert s1.is_setup is False
    assert s1.start_line == 5
    assert s1.end_line == 10

    assert s2.is_setup is True
    assert s2.start_line == 12
    assert s2.end_line == 19

    factory = ParserFactory()
    tree2 = factory.get("typescript").parse(s2.content.encode("utf-8"))
    func_nodes = find_nodes_by_type(tree2.root_node, "function_declaration")
    assert len(func_nodes) == 1
    # 'function toggle()' is on line 16
    assert func_nodes[0].start_point.row + 1 == 16


def test_06_template_heavy_coordinates_and_elements():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "06-template-heavy.vue")

    assert res.template_block is not None
    assert res.template_block.start_line == 1
    assert res.template_block.end_line == 18

    # Verify extracted component tags
    assert "el-menu" in res.component_references
    assert "el-table" in res.component_references
    assert "CallDetails" in res.component_references

    # Verify extracted event bindings
    assert any("current-change->handlePageChange" in e for e in res.event_bindings)
    assert any("call-ended->onCallEnded" in e for e in res.event_bindings)

    # Verify script line alignment
    assert len(res.script_blocks) == 1
    script = res.script_blocks[0]
    assert script.start_line == 20
    assert script.end_line == 30

    factory = ParserFactory()
    tree = factory.get("typescript").parse(script.content.encode("utf-8"))
    funcs = find_nodes_by_type(tree.root_node, "function_declaration")
    assert len(funcs) == 2
    # 'function handlePageChange' on line 24, 'function onCallEnded' on line 27
    func_lines = {f.start_point.row + 1 for f in funcs}
    assert 24 in func_lines
    assert 27 in func_lines


def test_07_style_scoped_coordinates():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "07-style-scoped.vue")

    assert len(res.style_blocks) == 1
    style = res.style_blocks[0]
    assert style.is_scoped is True
    assert style.lang == "scss"
    assert style.start_line == 9
    assert style.end_line == 14


def test_08_empty_script_coordinates():
    slicer = SfcBlockSlicer(preserve_physical_lines=True)
    res = slicer.slice_file(GOLD_VUE_DIR / "08-empty-script.vue")

    assert len(res.script_blocks) == 1
    script = res.script_blocks[0]
    assert script.start_line == 5
    assert script.end_line == 6

    factory = ParserFactory()
    tree = factory.get("typescript").parse(script.content.encode("utf-8"))
    assert tree.root_node.type == "program"
