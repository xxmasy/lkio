"""LKIO Symbol Extraction Orchestrator (Lock v0.3 / B-06 Approved)
Coordinates language-specific extractors, handles preflight checks, enforces failure isolation,
and attaches canonical deterministic keys according to the 10 Orchestrator Architecture Locks.
"""

from enum import Enum
from pathlib import Path
import time
from typing import Any

from core.extraction.dto import (
    BatchExtractionSummary,
    ExtractionFailureReason,
    FileExtractionResult,
    SymbolCandidate,
)
from core.extraction.java import JavaExtractor
from core.extraction.normalizer import build_symbol_key, normalize_rel_path
from core.extraction.typescript import TypeScriptExtractor
from core.extraction.vue import VueExtractor
from core.parsing.models import LanguageType
from core.parsing.parser_factory import ParserFactory

EXT_TO_LANGUAGE: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".java": "java",
    ".vue": "vue",
}


class SymbolExtractionOrchestrator:
    """Coordinates language-specific extractors with failure isolation and deterministic ordering (LOCK-ORCH-01 ~ 10)."""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.parser_factory = parser_factory or ParserFactory()
        self.ts_extractor = TypeScriptExtractor(self.parser_factory)
        self.java_extractor = JavaExtractor(self.parser_factory)
        self.vue_extractor = VueExtractor(self.ts_extractor)

    def detect_language(self, file_path: str | Path) -> str:
        """Determines the target language from the file extension (LOCK-ORCH-01)."""
        ext = Path(file_path).suffix.lower()
        return EXT_TO_LANGUAGE.get(ext, "unknown")

    def is_supported(self, file_path: str | Path) -> bool:
        """Returns True if the file type is supported for symbol extraction."""
        return self.detect_language(file_path) != "unknown"

    def extract_file(
        self,
        code_bytes: bytes,
        project_key: str,
        file_path: str,
        file_rel_path: str,
        language: str | None = None,
    ) -> FileExtractionResult:
        """Extracts symbols from a single file in an isolated execution sandbox (LOCK-ORCH-03).

        Performs deterministic preflight checks (extension, empty source, encoding, parser availability)
        and delegates to the frozen language extractor without mutating extractor-owned semantic fields.
        """
        start_time = time.perf_counter()
        norm_rel_path = normalize_rel_path(file_rel_path)
        lang = (language or self.detect_language(file_path)).lower()

        # 1. Preflight: Unsupported extension (LOCK-ORCH-01, LOCK-ORCH-06)
        if lang not in EXT_TO_LANGUAGE.values():
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            ext = Path(file_path).suffix.lower()
            return FileExtractionResult(
                file_rel_path=norm_rel_path,
                file_path=file_path,
                language="unsupported",
                success=False,
                error_reason=ExtractionFailureReason.UNSUPPORTED_EXTENSION.value,
                error_detail=f"Unsupported file extension: '{ext}'",
                duration_ms=duration_ms,
            )

        # 2. Preflight: Empty source detection (LOCK-ORCH-06, Gate H)
        if not code_bytes or not code_bytes.strip():
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return FileExtractionResult(
                file_rel_path=norm_rel_path,
                file_path=file_path,
                language=lang,
                success=False,
                error_reason=ExtractionFailureReason.EMPTY_SOURCE.value,
                error_detail="File content is empty or contains only whitespace",
                duration_ms=duration_ms,
            )

        # 3. Preflight: Encoding robustness (LOCK-ORCH-06, Gate G)
        try:
            code_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return FileExtractionResult(
                file_rel_path=norm_rel_path,
                file_path=file_path,
                language=lang,
                success=False,
                error_reason=ExtractionFailureReason.ENCODING_FAILURE.value,
                error_detail=f"UTF-8 decode failure: {err}",
                duration_ms=duration_ms,
            )

        # 4. Preflight: Parser availability (LOCK-ORCH-06, Gate E)
        try:
            parser_lang = "typescript" if lang in ["typescript", "tsx"] else ("javascript" if lang in ["javascript", "jsx"] else lang)
            if parser_lang in ["typescript", "javascript", "java"]:
                self.parser_factory.get(parser_lang)
        except Exception as err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return FileExtractionResult(
                file_rel_path=norm_rel_path,
                file_path=file_path,
                language=lang,
                success=False,
                error_reason=ExtractionFailureReason.PARSER_UNAVAILABLE.value,
                error_detail=f"Parser unavailable for language '{lang}': {err}",
                duration_ms=duration_ms,
            )

        # 5. Isolated Extractor Execution (LOCK-ORCH-02, LOCK-ORCH-03, LOCK-ORCH-06)
        try:
            if lang in ["typescript", "tsx", "javascript", "jsx"]:
                candidates = self.ts_extractor.extract(
                    code_bytes=code_bytes,
                    file_path=file_path,
                    file_rel_path=norm_rel_path,
                    language=lang,
                )
            elif lang == "java":
                candidates = self.java_extractor.extract(
                    code_bytes=code_bytes,
                    file_path=file_path,
                    file_rel_path=norm_rel_path,
                    language=lang,
                )
            elif lang == "vue":
                candidates = self.vue_extractor.extract(
                    code_bytes=code_bytes,
                    file_path=file_path,
                    file_rel_path=norm_rel_path,
                    language=lang,
                )
            else:
                candidates = []

            # 6. Candidate Key Derivation without semantic mutation (LOCK-ORCH-07, LOCK-ORCH-10)
            symbol_keys: list[str] = []
            for candidate in candidates:
                # Propagate orchestration-owned identity context only
                candidate.project_key = project_key
                candidate.file_rel_path = norm_rel_path
                # Compute key using file_rel_path strictly (LOCK-ORCH-07)
                key = candidate.compute_key()
                symbol_keys.append(key)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return FileExtractionResult(
                file_rel_path=norm_rel_path,
                file_path=file_path,
                language=lang,
                success=True,
                symbols=candidates,
                symbol_keys=symbol_keys,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            # LOCK-ORCH-09: MALFORMED_SOURCE only if extractor explicitly signals syntax break
            exc_str = str(exc)
            if "SyntaxError" in exc_str or "MalformedSource" in exc_str:
                reason = ExtractionFailureReason.MALFORMED_SOURCE.value
            else:
                reason = ExtractionFailureReason.EXTRACTOR_EXCEPTION.value

            return FileExtractionResult(
                file_rel_path=norm_rel_path,
                file_path=file_path,
                language=lang,
                success=False,
                error_reason=reason,
                error_detail=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
            )

    def extract_file_symbols(
        self,
        code_bytes: bytes,
        project_key: str,
        file_path: str,
        file_rel_path: str,
        language: str | None = None,
    ) -> list[tuple[str, SymbolCandidate]]:
        """Convenience method returning paired (symbol_key, SymbolCandidate) tuples.
        Maintains backward compatibility with earlier integration suites.
        """
        result = self.extract_file(
            code_bytes=code_bytes,
            project_key=project_key,
            file_path=file_path,
            file_rel_path=file_rel_path,
            language=language,
        )
        if not result.success:
            return []
        return list(zip(result.symbol_keys, result.symbols))

    def extract_batch(
        self,
        files: list[tuple[bytes, str, str]],
        project_key: str,
    ) -> BatchExtractionSummary:
        """Extracts symbols for a batch of files with deterministic lexical ordering and counter integrity (LOCK-ORCH-08).

        Args:
            files: List of (code_bytes, file_path, file_rel_path) tuples.
            project_key: Identifier of the target project.

        Returns:
            BatchExtractionSummary satisfying the Counter Integrity Rule:
            total_files == successful_files + failed_files + unsupported_files
            scanned_files == successful_files + failed_files
        """
        batch_start = time.perf_counter()

        # 1. Deterministic Lexical Sort by file_rel_path (LOCK-ORCH-08)
        sorted_files = sorted(files, key=lambda f: normalize_rel_path(f[2]))

        total_files = len(sorted_files)
        successful_files = 0
        failed_files = 0
        unsupported_files = 0
        total_symbols = 0

        symbols_by_type: dict[str, int] = {}
        failures_by_reason: dict[str, int] = {}
        results: list[FileExtractionResult] = []

        for code_bytes, file_path, file_rel_path in sorted_files:
            file_res = self.extract_file(
                code_bytes=code_bytes,
                project_key=project_key,
                file_path=file_path,
                file_rel_path=file_rel_path,
            )
            results.append(file_res)

            if file_res.error_reason == ExtractionFailureReason.UNSUPPORTED_EXTENSION.value:
                # Unsupported is an independent terminal state; does NOT count as failed_files
                unsupported_files += 1
                failures_by_reason[file_res.error_reason] = failures_by_reason.get(file_res.error_reason, 0) + 1
            elif file_res.success:
                successful_files += 1
                total_symbols += len(file_res.symbols)
                for sym in file_res.symbols:
                    symbols_by_type[sym.symbol_type] = symbols_by_type.get(sym.symbol_type, 0) + 1
            else:
                failed_files += 1
                reason = file_res.error_reason or "unknown"
                failures_by_reason[reason] = failures_by_reason.get(reason, 0) + 1

        scanned_files = successful_files + failed_files
        duration_ms = (time.perf_counter() - batch_start) * 1000.0

        summary = BatchExtractionSummary(
            project_key=project_key,
            total_files=total_files,
            scanned_files=scanned_files,
            successful_files=successful_files,
            failed_files=failed_files,
            unsupported_files=unsupported_files,
            total_symbols=total_symbols,
            symbols_by_type=symbols_by_type,
            failures_by_reason=failures_by_reason,
            duration_ms=duration_ms,
            results=results,
        )

        # Enforce Counter Integrity Rule
        if not summary.verify_counter_integrity():
            raise AssertionError(
                f"Batch counter integrity violated! Total: {total_files}, "
                f"Scanned: {scanned_files}, Success: {successful_files}, "
                f"Failed: {failed_files}, Unsupported: {unsupported_files}"
            )

        return summary
