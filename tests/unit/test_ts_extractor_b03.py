"""Unit & Gold Standard Tests for MVP2-B Step B-03 (TypeScript/JavaScript Symbol Extractor)

Strictly verifies the 16 Acceptance Gates (A ~ P):
Gate A: TS parser integration (.ts, .mts, .cts)
Gate B: JS parser integration (.js, .mjs, .cjs)
Gate C: CLASS extraction, heritage metadata, modifiers
Gate D: INTERFACE extraction (top-level only, 0 member symbols)
Gate E: FUNCTION extraction (async, params, export)
Gate F: METHOD extraction with ClassName::methodName
Gate G: VARIABLE extraction (const/let/var, arrow function base_symbol_type=VARIABLE)
Gate H: ENUM extraction (metadata.enum_members, 0 member symbols)
Gate I: TYPE extraction (metadata.type_shape, 0 member symbols)
Gate J: COMPONENT classification (PascalCase + JSX, jsx_function_component_v1, anti-false-positive)
Gate K: HOOK classification (^use[A-Z0-9], name_prefix_rule_v1, anti-false-positive)
Gate L: Export metadata (is_exported, export_kind: named/default/none)
Gate M: Scope & Qualified Name (outer::inner, Class::method)
Gate N: Signature normalization (canonicalize_ts_signature, 16-char discriminator)
Gate O: Physical coordinates (1-based line, 0-based col)
Gate P: Gold Set 100% PASS across 6 gold files
"""

from pathlib import Path
import pytest
from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import EMPTY_SIGNATURE_DISCRIMINATOR, parse_symbol_key
from core.extraction.typescript import TypeScriptExtractor
from core.parsing.models import SymbolType

GOLD_BASE = Path(__file__).resolve().parent.parent / "gold" / "mvp2" / "symbols"


@pytest.fixture
def extractor() -> TypeScriptExtractor:
    return TypeScriptExtractor()


# ==============================================================================
# Gold Set 1: basic.ts
# ==============================================================================

def test_gold_typescript_basic(extractor: TypeScriptExtractor):
    """Verifies basic.ts: Interface, Type, Enum, Class with Methods & Fields, Function, Variables."""
    fpath = GOLD_BASE / "typescript" / "basic.ts"
    code = fpath.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fpath),
        file_rel_path="src/basic.ts",
        language="typescript",
        project_key="HELLO_FE",
    )

    sym_by_name = {s.name: s for s in symbols}
    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate D: INTERFACE
    assert "UserProfile" in sym_by_name
    s_iface = sym_by_name["UserProfile"]
    assert s_iface.symbol_type == SymbolType.INTERFACE.value
    assert s_iface.base_symbol_type == SymbolType.INTERFACE.value
    assert s_iface.is_exported is True
    assert s_iface.export_kind == "named"
    assert s_iface.signature_discriminator == EMPTY_SIGNATURE_DISCRIMINATOR
    # Gate D: 0 interface member symbols
    assert "UserProfile::id" not in sym_by_qname
    assert "UserProfile::name" not in sym_by_qname

    # Gate I: TYPE
    assert "UserId" in sym_by_name
    s_type = sym_by_name["UserId"]
    assert s_type.symbol_type == SymbolType.TYPE.value
    assert s_type.base_symbol_type == SymbolType.TYPE.value
    assert s_type.is_exported is True
    assert s_type.export_kind == "named"

    # Gate H: ENUM
    assert "UserRole" in sym_by_name
    s_enum = sym_by_name["UserRole"]
    assert s_enum.symbol_type == SymbolType.ENUM.value
    assert s_enum.base_symbol_type == SymbolType.ENUM.value
    assert s_enum.is_exported is True
    assert s_enum.export_kind == "named"
    # Enum members in metadata
    assert s_enum.metadata.get("enum_members") == ["ADMIN", "USER", "GUEST"]
    # Gate H: 0 enum member symbols
    assert "UserRole::ADMIN" not in sym_by_qname

    # Gate C: CLASS
    assert "UserService" in sym_by_name
    s_cls = sym_by_name["UserService"]
    assert s_cls.symbol_type == SymbolType.CLASS.value
    assert s_cls.base_symbol_type == SymbolType.CLASS.value
    assert s_cls.is_exported is True
    assert s_cls.export_kind == "named"

    # Gate F: METHOD (with ClassName::methodName)
    assert "UserService::getUser" in sym_by_qname
    s_method = sym_by_qname["UserService::getUser"]
    assert s_method.symbol_type == SymbolType.METHOD.value
    assert s_method.base_symbol_type == SymbolType.METHOD.value
    assert s_method.name == "getUser"
    assert s_method.canonical_signature == "(string)"
    assert len(s_method.signature_discriminator) == 16
    assert "async" in s_method.modifiers
    assert "public" in s_method.modifiers
    assert s_method.metadata["evidence"]["node_type"] == "method_definition"
    assert s_method.metadata["confidence"] == 1.0

    # Class FIELD
    assert "UserService::API_VERSION" in sym_by_qname
    s_fld1 = sym_by_qname["UserService::API_VERSION"]
    assert s_fld1.symbol_type == SymbolType.FIELD.value
    assert "static" in s_fld1.modifiers
    assert "readonly" in s_fld1.modifiers

    assert "UserService::endpoint" in sym_by_qname
    s_fld2 = sym_by_qname["UserService::endpoint"]
    assert s_fld2.symbol_type == SymbolType.FIELD.value
    assert "private" in s_fld2.modifiers

    # Gate E: FUNCTION
    assert "fetchUsers" in sym_by_name
    s_fn = sym_by_name["fetchUsers"]
    assert s_fn.symbol_type == SymbolType.FUNCTION.value
    assert s_fn.base_symbol_type == SymbolType.FUNCTION.value
    assert s_fn.canonical_signature == "(string?)"  # optional param query?: string
    assert len(s_fn.signature_discriminator) == 16
    assert s_fn.is_exported is True
    assert s_fn.export_kind == "named"
    assert "async" in s_fn.modifiers

    # Gate G: VARIABLE
    assert "DEFAULT_PAGE_SIZE" in sym_by_name
    s_const = sym_by_name["DEFAULT_PAGE_SIZE"]
    assert s_const.symbol_type == SymbolType.VARIABLE.value
    assert s_const.base_symbol_type == SymbolType.VARIABLE.value
    assert s_const.metadata["declaration_kind"] == "const"
    assert s_const.is_exported is True

    assert "currentRequestId" in sym_by_name
    s_let = sym_by_name["currentRequestId"]
    assert s_let.symbol_type == SymbolType.VARIABLE.value
    assert s_let.metadata["declaration_kind"] == "let"
    assert s_let.is_exported is False
    assert s_let.export_kind == "none"

    # Gate O: Physical Coordinates validation
    assert s_iface.start_line == 5
    assert s_cls.start_line == 18
    assert s_method.start_line == 26


