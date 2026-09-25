"""LKIO Code Symbol Normalization and Deterministic Key Generation
Enforces Lock 3: Symbol Keys do not depend on physical line numbers,
preventing line shift invalidation while uniquely identifying symbols.
"""

import hashlib
import re
from core.parsing.models import NATIVE_SYMBOL_TYPES

# Precomputed empty signature discriminator: SHA-256("")[:16]
EMPTY_SIGNATURE_DISCRIMINATOR = "e3b0c44298fc1c14"

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_SPACES_RE = re.compile(r"\s*([,:\(\)\{\}\[\]=>;\?\&\|])\s*")


def normalize_signature(signature: str | None) -> str:
    """Normalizes a code signature by collapsing whitespace and standardizing delimiters."""
    if not signature:
        return ""
    # 1. Strip leading and trailing whitespace
    sig = signature.strip()
    if not sig:
        return ""
    # 2. Collapse internal multi-spaces and newlines into single spaces
    sig = _WHITESPACE_RE.sub(" ", sig)
    # 3. Standardize spaces around punctuation: e.g. "( a , b : string )" -> "(a,b:string)"
    sig = _PUNCT_SPACES_RE.sub(r"\1", sig)
    return sig


def compute_signature_discriminator(signature: str | None) -> str:
    """Computes a deterministic 16-hex-character discriminator for a symbol signature.

    Returns:
        16-character hex string representing SHA256(normalized_signature)[:16].
    """
    normalized = normalize_signature(signature)
    if not normalized:
        return EMPTY_SIGNATURE_DISCRIMINATOR
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def normalize_rel_path(rel_path: str) -> str:
    """Normalizes relative file path to standard forward slashes without leading/trailing slashes."""
    p = rel_path.replace("\\", "/").strip()
    while p.startswith("/"):
        p = p[1:]
    return p


def build_symbol_key(
    project_key: str,
    file_rel_path: str,
    base_symbol_type: str,
    qualified_name: str,
    signature: str | None = None,
    signature_discriminator: str | None = None,
) -> str:
    """Generates the canonical deterministic Symbol Key.

    Format:
        SYMBOL:<project_key>:<file_rel_path>:<base_symbol_type>:<qualified_name>:<signature_discriminator>

    Guarantees:
        1. 0 dependency on physical line numbers (immune to line insertions/deletions).
        2. Differentiates overloaded methods/functions in Java / TS via signature_discriminator.
        3. base_symbol_type is strictly constrained to native controlled enum.
    """
    if base_symbol_type not in NATIVE_SYMBOL_TYPES:
        raise ValueError(
            f"Invalid base_symbol_type '{base_symbol_type}' for symbol key. "
            f"Must be one of: {sorted(list(NATIVE_SYMBOL_TYPES))}"
        )

    norm_path = normalize_rel_path(file_rel_path)
    clean_qname = qualified_name.strip()

    if signature_discriminator is None:
        discriminator = compute_signature_discriminator(signature)
    else:
        discriminator = signature_discriminator.strip()

    return f"SYMBOL:{project_key.strip()}:{norm_path}:{base_symbol_type}:{clean_qname}:{discriminator}"
