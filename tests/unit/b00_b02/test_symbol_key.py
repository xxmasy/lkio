"""Unit Tests for Symbol Key & Language-Specific Normalization (Lock v0.3)
Strictly verifies the 5 User Criteria and identity system invariants:
1. Criterion 1: Line Shift Invariance (same symbol + arbitrary line insertion -> Key identical)
2. Criterion 2: Lexical Scope Isolation (same name + different scope chain -> Key distinct)
3. Criterion 3: Java Overload Differentiation (same method name + different params -> Key distinct)
4. Criterion 4: TypeScript Optional & Rest Differentiation ((string) vs (string?) vs (...string[]) -> Key distinct)
5. Criterion 5: Vue SFC Multi-Script Block Isolation (script::foo vs script_setup::foo -> Key distinct)

Plus supporting guarantees:
- Controlled base_symbol_type enforcement (Lock 2)
- Zero key truncation with TEXT column support
- Deterministic empty signature discriminator constant
"""

import pytest
from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_qualified_name,
    build_symbol_key,
    canonicalize_java_signature,
    canonicalize_ts_signature,
    compute_signature_discriminator,
    normalize_rel_path,
    parse_symbol_key,
)
from core.parsing.models import SymbolType


# ==============================================================================
# 5 Core Invariance & Isolation Criteria Tests
# ==============================================================================

def test_criterion_1_line_shift_invariance():
    """Criterion 1: 同一符号 + 插入任意行 ➔ Key 绝对不变 (Line Shift Invariance).
    
    Verifies Lock 3: Symbol Keys MUST NOT depend on physical line numbers.
    Moving a function or method from line 10 to line 250 must result in the EXACT same key.
    """
    canon_sig = canonicalize_ts_signature("(userId: string)")
    discriminator = compute_signature_discriminator(canon_sig)

    # Symbol at line 10
    cand_line_10 = SymbolCandidate(
        project_key="HELLO_FE",
        file_rel_path="src/api/user.ts",
        symbol_type=SymbolType.FUNCTION.value,
        base_symbol_type=SymbolType.FUNCTION.value,
        name="getUserProfile",
        qualified_name="getUserProfile",
        start_line=10,
        end_line=25,
        start_column=0,
        end_column=1,
        signature="(userId: string)",
        canonical_signature=canon_sig,
        signature_discriminator=discriminator,
    )

    # The exact same symbol after 200 lines inserted above it (now at line 210)
    cand_line_210 = SymbolCandidate(
        project_key="HELLO_FE",
        file_rel_path="src/api/user.ts",
        symbol_type=SymbolType.FUNCTION.value,
        base_symbol_type=SymbolType.FUNCTION.value,
        name="getUserProfile",
        qualified_name="getUserProfile",
        start_line=210,
        end_line=225,
        start_column=0,
        end_column=1,
        signature="(userId: string)",
        canonical_signature=canon_sig,
        signature_discriminator=discriminator,
    )

    key_10 = cand_line_10.compute_key()
    key_210 = cand_line_210.compute_key()

    assert key_10 == key_210, "Symbol Key must be invariant to line shifts!"
    assert ":10:" not in key_10, "Line numbers must never leak into Symbol Key!"
    assert ":210:" not in key_210, "Line numbers must never leak into Symbol Key!"