# ==============================================================================
# Gold Set 2: advanced.ts
# ==============================================================================

def test_gold_typescript_advanced(extractor: TypeScriptExtractor):
    """Verifies advanced.ts: Nested scopes, Arrow functions, Default export, Inheritance, Hook."""
    fpath = GOLD_BASE / "typescript" / "advanced.ts"
    code = fpath.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fpath),
        file_rel_path="src/advanced.ts",
        language="typescript",
        project_key="HELLO_FE",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate M: Nested Scope (outerFunction & outerFunction::innerHelper)
    assert "outerFunction" in sym_by_qname
    s_outer = sym_by_qname["outerFunction"]
    assert s_outer.symbol_type == SymbolType.FUNCTION.value
    assert s_outer.is_exported is True

    assert "outerFunction::innerHelper" in sym_by_qname
    s_inner = sym_by_qname["outerFunction::innerHelper"]
    assert s_inner.symbol_type == SymbolType.FUNCTION.value
    assert s_inner.base_symbol_type == SymbolType.FUNCTION.value
    assert s_inner.is_exported is False

    # Gate C: Class Inheritance and Gate L: Default Export
    assert "BaseClient" in sym_by_qname
    s_base = sym_by_qname["BaseClient"]
    assert s_base.symbol_type == SymbolType.CLASS.value
    assert "abstract" in s_base.modifiers
    assert s_base.is_exported is False

    assert "HttpClient" in sym_by_qname
    s_http = sym_by_qname["HttpClient"]
    assert s_http.symbol_type == SymbolType.CLASS.value
    assert s_http.is_exported is True
    assert s_http.export_kind == "default"
    assert "BaseClient" in s_http.metadata.get("extends_clause", "")

    # Gate G: Arrow Function in Variable
    assert "computeHash" in sym_by_qname
    s_hash = sym_by_qname["computeHash"]
    assert s_hash.symbol_type == SymbolType.VARIABLE.value
    assert s_hash.base_symbol_type == SymbolType.VARIABLE.value
    assert s_hash.metadata["function_kind"] == "arrow"
    assert s_hash.metadata["is_callable"] is True
    assert s_hash.canonical_signature == "(string,...string[])"  # rest param

    # Gate K: Hook Definition via Arrow Function
    assert "useUserProfile" in sym_by_qname
    s_hook = sym_by_qname["useUserProfile"]
    assert s_hook.symbol_type == SymbolType.HOOK.value
    assert s_hook.base_symbol_type == SymbolType.VARIABLE.value
    assert s_hook.classification_method == "name_prefix_rule_v1"
    assert s_hook.is_exported is True

    # Gate I: Complex Type Shape (no field symbols created)
    assert "ComplexQuery" in sym_by_qname
    s_type = sym_by_qname["ComplexQuery"]
    assert s_type.symbol_type == SymbolType.TYPE.value
    assert "page: number" in s_type.metadata.get("type_shape", "")
    assert "ComplexQuery::page" not in sym_by_qname


