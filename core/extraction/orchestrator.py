"""LKIO Symbol Extraction Orchestrator
Routes source files to the appropriate language extractor and attaches canonical deterministic keys.
"""

from pathlib import Path
from typing import Any
from core.extraction.dto import SymbolCandidate
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
    """Coordinates language-specific extractors and assigns deterministic symbol keys."""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.parser_factory = parser_factory or ParserFactory()
        self.ts_extractor = TypeScriptExtractor(self.parser_factory)
        self.java_extractor = JavaExtractor(self.parser_factory)
        self.vue_extractor = VueExtractor(self.ts_extractor)

    def detect_language(self, file_path: str | Path) -> str:
        """Determines the target language from the file extension."""
        ext = Path(file_path).suffix.lower()
        return EXT_TO_LANGUAGE.get(ext, "unknown")

    def is_supported(self, file_path: str | Path) -> bool:
        """Returns True if the file type is supported for symbol extraction."""
        return self.detect_language(file_path) != "unknown"

    def extract_file_symbols(
        self,
        code_bytes: bytes,
        project_key: str,
        file_path: str,
        file_rel_path: str,
        language: str | None = None,
    ) -> list[tuple[str, SymbolCandidate]]:
        """Extracts symbol candidates and pairs each with its canonical deterministic symbol key.

        Returns:
            List of (symbol_key, SymbolCandidate).
        """
        lang = (language or self.detect_language(file_path)).lower()
        if lang not in EXT_TO_LANGUAGE.values():
            return []

        norm_rel_path = normalize_rel_path(file_rel_path)

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

        # Generate canonical deterministic keys for each candidate
        results: list[tuple[str, SymbolCandidate]] = []
        for candidate in candidates:
            candidate.project_key = project_key
            key = candidate.compute_key()
            results.append((key, candidate))

        return results
