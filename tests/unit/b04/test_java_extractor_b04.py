"""LKIO MVP2-B B-04 Java Symbol Extractor Unit Tests
Dedicated test suite verifying all 16 Acceptance Gates (Gate A ~ Gate P) and 4 Lock Patches:
- LOCK-JAVA-01: Record compact constructor signature derived from record components
- LOCK-JAVA-02: Receiver parameter excluded from canonical signature
- LOCK-JAVA-03: Record components recorded as CLASS metadata only (no FIELD/accessor expansion)
- LOCK-JAVA-04: Enum constant class body recursively extracted (Outer::Inner::Member)
"""

from pathlib import Path
import pytest

from core.extraction.java import JavaExtractor
from core.extraction.normalizer import parse_symbol_key
from core.parsing.models import SymbolType

GOLD_JAVA_DIR = Path(__file__).resolve().parent.parent.parent / "gold" / "mvp2" / "symbols" / "java"


@pytest.fixture
def extractor() -> JavaExtractor:
    return JavaExtractor()


# ==============================================================================
# Gold Set 1: basic.java (Gate A, B, C, G, H, I, K, M, N, O)
# ==============================================================================

def test_gold_java_basic(extractor: JavaExtractor):
    """Verifies standard Spring Boot Service with fields, constructors, methods, and package."""
    fixture_path = GOLD_JAVA_DIR / "basic.java"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/main/java/com/example/crm/UserService.java",
    )

    sym_by_name = {s.name: s for s in symbols}
    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate B: Package & Unit extraction
    for s in symbols:
        assert s.metadata.get("package") == "com.example.crm", "All symbols must have package in metadata"
        assert s.metadata.get("package_qualified_name", "").startswith("com.example.crm.")
        # Evidence check (Gate O)
        assert s.metadata["confidence"] == 1.0
        assert s.metadata["extraction_method"] == "static_ast"
        assert "evidence" in s.metadata
        assert s.metadata["evidence"]["node_type"] is not None
        # Coordinates check (Gate N)
        assert s.start_line >= 1
        assert s.end_line >= s.start_line
        assert s.start_column >= 0

    # Gate C: CLASS extraction
    assert "UserService" in sym_by_qname
    cls = sym_by_qname["UserService"]
    assert cls.symbol_type == SymbolType.CLASS.value
    assert cls.base_symbol_type == SymbolType.CLASS.value
    assert cls.is_exported is True
    assert cls.export_kind == "public"
    # Gate K: Annotation usage metadata
    assert any(a["name"] == "Service" for a in cls.annotations)

    # Gate I: Multi-declarator field splitting
    assert "UserService::userRepository" in sym_by_qname
    f1 = sym_by_qname["UserService::userRepository"]
    assert f1.symbol_type == SymbolType.FIELD.value
    assert f1.base_symbol_type == SymbolType.FIELD.value
    assert f1.metadata["field_type"] == "UserRepository"
    assert "private" in f1.modifiers
    assert "final" in f1.modifiers

    # Both retries and timeout must be extracted as separate FIELD symbols
    assert "UserService::retries" in sym_by_qname
    assert "UserService::timeout" in sym_by_qname
    f_retries = sym_by_qname["UserService::retries"]
    f_timeout = sym_by_qname["UserService::timeout"]
    assert f_retries.symbol_type == SymbolType.FIELD.value
    assert f_timeout.symbol_type == SymbolType.FIELD.value
    assert f_retries.metadata["field_type"] == "int"
    assert f_timeout.metadata["field_type"] == "int"
    assert f_retries.metadata["initial_value"] == "3"
    assert f_timeout.metadata["initial_value"] == "5000"

    # Gate H: Constructor extraction
    assert "UserService::<init>" in sym_by_qname
    ctor = sym_by_qname["UserService::<init>"]
    assert ctor.symbol_type == SymbolType.METHOD.value
    assert ctor.base_symbol_type == SymbolType.METHOD.value
    assert ctor.metadata["method_kind"] == "CONSTRUCTOR"
    assert ctor.metadata["raw_name"] == "UserService"
    assert ctor.canonical_signature == "(UserRepository)"

    # Gate G: METHOD extraction
    assert "UserService::findAll" in sym_by_qname
    m_find_all = sym_by_qname["UserService::findAll"]
    assert m_find_all.symbol_type == SymbolType.METHOD.value
    assert m_find_all.metadata["return_type"] == "List<UserDTO>"
    assert m_find_all.canonical_signature == "()"

    assert "UserService::findById" in sym_by_qname
    m_find_id = sym_by_qname["UserService::findById"]
    assert m_find_id.symbol_type == SymbolType.METHOD.value
    assert m_find_id.metadata["return_type"] == "Optional<UserDTO>"
    assert m_find_id.canonical_signature == "(Long)"

    assert "UserService::helper" in sym_by_qname
    m_helper = sym_by_qname["UserService::helper"]
    assert m_helper.export_kind == "private"
    assert m_helper.is_exported is False


