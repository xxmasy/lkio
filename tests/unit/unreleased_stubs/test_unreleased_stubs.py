"""[UNRELEASED / NOT ACCEPTED DRAFT STUBS]
Quarantined early prototype tests for Java, Vue SFC, and multi-language Orchestration.
STRICTLY EXCLUDED from B-03 Acceptance Gate (B-03-AUDIT-01).
B-04 (Java) and B-05 (Vue) will be planned, implemented, and accepted in their respective milestones.
"""

from pathlib import Path
import pytest
from core.extraction.java import JavaExtractor
from core.extraction.normalizer import parse_symbol_key
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.extraction.typescript import TypeScriptExtractor
from core.extraction.vue import VueExtractor
from core.parsing.models import SymbolType

GOLD_DIR = Path(__file__).resolve().parent.parent.parent / "gold" / "mvp2" / "symbols"


def test_typescript_extractor_gold():
    fixture_path = GOLD_DIR / "sample_ts.ts"
    code = fixture_path.read_bytes()
    extractor = TypeScriptExtractor()
    symbols = extractor.extract(code, str(fixture_path), "src/sample_ts.ts", "typescript")

    sym_map = {s.name: s for s in symbols}

    # 1. Interface
    assert "UserProfile" in sym_map
    assert sym_map["UserProfile"].symbol_type == SymbolType.INTERFACE.value
    assert sym_map["UserProfile"].base_symbol_type == SymbolType.INTERFACE.value

    # 2. Type Alias
    assert "UserRole" in sym_map
    assert sym_map["UserRole"].symbol_type == SymbolType.TYPE.value
    assert sym_map["UserRole"].base_symbol_type == SymbolType.TYPE.value

    # 3. Enum
    assert "StatusEnum" in sym_map
    assert sym_map["StatusEnum"].symbol_type == SymbolType.ENUM.value
    assert sym_map["StatusEnum"].base_symbol_type == SymbolType.ENUM.value

    # 4. Hook (Lock 2: base_symbol_type = FUNCTION, classification = name_prefix_rule_v1)
    assert "useUserProfile" in sym_map
    hook = sym_map["useUserProfile"]
    assert hook.symbol_type == SymbolType.HOOK.value
    assert hook.base_symbol_type == SymbolType.FUNCTION.value
    assert hook.classification_method == "name_prefix_rule_v1"
    assert hook.is_exported is True

    # 5. Arrow function in variable (Lock 2 & Section 9: base_symbol_type = VARIABLE)
    assert "fetchUsers" in sym_map
    fn = sym_map["fetchUsers"]
    assert fn.symbol_type == SymbolType.VARIABLE.value
    assert fn.base_symbol_type == SymbolType.VARIABLE.value
    assert fn.metadata["function_kind"] == "arrow"

    # 6. Class and Members (Lock 5: :: delimiter)
    assert "UserService" in sym_map
    cls_sym = sym_map["UserService"]
    assert cls_sym.symbol_type == SymbolType.CLASS.value

    qname_map = {s.qualified_name: s for s in symbols}
    assert "UserService::endpoint" in qname_map
    assert qname_map["UserService::endpoint"].symbol_type == SymbolType.FIELD.value

    assert "UserService::getUser" in qname_map
    assert qname_map["UserService::getUser"].symbol_type == SymbolType.METHOD.value


def test_tsx_extractor_gold():
    fixture_path = GOLD_DIR / "sample_tsx.tsx"
    code = fixture_path.read_bytes()
    extractor = TypeScriptExtractor()
    symbols = extractor.extract(code, str(fixture_path), "src/sample_tsx.tsx", "tsx")

    sym_map = {s.name: s for s in symbols}

    # Hook
    assert "useCardCounter" in sym_map
    assert sym_map["useCardCounter"].symbol_type == SymbolType.HOOK.value
    assert sym_map["useCardCounter"].base_symbol_type == SymbolType.FUNCTION.value
    assert sym_map["useCardCounter"].classification_method == "name_prefix_rule_v1"

    # React Component (Lock 2 & Section 9: arrow function -> base_symbol_type = VARIABLE, classification = jsx_function_component_v1)
    assert "StatsCard" in sym_map
    comp = sym_map["StatsCard"]
    assert comp.symbol_type == SymbolType.COMPONENT.value
    assert comp.base_symbol_type == SymbolType.VARIABLE.value
    assert comp.classification_method == "jsx_function_component_v1"


