"""LKIO Code Intelligence Symbol Extraction Package
"""

from core.extraction.dto import SymbolCandidate
from core.extraction.java import JavaExtractor
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_symbol_key,
    compute_signature_discriminator,
    normalize_rel_path,
    normalize_signature,
)
from core.extraction.orchestrator import SymbolExtractionOrchestrator
from core.extraction.typescript import TypeScriptExtractor
from core.extraction.vue import VueExtractor

__all__ = [
    "SymbolCandidate",
    "SymbolExtractionOrchestrator",
    "TypeScriptExtractor",
    "JavaExtractor",
    "VueExtractor",
    "build_symbol_key",
    "compute_signature_discriminator",
    "normalize_signature",
    "normalize_rel_path",
    "EMPTY_SIGNATURE_DISCRIMINATOR",
]
