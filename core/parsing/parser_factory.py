"""LKIO ParserFactory
Single-responsibility Tree-sitter Parser factory.
Provides language registration, parser construction, and thread-local lazy initialization.
"""

from pathlib import Path
import threading
from typing import Any
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser
from core.parsing.models import LanguageType

# Pinned bundle version metadata for AST cache key generation
PARSER_BUNDLE_VERSION = {
    "tree_sitter": "0.25.2",
    "tree_sitter_javascript": "0.25.0",
    "tree_sitter_typescript": "0.23.2",
    "tree_sitter_java": "0.23.5",
}


class ParserFactory:
    """Thread-safe factory managing Tree-sitter Language and Parser instances."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_languages()
            return cls._instance

    def _init_languages(self):
        """Initialize Language grammars once."""
        js_lang = Language(tsjs.language())
        ts_lang = Language(tsts.language_typescript())
        tsx_lang = Language(tsts.language_tsx())
        java_lang = Language(tsjava.language())

        self._languages: dict[str, Language] = {
            "javascript": js_lang,
            "jsx": js_lang,  # tree-sitter-javascript natively supports JSX
            "typescript": ts_lang,
            "tsx": tsx_lang,
            "java": java_lang,
        }
        self._thread_local = threading.local()

    def _normalize_lang_key(self, lang: str | LanguageType) -> str:
        if isinstance(lang, LanguageType):
            key = lang.value.lower()
        else:
            key = str(lang).lower().strip()
        if key not in self._languages:
            raise ValueError(
                f"Unsupported language '{lang}'. Supported languages: {list(self._languages.keys())}"
            )
        return key

    def get_language(self, lang: str | LanguageType) -> Language:
        """Get the compiled Language grammar."""
        key = self._normalize_lang_key(lang)
        return self._languages[key]

    def get(self, lang: str | LanguageType) -> Parser:
        """Get or lazily create a thread-local Parser configured for the requested language."""
        key = self._normalize_lang_key(lang)
        if not hasattr(self._thread_local, "parsers"):
            self._thread_local.parsers = {}

        if key not in self._thread_local.parsers:
            language_obj = self.get_language(key)
            self._thread_local.parsers[key] = Parser(language_obj)

        return self._thread_local.parsers[key]

    def detect_language(self, file_path: str | Path) -> str:
        """Maps file extension to canonical language key."""
        ext = Path(file_path).suffix.lower()
        if ext in [".ts", ".mts", ".cts"]:
            return "typescript"
        elif ext == ".tsx":
            return "tsx"
        elif ext in [".js", ".mjs", ".cjs"]:
            return "javascript"
        elif ext == ".jsx":
            return "jsx"
        elif ext == ".java":
            return "java"
        elif ext == ".vue":
            return "vue"
        return "unknown"

    @classmethod
    def get_bundle_version_string(cls) -> str:
        """Returns deterministic version signature of active grammars."""
        return ";".join(f"{k}={v}" for k, v in sorted(PARSER_BUNDLE_VERSION.items()))
