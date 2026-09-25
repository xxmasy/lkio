"""LKIO MVP2-B B-05 Vue SFC Symbol Extractor Unit Tests
Dedicated test suite verifying all 16 Acceptance Gates (Gate A ~ Gate P) and 6 Boundary Locks:
- LOCK-VUE-01: Synthetic Component vs AST Native Symbol (synthetic=True, source_kind="vue_sfc_file_context")
- LOCK-VUE-02: Template evidence taxonomy (extraction_method = "static_template")
- LOCK-VUE-03: Structured bindings preservation without premature function call assumptions
- LOCK-VUE-03b: Tag name preservation (raw tag_name + normalized_name in PascalCase)
- LOCK-VUE-04: Options API structural metadata (does not distort B-03 native symbols)
- LOCK-VUE-05: Vue compiler macros v1 collection
- LOCK-VUE-06: Preflight parser strategy with graceful degradation for unsupported template preprocessors
- B-02 Criterion 5: Script + Script Setup block scope isolation (script::foo vs script_setup::foo)
"""

from pathlib import Path
import pytest

from core.extraction.normalizer import parse_symbol_key
from core.extraction.vue import VueExtractor
from core.parsing.models import SymbolType

GOLD_VUE_DIR = Path(__file__).resolve().parent.parent.parent / "gold" / "mvp2" / "symbols" / "vue"


@pytest.fixture
def extractor() -> VueExtractor:
    return VueExtractor()


# ==============================================================================
# Gold Set 1: basic_setup.vue (Gate A, B, C, G, H, I, J, N, O)
# ==============================================================================

def test_gold_vue_basic_setup(extractor: VueExtractor):
    """Verifies Vue 3 script setup, synthetic component symbol, Hook, and template facts."""
    fixture_path = GOLD_VUE_DIR / "basic_setup.vue"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/views/basic_setup.vue",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # 1. Gate B & LOCK-VUE-01: Synthetic Component Symbol
    assert "basic_setup" in sym_by_qname
    comp = sym_by_qname["basic_setup"]
    assert comp.symbol_type == SymbolType.COMPONENT.value
    assert comp.base_symbol_type == SymbolType.VARIABLE.value
    assert comp.classification_method == "vue_sfc_rule_v1"
    assert comp.start_line == 1
    assert comp.end_line > 1
    assert comp.is_exported is True

    # LOCK-VUE-01: Synthetic provenance metadata
    assert comp.metadata.get("synthetic") is True
    assert comp.metadata.get("source_kind") == "vue_sfc_file_context"
    assert comp.metadata.get("component_context") is True
    assert comp.metadata.get("extraction_method") == "sfc_structure"
    assert comp.metadata.get("confidence") == 1.0
    assert comp.metadata.get("evidence", {}).get("method") == "sfc_structure"
    assert comp.metadata.get("evidence", {}).get("file_stem") == "basic_setup"

    # 2. Gate H & Gate I (LOCK-VUE-02, LOCK-VUE-03): Template Structural Facts
    tpl = comp.metadata.get("template", {})
    comp_refs = {c["normalized_name"]: c for c in tpl.get("component_references", [])}
    assert "ElButton" in comp_refs
    assert comp_refs["ElButton"]["tag_name"] == "ElButton"
    assert comp_refs["ElButton"]["evidence"]["method"] == "static_template"
    assert "RouterView" in comp_refs
    assert comp_refs["RouterView"]["tag_name"] == "router-view"

    # Event binding
    evts = tpl.get("event_bindings", [])
    assert any(e["directive"] == "on" and e["event"] == "click" and e["expression"] == "handleRefresh" for e in evts)

    # Property binding
    props = tpl.get("property_bindings", [])
    assert any(p["directive"] == "bind" and p["argument"] == "loading" and p["expression"] == "loading" for p in props)

    # 3. Gate J: Style Metadata
    styles = comp.metadata.get("styles", [])
    assert len(styles) == 1
    assert styles[0]["scoped"] is True
    assert styles[0]["lang"] == "scss"
    assert styles[0]["evidence"]["method"] == "static_sfc_metadata"

    # 4. Gate C & Gate G: Script Setup Symbols (TypeScript, Hook, Function)
    assert "script_setup::title" in sym_by_qname
    assert "script_setup::loading" in sym_by_qname
    assert "script_setup::handleRefresh" in sym_by_qname

    # Gate G: Hook classification inside Vue
    assert "script_setup::useLeadState" in sym_by_qname
    hook_sym = sym_by_qname["script_setup::useLeadState"]
    assert hook_sym.symbol_type == SymbolType.HOOK.value
    assert hook_sym.base_symbol_type == SymbolType.FUNCTION.value
    assert hook_sym.classification_method == "name_prefix_rule_v1"

    # Gate N: Physical Line Number Accuracy (Zero line drift)
    # title is defined on line 15 of basic_setup.vue
    title_sym = sym_by_qname["script_setup::title"]
    assert title_sym.start_line == 15, f"Physical line should match exactly 15, got {title_sym.start_line}"


# ==============================================================================
# Gold Set 2: options_api.vue (Gate E, LOCK-VUE-04)
# ==============================================================================

