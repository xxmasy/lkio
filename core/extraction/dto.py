"""LKIO Code Symbol Extraction DTOs
Defines data structures for extracted code symbols decoupled from AST and DB layers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from core.parsing.models import (
    CLASSIFICATION_TYPES,
    NATIVE_SYMBOL_TYPES,
    LanguageType,
    SymbolType,
)


@dataclass
class SymbolCandidate:
    """Decoupled candidate representation of an extracted code symbol."""
    file_path: str
    file_rel_path: str
    name: str
    qualified_name: str
    symbol_type: str  # Native (e.g. FUNCTION, CLASS) or Rule Classification (COMPONENT, HOOK)
    base_symbol_type: str  # Must strictly be in NATIVE_SYMBOL_TYPES
    start_line: int  # 1-based physical line number
    end_line: int    # 1-based physical line number
    start_column: int  # 0-based column
    end_column: int    # 0-based column
    signature: str | None = None
    signature_discriminator: str = "e3b0c44298fc1c14"
    language: str = "unknown"
    parser_version: str = "tree-sitter-0.25.2"
    extractor_version: str = "0.2.0"
    classification_method: str = "ast_native"  # ast_native, name_prefix_rule, vue_sfc_rule, jsx_return_rule
    modifiers: list[str] = field(default_factory=list)
    is_exported: bool = False
    annotations: list[dict[str, Any]] = field(default_factory=list)
    docstring: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Enforce Lock 2: base_symbol_type must strictly come from controlled native enum
        if self.base_symbol_type not in NATIVE_SYMBOL_TYPES:
            raise ValueError(
                f"Invalid base_symbol_type '{self.base_symbol_type}'. "
                f"Must strictly be one of: {sorted(list(NATIVE_SYMBOL_TYPES))}"
            )
        # Ensure forward slashes in relative path
        self.file_rel_path = self.file_rel_path.replace("\\", "/")
