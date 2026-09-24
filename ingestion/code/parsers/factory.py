"""ParserFactory for Tree-sitter Parsers
Provides thread-safe, pre-configured Tree-sitter Parsers for supported languages.
"""

from pathlib import Path
import threading
from typing import Any
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser, Tree
from ingestion.code.dto import LanguageType

# Pinned bundle version metadata for AST cache key generation
PARSER_BUNDLE_VERSION = {
    "tree_sitter": "0.25.2",
    "tree_sitter_javascript": "0.25.0",
    "tree_sitter_typescript": "0.23.2",
    "tree_sitter_java": "0.23.5",
}


class ParserFactory:
    """Singleton factory for managing Tree-sitter Language and Parser instances."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_languages()
            return cls._instance

    def _init_languages(self):
        """Initialize Language instances once at startup."""
        self._languages: dict[LanguageType, Language] = {
            LanguageType.JAVASCRIPT: Language(tsjs.language()),
            LanguageType.TYPESCRIPT: Language(tsts.language_typescript()),
            LanguageType.TSX: Language(tsts.language_tsx()),
            LanguageType.JAVA: Language(tsjava.language()),
        }
        # Thread-local storage for parsers since Parser instances are not thread-safe
        self._thread_local = threading.local()

    def get_language(self, lang_type: LanguageType) -> Language:
        """Get the compiled Language grammar."""
        if lang_type not in self._languages:
            raise ValueError(f"Unsupported language grammar: {lang_type}")
        return self._languages[lang_type]

    def get_parser(self, lang_type: LanguageType) -> Parser:
        """Get or create a thread-local Parser configured for the requested language."""
        if not hasattr(self._thread_local, "parsers"):
            self._thread_local.parsers = {}

        lang = self.get_language(lang_type)
        if lang_type not in self._thread_local.parsers:
            self._thread_local.parsers[lang_type] = Parser(lang)

        return self._thread_local.parsers[lang_type]

    def detect_language(self, file_path: str | Path) -> LanguageType:
        """Deterministic mapping from file extension to LanguageType."""
        ext = Path(file_path).suffix.lower()
        if ext in [".ts", ".mts", ".cts"]:
            return LanguageType.TYPESCRIPT
        elif ext == ".tsx":
            return LanguageType.TSX
        elif ext in [".js", ".mjs", ".cjs"]:
            return LanguageType.JAVASCRIPT
        elif ext == ".jsx":
            return LanguageType.JAVASCRIPT
        elif ext == ".java":
            return LanguageType.JAVA
        elif ext == ".vue":
            return LanguageType.VUE
        return LanguageType.UNKNOWN

    def parse_source(
        self,
        source_code: str | bytes,
        lang_type: LanguageType,
    ) -> Tree:
        """Parses source code into a Tree-sitter Tree."""
        if isinstance(source_code, str):
            source_bytes = source_code.encode("utf-8")
        else:
            source_bytes = source_code

        parser = self.get_parser(lang_type)
        return parser.parse(source_bytes)

    @classmethod
    def get_bundle_version_string(cls) -> str:
        """Returns deterministic version signature of all active grammars."""
        return ";".join(f"{k}={v}" for k, v in sorted(PARSER_BUNDLE_VERSION.items()))