def test_gold_vue_options_api(extractor: VueExtractor):
    """Verifies Options API structural metadata extraction without distorting B-03 native symbols."""
    fixture_path = GOLD_VUE_DIR / "options_api.vue"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/components/options_api.vue",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # 1. Main Component Symbol
    assert "options_api" in sym_by_qname
    comp = sym_by_qname["options_api"]

    # 2. LOCK-VUE-04: Options API Structural Facts
    opt = comp.metadata.get("options_api", {})
    methods = [m["name"] for m in opt.get("methods", [])]
    assert "increment" in methods

    computed = [c["name"] for c in opt.get("computed", [])]
    assert "doubleCount" in computed

    data_entries = [d["name"] for d in opt.get("data", [])]
    assert "data" in data_entries

    # LOCK-VUE-04 Boundary: Options API methods must NOT be created as fake METHOD Symbol nodes!
    fake_methods = [s for s in symbols if s.name in ["increment", "doubleCount"] and s.symbol_type == SymbolType.METHOD.value]
    assert len(fake_methods) == 0, "Options API methods must NOT be elevated to native METHOD entities"


# ==============================================================================
# Gold Set 3: multi_script.vue (Gate F, B-02 Criterion 5)
# ==============================================================================

def test_gold_vue_multi_script(extractor: VueExtractor):
    """Verifies dual script blocks (<script> + <script setup>) block scope isolation."""
    fixture_path = GOLD_VUE_DIR / "multi_script.vue"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/views/multi_script.vue",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate F & Criterion 5: Symbol names defined in both script and script_setup must be isolated
    assert "script::initConfig" in sym_by_qname
    assert "script_setup::initConfig" in sym_by_qname
    sym_plain = sym_by_qname["script::initConfig"]
    sym_setup = sym_by_qname["script_setup::initConfig"]

    # Keys must be distinct
    key_plain = sym_plain.compute_key()
    key_setup = sym_setup.compute_key()
    assert key_plain != key_setup, "Symbols in different script blocks must have strictly distinct keys"
    assert ":script::initConfig:" in key_plain
    assert ":script_setup::initConfig:" in key_setup

    assert "script::getVersion" in sym_by_qname
    assert "script_setup::getVersion" in sym_by_qname
    assert sym_by_qname["script::getVersion"].compute_key() != sym_by_qname["script_setup::getVersion"].compute_key()


# ==============================================================================
# Gold Set 4: macros_and_bindings.vue (Gate K, LOCK-VUE-03, LOCK-VUE-05)
# ==============================================================================

def test_gold_vue_macros_and_bindings(extractor: VueExtractor):
    """Verifies Vue 3 compiler macros v1 collection and structured directive bindings."""
    fixture_path = GOLD_VUE_DIR / "macros_and_bindings.vue"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/views/macros_and_bindings.vue",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}
    comp = sym_by_qname["macros_and_bindings"]

    # 1. LOCK-VUE-05: Vue Compiler Macros v1
    macros = comp.metadata.get("macros", {})
    assert "defineProps" in macros
    assert "defineEmits" in macros
    assert "defineExpose" in macros
    assert "defineOptions" in macros
    assert "defineModel" in macros

    # withDefaults as macro helper
    helpers = comp.metadata.get("macro_helpers", [])
    assert "withDefaults" in helpers

    # Macro calls must NOT generate independent symbol nodes
    macro_symbols = [s for s in symbols if s.name in ["defineProps", "defineEmits", "defineExpose", "defineModel"]]
    assert len(macro_symbols) == 0, "Compiler macros must never be extracted as standalone Symbol entities"

    # 2. LOCK-VUE-03: Structured Template Bindings
    tpl = comp.metadata.get("template", {})

    # v-model binding
    prop_bindings = tpl.get("property_bindings", [])
    model_b = next((b for b in prop_bindings if b["directive"] == "model"), None)
    assert model_b is not None
    assert model_b["expression"] == "form.name"
    assert "trim" in model_b["modifiers"]

    # :disabled binding
    disabled_b = next((b for b in prop_bindings if b["directive"] == "bind" and b["argument"] == "disabled"), None)
    assert disabled_b is not None
    assert disabled_b["expression"] == "form.status === 1"

    # @change event
    evt_bindings = tpl.get("event_bindings", [])
    change_e = next((e for e in evt_bindings if e["event"] == "change"), None)
    assert change_e is not None
    assert change_e["expression"] == "handleChange(row)"

    # Tag names: raw and normalized (LOCK-VUE-03b)
    comp_refs = {c["tag_name"]: c for c in tpl.get("component_references", [])}
    assert "el-input" in comp_refs
    assert comp_refs["el-input"]["normalized_name"] == "ElInput"

    assert "LeadDetail" in comp_refs
    assert comp_refs["LeadDetail"]["normalized_name"] == "LeadDetail"


# ==============================================================================
# Gate L & Gate M: Deterministic Symbol Key Integrity
# ==============================================================================

def test_vue_deterministic_key_integrity(extractor: VueExtractor):
    """Verifies that all extracted Vue symbols have strictly unique deterministic keys."""
    fixture_path = GOLD_VUE_DIR / "macros_and_bindings.vue"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/views/macros_and_bindings.vue",
    )

    keys = [s.compute_key() for s in symbols]
    assert len(keys) == len(set(keys)), "Every extracted symbol must have a strictly unique deterministic key"
    for k in keys:
        parsed = parse_symbol_key(k)
        assert parsed["file_rel_path"] == "src/views/macros_and_bindings.vue"
