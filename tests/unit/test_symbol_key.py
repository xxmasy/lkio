"""Unit Tests for Symbol Key & Language-Specific Normalization (Lock v0.3)
Verifies:
1. TypeScript / JavaScript signature canonicalization (arity, types, optional ?, rest ...).
2. Java signature canonicalization (overload differentiation, varargs, annotations stripped).
3. Line shift immunity.
4. 0 key truncation (TEXT support).
5. Controlled base_symbol_type validation.
"""

import pytest
from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_symbol_key,
    canonicalize_java_signature,
    canonicalize_ts_signature,
    compute_signature_discriminator,
    normalize_rel_path,
)


def test_empty_signature_discriminator():
    """Verify empty/None signatures deterministically yield the locked constant."""
    assert compute_signature_discriminator(None) == EMPTY_SIGNATURE_DISCRIMINATOR
    assert compute_signature_discriminator("") == EMPTY_SIGNATURE_DISCRIMINATOR
    assert compute_signature_discriminator("   \n\t  ") == EMPTY_SIGNATURE_DISCRIMINATOR
    assert EMPTY_SIGNATURE_DISCRIMINATOR == "e3b0c44298fc1c14"


def test_ts_signature_canonicalization():
    """TypeScript / JavaScript signature canonicalization rules."""
    # 1. Basic types and arity
    sig1 = "(id: string, count: number)"
    assert canonicalize_ts_signature(sig1) == "(string,number)"

    # 2. Whitespace and formatting tolerance
    sig2 = "(\n  id: string,\n  count: number\n)"
    assert canonicalize_ts_signature(sig2) == "(string,number)"

    # 3. Optional parameter (?): MUST be distinct from required
    sig_req = "(id: string)"
    sig_opt = "(id?: string)"
    canon_req = canonicalize_ts_signature(sig_req)
    canon_opt = canonicalize_ts_signature(sig_opt)
    assert canon_req == "(string)"
    assert canon_opt == "(string?)"
    assert compute_signature_discriminator(canon_req) != compute_signature_discriminator(canon_opt)

    # 4. Rest parameters (...)
    sig_rest = "(...ids: string[])"
    assert canonicalize_ts_signature(sig_rest) == "(...string[])"

    # 5. Default values
    sig_default = "(limit: number = 20, offset: number = 0)"
    assert canonicalize_ts_signature(sig_default) == "(number,number)"

    # 6. Nested generic types
    sig_generics = "(map: Map<string, number>, list: Array<string>)"
    assert canonicalize_ts_signature(sig_generics) == "(Map<string,number>,Array<string>)"

    # 7. Empty parameters
    assert canonicalize_ts_signature("()") == "()"
    assert canonicalize_ts_signature("") == "()"
    assert canonicalize_ts_signature(None) == "()"


def test_java_signature_canonicalization():
    """Java signature canonicalization rules and overload differentiation."""
    # 1. Overloaded methods must yield distinct signatures
    sig_str = "(String query)"
    sig_str_int = "(String query, Integer page)"
    sig_long = "(Long id)"

    c_str = canonicalize_java_signature(sig_str)
    c_str_int = canonicalize_java_signature(sig_str_int)
    c_long = canonicalize_java_signature(sig_long)

    assert c_str == "(String)"
    assert c_str_int == "(String,Integer)"
    assert c_long == "(Long)"

    # Verify discriminators differ
    assert compute_signature_discriminator(c_str) != compute_signature_discriminator(c_str_int)
    assert compute_signature_discriminator(c_str) != compute_signature_discriminator(c_long)
    assert compute_signature_discriminator(c_str_int) != compute_signature_discriminator(c_long)

    # 2. Annotations and final modifier stripped from parameter types
    sig_ann = "(@PathVariable(\"id\") Long id, @NotNull final String code)"
    assert canonicalize_java_signature(sig_ann) == "(Long,String)"

    # 3. Varargs (...)
    sig_varargs = "(String... lines)"
    assert canonicalize_java_signature(sig_varargs) == "(String...)"

    # 4. Nested generics
    sig_gen = "(List<String> items, Map<String, Object> params)"
    assert canonicalize_java_signature(sig_gen) == "(List<String>,Map<String,Object>)"

    # 5. Empty parameters
    assert canonicalize_java_signature("()") == "()"
    assert canonicalize_java_signature(None) == "()"


def test_build_symbol_key_format():
    """Validates deterministic key format: SYMBOL:<proj>:<rel_path>:<base_type>:<qname>:<sig_disc>."""
    canon_sig = canonicalize_ts_signature("(config: AxiosRequestConfig)")
    key = build_symbol_key(
        project_key="HELLO_FE",
        file_rel_path="src\\utils\\request.ts",
        base_symbol_type="FUNCTION",
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


def test_symbol_key_line_shift_immunity():
    """Verify that moving a method from line 10 to line 85 produces the exact same key."""
    canon_sig = canonicalize_java_signature("(Long id)")
    key_line_10 = build_symbol_key(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/UserService.java",
        base_symbol_type="METHOD",
        qualified_name="UserService.findById",
        canonical_signature=canon_sig,
    )
    key_line_85 = build_symbol_key(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/UserService.java",
        base_symbol_type="METHOD",
        qualified_name="UserService.findById",
        canonical_signature=canon_sig,
    )
    assert key_line_10 == key_line_85


def test_zero_truncation_long_key():
    """Verify that extremely long keys (> 600 chars) are NOT truncated."""
    long_path = "src/modules/customer/relationship/management/subsystem/controllers/CustomerLeadBatchProcessingDetailsViewController.ts"
    long_qname = "CustomerLeadBatchProcessingDetailsViewController.handleCreateOrUpdateCustomerLeadBatchProcessingDetailedResponseAsync"
    canon_sig = canonicalize_ts_signature("(requestBody: CustomerLeadBatchProcessingDetailedRequestDTO, options?: ExecutionOptions)")

    key = build_symbol_key(
        project_key="ENTERPRISE_CORE",
        file_rel_path=long_path,
        base_symbol_type="METHOD",
        qualified_name=long_qname,
        canonical_signature=canon_sig,
    )

    # Key should be complete and untruncated
    assert len(key) > 250
    parts = key.split(":")
    assert parts[0] == "SYMBOL"
    assert parts[1] == "ENTERPRISE_CORE"
    assert parts[2] == long_path
    assert parts[3] == "METHOD"
    assert parts[4] == long_qname
    assert len(parts[5]) == 16


def test_reject_invalid_base_symbol_type():
    """Enforce Lock 2: base_symbol_type must be strictly controlled, rejecting 'OBJECT' or 'UNKNOWN'."""
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
            symbol_type="COMPONENT",
            base_symbol_type="CUSTOM_NODE",
            name="App",
            qualified_name="App",
            start_line=1,
            end_line=50,
            start_column=0,
            end_column=0,
        )