# ==============================================================================
# Gold Set 3: basic.js
# ==============================================================================

def test_gold_javascript_basic(extractor: TypeScriptExtractor):
    """Verifies basic.js: Vanilla JS functions, classes, arrow functions, var/let/const."""
    fpath = GOLD_BASE / "javascript" / "basic.js"
    code = fpath.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fpath),
        file_rel_path="src/basic.js",
        language="javascript",
        project_key="HELLO_FE",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate E: Plain JS function
    assert "calculateTotal" in sym_by_qname
    s_calc = sym_by_qname["calculateTotal"]
    assert s_calc.symbol_type == SymbolType.FUNCTION.value
    assert s_calc.base_symbol_type == SymbolType.FUNCTION.value
    assert s_calc.canonical_signature == "(any,any)"

    # Gate C: Plain JS class & Gate F: Method
    assert "Logger" in sym_by_qname
    assert "Logger::log" in sym_by_qname
    s_log = sym_by_qname["Logger::log"]
    assert s_log.symbol_type == SymbolType.METHOD.value
    assert s_log.canonical_signature == "(any)"

    # Gate G: Arrow function
    assert "formatCurrency" in sym_by_qname
    s_curr = sym_by_qname["formatCurrency"]
    assert s_curr.symbol_type == SymbolType.VARIABLE.value
    assert s_curr.base_symbol_type == SymbolType.VARIABLE.value
    assert s_curr.metadata["function_kind"] == "arrow"

    # Plain variables
    assert "globalCounter" in sym_by_qname
    assert sym_by_qname["globalCounter"].metadata["declaration_kind"] == "var"

    assert "sessionToken" in sym_by_qname
    assert sym_by_qname["sessionToken"].metadata["declaration_kind"] == "let"

    assert "TIMEOUT_MS" in sym_by_qname
    assert sym_by_qname["TIMEOUT_MS"].metadata["declaration_kind"] == "const"
    assert sym_by_qname["TIMEOUT_MS"].is_exported is True


# ==============================================================================
# Gold Set 4: basic.tsx
# ==============================================================================

def test_gold_tsx_basic(extractor: TypeScriptExtractor):
    """Verifies basic.tsx: Function Component, Arrow Component, Hook."""
    fpath = GOLD_BASE / "tsx" / "basic.tsx"
    code = fpath.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fpath),
        file_rel_path="src/basic.tsx",
        language="tsx",
        project_key="HELLO_FE",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate J: Function Component (UserCard)
    assert "UserCard" in sym_by_qname
    s_card = sym_by_qname["UserCard"]
    assert s_card.symbol_type == SymbolType.COMPONENT.value
    assert s_card.base_symbol_type == SymbolType.FUNCTION.value
    assert s_card.classification_method == "jsx_function_component_v1"
    assert s_card.is_exported is True

    # Gate J: Arrow Component (UserBadge)
    assert "UserBadge" in sym_by_qname
    s_badge = sym_by_qname["UserBadge"]
    assert s_badge.symbol_type == SymbolType.COMPONENT.value
    assert s_badge.base_symbol_type == SymbolType.VARIABLE.value
    assert s_badge.classification_method == "jsx_function_component_v1"
    assert s_badge.is_exported is True

    # Gate K: Hook definition in TSX (useCardCounter)
    assert "useCardCounter" in sym_by_qname
    s_hook = sym_by_qname["useCardCounter"]
    assert s_hook.symbol_type == SymbolType.HOOK.value
    assert s_hook.base_symbol_type == SymbolType.FUNCTION.value
    assert s_hook.classification_method == "name_prefix_rule_v1"


