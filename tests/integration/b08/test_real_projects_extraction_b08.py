"""B-08 Layer 2 Tests: Real Project Symbol Extraction & Deterministic Identity (Gate C, D, E, F)
Validates:
- Gate C: HELLO_FE real Vue SFC and JS/TS extraction.
- Gate D: HELLO_BE real Java Spring class, method, annotation, and record extraction.
- Gate E: L2C_FE real complex Vue 3 component and TS extraction.
- Gate F: Deterministic symbol keys on real code, format correctness, and line-drift invariance.
"""

from pathlib import Path
import pytest

from core.extraction.orchestrator import SymbolExtractionOrchestrator
from tests.integration.b08.conftest import REPOS


@pytest.fixture
def orchestrator() -> SymbolExtractionOrchestrator:
    return SymbolExtractionOrchestrator()


def test_gate_c_hello_fe_real_vue_ts_extraction(orchestrator: SymbolExtractionOrchestrator):
    """Gate C: Extracts real Vue SFC and JS symbols from HELLO_FE."""
    vue_rel = "demo/phone-frontend/components/TwilioCall.vue"
    vue_path = REPOS["HELLO_FE"] / vue_rel
    assert vue_path.exists()

    res_vue = orchestrator.extract_file(vue_path.read_bytes(), "HELLO_FE", vue_rel, vue_rel)
    assert res_vue.success is True
    assert len(res_vue.symbols) >= 5

    # Check component symbol
    comp_sym = next((s for s in res_vue.symbols if s.symbol_type == "COMPONENT"), None)
    assert comp_sym is not None
    assert comp_sym.name == "TwilioCall"
    assert comp_sym.language == "vue"

    # Check setup variables
    setup_vars = [s for s in res_vue.symbols if "script_setup" in s.qualified_name]
    assert len(setup_vars) >= 2

    # Check JS extraction
    js_rel = "baseline-service.js"
    js_path = REPOS["HELLO_FE"] / js_rel
    assert js_path.exists()
    res_js = orchestrator.extract_file(js_path.read_bytes(), "HELLO_FE", js_rel, js_rel)
    assert res_js.success is True
    assert len(res_js.symbols) >= 3


def test_gate_d_hello_be_real_java_spring_extraction(orchestrator: SymbolExtractionOrchestrator):
    """Gate D: Extracts real Spring controllers, methods, annotations from HELLO_BE."""
    java_rel = "src/main/java/org/example/hahamarket/callcenter/controller/cn/CallConfigController.java"
    java_path = REPOS["HELLO_BE"] / java_rel
    assert java_path.exists()

    res = orchestrator.extract_file(java_path.read_bytes(), "HELLO_BE", java_rel, java_rel)
    assert res.success is True
    assert len(res.symbols) >= 3

    # Check class symbol
    class_sym = next((s for s in res.symbols if s.symbol_type == "CLASS"), None)
    assert class_sym is not None
    assert class_sym.name == "CallConfigController"
    assert class_sym.language == "java"

    # Check method symbol
    method_sym = next((s for s in res.symbols if s.symbol_type == "METHOD"), None)
    assert method_sym is not None
    assert method_sym.name == "getConfig"
    assert method_sym.signature_discriminator is not None
    assert len(method_sym.signature_discriminator) == 16


def test_gate_e_l2c_fe_real_complex_vue_extraction(orchestrator: SymbolExtractionOrchestrator):
    """Gate E: Extracts real complex enterprise Vue 3 components and preferences from L2C_FE."""
    vue_rel = "apps/web-antd/src/layouts/basic.vue"
    vue_path = REPOS["L2C_FE"] / vue_rel
    assert vue_path.exists()

    res = orchestrator.extract_file(vue_path.read_bytes(), "L2C_FE", vue_rel, vue_rel)
    assert res.success is True
    assert len(res.symbols) >= 10

    comp = next((s for s in res.symbols if s.symbol_type == "COMPONENT"), None)
    assert comp is not None
    assert comp.name == "basic"

    ts_rel = "apps/web-ele/src/preferences.ts"
    ts_path = REPOS["L2C_FE"] / ts_rel
    assert ts_path.exists()
    res_ts = orchestrator.extract_file(ts_path.read_bytes(), "L2C_FE", ts_rel, ts_rel)
    assert res_ts.success is True
    assert len(res_ts.symbols) >= 1


def test_gate_f_real_symbols_deterministic_key_stability(orchestrator: SymbolExtractionOrchestrator):
    """Gate F: Verifies deterministic entity key generation, structure, and line-drift invariance on real code."""
    rel = "demo/phone-frontend/components/TwilioCall.vue"
    full_path = REPOS["HELLO_FE"] / rel
    code_raw = full_path.read_bytes()

    res_1 = orchestrator.extract_file(code_raw, "HELLO_FE", rel, rel)
    assert res_1.success is True
    keys_1 = res_1.symbol_keys

    # Keys must start with standard SYMBOL prefix and contain 16-char discriminator
    for k in keys_1:
        assert k.startswith(f"SYMBOL:HELLO_FE:{rel}:")
        parts = k.split(":")
        assert len(parts) >= 6
        discriminator = parts[-1]
        assert len(discriminator) == 16

    # Simulate line-drift: inject 10 blank lines at top of code
    code_drifted = b"\n\n\n\n\n\n\n\n\n\n" + code_raw
    res_drifted = orchestrator.extract_file(code_drifted, "HELLO_FE", rel, rel)
    assert res_drifted.success is True
    keys_drifted = res_drifted.symbol_keys

    # Line drift must NOT alter entity_keys (B-02 identity invariance criteria)
    assert keys_1 == keys_drifted
