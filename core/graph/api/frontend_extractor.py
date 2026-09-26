"""Frontend API Client Extractor (E-01)
Extracts HTTP requests, API client calls, and endpoint paths from frontend TS, JS, and Vue source files.

Enforces:
- LOCK-TRACE-01: Grounded AST call extraction (requestClient, axios, fetch).
- LOCK-TRACE-02: Path normalization.
"""

import logging
import re
from typing import Any
from tree_sitter import Node

from core.extraction.normalizer import EMPTY_SIGNATURE_DISCRIMINATOR
from core.graph.api.models import ApiEndpoint, HttpMethod, normalize_api_path
from core.parsing.parser_factory import ParserFactory
from core.parsing.sfc_block_slicer import SfcBlockSlicer

logger = logging.getLogger(__name__)

CLIENT_METHODS = {
    "get": HttpMethod.GET,
    "post": HttpMethod.POST,
    "put": HttpMethod.PUT,
    "delete": HttpMethod.DELETE,
    "patch": HttpMethod.PATCH,
    "options": HttpMethod.OPTIONS,
    "head": HttpMethod.HEAD,
}


class FrontendApiExtractor:
    """Extracts frontend outgoing HTTP endpoints and calls from AST."""

    def __init__(
        self,
        parser_factory: ParserFactory | None = None,
        sfc_slicer: SfcBlockSlicer | None = None,
    ):
        self.parser_factory = parser_factory or ParserFactory()
        self.sfc_slicer = sfc_slicer or SfcBlockSlicer()

    def extract_from_code(
        self,
        code_bytes: bytes,
        language: str,
        project_key: str,
        file_rel_path: str,
    ) -> list[ApiEndpoint]:
        """Extracts API endpoints from frontend code."""
        lang = language.lower()
        if lang == "vue":
            return self._extract_from_vue(code_bytes, project_key, file_rel_path)
        elif lang in {"typescript", "javascript", "tsx", "jsx"}:
            return self._extract_from_ts_js(code_bytes, lang, project_key, file_rel_path)
        return []

    def _extract_from_vue(
        self,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
    ) -> list[ApiEndpoint]:
        text = code_bytes.decode("utf-8", errors="replace")
        sfc_res = self.sfc_slicer.slice_text(text, file_rel_path)
        results: list[ApiEndpoint] = []

        for block in sfc_res.script_blocks:
            if not block or not block.content.strip():
                continue
            block_bytes = block.content.encode("utf-8")
            lang = "typescript" if block.lang in {"ts", "tsx", "typescript"} else "javascript"
            endpoints = self._extract_from_ts_js(
                block_bytes,
                lang,
                project_key,
                file_rel_path,
                line_offset=block.start_line - 1,
            )
            results.extend(endpoints)

        return results

    def _extract_from_ts_js(
        self,
        code_bytes: bytes,
        language: str,
        project_key: str,
        file_rel_path: str,
        line_offset: int = 0,
    ) -> list[ApiEndpoint]:
        parser = self.parser_factory.get(language)
        tree = parser.parse(code_bytes)
        root = tree.root_node

        file_subject = f"FILE:{project_key}:{file_rel_path}"
        endpoints: list[ApiEndpoint] = []

        self._traverse_nodes(
            root, code_bytes, project_key, file_rel_path, file_subject, [], line_offset, endpoints
        )
        return endpoints

    def _traverse_nodes(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        current_subject: str,
        scope: list[str],
        line_offset: int,
        endpoints: list[ApiEndpoint],
    ):
        for child in node.children:
            next_subject = current_subject
            next_scope = scope

            if child.type in {"function_declaration", "method_definition", "arrow_function"}:
                name_node = child.child_by_field_name("name")
                if name_node:
                    fname = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                    next_scope = scope + [fname]
                    qual = ".".join(next_scope)
                    next_subject = f"SYMBOL:{project_key}:{file_rel_path}:FUNCTION:{qual}:{EMPTY_SIGNATURE_DISCRIMINATOR}"

            elif child.type == "call_expression":
                ep = self._inspect_call_expression(child, code_bytes, project_key, file_rel_path, current_subject, line_offset)
                if ep:
                    endpoints.append(ep)

            # Check object properties for config constants like: RECORD_UPLOAD: '/api/call/record/upload'
            elif child.type == "pair":
                ep = self._inspect_pair(child, code_bytes, project_key, file_rel_path, current_subject, line_offset)
                if ep:
                    endpoints.append(ep)

            if child.child_count > 0:
                self._traverse_nodes(
                    child, code_bytes, project_key, file_rel_path, next_subject, next_scope, line_offset, endpoints
                )

    def _inspect_call_expression(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        subject_key: str,
        line_offset: int,
    ) -> ApiEndpoint | None:
        fn_node = node.child_by_field_name("function")
        if not fn_node:
            return None

        # Matches requestClient.get('/path') or axios.post('/path')
        if fn_node.type == "member_expression":
            prop_node = fn_node.child_by_field_name("property")
            if not prop_node:
                return None
            method_name = code_bytes[prop_node.start_byte : prop_node.end_byte].decode("utf-8", errors="replace").lower()
            http_method = CLIENT_METHODS.get(method_name)
            if not http_method:
                return None

            # First argument is typically the URL path
            args_node = node.child_by_field_name("arguments")
            if not args_node:
                return None

            path_str = self._extract_string_arg(args_node, code_bytes)
            if path_str and (path_str.startswith("/") or path_str.startswith("http")):
                line = fn_node.start_point.row + 1 + line_offset
                return ApiEndpoint(
                    project_key=project_key,
                    http_method=http_method,
                    raw_path=path_str,
                    normalized_path=normalize_api_path(path_str),
                    source_file_rel_path=file_rel_path,
                    line=line,
                    enclosing_symbol_key=subject_key,
                    is_backend_handler=False,
                )

        return None

    def _inspect_pair(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        subject_key: str,
        line_offset: int,
    ) -> ApiEndpoint | None:
        # e.g. RECORD_UPLOAD: '/api/call/record/upload'
        val_node = node.child_by_field_name("value")
        if not val_node or val_node.type != "string":
            return None

        val_text = code_bytes[val_node.start_byte : val_node.end_byte].decode("utf-8", errors="replace").strip("\"'")
        if val_text.startswith("/api/") or val_text.startswith("/crm/"):
            line = node.start_point.row + 1 + line_offset
            return ApiEndpoint(
                project_key=project_key,
                http_method=HttpMethod.ANY,
                raw_path=val_text,
                normalized_path=normalize_api_path(val_text),
                source_file_rel_path=file_rel_path,
                line=line,
                enclosing_symbol_key=subject_key,
                is_backend_handler=False,
            )

        return None

    def _extract_string_arg(self, args_node: Node, code_bytes: bytes) -> str | None:
        for child in args_node.children:
            if child.type == "string":
                return code_bytes[child.start_byte : child.end_byte].decode("utf-8", errors="replace").strip("\"'")
        return None
