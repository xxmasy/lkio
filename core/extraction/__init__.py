"""LKIO Code Intelligence Symbol Extraction Package
"""

from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_symbol_key,
    canonicalize_java_signature,
    canonicalize_ts_signature,
    compute_signature_discriminator,
    normalize_rel_path,
)

__all__ = [
    "SymbolCandidate",
    "build_symbol_key",
    "canonicalize_ts_signature",
    "canonicalize_java_signature",
    "compute_signature_discriminator",
    "normalize_rel_path",
    "EMPTY_SIGNATURE_DISCRIMINATOR",
]