# ==============================================================================
# Gold Set 2: overload.java (Gate G, H, L, LOCK-JAVA-02)
# ==============================================================================

def test_gold_java_overload(extractor: JavaExtractor):
    """Verifies method/constructor overloading and receiver parameter stripping."""
    fixture_path = GOLD_JAVA_DIR / "overload.java"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/main/java/com/example/crm/OverloadService.java",
    )

    # 1. Constructor Overloading (3 levels: (), (String), (String,int))
    ctors = [s for s in symbols if s.name == "<init>" and s.metadata.get("method_kind") == "CONSTRUCTOR"]
    assert len(ctors) == 3, "Must extract exactly 3 overloaded constructors"

    ctor_sigs = {c.canonical_signature for c in ctors}
    assert ctor_sigs == {"()", "(String)", "(String,int)"}

    # Gate L: Constructor Keys must all be distinct
    ctor_keys = {c.compute_key() for c in ctors}
    assert len(ctor_keys) == 3, "Overloaded constructors must have distinct Symbol Keys"
    for k in ctor_keys:
        parsed = parse_symbol_key(k)
        assert parsed["qualified_name"] == "OverloadService::<init>"
        assert parsed["base_symbol_type"] == "METHOD"

    # 2. Method Overloading (5 levels of process)
    process_methods = [s for s in symbols if s.name == "process"]
    assert len(process_methods) == 5, "Must extract exactly 5 overloaded process methods"

    process_sigs = {m.canonical_signature for m in process_methods}
    assert process_sigs == {
        "()",
        "(String)",
        "(String,int)",
        "(List<String>)",
        "(String...)",
    }

    # Gate L: All 5 process methods must generate distinct Symbol Keys
    process_keys = {m.compute_key() for m in process_methods}
    assert len(process_keys) == 5, "All 5 overloaded method keys must be unique"

    # 3. LOCK-JAVA-02: Receiver Parameter Stripping
    inspect_methods = [s for s in symbols if s.name == "inspect"]
    assert len(inspect_methods) == 1
    inspect_m = inspect_methods[0]
    assert inspect_m.canonical_signature == "(String)", "Receiver parameter 'OverloadService this' must NOT enter canonical signature"
    assert "receiver_parameter" in inspect_m.metadata
    assert inspect_m.metadata["receiver_parameter"]["type"] == "OverloadService"
    assert inspect_m.metadata["receiver_parameter"]["name"] == "this"


# ==============================================================================
# Gold Set 3: annotations.java (Gate F, K, Lock 1, Lock 1b)
# ==============================================================================

