"""LKIO TypeScript / JavaScript Symbol Extractor
Extracts code symbols from TS, TSX, JS, and JSX files using Tree-sitter.
Enforces:
- Lock 1: 9 Native Symbol Types
- Lock 2: Rule Classifications (HOOK, COMPONENT) retain controlled base_symbol_type
- Lock 3: Deterministic signature discriminator (line-shift immune)
"""

import re
from typing import Any
from tree_sitter import Node, Tree
from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import compute_signature_discriminator, normalize_rel_path
from core.parsing.models import LanguageType, SymbolType
from core.parsing.parser_factory import ParserFactory

_HOOK_NAME_RE = re.compile(r"^use[A-Z0-9].*")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")


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
    ) -> list[SymbolCandidate]:
        """Parses source code bytes and extracts all symbol candidates."""
        lang_key = language.lower()
        if lang_key not in ["typescript", "tsx", "javascript", "jsx"]:
            lang_key = "typescript"

        tree = self.parser_factory.get(lang_key).parse(code_bytes)
        candidates: list[SymbolCandidate] = []
        norm_rel_path = normalize_rel_path(file_rel_path)

        self._walk_root(
            tree.root_node,
            code_bytes,
            file_path,
            norm_rel_path,
            lang_key,
            candidates,
        )
        return candidates

    def _walk_root(
        self,
        root_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        out: list[SymbolCandidate],
    ):
        """Walks top-level statements of the program."""
        for child in root_node.children:
            is_exported = False
            target_node = child

            if child.type == "export_statement":
                is_exported = True
                # Find declaration child inside export_statement
                for sub in child.children:
                    if sub.type in [
                        "function_declaration",
                        "class_declaration",
                        "interface_declaration",
                        "type_alias_declaration",
                        "enum_declaration",
                        "lexical_declaration",
                        "variable_declaration",
                    ]:
                        target_node = sub
                        break

            self._process_declaration(
                target_node,
                code_bytes,
                file_path,
                file_rel_path,
                language,
                is_exported,
                parent_prefix="",
                out=out,
            )

    def _process_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        is_exported: bool,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        """Processes a single declaration node."""
        node_type = node.type

        if node_type == "function_declaration":
            self._handle_function_declaration(
                node, code_bytes, file_path, file_rel_path, language, is_exported, parent_prefix, out
            )
        elif node_type == "class_declaration":
            self._handle_class_declaration(
                node, code_bytes, file_path, file_rel_path, language, is_exported, parent_prefix, out
            )
        elif node_type == "interface_declaration":
            self._handle_interface_declaration(
                node, code_bytes, file_path, file_rel_path, language, is_exported, parent_prefix, out
            )
        elif node_type == "type_alias_declaration":
            self._handle_type_alias_declaration(
                node, code_bytes, file_path, file_rel_path, language, is_exported, parent_prefix, out
            )
        elif node_type == "enum_declaration":
            self._handle_enum_declaration(
                node, code_bytes, file_path, file_rel_path, language, is_exported, parent_prefix, out
            )
        elif node_type in ["lexical_declaration", "variable_declaration"]:
            self._handle_variable_declaration(
                node, code_bytes, file_path, file_rel_path, language, is_exported, parent_prefix, out
            )

    def _handle_function_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        is_exported: bool,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        params_node = node.child_by_field_name("parameters")
        ret_node = node.child_by_field_name("return_type")

        params_text = params_node.text.decode("utf-8", errors="replace") if params_node else "()"
        ret_text = ret_node.text.decode("utf-8", errors="replace") if ret_node else ""
        signature = f"{params_text}{ret_text}"

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")

        # Classifications: Hook or Component
        symbol_type, base_symbol_type, method = self._classify_function(name, node, language)

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=symbol_type,
                base_symbol_type=base_symbol_type,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=signature,
                signature_discriminator=compute_signature_discriminator(signature),
                language=language,
                classification_method=method,
                modifiers=modifiers,
                is_exported=is_exported,
            )
        )

    def _handle_class_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        is_exported: bool,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")

        # Check superclass/heritage
        heritage = []
        for child in node.children:
            if child.type == "class_heritage":
                heritage.append(child.text.decode("utf-8", errors="replace"))

        metadata = {"heritage": heritage} if heritage else {}

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.CLASS.value,
                base_symbol_type=SymbolType.CLASS.value,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                signature_discriminator=compute_signature_discriminator(None),
                language=language,
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                metadata=metadata,
            )
        )

        # Process class body members
        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_class_body(
                body_node,
                code_bytes,
                file_path,
                file_rel_path,
                language,
                class_qname=qualified_name,
                out=out,
            )

    def _walk_class_body(
        self,
        body_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        class_qname: str,
        out: list[SymbolCandidate],
    ):
        for member in body_node.children:
            if member.type == "method_definition":
                m_name_node = member.child_by_field_name("name")
                if not m_name_node:
                    continue
                m_name = m_name_node.text.decode("utf-8", errors="replace")
                m_qname = f"{class_qname}.{m_name}"

                params_node = member.child_by_field_name("parameters")
                ret_node = member.child_by_field_name("return_type")
                p_text = params_node.text.decode("utf-8", errors="replace") if params_node else "()"
                r_text = ret_node.text.decode("utf-8", errors="replace") if ret_node else ""
                sig = f"{p_text}{r_text}"

                m_mods = self._extract_modifiers(member)

                out.append(
                    SymbolCandidate(
                        file_path=file_path,
                        file_rel_path=file_rel_path,
                        name=m_name,
                        qualified_name=m_qname,
                        symbol_type=SymbolType.METHOD.value,
                        base_symbol_type=SymbolType.METHOD.value,
                        start_line=member.start_point.row + 1,
                        end_line=member.end_point.row + 1,
                        start_column=member.start_point.column,
                        end_column=member.end_point.column,
                        signature=sig,
                        signature_discriminator=compute_signature_discriminator(sig),
                        language=language,
                        classification_method="ast_native",
                        modifiers=m_mods,
                        is_exported=False,
                    )
                )

            elif member.type in ["public_field_definition", "field_definition"]:
                f_name_node = member.child_by_field_name("name")
                if not f_name_node:
                    # Fallback to first property_identifier child
                    for c in member.children:
                        if c.type == "property_identifier":
                            f_name_node = c
                            break
                if not f_name_node:
                    continue
                f_name = f_name_node.text.decode("utf-8", errors="replace")
                f_qname = f"{class_qname}.{f_name}"
                f_mods = self._extract_modifiers(member)

                out.append(
                    SymbolCandidate(
                        file_path=file_path,
                        file_rel_path=file_rel_path,
                        name=f_name,
                        qualified_name=f_qname,
                        symbol_type=SymbolType.FIELD.value,
                        base_symbol_type=SymbolType.FIELD.value,
                        start_line=member.start_point.row + 1,
                        end_line=member.end_point.row + 1,
                        start_column=member.start_point.column,
                        end_column=member.end_point.column,
                        signature=None,
                        signature_discriminator=compute_signature_discriminator(None),
                        language=language,
                        classification_method="ast_native",
                        modifiers=f_mods,
                        is_exported=False,
                    )
                )

    def _handle_interface_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        is_exported: bool,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.INTERFACE.value,
                base_symbol_type=SymbolType.INTERFACE.value,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                signature_discriminator=compute_signature_discriminator(None),
                language=language,
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
            )
        )

    def _handle_type_alias_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        is_exported: bool,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.TYPE.value,
                base_symbol_type=SymbolType.TYPE.value,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                signature_discriminator=compute_signature_discriminator(None),
                language=language,
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
            )
        )

    def _handle_enum_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        is_exported: bool,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in modifiers:
            modifiers.append("export")

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.ENUM.value,
                base_symbol_type=SymbolType.ENUM.value,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                signature_discriminator=compute_signature_discriminator(None),
                language=language,
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
            )
        )

    def _handle_variable_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str,
        is_exported: bool,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        top_modifiers = self._extract_modifiers(node)
        if is_exported and "export" not in top_modifiers:
            top_modifiers.append("export")

        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                name = name_node.text.decode("utf-8", errors="replace")
                qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

                val_node = child.child_by_field_name("value")

                if val_node and val_node.type in ["arrow_function", "function_expression"]:
                    # Treat function stored in variable as FUNCTION (or Hook/Component)
                    params_node = val_node.child_by_field_name("parameters")
                    ret_node = val_node.child_by_field_name("return_type")
                    p_text = params_node.text.decode("utf-8", errors="replace") if params_node else "()"
                    r_text = ret_node.text.decode("utf-8", errors="replace") if ret_node else ""
                    sig = f"{p_text}{r_text}"

                    sym_type, base_sym_type, method = self._classify_function(name, val_node, language)

                    out.append(
                        SymbolCandidate(
                            file_path=file_path,
                            file_rel_path=file_rel_path,
                            name=name,
                            qualified_name=qualified_name,
                            symbol_type=sym_type,
                            base_symbol_type=base_sym_type,
                            start_line=child.start_point.row + 1,
                            end_line=child.end_point.row + 1,
                            start_column=child.start_point.column,
                            end_column=child.end_point.column,
                            signature=sig,
                            signature_discriminator=compute_signature_discriminator(sig),
                            language=language,
                            classification_method=method,
                            modifiers=list(top_modifiers),
                            is_exported=is_exported,
                        )
                    )
                else:
                    # Regular variable
                    out.append(
                        SymbolCandidate(
                            file_path=file_path,
                            file_rel_path=file_rel_path,
                            name=name,
                            qualified_name=qualified_name,
                            symbol_type=SymbolType.VARIABLE.value,
                            base_symbol_type=SymbolType.VARIABLE.value,
                            start_line=child.start_point.row + 1,
                            end_line=child.end_point.row + 1,
                            start_column=child.start_point.column,
                            end_column=child.end_point.column,
                            signature=None,
                            signature_discriminator=compute_signature_discriminator(None),
                            language=language,
                            classification_method="ast_native",
                            modifiers=list(top_modifiers),
                            is_exported=is_exported,
                        )
                    )

    def _classify_function(
        self,
        name: str,
        func_node: Node,
        language: str,
    ) -> tuple[str, str, str]:
        """Determines (symbol_type, base_symbol_type, classification_method).
        Guarantees Lock 2: base_symbol_type is strictly FUNCTION.
        """
        # 1. Hook rule: useXxx
        if _HOOK_NAME_RE.match(name):
            return (SymbolType.HOOK.value, SymbolType.FUNCTION.value, "name_prefix_rule")

        # 2. Component rule: PascalCase and returns JSX / contains JSX
        if language in ["tsx", "jsx"] and _PASCAL_CASE_RE.match(name):
            if self._has_jsx_descendant(func_node):
                return (SymbolType.COMPONENT.value, SymbolType.FUNCTION.value, "jsx_return_rule")

        # 3. Default native function
        return (SymbolType.FUNCTION.value, SymbolType.FUNCTION.value, "ast_native")

    def _has_jsx_descendant(self, node: Node) -> bool:
        """Checks if a node has any jsx_element or jsx_self_closing_element descendants."""
        for child in node.children:
            if child.type in ["jsx_element", "jsx_self_closing_element"]:
                return True
            if self._has_jsx_descendant(child):
                return True
        return False

    def _extract_modifiers(self, node: Node) -> list[str]:
        """Extracts modifier strings attached to the node."""
        mods = []
        for child in node.children:
            if child.type in [
                "accessibility_modifier",
                "static",
                "async",
                "readonly",
                "abstract",
                "export",
            ]:
                mods.append(child.text.decode("utf-8", errors="replace"))
        return mods
