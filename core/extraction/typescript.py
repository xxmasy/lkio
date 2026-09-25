"""LKIO TypeScript / JavaScript / TSX / JSX Symbol Extractor (MVP2-B Step B-03)
Extracts code symbols from TS, TSX, JS, and JSX files using Tree-sitter AST.

Enforces:
- Lock 1: 9 Native Symbol Types (CLASS, INTERFACE, FUNCTION, METHOD, VARIABLE, ENUM, TYPE)
- Lock 2: Rule Classifications (HOOK, COMPONENT) retain controlled base_symbol_type
- Lock 3: Deterministic signature discriminator (line-shift immune)
- Lock 4: Language-specific canonical signature (canonicalize_ts_signature)
- Lock 5: Lexical scope chain in qualified_name (build_qualified_name with ::)
- AST Evidence & Confidence (1.0, static_ast, evidence coordinates)
- Safe error handling: AST ERROR nodes do not crash file extraction
"""

import logging
import re
from typing import Any
from tree_sitter import Node, Tree
from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_qualified_name,
    canonicalize_ts_signature,
    compute_signature_discriminator,
    normalize_rel_path,
)
from core.parsing.models import LanguageType, SymbolType
from core.parsing.parser_factory import ParserFactory

logger = logging.getLogger(__name__)

_HOOK_NAME_RE = re.compile(r"^use[A-Z0-9].*")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")