def test_gold_java_annotations(extractor: JavaExtractor):
    """Verifies @interface annotation definition vs Spring annotation usages."""
    fixture_path = GOLD_JAVA_DIR / "annotations.java"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/main/java/com/example/crm/UserController.java",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # Gate F & Lock 1: Annotation Definition is a native ANNOTATION symbol
    assert "OperLog" in sym_by_qname
    ann_def = sym_by_qname["OperLog"]
    assert ann_def.symbol_type == SymbolType.ANNOTATION.value
    assert ann_def.base_symbol_type == SymbolType.ANNOTATION.value
    assert any(a["name"] == "Documented" for a in ann_def.annotations)
    assert any(a["name"] == "Retention" for a in ann_def.annotations)

    elements = {e["name"]: e for e in ann_def.metadata.get("elements", [])}
    assert "module" in elements
    assert elements["module"]["type"] == "String"
    assert "saveParam" in elements
    assert elements["saveParam"]["type"] == "boolean"

    # Lock 1b & Gate K: Annotation Usages do NOT generate independent symbol nodes
    ann_symbols = [s for s in symbols if s.name in ["RestController", "RequestMapping", "PostMapping", "GetMapping", "Autowired"]]
    assert len(ann_symbols) == 0, "Annotation usages MUST NEVER generate independent Symbol nodes"

    # Class annotations
    assert "UserController" in sym_by_qname
    ctrl = sym_by_qname["UserController"]
    assert ctrl.symbol_type == SymbolType.CLASS.value
    ctrl_ann_names = [a["name"] for a in ctrl.annotations]
    assert "RestController" in ctrl_ann_names
    assert "RequestMapping" in ctrl_ann_names

    # Method annotations & parameter annotations
    assert "UserController::createUser" in sym_by_qname
    m_create = sym_by_qname["UserController::createUser"]
    m_ann_names = [a["name"] for a in m_create.annotations]
    assert "PostMapping" in m_ann_names
    assert "OperLog" in m_ann_names

    params = m_create.metadata.get("parameters", [])
    assert len(params) == 1
    dto_param = params[0]
    assert dto_param["name"] == "dto"
    assert dto_param["type"] == "UserDTO"
    dto_anns = [a["name"] for a in dto_param.get("annotations", [])]
    assert "RequestBody" in dto_anns
    assert "Valid" in dto_anns

    # Method GetMapping with PathVariable
    assert "UserController::getUserById" in sym_by_qname
    m_get = sym_by_qname["UserController::getUserById"]
    id_param = m_get.metadata["parameters"][0]
    assert id_param["name"] == "id"
    assert id_param["type"] == "Long"
    assert any(a["name"] == "PathVariable" for a in id_param.get("annotations", []))


# ==============================================================================
# Gold Set 4: enums_interfaces.java (Gate D, E, H, J, LOCK-JAVA-01, 03, 04)
# ==============================================================================

