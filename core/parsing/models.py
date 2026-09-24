"""LKIO Core Parsing Models & DTOs
Defines data structures for Tree-sitter parsers and Vue SFC block slicers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LanguageType(str, Enum):
    TYPESCRIPT = "typescript"
    TSX = "tsx"
    JAVASCRIPT = "javascript"
    JSX = "jsx"
    JAVA = "java"
    VUE = "vue"
    UNKNOWN = "unknown"


@dataclass
class SfcBlock:
    """A structural block extracted from a Vue Single File Component."""
    block_type: str  # template, script, script_setup, style
    content: str
    start_line: int  # 1-based line of opening tag
    end_line: int    # 1-based line of closing tag
    lang: str = "javascript"
    is_setup: bool = False
    is_scoped: bool = False
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class SfcParseResult:
    """Structured extraction of a .vue SFC file."""
    file_path: str
    script_blocks: list[SfcBlock] = field(default_factory=list)
    template_block: SfcBlock | None = None
    style_blocks: list[SfcBlock] = field(default_factory=list)
    component_references: list[str] = field(default_factory=list)
    event_bindings: list[str] = field(default_factory=list)
    property_bindings: list[str] = field(default_factory=list)