def test_java_extractor_gold():
    fixture_path = GOLD_DIR / "sample_java.java"
    code = fixture_path.read_bytes()
    extractor = JavaExtractor()
    symbols = extractor.extract(code, str(fixture_path), "src/main/java/com/example/crm/LeadController.java")

    sym_map = {s.name: s for s in symbols}
    qname_map = {s.qualified_name: s for s in symbols}

    # 1. Enum
    assert "LeadState" in sym_map
    assert sym_map["LeadState"].symbol_type == SymbolType.ENUM.value

    # 2. Annotation Definition (@interface Foo) - Lock 1
    assert "AuditLog" in sym_map
    ann_def = sym_map["AuditLog"]
    assert ann_def.symbol_type == SymbolType.ANNOTATION.value
    assert ann_def.base_symbol_type == SymbolType.ANNOTATION.value

    # 3. Class and its Annotation usages (Lock 1b: stored as metadata)
    assert "LeadController" in sym_map
    ctrl = sym_map["LeadController"]
    assert ctrl.symbol_type == SymbolType.CLASS.value
    ann_names = [a["name"] for a in ctrl.annotations]
    assert "RestController" in ann_names
    assert "RequestMapping" in ann_names

    # 4. Field with Annotation
    assert "LeadController::leadService" in qname_map
    fld = qname_map["LeadController::leadService"]
    assert fld.symbol_type == SymbolType.FIELD.value
    assert any(a["name"] == "Autowired" for a in fld.annotations)

    # 5. Methods and Overloading
    assert "LeadController::getLeadById" in qname_map
    m1 = qname_map["LeadController::getLeadById"]
    assert m1.symbol_type == SymbolType.METHOD.value
    assert any(a["name"] == "GetMapping" for a in m1.annotations)

    assert "LeadController::getLeadByCode" in qname_map
    m2 = qname_map["LeadController::getLeadByCode"]
    assert m2.symbol_type == SymbolType.METHOD.value

    # Method signatures and discriminators must distinguish overloads
    assert m1.signature != m2.signature
    assert m1.signature_discriminator != m2.signature_discriminator


def test_vue_extractor_gold():
    fixture_path = GOLD_DIR / "sample_vue.vue"
    code = fixture_path.read_bytes()
    extractor = VueExtractor()
    symbols = extractor.extract(code, str(fixture_path), "src/views/sample_vue.vue")

    qname_map = {s.qualified_name: s for s in symbols}

    # 1. Component Symbol
    assert "sample_vue" in qname_map
    comp = qname_map["sample_vue"]
    assert comp.symbol_type == SymbolType.COMPONENT.value
    assert comp.base_symbol_type == SymbolType.VARIABLE.value
    assert comp.classification_method == "vue_sfc_rule"

    # 2. Inner script Hook
    assert "sample_vue.useLeadViewHook" in qname_map
    hook = qname_map["sample_vue.useLeadViewHook"]
    assert hook.symbol_type == SymbolType.HOOK.value
    assert hook.base_symbol_type == SymbolType.FUNCTION.value

    # 3. Inner function with exact physical coordinates
    assert "sample_vue.handleRefresh" in qname_map
    fn = qname_map["sample_vue.handleRefresh"]
    assert fn.symbol_type == SymbolType.FUNCTION.value
    # In sample_vue.vue, handleRefresh is on line 19!
    assert fn.start_line == 19, f"Expected physical line 19, got {fn.start_line}"


def test_orchestrator_gold_suite():
    orchestrator = SymbolExtractionOrchestrator()

    fixtures = [
        ("HELLO_FE", GOLD_DIR / "sample_ts.ts", "src/sample_ts.ts"),
        ("HELLO_FE", GOLD_DIR / "sample_tsx.tsx", "src/sample_tsx.tsx"),
        ("HELLO_BE", GOLD_DIR / "sample_java.java", "src/main/java/sample_java.java"),
        ("HELLO_FE", GOLD_DIR / "sample_vue.vue", "src/views/sample_vue.vue"),
    ]

    for proj_key, fpath, rel_path in fixtures:
        code = fpath.read_bytes()
        results = orchestrator.extract_file_symbols(
            code_bytes=code,
            project_key=proj_key,
            file_path=str(fpath),
            file_rel_path=rel_path,
        )
        assert len(results) > 0

        for key, candidate in results:
            parsed = parse_symbol_key(key)
            assert parsed["project_key"] == proj_key
            assert parsed["file_rel_path"] == rel_path
            assert parsed["base_symbol_type"] == candidate.base_symbol_type
            assert parsed["qualified_name"] == candidate.qualified_name
            assert len(parsed["signature_discriminator"]) == 16