def test_criterion_2_lexical_scope_isolation():
    """Criterion 2: 同名符号 + 不同词法作用域 ➔ Key 绝对不同 (Lexical Scope Isolation).
    
    Verifies Lock 5: In the same file, symbols with the exact same name in different
    lexical scopes must have distinct qualified_name and therefore distinct Keys:
    - top-level: 'loadData'
    - nested: 'outer::loadData'
    - class method: 'DataLoader::loadData'
    """
    proj = "HELLO_FE"
    rel_path = "src/services/data.ts"
    sym_name = "loadData"
    canon_sig = "()"
    disc = compute_signature_discriminator(canon_sig)

    # 1. Top-level function
    qname_top = build_qualified_name(sym_name)
    key_top = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname_top,
        signature_discriminator=disc,
    )

    # 2. Nested function inside outer()
    qname_nested = build_qualified_name(sym_name, scope_chain=["outer"])
    key_nested = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname_nested,
        signature_discriminator=disc,
    )

    # 3. Method inside class DataLoader
    qname_class = build_qualified_name(sym_name, scope_chain=["DataLoader"])
    key_class = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name=qname_class,
        signature_discriminator=disc,
    )

    # 4. Method inside inner class DataLoader.InnerHelper
    qname_inner_class = build_qualified_name(sym_name, scope_chain=["DataLoader", "InnerHelper"])
    key_inner_class = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name=qname_inner_class,
        signature_discriminator=disc,
    )

    assert qname_top == "loadData"
    assert qname_nested == "outer::loadData"
    assert qname_class == "DataLoader::loadData"
    assert qname_inner_class == "DataLoader::InnerHelper::loadData"

    keys = {key_top, key_nested, key_class, key_inner_class}
    assert len(keys) == 4, f"All 4 scoped keys must be strictly unique! Keys: {keys}"


def test_criterion_3_java_overload_differentiation():
    """Criterion 3: Java Overload ➔ Key 绝对不同 (Java Overload Differentiation).
    
    Verifies Lock 4: Overloaded Java methods sharing class and method name must be
    differentiated by their canonical parameter signature and discriminator:
    - list(String query) -> (String)
    - list(String query, Integer page) -> (String,Integer)
    - list(Long id) -> (Long)
    - list() -> ()
    """
    proj = "HELLO_BE"
    rel_path = "src/main/java/com/example/crm/LeadController.java"
    qname = "LeadController::list"

    sig_str = canonicalize_java_signature("(String query)")
    sig_str_int = canonicalize_java_signature("(String query, Integer page)")
    sig_long = canonicalize_java_signature("(Long id)")
    sig_empty = canonicalize_java_signature("()")

    assert sig_str == "(String)"
    assert sig_str_int == "(String,Integer)"
    assert sig_long == "(Long)"
    assert sig_empty == "()"

    key_str = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name=qname,
        canonical_signature=sig_str,
    )
    key_str_int = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name=qname,
        canonical_signature=sig_str_int,
    )
    key_long = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name=qname,
        canonical_signature=sig_long,
    )
    key_empty = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name=qname,
        canonical_signature=sig_empty,
    )

    overload_keys = {key_str, key_str_int, key_long, key_empty}
    assert len(overload_keys) == 4, f"All 4 Java overload keys must be distinct! Keys: {overload_keys}"


def test_criterion_4_ts_optional_and_rest_differentiation():
    """Criterion 4: TS Optional / Rest ➔ Key 绝对不同 (TypeScript Optional & Rest Differentiation).
    
    Verifies Lock 4: TypeScript parameter forms must NOT be arbitrarily flattened:
    - required: (id: string) -> (string)
    - optional: (id?: string) -> (string?)
    - rest: (...ids: string[]) -> (...string[])
    - zero-arg: () -> ()
    """
    proj = "HELLO_FE"
    rel_path = "src/services/batch.ts"
    qname = "batchFetch"

    c_req = canonicalize_ts_signature("(id: string)")
    c_opt = canonicalize_ts_signature("(id?: string)")
    c_rest = canonicalize_ts_signature("(...ids: string[])")
    c_empty = canonicalize_ts_signature("()")

    assert c_req == "(string)"
    assert c_opt == "(string?)"
    assert c_rest == "(...string[])"
    assert c_empty == "()"

    key_req = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname,
        canonical_signature=c_req,
    )
    key_opt = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname,
        canonical_signature=c_opt,
    )
    key_rest = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname,
        canonical_signature=c_rest,
    )
    key_empty = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname,
        canonical_signature=c_empty,
    )

    ts_keys = {key_req, key_opt, key_rest, key_empty}
    assert len(ts_keys) == 4, f"All 4 TypeScript variant keys must be distinct! Keys: {ts_keys}"


