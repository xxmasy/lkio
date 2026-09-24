"""LKIO Code Intelligence Data Transfer Objects (DTO)
Decouples Tree-sitter parsers and extractors from Knowledge Core database models.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SymbolType(str, Enum):
    CLASS = "CLASS"
    INTERFACE = "INTERFACE"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    VARIABLE = "VARIABLE"
    COMPONENT = "COMPONENT"
    HOOK = "HOOK"
    ENUM = "ENUM"
    TYPE = "TYPE"


class LanguageType(str, Enum):
    TYPESCRIPT = "typescript"
    TSX = "tsx"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    VUE = "vue"
    UNKNOWN = "unknown"


@dataclass
class SymbolCandidate:
    """Decoupled representation of an extracted code symbol before persistence."""
    file_path: str
    symbol_type: str  # e.g., FUNCTION, CLASS, HOOK, COMPONENT
    name: str
    canonical_name: str
    start_line: int
    end_line: int
    start_column: int
    end_column: int
    signature: str | None = None
    language: str = "unknown"
    parser_version: str = "unknown"
    base_symbol_type: str | None = None  # Native AST fact: FUNCTION, CLASS, etc.
    classification_method: str = "ast_native"  # ast_native, name_prefix_rule, vue_sfc_rule
    modifiers: list[str] = field(default_factory=list)
    is_exported: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CallSiteCandidate:
    """A call expression observed in the AST before target resolution."""
    caller_file: str
    caller_symbol: str | None
    callee_name: str
    line: int
    column: int
    arguments_count: int
    is_member_call: bool = False
    receiver_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationCandidate:
    """A candidate code relation between symbols or files."""
    subject_key: str
    predicate: str  # defines, imports, exports, calls, extends, implements, uses, unresolved_call
    object_key: str
    confidence: float = 1.0
    extraction_method: str = "static_ast"
    evidence: dict[str, Any] = field(default_factory=dict)
    inferred: bool = False


@dataclass
class SfcBlock:
    """A structural block sliced from a Vue SFC file."""
    block_type: str  # template, script, script_setup, style
    content: str
    start_line: int
    end_line: int
    lang: str = "javascript"
    is_setup: bool = False
    is_scoped: bool = False
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class SfcParseResult:
    """Result of slicing a .vue file."""
    file_path: str
    script_blocks: list[SfcBlock] = field(default_factory=list)
    template_block: SfcBlock | None = None
    style_blocks: list[SfcBlock] = field(default_factory=list)
    component_references: list[str] = field(default_factory=list)
    event_bindings: list[str] = field(default_factory=list)
    property_bindings: list[str] = field(default_factory=list)
