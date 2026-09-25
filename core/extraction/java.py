"""LKIO Java Symbol and Annotation Extractor
Extracts code symbols from Java source files using Tree-sitter.
Enforces:
- Lock 1: 9 Native Symbol Types (including FIELD and ANNOTATION definition)
- Lock 1b: Annotation usages are stored as Symbol metadata, not independent symbol nodes
- Lock 3: Deterministic signature discriminator (line-shift immune)
"""

from typing import Any
from tree_sitter import Node, Tree
from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import compute_signature_discriminator, normalize_rel_path
from core.parsing.models import SymbolType
from core.parsing.parser_factory import ParserFactory


class JavaExtractor:
    """Extracts symbols and annotation metadata from Java source code."""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.parser_factory = parser_factory or ParserFactory()

    def extract(
        self,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str = "java",
    ) -> list[SymbolCandidate]:
        """Parses Java code bytes and extracts all symbol candidates."""
        tree = self.parser_factory.get("java").parse(code_bytes)
        candidates: list[SymbolCandidate] = []
        norm_rel_path = normalize_rel_path(file_rel_path)

        self._walk_root(
            tree.root_node,
            code_bytes,
            file_path,
            norm_rel_path,
            candidates,
        )
        return candidates

    def _walk_root(
        self,
        root_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        out: list[SymbolCandidate],
    ):
        """Walks top-level declarations in the Java compilation unit."""
        for child in root_node.children:
            self._process_type_declaration(
                child,
                code_bytes,
                file_path,
                file_rel_path,
                parent_prefix="",
                out=out,
            )

    def _process_type_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        node_type = node.type

        if node_type == "class_declaration":
            self._handle_class(node, code_bytes, file_path, file_rel_path, parent_prefix, out)
        elif node_type == "interface_declaration":
            self._handle_interface(node, code_bytes, file_path, file_rel_path, parent_prefix, out)
        elif node_type == "enum_declaration":
            self._handle_enum(node, code_bytes, file_path, file_rel_path, parent_prefix, out)
        elif node_type == "annotation_type_declaration":
            self._handle_annotation_definition(node, code_bytes, file_path, file_rel_path, parent_prefix, out)

    def _handle_class(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        is_exported = "public" in modifiers

        # Heritage (superclass, interfaces)
        superclass = node.child_by_field_name("superclass")
        interfaces = node.child_by_field_name("interfaces")
        metadata: dict[str, Any] = {}
        if superclass:
            metadata["superclass"] = superclass.text.decode("utf-8", errors="replace")
        if interfaces:
            metadata["interfaces"] = interfaces.text.decode("utf-8", errors="replace")

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
                language="java",
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                annotations=annotations,
                metadata=metadata,
            )
        )

        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_type_body(
                body_node,
                code_bytes,
                file_path,
                file_rel_path,
                class_qname=qualified_name,
                out=out,
            )

    def _handle_interface(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        is_exported = "public" in modifiers

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
                language="java",
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                annotations=annotations,
            )
        )

        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_type_body(
                body_node,
                code_bytes,
                file_path,
                file_rel_path,
                class_qname=qualified_name,
                out=out,
            )

    def _handle_enum(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        is_exported = "public" in modifiers

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
                language="java",
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                annotations=annotations,
            )
        )

        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_type_body(
                body_node,
                code_bytes,
                file_path,
                file_rel_path,
                class_qname=qualified_name,
                out=out,
            )

    def _handle_annotation_definition(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        parent_prefix: str,
        out: list[SymbolCandidate],
    ):
        """Handles Java @interface Annotation definition. (Lock 1)"""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{parent_prefix}{name}" if parent_prefix else name

        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        is_exported = "public" in modifiers

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.ANNOTATION.value,
                base_symbol_type=SymbolType.ANNOTATION.value,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=None,
                signature_discriminator=compute_signature_discriminator(None),
                language="java",
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                annotations=annotations,
            )
        )

    def _walk_type_body(
        self,
        body_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        class_qname: str,
        out: list[SymbolCandidate],
    ):
        """Walks methods, fields, constructors, and nested types inside a type body."""
        for member in body_node.children:
            m_type = member.type

            if m_type == "method_declaration":
                self._handle_method(member, code_bytes, file_path, file_rel_path, class_qname, out)
            elif m_type == "constructor_declaration":
                self._handle_constructor(member, code_bytes, file_path, file_rel_path, class_qname, out)
            elif m_type == "field_declaration":
                self._handle_field(member, code_bytes, file_path, file_rel_path, class_qname, out)
            elif m_type in [
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "annotation_type_declaration",
            ]:
                self._process_type_declaration(
                    member,
                    code_bytes,
                    file_path,
                    file_rel_path,
                    parent_prefix=f"{class_qname}.",
                    out=out,
                )

    def _handle_method(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        class_qname: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = f"{class_qname}.{name}"

        params_node = node.child_by_field_name("parameters")
        ret_node = node.child_by_field_name("type")
        p_text = params_node.text.decode("utf-8", errors="replace") if params_node else "()"
        r_text = ret_node.text.decode("utf-8", errors="replace") if ret_node else "void"
        sig = f"{p_text}:{r_text}"

        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        is_exported = "public" in modifiers

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.METHOD.value,
                base_symbol_type=SymbolType.METHOD.value,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=sig,
                signature_discriminator=compute_signature_discriminator(sig),
                language="java",
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                annotations=annotations,
            )
        )

    def _handle_constructor(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        class_qname: str,
        out: list[SymbolCandidate],
    ):
        name_node = node.child_by_field_name("name")
        raw_name = name_node.text.decode("utf-8", errors="replace") if name_node else class_qname.split(".")[-1]
        name = "<init>"
        qualified_name = f"{class_qname}.<init>"

        params_node = node.child_by_field_name("parameters")
        p_text = params_node.text.decode("utf-8", errors="replace") if params_node else "()"
        sig = f"{p_text}:void"

        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        is_exported = "public" in modifiers

        out.append(
            SymbolCandidate(
                file_path=file_path,
                file_rel_path=file_rel_path,
                name=name,
                qualified_name=qualified_name,
                symbol_type=SymbolType.METHOD.value,
                base_symbol_type=SymbolType.METHOD.value,
                start_line=node.start_point.row + 1,
                end_line=node.end_point.row + 1,
                start_column=node.start_point.column,
                end_column=node.end_point.column,
                signature=sig,
                signature_discriminator=compute_signature_discriminator(sig),
                language="java",
                classification_method="ast_native",
                modifiers=modifiers,
                is_exported=is_exported,
                annotations=annotations,
            )
        )

    def _handle_field(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        class_qname: str,
        out: list[SymbolCandidate],
    ):
        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        is_exported = "public" in modifiers

        type_node = node.child_by_field_name("type")
        type_str = type_node.text.decode("utf-8", errors="replace") if type_node else None

        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                name = name_node.text.decode("utf-8", errors="replace")
                qualified_name = f"{class_qname}.{name}"

                metadata = {"field_type": type_str} if type_str else {}

                out.append(
                    SymbolCandidate(
                        file_path=file_path,
                        file_rel_path=file_rel_path,
                        name=name,
                        qualified_name=qualified_name,
                        symbol_type=SymbolType.FIELD.value,
                        base_symbol_type=SymbolType.FIELD.value,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                        start_column=child.start_point.column,
                        end_column=child.end_point.column,
                        signature=type_str,
                        signature_discriminator=compute_signature_discriminator(type_str),
                        language="java",
                        classification_method="ast_native",
                        modifiers=modifiers,
                        is_exported=is_exported,
                        annotations=annotations,
                        metadata=metadata,
                    )
                )

    def _extract_modifiers_and_annotations(
        self, node: Node
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Extracts text modifiers and structured annotation metadata attached to a node."""
        modifiers: list[str] = []
        annotations: list[dict[str, Any]] = []

        mods_node = node.child_by_field_name("modifiers")
        if not mods_node:
            # Check direct children for modifiers or annotations
            for c in node.children:
                if c.type == "modifiers":
                    mods_node = c
                    break

        if not mods_node:
            return modifiers, annotations

        for child in mods_node.children:
            c_type = child.type
            if c_type in ["marker_annotation", "annotation"]:
                name_node = child.child_by_field_name("name")
                ann_name = name_node.text.decode("utf-8", errors="replace") if name_node else ""
                ann_raw = child.text.decode("utf-8", errors="replace")

                args_node = child.child_by_field_name("arguments")
                ann_args = args_node.text.decode("utf-8", errors="replace") if args_node else None

                annotations.append(
                    {
                        "name": ann_name,
                        "raw": ann_raw,
                        "arguments": ann_args,
                    }
                )
            elif c_type in [
                "public",
                "private",
                "protected",
                "static",
                "final",
                "abstract",
                "synchronized",
                "transient",
                "volatile",
                "default",
            ]:
                modifiers.append(c_type)

        return modifiers, annotations