def test_criterion_5_vue_script_block_isolation():
    """Criterion 5: 不同 script block ➔ Key 绝对不同 (Vue Multi-Script Block Isolation).
    
    Verifies Lock 5: In Vue SFC files containing both <script> and <script setup>,
    symbols defined in different blocks must be disambiguated by their block scope:
    - <script> -> 'script::foo'
    - <script setup> -> 'script_setup::foo'
    """
    proj = "HELLO_FE"
    rel_path = "src/views/MultiScriptView.vue"
    sym_name = "initComponent"

    qname_plain_script = build_qualified_name(sym_name, block_scope="script")
    qname_setup_script = build_qualified_name(sym_name, block_scope="script_setup")

    assert qname_plain_script == "script::initComponent"
    assert qname_setup_script == "script_setup::initComponent"

    key_plain = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname_plain_script,
    )
    key_setup = build_symbol_key(
        project_key=proj,
        file_rel_path=rel_path,
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name=qname_setup_script,
    )

    assert key_plain != key_setup, "Symbols in different script blocks must have distinct keys!"
    assert ":script::initComponent:" in key_plain
    assert ":script_setup::initComponent:" in key_setup


# ==============================================================================
# Supporting Identity System Unit Tests
# ==============================================================================

def test_build_qualified_name_variations():
    """Validates scope chain handling and delimiter normalization."""
    # 1. Plain symbol
    assert build_qualified_name("simple") == "simple"

    # 2. Scope chain as list
    assert build_qualified_name("method", ["ClassA", "InnerB"]) == "ClassA::InnerB::method"

    # 3. Scope chain as dot-delimited string
    assert build_qualified_name("service", "com.example.service") == "com::example::service::service"

    # 4. Scope chain with existing ::
    assert build_qualified_name("func", "Module::SubModule") == "Module::SubModule::func"

    # 5. Block scope combined with scope chain
    assert (
        build_qualified_name("helper", scope_chain=["HelperClass"], block_scope="script_setup")
        == "script_setup::HelperClass::helper"
    )


def test_empty_signature_discriminator():
    """Verify empty/None signatures deterministically yield the locked constant."""
    assert compute_signature_discriminator(None) == EMPTY_SIGNATURE_DISCRIMINATOR
    assert compute_signature_discriminator("") == EMPTY_SIGNATURE_DISCRIMINATOR
    assert compute_signature_discriminator("   \n\t  ") == EMPTY_SIGNATURE_DISCRIMINATOR
    assert EMPTY_SIGNATURE_DISCRIMINATOR == "e3b0c44298fc1c14"


def test_ts_signature_canonicalization_matrix():
    """TypeScript / JavaScript signature edge case matrix."""
    # 1. Whitespace and formatting tolerance
    sig = "(\n  id: string,\n  count: number\n)"
    assert canonicalize_ts_signature(sig) == "(string,number)"

    # 2. Default values stripped
    sig_default = "(limit: number = 20, offset: number = 0)"
    assert canonicalize_ts_signature(sig_default) == "(number,number)"

    # 3. Nested generic types preserved
    sig_generics = "(map: Map<string, number>, list: Array<string>)"
    assert canonicalize_ts_signature(sig_generics) == "(Map<string,number>,Array<string>)"

    # 4. Untyped JS params treated as '?' (B-03-AUDIT-02: faithful structural fact, zero fake 'any')
    sig_untyped = "(a, b)"
    assert canonicalize_ts_signature(sig_untyped) == "(?,?)"

    # 5. Empty parameters
    assert canonicalize_ts_signature("()") == "()"
    assert canonicalize_ts_signature("") == "()"
    assert canonicalize_ts_signature(None) == "()"


def test_java_signature_canonicalization_matrix():
    """Java signature edge case matrix."""
    # 1. Annotations and final modifier stripped from parameter types
    sig_ann = "(@PathVariable(\"id\") Long id, @NotNull final String code)"
    assert canonicalize_java_signature(sig_ann) == "(Long,String)"

    # 2. Varargs (...) preserved
    sig_varargs = "(String... lines)"
    assert canonicalize_java_signature(sig_varargs) == "(String...)"

    # 3. Nested generics preserved
    sig_gen = "(List<String> items, Map<String, Object> params)"
    assert canonicalize_java_signature(sig_gen) == "(List<String>,Map<String,Object>)"

    # 4. Empty parameters
    assert canonicalize_java_signature("()") == "()"
    assert canonicalize_java_signature(None) == "()"