def test_gold_java_enums_interfaces(extractor: JavaExtractor):
    """Verifies Enums, Records, Interfaces, Compact Constructors, and Nested Scopes."""
    fixture_path = GOLD_JAVA_DIR / "enums_interfaces.java"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/main/java/com/example/crm/OrderEntities.java",
    )

    sym_by_qname = {s.qualified_name: s for s in symbols}

    # 1. Gate E: Enum Extraction
    assert "OrderStatus" in sym_by_qname
    status_enum = sym_by_qname["OrderStatus"]
    assert status_enum.symbol_type == SymbolType.ENUM.value
    assert status_enum.base_symbol_type == SymbolType.ENUM.value

    enum_consts = status_enum.metadata.get("enum_constants", [])
    const_names = [c["name"] for c in enum_consts]
    assert "INIT" in const_names
    assert "PAID" in const_names
    assert "RUNNING" in const_names

    # LOCK-JAVA-04: Enum Constant Body Recursion
    assert "OrderStatus::RUNNING::label" in sym_by_qname
    running_label = sym_by_qname["OrderStatus::RUNNING::label"]
    assert running_label.symbol_type == SymbolType.METHOD.value
    assert running_label.base_symbol_type == SymbolType.METHOD.value
    assert running_label.canonical_signature == "()"

    # Enum members (constructors, fields, methods)
    assert "OrderStatus::code" in sym_by_qname
    assert "OrderStatus::desc" in sym_by_qname
    assert "OrderStatus::label" in sym_by_qname
    assert "OrderStatus::<init>" in sym_by_qname

    # 2. LOCK-JAVA-01 & LOCK-JAVA-03: Record Class & Compact Constructor
    assert "OrderRecord" in sym_by_qname
    rec = sym_by_qname["OrderRecord"]
    assert rec.symbol_type == SymbolType.CLASS.value
    assert rec.metadata.get("class_kind") == "record"

    # LOCK-JAVA-03: Record components recorded in metadata ONLY
    rec_comps = rec.metadata.get("record_components", [])
    assert len(rec_comps) == 2
    comp_map = {c["name"]: c["type"] for c in rec_comps}
    assert comp_map == {"id": "String", "amount": "Long"}

    # Must NOT generate FIELD id or FIELD amount
    assert "OrderRecord::id" not in sym_by_qname
    assert "OrderRecord::amount" not in sym_by_qname

    # LOCK-JAVA-01: Compact constructor signature derived from components
    assert "OrderRecord::<init>" in sym_by_qname
    rec_ctor = sym_by_qname["OrderRecord::<init>"]
    assert rec_ctor.symbol_type == SymbolType.METHOD.value
    assert rec_ctor.metadata["method_kind"] == "CONSTRUCTOR"
    assert rec_ctor.canonical_signature == "(String,Long)", "Compact constructor signature must be derived from record components, NOT ()"
    assert rec_ctor.metadata["constructor_form"] == "compact"

    # 3. Gate D: Interface Extraction
    assert "OrderApi" in sym_by_qname
    api = sym_by_qname["OrderApi"]
    assert api.symbol_type == SymbolType.INTERFACE.value
    assert api.base_symbol_type == SymbolType.INTERFACE.value
    assert "Closeable" in api.metadata.get("extends_interfaces", "")

    # Interface Constant (Gate I)
    assert "OrderApi::API_VERSION" in sym_by_qname
    const_sym = sym_by_qname["OrderApi::API_VERSION"]
    assert const_sym.symbol_type == SymbolType.FIELD.value
    assert "public" in const_sym.modifiers
    assert "static" in const_sym.modifiers
    assert "final" in const_sym.modifiers

    # Interface Methods (abstract, default, static)
    assert "OrderApi::findOrder" in sym_by_qname
    m_find = sym_by_qname["OrderApi::findOrder"]
    assert m_find.canonical_signature == "(String)"

    assert "OrderApi::isActive" in sym_by_qname
    m_active = sym_by_qname["OrderApi::isActive"]
    assert "default" in m_active.modifiers

    assert "OrderApi::printVersion" in sym_by_qname
    m_print = sym_by_qname["OrderApi::printVersion"]
    assert "static" in m_print.modifiers

    # 4. Gate J: Nested Scopes
    assert "OrderContainer" in sym_by_qname
    assert "OrderContainer::Builder" in sym_by_qname
    builder = sym_by_qname["OrderContainer::Builder"]
    assert builder.symbol_type == SymbolType.CLASS.value
    assert "static" in builder.modifiers

    assert "OrderContainer::Builder::orderId" in sym_by_qname
    # Both field and method exist under Builder
    builder_syms = [s for s in symbols if s.qualified_name.startswith("OrderContainer::Builder")]
    assert len(builder_syms) >= 3  # Class, field, method, constructor


# ==============================================================================
# Gate L & Criterion 3: Java Overload Key Integrity Test
# ==============================================================================

def test_java_overload_key_integrity(extractor: JavaExtractor):
    """Explicitly verifies Gate L: overloaded methods generate collision-free deterministic keys."""
    fixture_path = GOLD_JAVA_DIR / "overload.java"
    code = fixture_path.read_bytes()
    symbols = extractor.extract(
        code_bytes=code,
        file_path=str(fixture_path),
        file_rel_path="src/main/java/com/example/crm/OverloadService.java",
    )

    keys = [s.compute_key() for s in symbols]
    assert len(keys) == len(set(keys)), "Every extracted symbol must have a strictly unique deterministic key"
