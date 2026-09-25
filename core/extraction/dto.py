"""LKIO Code Symbol Extraction DTOs (Lock v0.3)
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
    """Decoupled candidate representation of an extracted code symbol (Section 18)."""
    symbol_type: str  # Native (e.g. FUNCTION, CLASS) or Rule Classification (COMPONENT, HOOK)
    base_symbol_type: str  # Must strictly be in NATIVE_SYMBOL_TYPES

    name: str
    qualified_name: str

    start_line: int  # 1-based physical line number
    end_line: int    # 1-based physical line number
    start_column: int  # 0-based column
    end_column: int    # 0-based column

    project_key: str = ""
    file_rel_path: str = ""

    signature: str | None = None
    canonical_signature: str | None = None
    signature_discriminator: str = "e3b0c44298fc1c14"

    language: str = "unknown"

    modifiers: list[str] = field(default_factory=list)
    annotations: list[dict[str, Any]] = field(default_factory=list)

    is_exported: bool = False
    export_kind: str = "none"  # "named", "default", "none"

    classification_method: str | None = None  # None, name_prefix_rule_v1, vue_sfc_rule_v1, jsx_function_component_v1

    parser_version: str = "tree-sitter@0.25.2"
    extractor_version: str = "mvp2-symbol-0.1"

    file_path: str | None = None
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
        if self.file_rel_path:
            self.file_rel_path = self.file_rel_path.replace("\\", "/")
        if not self.file_path and self.file_rel_path:
            self.file_path = self.file_rel_path

    def compute_key(self) -> str:
        """Computes the deterministic entity key for this symbol candidate."""
        from core.extraction.normalizer import build_symbol_key
        return build_symbol_key(
            project_key=self.project_key,
            file_rel_path=self.file_rel_path,
            base_symbol_type=self.base_symbol_type,
            qualified_name=self.qualified_name,
            signature_discriminator=self.signature_discriminator,
            canonical_signature=self.canonical_signature,
        )


class ExtractionFailureReason(str, Enum):
    """Discrete, controlled taxonomy of extraction failure causes (LOCK-ORCH-04)."""
    UNSUPPORTED_EXTENSION = "unsupported_extension"  # 不受支持的文件后缀（如 .css, .json, .py）
    PARSER_UNAVAILABLE = "parser_unavailable"        # 目标语言 Tree-sitter Parser/Grammar 未能加载
    ENCODING_FAILURE = "encoding_failure"            # 文件二进制乱码或无法按 UTF-8 安全解码
    MALFORMED_SOURCE = "malformed_source"            # 源码严重残缺，AST 根节点或关键骨架解析失败
    EXTRACTOR_EXCEPTION = "extractor_exception"       # 抽取器在遍历 AST 过程中抛出未预期的内部异常
    EMPTY_SOURCE = "empty_source"                    # 文件内容为 0 字节或纯空白


@dataclass
class FileExtractionResult:
    """Diagnostic and extracted symbol result for a single file (LOCK-ORCH-03)."""
    file_rel_path: str
    file_path: str
    language: str
    success: bool
    symbols: list[SymbolCandidate] = field(default_factory=list)
    symbol_keys: list[str] = field(default_factory=list)
    error_reason: str | None = None  # From ExtractionFailureReason
    error_detail: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.file_rel_path:
            self.file_rel_path = self.file_rel_path.replace("\\", "/")


@dataclass
class BatchExtractionSummary:
    """Summary of a batch symbol extraction scan across multiple files with counter integrity (LOCK-ORCH-08)."""
    project_key: str
    total_files: int
    scanned_files: int
    successful_files: int
    failed_files: int
    unsupported_files: int
    total_symbols: int
    symbols_by_type: dict[str, int] = field(default_factory=dict)
    failures_by_reason: dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0
    results: list[FileExtractionResult] = field(default_factory=list)

    def verify_counter_integrity(self) -> bool:
        """Verifies the counter integrity invariants:
        total_files == successful_files + failed_files + unsupported_files
        scanned_files == successful_files + failed_files
        """
        scanned_valid = self.scanned_files == (self.successful_files + self.failed_files)
        total_valid = self.total_files == (self.successful_files + self.failed_files + self.unsupported_files)
        return scanned_valid and total_valid