def test_build_symbol_key_format():
    """Validates deterministic key format: SYMBOL:<proj>:<rel_path>:<base_type>:<qname>:<sig_disc>."""
    canon_sig = canonicalize_ts_signature("(config: AxiosRequestConfig)")
    key = build_symbol_key(
        project_key="HELLO_FE",
        file_rel_path="src\\utils\\request.ts",
        base_symbol_type=SymbolType.FUNCTION.value,
        qualified_name="request",
        canonical_signature=canon_sig,
    )
    parts = key.split(":")
    assert parts[0] == "SYMBOL"
    assert parts[1] == "HELLO_FE"
    assert parts[2] == "src/utils/request.ts"
    assert parts[3] == "FUNCTION"
    assert parts[4] == "request"
    assert len(parts[5]) == 16  # SHA-256 discriminator length


def test_zero_truncation_long_key():
    """Verify that extremely long keys (> 250 chars) are NOT truncated (B-01 TEXT column)."""
    long_path = "src/modules/customer/relationship/management/subsystem/controllers/CustomerLeadBatchProcessingDetailsViewController.ts"
    long_qname = "CustomerLeadBatchProcessingDetailsViewController::handleCreateOrUpdateCustomerLeadBatchProcessingDetailedResponseAsync"
    canon_sig = canonicalize_ts_signature("(requestBody: CustomerLeadBatchProcessingDetailedRequestDTO, options?: ExecutionOptions)")

    key = build_symbol_key(
        project_key="ENTERPRISE_CORE",
        file_rel_path=long_path,
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name=long_qname,
        canonical_signature=canon_sig,
    )

    # Key should be complete and untruncated (> 250 characters)
    assert len(key) > 250

    # Parse key using canonical parser that correctly respects lexical scope '::'
    parsed = parse_symbol_key(key)
    assert parsed["project_key"] == "ENTERPRISE_CORE"
    assert parsed["file_rel_path"] == long_path
    assert parsed["base_symbol_type"] == "METHOD"
    assert parsed["qualified_name"] == long_qname
    assert len(parsed["signature_discriminator"]) == 16


def test_reject_invalid_base_symbol_type():
    """Enforce Lock 2: base_symbol_type must be strictly controlled, rejecting 'OBJECT' or 'CUSTOM_NODE'."""
    with pytest.raises(ValueError, match="Invalid base_symbol_type 'OBJECT'"):
        build_symbol_key(
            project_key="HELLO_FE",
            file_rel_path="src/App.vue",
            base_symbol_type="OBJECT",
            qualified_name="App",
        )

    with pytest.raises(ValueError, match="Invalid base_symbol_type 'CUSTOM_NODE'"):
        SymbolCandidate(
            project_key="HELLO_FE",
            file_rel_path="src/App.vue",
            symbol_type=SymbolType.COMPONENT.value,
            base_symbol_type="CUSTOM_NODE",
            name="App",
            qualified_name="App",
            start_line=1,
            end_line=50,
            start_column=0,
            end_column=0,
        )


def test_symbol_candidate_compute_key_integration():
    """Validates that SymbolCandidate.compute_key() seamlessly integrates with build_symbol_key."""
    canon_sig = canonicalize_java_signature("(Long id)")
    disc = compute_signature_discriminator(canon_sig)

    candidate = SymbolCandidate(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/crm/LeadService.java",
        symbol_type=SymbolType.METHOD.value,
        base_symbol_type=SymbolType.METHOD.value,
        name="getLead",
        qualified_name="LeadService::getLead",
        start_line=45,
        end_line=52,
        start_column=4,
        end_column=5,
        canonical_signature=canon_sig,
        signature_discriminator=disc,
    )

    expected_key = build_symbol_key(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/crm/LeadService.java",
        base_symbol_type=SymbolType.METHOD.value,
        qualified_name="LeadService::getLead",
        signature_discriminator=disc,
    )

    assert candidate.compute_key() == expected_key