SUPPORTED_EXTENSIONS = {
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".mts": "typescript",
    ".cts": "typescript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}


class TypeScriptExtractor:
    """Extracts symbols from TypeScript, TSX, JavaScript, and JSX source code."""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.parser_factory = parser_factory or ParserFactory()

    def extract(
        self,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str = "typescript",
        project_key: str = "",
    ) -> list[SymbolCandidate]:
        """Parses source code bytes and extracts all symbol candidates.

        Args:
            code_bytes: Source code content in bytes.
            file_path: Full file path.
            file_rel_path: Relative path within the project.
            language: 'typescript', 'tsx', 'javascript', or 'jsx'.
            project_key: Optional project key (e.g. 'HELLO_FE').

        Returns:
            List of decoupled SymbolCandidate DTOs.
        """
        lang_key = language.lower()
        if lang_key not in ["typescript", "tsx", "javascript", "jsx"]:
            lang_key = "typescript"

        try:
            tree = self.parser_factory.get(lang_key).parse(code_bytes)
        except Exception as e:
            logger.warning(f"Tree-sitter parse failed for {file_rel_path}: {e}")
            return []

        candidates: list[SymbolCandidate] = []
        norm_rel_path = normalize_rel_path(file_rel_path)

        self._walk_statements(
            container_node=tree.root_node,
            code_bytes=code_bytes,
            file_path=file_path,
            file_rel_path=norm_rel_path,
            language=lang_key,
            project_key=project_key,
            scope_chain=[],
            out=candidates,
        )

        return candidates

    def _walk_statements(
        self,
        container_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Walks child statements in a container (root node or statement_block)."""
        for child in container_node.children:
            if child.type == "ERROR":
                # Gate 23: Syntax error node encountered - record warning and continue
                logger.warning(
                    f"AST syntax error in {file_rel_path} near line {child.start_point.row + 1}"
                )
                continue

            is_exported = False
            export_kind = "none"
            target_node = child

            if child.type == "export_statement":
                is_exported = True
                export_kind = "named"
                for sub in child.children:
                    if sub.type == "default" or sub.text == b"default":
                        export_kind = "default"
                    if sub.type in [
                        "function_declaration",
                        "class_declaration",
                        "abstract_class_declaration",
                        "interface_declaration",
                        "type_alias_declaration",
                        "enum_declaration",
                        "lexical_declaration",
                        "variable_declaration",
                    ]:
                        target_node = sub

            self._process_statement(
                node=target_node,
                code_bytes=code_bytes,
                file_path=file_path,
                file_rel_path=file_rel_path,
                language=language,
                project_key=project_key,
                is_exported=is_exported,
                export_kind=export_kind,
                scope_chain=scope_chain,
                out=out,
            )

    def _process_statement(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        is_exported: bool,
        export_kind: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Processes a single declaration statement node."""
        node_type = node.type

        try:
            if node_type == "function_declaration":
                self._handle_function_declaration(
                    node, code_bytes, file_path, file_rel_path, language, project_key,
                    is_exported, export_kind, scope_chain, out
                )
            elif node_type in ["class_declaration", "abstract_class_declaration"]:
                self._handle_class_declaration(
                    node, code_bytes, file_path, file_rel_path, language, project_key,
                    is_exported, export_kind, scope_chain, out
                )
            elif node_type == "interface_declaration":
                self._handle_interface_declaration(
                    node, code_bytes, file_path, file_rel_path, language, project_key,
                    is_exported, export_kind, scope_chain, out
                )
            elif node_type == "type_alias_declaration":
                self._handle_type_alias_declaration(
                    node, code_bytes, file_path, file_rel_path, language, project_key,
                    is_exported, export_kind, scope_chain, out
                )
            elif node_type == "enum_declaration":
                self._handle_enum_declaration(
                    node, code_bytes, file_path, file_rel_path, language, project_key,
                    is_exported, export_kind, scope_chain, out
                )
            elif node_type in ["lexical_declaration", "variable_declaration"]:
                self._handle_variable_declaration(
                    node, code_bytes, file_path, file_rel_path, language, project_key,
                    is_exported, export_kind, scope_chain, out
                )
        except Exception as e:
            logger.warning(
                f"Error extracting symbol from {node_type} at line {node.start_point.row + 1}: {e}"
            )

    def _handle_function_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        is_exported: bool,
        export_kind: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            if is_exported and export_kind == "default":
                name = "default"
            else:
                return
        else:
            name = name_node.text.decode("utf-8", errors="replace")

        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        params_node = node.child_by_field_name("parameters")
        ret_node = node.child_by_field_name("return_type")

        params_text = params_node.text.decode("utf-8", errors="replace") if params_node else "()"
        ret_text = ret_node.text.decode("utf-8", errors="replace") if ret_node else ""
        raw_signature = f"{params_text}{ret_text}"

        canonical_sig = canonicalize_ts_signature(params_text)
        sig_discriminator = compute_signature_discriminator(canonical_sig)

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")
        if export_kind == "default" and "default" not in modifiers:
            modifiers.append("default")

        # Classification: Hook or Component or Native FUNCTION
        symbol_type, base_symbol_type, method = self._classify_callable(
            name=name, node=node, is_arrow=False, language=language
        )

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1
        start_col = node.start_point.column
        end_col = node.end_point.column

        metadata: dict[str, Any] = {
            "evidence": {
                "node_type": node.type,
                "start_line": start_line,
                "end_line": end_line,
            },
            "extraction_method": "static_ast",
            "confidence": 1.0,
            "export_kind": export_kind,
            "is_async": "async" in modifiers,
            "is_generator": any(c.type == "*" for c in node.children),
        }

        candidate = SymbolCandidate(
            project_key=project_key,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=symbol_type,
            base_symbol_type=base_symbol_type,
            start_line=start_line,
            end_line=end_line,
            start_column=start_col,
            end_column=end_col,
            signature=raw_signature,
            canonical_signature=canonical_sig,
            signature_discriminator=sig_discriminator,
            language=language,
            classification_method=method,
            modifiers=modifiers,
            is_exported=is_exported,
            export_kind=export_kind,
            metadata=metadata,
        )
        out.append(candidate)

        # Recurse into function body for nested scopes (e.g. outer::inner)
        body_node = node.child_by_field_name("body")
        if body_node and body_node.type == "statement_block":
            self._walk_statements(
                container_node=body_node,
                code_bytes=code_bytes,
                file_path=file_path,
                file_rel_path=file_rel_path,
                language=language,
                project_key=project_key,
                scope_chain=scope_chain + [name],
                out=out,
            )

    def _handle_class_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        is_exported: bool,
        export_kind: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            if is_exported and export_kind == "default":
                name = "default"
            else:
                return
        else:
            name = name_node.text.decode("utf-8", errors="replace")

        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers = self._extract_modifiers(node)
        if node.type == "abstract_class_declaration" and "abstract" not in modifiers:
            modifiers.append("abstract")
        if is_exported and "export" not in modifiers:
            modifiers.append("export")
        if export_kind == "default" and "default" not in modifiers:
            modifiers.append("default")

        # Heritage (extends / implements) metadata
        extends_clause = ""
        implements_clause = ""
        for child in node.children:
            if child.type == "class_heritage":
                for hc in child.children:
                    if hc.type == "extends_clause":
                        extends_clause = hc.text.decode("utf-8", errors="replace").strip()
                    elif hc.type == "implements_clause":
                        implements_clause = hc.text.decode("utf-8", errors="replace").strip()

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1
        start_col = node.start_point.column
        end_col = node.end_point.column

        metadata: dict[str, Any] = {
            "evidence": {
                "node_type": node.type,
                "start_line": start_line,
                "end_line": end_line,
            },
            "extraction_method": "static_ast",
            "confidence": 1.0,
            "export_kind": export_kind,
        }
        if extends_clause:
            metadata["extends_clause"] = extends_clause
        if implements_clause:
            metadata["implements"] = implements_clause

        candidate = SymbolCandidate(
            project_key=project_key,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.CLASS.value,
            base_symbol_type=SymbolType.CLASS.value,
            start_line=start_line,
            end_line=end_line,
            start_column=start_col,
            end_column=end_col,
            signature=None,
            canonical_signature=None,
            signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
            language=language,
            classification_method="ast_native",
            modifiers=modifiers,
            is_exported=is_exported,
            export_kind=export_kind,
            metadata=metadata,
        )
        out.append(candidate)

        # Process class body members
        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_class_body(
                body_node=body_node,
                code_bytes=code_bytes,
                file_path=file_path,
                file_rel_path=file_rel_path,
                language=language,
                project_key=project_key,
                class_scope=scope_chain + [name],
                out=out,
            )

    def _walk_class_body(
        self,
        body_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        class_scope: list[str],
        out: list[SymbolCandidate],
    ):
        """Walks members inside class body."""
        for member in body_node.children:
            if member.type in ["method_definition", "abstract_method_signature"]:
                m_name_node = member.child_by_field_name("name")
                if not m_name_node:
                    continue
                m_name = m_name_node.text.decode("utf-8", errors="replace")
                m_qname = build_qualified_name(m_name, scope_chain=class_scope)

                params_node = member.child_by_field_name("parameters")
                ret_node = member.child_by_field_name("return_type")

                p_text = params_node.text.decode("utf-8", errors="replace") if params_node else "()"
                r_text = ret_node.text.decode("utf-8", errors="replace") if ret_node else ""
                raw_sig = f"{p_text}{r_text}"

                canon_sig = canonicalize_ts_signature(p_text)
                sig_disc = compute_signature_discriminator(canon_sig)

                m_mods = self._extract_modifiers(member)
                if member.type == "abstract_method_signature" and "abstract" not in m_mods:
                    m_mods.append("abstract")
                m_start_line = member.start_point.row + 1
                m_end_line = member.end_point.row + 1

                m_meta: dict[str, Any] = {
                    "evidence": {
                        "node_type": member.type,
                        "start_line": m_start_line,
                        "end_line": m_end_line,
                    },
                    "extraction_method": "static_ast",
                    "confidence": 1.0,
                    "is_static": "static" in m_mods,
                    "is_async": "async" in m_mods,
                }

                out.append(
                    SymbolCandidate(
                        project_key=project_key,
                        file_path=file_path,
                        file_rel_path=file_rel_path,
                        name=m_name,
                        qualified_name=m_qname,
                        symbol_type=SymbolType.METHOD.value,
                        base_symbol_type=SymbolType.METHOD.value,
                        start_line=m_start_line,
                        end_line=m_end_line,
                        start_column=member.start_point.column,
                        end_column=member.end_point.column,
                        signature=raw_sig,
                        canonical_signature=canon_sig,
                        signature_discriminator=sig_disc,
                        language=language,
                        classification_method="ast_native",
                        modifiers=m_mods,
                        is_exported=False,
                        export_kind="none",
                        metadata=m_meta,
                    )
                )

                # Nested scopes inside method body
                m_body = member.child_by_field_name("body")
                if m_body and m_body.type == "statement_block":
                    self._walk_statements(
                        container_node=m_body,
                        code_bytes=code_bytes,
                        file_path=file_path,
                        file_rel_path=file_rel_path,
                        language=language,
                        project_key=project_key,
                        scope_chain=class_scope + [m_name],
                        out=out,
                    )

            elif member.type in ["public_field_definition", "field_definition", "property_definition"]:
                f_name_node = member.child_by_field_name("name")
                if not f_name_node:
                    for c in member.children:
                        if c.type == "property_identifier":
                            f_name_node = c
                            break
                if not f_name_node:
                    continue
                f_name = f_name_node.text.decode("utf-8", errors="replace")
                f_qname = build_qualified_name(f_name, scope_chain=class_scope)
                f_mods = self._extract_modifiers(member)

                f_start_line = member.start_point.row + 1
                f_end_line = member.end_point.row + 1

                f_meta: dict[str, Any] = {
                    "evidence": {
                        "node_type": member.type,
                        "start_line": f_start_line,
                        "end_line": f_end_line,
                    },
                    "extraction_method": "static_ast",
                    "confidence": 1.0,
                    "is_static": "static" in f_mods,
                    "is_readonly": "readonly" in f_mods,
                }

                out.append(
                    SymbolCandidate(
                        project_key=project_key,
                        file_path=file_path,
                        file_rel_path=file_rel_path,
                        name=f_name,
                        qualified_name=f_qname,
                        symbol_type=SymbolType.FIELD.value,
                        base_symbol_type=SymbolType.FIELD.value,
                        start_line=f_start_line,
                        end_line=f_end_line,
                        start_column=member.start_point.column,
                        end_column=member.end_point.column,
                        signature=None,
                        canonical_signature=None,
                        signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
                        language=language,
                        classification_method="ast_native",
                        modifiers=f_mods,
                        is_exported=False,
                        export_kind="none",
                        metadata=f_meta,
                    )
                )

    def _handle_interface_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        is_exported: bool,
        export_kind: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")
        if export_kind == "default" and "default" not in modifiers:
            modifiers.append("default")

        extends_clause = ""
        for child in node.children:
            if child.type in ["extends_clause", "extends_type_clause"]:
                extends_clause = child.text.decode("utf-8", errors="replace").strip()

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        metadata: dict[str, Any] = {
            "evidence": {
                "node_type": node.type,
                "start_line": start_line,
                "end_line": end_line,
            },
            "extraction_method": "static_ast",
            "confidence": 1.0,
            "export_kind": export_kind,
        }
        if extends_clause:
            metadata["extends_clause"] = extends_clause

        # Gate 6: Interface members are NOT modeled as independent symbols in B-03
        out.append(
            SymbolCandidate(
                project_key=project_key,
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.INTERFACE.value,
                base_symbol_type=SymbolType.INTERFACE.value,
                start_line=start_line,
                end_line=end_line,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                canonical_signature=None,
                signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
                language=language,
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                export_kind=export_kind,
                metadata=metadata,
            )
        )

    def _handle_type_alias_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        is_exported: bool,
        export_kind: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")

        val_node = node.child_by_field_name("value")
        type_shape = val_node.text.decode("utf-8", errors="replace").strip() if val_node else ""

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        metadata: dict[str, Any] = {
            "evidence": {
                "node_type": node.type,
                "start_line": start_line,
                "end_line": end_line,
            },
            "extraction_method": "static_ast",
            "confidence": 1.0,
            "export_kind": export_kind,
        }
        if type_shape:
            metadata["type_shape"] = type_shape

        # Gate 7: Complex type details stored in metadata.type_shape, no FIELD symbols created
        out.append(
            SymbolCandidate(
                project_key=project_key,
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.TYPE.value,
                base_symbol_type=SymbolType.TYPE.value,
                start_line=start_line,
                end_line=end_line,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                canonical_signature=None,
                signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
                language=language,
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                export_kind=export_kind,
                metadata=metadata,
            )
        )

    def _handle_enum_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        is_exported: bool,
        export_kind: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")

        # Collect enum member names into metadata (Gate 12)
        enum_members: list[str] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "property_identifier":
                    enum_members.append(child.text.decode("utf-8", errors="replace"))
                elif child.type == "enum_assignment":
                    m_node = child.child_by_field_name("name")
                    if m_node:
                        enum_members.append(m_node.text.decode("utf-8", errors="replace"))
                    elif child.children:
                        enum_members.append(child.children[0].text.decode("utf-8", errors="replace"))

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        metadata: dict[str, Any] = {
            "evidence": {
                "node_type": node.type,
                "start_line": start_line,
                "end_line": end_line,
            },
            "extraction_method": "static_ast",
            "confidence": 1.0,
            "export_kind": export_kind,
            "enum_members": enum_members,
        }

        out.append(
            SymbolCandidate(
                project_key=project_key,
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.ENUM.value,
                base_symbol_type=SymbolType.ENUM.value,
                start_line=start_line,
                end_line=end_line,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                canonical_signature=None,
                signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
                language=language,
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                export_kind=export_kind,
                metadata=metadata,
            )
        )

    def _handle_variable_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        project_key: str,
        is_exported: bool,
        export_kind: str,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        top_modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in top_modifiers:
            top_modifiers.append("export")
        if export_kind == "default" and "default" not in top_modifiers:
            top_modifiers.append("default")

        # Determine declaration kind (const, let, var)
        declaration_kind = "const"
        for c in node.children:
            if c.type in ["const", "let", "var"]:
                declaration_kind = c.type
                break

        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                name = name_node.text.decode("utf-8", errors="replace")
                qualified_name = build_qualified_name(name, scope_chain=scope_chain)

                val_node = child.child_by_field_name("value")

                start_line = child.start_point.row + 1
                end_line = child.end_point.row + 1
                start_col = child.start_point.column
                end_col = child.end_point.column

                if val_node and val_node.type in ["arrow_function", "function_expression"]:
                    # Arrow Function or Function Expression stored in variable
                    params_node = val_node.child_by_field_name("parameters")
                    if params_node:
                        p_text = params_node.text.decode("utf-8", errors="replace")
                    else:
                        p_child = val_node.child_by_field_name("parameter")
                        p_text = f"({p_child.text.decode('utf-8', errors='replace')})" if p_child else "()"

                    ret_node = val_node.child_by_field_name("return_type")
                    r_text = ret_node.text.decode("utf-8", errors="replace") if ret_node else ""
                    raw_sig = f"{p_text}{r_text}"

                    canon_sig = canonicalize_ts_signature(p_text)
                    sig_disc = compute_signature_discriminator(canon_sig)

                    # Section 9 & 13 & 14: base_symbol_type = VARIABLE
                    symbol_type, base_symbol_type, method = self._classify_callable(
                        name=name, node=val_node, is_arrow=True, language=language
                    )

                    metadata: dict[str, Any] = {
                        "evidence": {
                            "node_type": val_node.type,
                            "start_line": start_line,
                            "end_line": end_line,
                        },
                        "extraction_method": "static_ast",
                        "confidence": 1.0,
                        "export_kind": export_kind,
                        "function_kind": "arrow" if val_node.type == "arrow_function" else "expression",
                        "is_callable": True,
                        "declaration_kind": declaration_kind,
                        "is_async": any(c.type == "async" for c in val_node.children),
                    }

                    candidate = SymbolCandidate(
                        project_key=project_key,
                        file_path=file_path,
                        file_rel_path=file_rel_path,
                        name=name,
                        qualified_name=qualified_name,
                        symbol_type=symbol_type,
                        base_symbol_type=base_symbol_type,
                        start_line=start_line,
                        end_line=end_line,
                        start_column=start_col,
                        end_column=end_col,
                        signature=raw_sig,
                        canonical_signature=canon_sig,
                        signature_discriminator=sig_disc,
                        language=language,
                        classification_method=method,
                        modifiers=list(top_modifiers),
                        is_exported=is_exported,
                        export_kind=export_kind,
                        metadata=metadata,
                    )
                    out.append(candidate)

                    # Recurse into arrow function body if statement_block
                    arrow_body = val_node.child_by_field_name("body")
                    if arrow_body and arrow_body.type == "statement_block":
                        self._walk_statements(
                            container_node=arrow_body,
                            code_bytes=code_bytes,
                            file_path=file_path,
                            file_rel_path=file_rel_path,
                            language=language,
                            project_key=project_key,
                            scope_chain=scope_chain + [name],
                            out=out,
                        )
                else:
                    # Regular variable (const / let / var), with destructuring pattern support
                    id_nodes = self._extract_pattern_identifiers(name_node)
                    if not id_nodes:
                        id_nodes = [(name_node.text.decode("utf-8", errors="replace"), name_node)]

                    for id_name, id_node in id_nodes:
                        id_qname = build_qualified_name(id_name, scope_chain=scope_chain)
                        v_start_line = id_node.start_point.row + 1
                        v_end_line = id_node.end_point.row + 1
                        v_start_col = id_node.start_point.column
                        v_end_col = id_node.end_point.column

                        metadata = {
                            "evidence": {
                                "node_type": id_node.type,
                                "start_line": v_start_line,
                                "end_line": v_end_line,
                            },
                            "extraction_method": "static_ast",
                            "confidence": 1.0,
                            "export_kind": export_kind,
                            "declaration_kind": declaration_kind,
                        }

                        candidate = SymbolCandidate(
                            project_key=project_key,
                            file_path=file_path,
                            file_rel_path=file_rel_path,
                            name=id_name,
                            qualified_name=id_qname,
                            symbol_type=SymbolType.VARIABLE.value,
                            base_symbol_type=SymbolType.VARIABLE.value,
                            start_line=v_start_line,
                            end_line=v_end_line,
                            start_column=v_start_col,
                            end_column=v_end_col,
                            signature=None,
                            canonical_signature=None,
                            signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
                            language=language,
                            classification_method="ast_native",
                            modifiers=list(top_modifiers),
                            is_exported=is_exported,
                            export_kind=export_kind,
                            metadata=metadata,
                        )
                        out.append(candidate)

    def _extract_pattern_identifiers(self, node: Node) -> list[tuple[str, Node]]:
        """Extracts (identifier_name, node) tuples from identifier, object_pattern, or array_pattern."""
        res: list[tuple[str, Node]] = []
        if node.type in ("identifier", "shorthand_property_identifier_pattern"):
            res.append((node.text.decode("utf-8", errors="replace"), node))
        elif node.type == "pair_pattern":
            val = node.child_by_field_name("value")
            if val:
                res.extend(self._extract_pattern_identifiers(val))
        elif node.type == "object_assignment_pattern":
            left = node.child_by_field_name("left")
            if left:
                res.extend(self._extract_pattern_identifiers(left))
        elif node.type in ("object_pattern", "array_pattern"):
            for c in node.children:
                if c.type not in ("{", "}", "[", "]", ","):
                    res.extend(self._extract_pattern_identifiers(c))
        return res

    def _classify_callable(
        self,
        name: str,
        node: Node,
        is_arrow: bool,
        language: str,
    ) -> tuple[str, str, str]:
        """Determines (symbol_type, base_symbol_type, classification_method).

        Guarantees:
        - Hook Rule (Section 16): ^use[A-Z0-9].* -> HOOK, classification_method = "name_prefix_rule_v1".
          Preserves base_symbol_type (FUNCTION or VARIABLE).
        - Component Rule (Section 14-15):
          PascalCase name AND contains JSX (element/self-closing/fragment) AND callable
          -> COMPONENT, classification_method = "jsx_function_component_v1".
          Preserves base_symbol_type (FUNCTION or VARIABLE).
        - Anti-False-Positive:
          createMarkup -> FUNCTION (fails PascalCase).
          usefulUtil -> FUNCTION (fails ^use[A-Z0-9]).
        - Native Fallback:
          is_arrow=True -> (VARIABLE, VARIABLE, "ast_native")
          is_arrow=False -> (FUNCTION, FUNCTION, "ast_native")
        """
        base_sym = SymbolType.VARIABLE.value if is_arrow else SymbolType.FUNCTION.value

        # 1. Hook rule: ^use[A-Z0-9].*
        if _HOOK_NAME_RE.match(name):
            return (SymbolType.HOOK.value, base_sym, "name_prefix_rule_v1")

        # 2. Component rule: PascalCase and contains JSX (jsx_element, jsx_self_closing_element, jsx_fragment)
        if language in ["tsx", "jsx"] and _PASCAL_CASE_RE.match(name):
            if self._has_jsx_descendant(node):
                return (SymbolType.COMPONENT.value, base_sym, "jsx_function_component_v1")

        # 3. Default native
        return (base_sym, base_sym, "ast_native")

    def _has_jsx_descendant(self, node: Node) -> bool:
        """Checks if a node has any jsx_element, jsx_self_closing_element, or jsx_fragment descendants."""
        for child in node.children:
            if child.type in ["jsx_element", "jsx_self_closing_element", "jsx_fragment"]:
                return True
            if self._has_jsx_descendant(child):
                return True
        return False

    def _extract_modifiers(self, node: Node) -> list[str]:
        """Extracts modifier strings attached to the node."""
        mods: list[str] = []
        for child in node.children:
            if child.type in [
                "accessibility_modifier",
                "static",
                "async",
                "readonly",
                "abstract",
                "export",
                "default",
                "declare",
            ]:
                mods.append(child.text.decode("utf-8", errors="replace"))
        return mods