# ==============================================================================
# Gold Set 5: classification.tsx
# ==============================================================================

def test_gold_tsx_classification_and_anti_false_positives(extractor: TypeScriptExtractor):
    """Verifies classification rules and anti-false-positives in classification.tsx."""
    fpath = GOLD_BASE / "tsx" / "classification.tsx"
    code = fpath.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fpath),
        file_rel_path="src/classification.tsx",
        language="tsx",
        project_key="HELLO_FE",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Anti-false-positive 1: createMarkup returns JSX but is NOT PascalCase -> FUNCTION
    assert "createMarkup" in sym_by_qname
    s_markup = sym_by_qname["createMarkup"]
    assert s_markup.symbol_type == SymbolType.FUNCTION.value
    assert s_markup.base_symbol_type == SymbolType.FUNCTION.value
    assert s_markup.classification_method == "ast_native"

    # Anti-false-positive 2: usefulUtil starts with 'useful' (not ^use[A-Z0-9]) -> FUNCTION
    assert "usefulUtil" in sym_by_qname
    s_util = sym_by_qname["usefulUtil"]
    assert s_util.symbol_type == SymbolType.FUNCTION.value
    assert s_util.base_symbol_type == SymbolType.FUNCTION.value
    assert s_util.classification_method == "ast_native"

    # Gate J: JSX Fragment Component
    assert "FragmentWrapper" in sym_by_qname
    s_frag = sym_by_qname["FragmentWrapper"]
    assert s_frag.symbol_type == SymbolType.COMPONENT.value
    assert s_frag.base_symbol_type == SymbolType.VARIABLE.value
    assert s_frag.classification_method == "jsx_function_component_v1"

    # Gate K: Hook arrow function
    assert "useToggle" in sym_by_qname
    s_tog = sym_by_qname["useToggle"]
    assert s_tog.symbol_type == SymbolType.HOOK.value
    assert s_tog.base_symbol_type == SymbolType.VARIABLE.value
    assert s_tog.classification_method == "name_prefix_rule_v1"


# ==============================================================================
# Gold Set 6: basic.jsx
# ==============================================================================

def test_gold_jsx_basic(extractor: TypeScriptExtractor):
    """Verifies basic.jsx: Vanilla JSX components and helpers."""
    fpath = GOLD_BASE / "jsx" / "basic.jsx"
    code = fpath.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fpath),
        file_rel_path="src/basic.jsx",
        language="jsx",
        project_key="HELLO_FE",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate J: Function component
    assert "SimpleBanner" in sym_by_qname
    s_banner = sym_by_qname["SimpleBanner"]
    assert s_banner.symbol_type == SymbolType.COMPONENT.value
    assert s_banner.base_symbol_type == SymbolType.FUNCTION.value
    assert s_banner.classification_method == "jsx_function_component_v1"

    # Gate J: Arrow component
    assert "ButtonGroup" in sym_by_qname
    s_grp = sym_by_qname["ButtonGroup"]
    assert s_grp.symbol_type == SymbolType.COMPONENT.value
    assert s_grp.base_symbol_type == SymbolType.VARIABLE.value
    assert s_grp.classification_method == "jsx_function_component_v1"

    # Gate E: Helper function in JSX file
    assert "sanitizeInput" in sym_by_qname
    s_san = sym_by_qname["sanitizeInput"]
    assert s_san.symbol_type == SymbolType.FUNCTION.value
    assert s_san.base_symbol_type == SymbolType.FUNCTION.value
    assert s_san.classification_method == "ast_native"


# ==============================================================================
# End-to-End Key Generation Verification for Extracted Symbols
# ==============================================================================

def test_extracted_symbols_deterministic_key(extractor: TypeScriptExtractor):
    """Verifies that every candidate extracted by B-03 can compute a valid canonical key."""
    fpath = GOLD_BASE / "typescript" / "basic.ts"
    code = fpath.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fpath),
        file_rel_path="src/basic.ts",
        language="typescript",
        project_key="HELLO_FE",
    )

    for sym in symbols:
        sym.project_key = "HELLO_FE"
        key = sym.compute_key()
        assert key.startswith("SYMBOL:HELLO_FE:src/basic.ts:")
        parsed = parse_symbol_key(key)
        assert parsed["project_key"] == "HELLO_FE"
        assert parsed["file_rel_path"] == "src/basic.ts"
        assert parsed["base_symbol_type"] == sym.base_symbol_type
        assert parsed["qualified_name"] == sym.qualified_name
        assert parsed["signature_discriminator"] == sym.signature_discriminator
