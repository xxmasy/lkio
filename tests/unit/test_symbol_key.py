"""Unit Tests for Symbol Key & Normalization (Lock 3)
Verifies:
1. Line shift immunity.
2. Controlled base_symbol_type validation.
3. Signature normalization & discriminator stability.
4. Overloaded signatures uniqueness.
"""

import pytest
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_symbol_key,
    compute_signature_discriminator,
    normalize_rel_path,
    normalize_signature,
)


def test_empty_signature_discriminator():
    assert compute_signature_discriminator(None) == EMPTY_SIGNATURE_DISCRIMINATOR
    assert compute_signature_discriminator("") == EMPTY_SIGNATURE_DISCRIMINATOR
    assert compute_signature_discriminator("   \n\t  ") == EMPTY_SIGNATURE_DISCRIMINATOR
    assert EMPTY_SIGNATURE_DISCRIMINATOR == "e3b0c44298fc1c14"


def test_signature_normalization():
    sig1 = "( a: string ,  b: number ) : boolean"
    sig2 = "(a: string, b: number): boolean"
    sig3 = "(\n  a: string,\n  b: number\n): boolean"
    assert normalize_signature(sig1) == normalize_signature(sig2)
    assert normalize_signature(sig2) == normalize_signature(sig3)
    assert compute_signature_discriminator(sig1) == compute_signature_discriminator(sig3)


def test_build_symbol_key_format():
    key = build_symbol_key(
        project_key="HELLO_FE",
        file_rel_path="src\\utils\\request.ts",
        base_symbol_type="FUNCTION",
        qualified_name="request",
        signature="(config: AxiosRequestConfig): Promise<AxiosResponse>",
    )
    # Check normalized forward slash path and structure
    parts = key.split(":")
    assert parts[0] == "SYMBOL"
    assert parts[1] == "HELLO_FE"
    assert parts[2] == "src/utils/request.ts"
    assert parts[3] == "FUNCTION"
    assert parts[4] == "request"
    assert len(parts[5]) == 16  # discriminator


def test_symbol_key_line_shift_immunity():
    """Verify that moving a function from line 10 to line 85 produces the exact same key."""
    key_line_10 = build_symbol_key(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/UserService.java",
        base_symbol_type="METHOD",
        qualified_name="UserService.findById",
        signature="(Long id)",
    )
    key_line_85 = build_symbol_key(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/UserService.java",
        base_symbol_type="METHOD",
        qualified_name="UserService.findById",
        signature="(Long id)",
    )
    assert key_line_10 == key_line_85


def test_overloaded_methods_unique_keys():
    """Java overloaded methods must have distinct keys via signature discriminator."""
    key1 = build_symbol_key(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/Calc.java",
        base_symbol_type="METHOD",
        qualified_name="Calc.add",
        signature="(int a, int b)",
    )
    key2 = build_symbol_key(
        project_key="HELLO_BE",
        file_rel_path="src/main/java/com/example/Calc.java",
        base_symbol_type="METHOD",
        qualified_name="Calc.add",
        signature="(double a, double b)",
    )
    assert key1 != key2
    assert key1.split(":")[:5] == key2.split(":")[:5]
    assert key1.split(":")[5] != key2.split(":")[5]


def test_reject_invalid_base_symbol_type():
    """Enforce Lock 2: base_symbol_type must be strictly controlled, rejecting 'OBJECT' etc."""
    with pytest.raises(ValueError, match="Invalid base_symbol_type 'OBJECT'"):
        build_symbol_key(
            project_key="HELLO_FE",
            file_rel_path="src/App.vue",
            base_symbol_type="OBJECT",
            qualified_name="App",
        )
