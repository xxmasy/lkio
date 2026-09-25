"""LKIO Java Symbol and Annotation Extractor (B-04 Approved Baseline)
Extracts code symbols from Java source files using Tree-sitter.

Enforces:
- Lock 1: 9 Native Symbol Types (including FIELD and ANNOTATION definition)
- Lock 1b: Annotation usages are stored as Symbol metadata, never independent symbol nodes
- Lock 2: Constructor mapped to METHOD with method_kind="CONSTRUCTOR", name="<init>"
- Lock 3: Standardized '::' lexical delimiter and line-shift immune deterministic Key
- Lock 4: Overload disambiguation via canonicalize_java_signature & 16-hex discriminator
- Lock 5: 1-based line & 0-based col coordinates with static AST evidence
- LOCK-JAVA-01: Record compact constructor signature derived from record components
- LOCK-JAVA-02: Receiver parameter excluded from overload signature
- LOCK-JAVA-03: Record components recorded as CLASS metadata only (no FIELD/accessor expansion)
- LOCK-JAVA-04: Enum constant class body recursively extracted with Outer::Inner::Member scope
"""

import logging
from typing import Any
from tree_sitter import Node, Tree

from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_qualified_name,
    canonicalize_java_signature,
    compute_signature_discriminator,
    normalize_rel_path,
)
from core.parsing.models import SymbolType
from core.parsing.parser_factory import ParserFactory

logger = logging.getLogger(__name__)


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

        # 1. Extract package declaration (Gate B)
        package_name: str | None = None
        for child in tree.root_node.children:
            if child.type == "package_declaration":
                # package_declaration: package com.example.crm;
                for c in child.children:
                    if c.type in ["scoped_identifier", "identifier"]:
                        package_name = c.text.decode("utf-8", errors="replace")
                        break

        # 2. Walk top-level declarations
        self._walk_compilation_unit(
            tree.root_node,
            code_bytes,
            file_path,
            norm_rel_path,
            package_name,
            candidates,
        )

        return candidates

    def _walk_compilation_unit(
        self,
        root_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        out: list[SymbolCandidate],
    ):
        """Walks declarations in the Java compilation unit."""
        for child in root_node.children:
            if child.type == "ERROR":
                logger.warning("Encountered top-level AST ERROR node in %s; skipping node.", file_rel_path)
                continue
            self._process_type_declaration(
                child,
                code_bytes,
                file_path,
                file_rel_path,
                package_name=package_name,
                scope_chain=[],
                out=out,
            )

    def _process_type_declaration(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Processes a type declaration (class, interface, enum, annotation, record)."""
        node_type = node.type

        if node_type == "class_declaration":
            self._handle_class(node, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)
        elif node_type == "interface_declaration":
            self._handle_interface(node, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)
        elif node_type == "enum_declaration":
            self._handle_enum(node, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)
        elif node_type == "annotation_type_declaration":
            self._handle_annotation_definition(node, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)
        elif node_type == "record_declaration":
            self._handle_record(node, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)

    def _build_base_candidate(
        self,
        node: Node,
        file_path: str,
        file_rel_path: str,
        name: str,
        qualified_name: str,
        symbol_type: str,
        base_symbol_type: str,
        modifiers: list[str],
        annotations: list[dict[str, Any]],
        signature: str | None = None,
        canonical_signature: str | None = None,
        signature_discriminator: str | None = None,
        package_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SymbolCandidate:
        """Constructs a SymbolCandidate with standard coordinates, evidence, and metadata."""
        meta = metadata.copy() if metadata else {}
        if package_name:
            meta["package"] = package_name
            meta["package_qualified_name"] = f"{package_name}.{qualified_name}"

        # Export kind from modifiers
        is_exported = "public" in modifiers
        if "public" in modifiers:
            export_kind = "public"
        elif "protected" in modifiers:
            export_kind = "protected"
        elif "private" in modifiers:
            export_kind = "private"
        else:
            export_kind = "package_private"

        meta["export_kind"] = export_kind
        meta["extraction_method"] = "static_ast"
        meta["confidence"] = 1.0
        meta["evidence"] = {
            "node_type": node.type,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "start_point": [node.start_point.row, node.start_point.column],
            "end_point": [node.end_point.row, node.end_point.column],
        }

        disc = signature_discriminator or compute_signature_discriminator(canonical_signature or signature)

        return SymbolCandidate(
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
            canonical_signature=canonical_signature,
            signature_discriminator=disc,
            language="java",
            classification_method="ast_native",
            modifiers=modifiers,
            is_exported=is_exported,
            export_kind=export_kind,
            annotations=annotations,
            metadata=meta,
        )

    def _handle_class(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts CLASS declaration (Gate C)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        metadata: dict[str, Any] = {}
        superclass = node.child_by_field_name("superclass")
        if superclass:
            metadata["superclass"] = superclass.text.decode("utf-8", errors="replace")

        interfaces = node.child_by_field_name("interfaces")
        if interfaces:
            metadata["interfaces"] = interfaces.text.decode("utf-8", errors="replace")

        type_params = node.child_by_field_name("type_parameters")
        if type_params:
            metadata["type_parameters"] = type_params.text.decode("utf-8", errors="replace")

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.CLASS.value,
            base_symbol_type=SymbolType.CLASS.value,
            modifiers=modifiers,
            annotations=annotations,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

        # Walk class body
        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_type_body(
                body_node,
                code_bytes,
                file_path,
                file_rel_path,
                package_name=package_name,
                scope_chain=scope_chain + [name],
                record_components=None,
                out=out,
            )

    def _handle_record(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts Record declaration (LOCK-JAVA-01, LOCK-JAVA-03, Gate C)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        # Extract record components (formal_parameters of the record header)
        record_components: list[dict[str, Any]] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for child in params_node.children:
                if child.type == "formal_parameter":
                    c_type_node = child.child_by_field_name("type")
                    c_name_node = child.child_by_field_name("name")
                    if c_type_node and c_name_node:
                        c_type = c_type_node.text.decode("utf-8", errors="replace")
                        c_name = c_name_node.text.decode("utf-8", errors="replace")
                        _, c_anns = self._extract_modifiers_and_annotations(child)
                        record_components.append({
                            "name": c_name,
                            "type": c_type,
                            "annotations": c_anns,
                        })

        metadata: dict[str, Any] = {
            "class_kind": "record",
            "record_components": record_components,
        }

        interfaces = node.child_by_field_name("interfaces")
        if interfaces:
            metadata["interfaces"] = interfaces.text.decode("utf-8", errors="replace")

        type_params = node.child_by_field_name("type_parameters")
        if type_params:
            metadata["type_parameters"] = type_params.text.decode("utf-8", errors="replace")

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.CLASS.value,
            base_symbol_type=SymbolType.CLASS.value,
            modifiers=modifiers,
            annotations=annotations,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

        # Walk record body (can contain compact_constructor_declaration or regular constructors/methods)
        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_type_body(
                body_node,
                code_bytes,
                file_path,
                file_rel_path,
                package_name=package_name,
                scope_chain=scope_chain + [name],
                record_components=record_components,
                out=out,
            )

    def _handle_interface(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts INTERFACE declaration (Gate D)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        metadata: dict[str, Any] = {}
        for child in node.children:
            if child.type == "extends_interfaces":
                metadata["extends_interfaces"] = child.text.decode("utf-8", errors="replace")
                break

        type_params = node.child_by_field_name("type_parameters")
        if type_params:
            metadata["type_parameters"] = type_params.text.decode("utf-8", errors="replace")

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.INTERFACE.value,
            base_symbol_type=SymbolType.INTERFACE.value,
            modifiers=modifiers,
            annotations=annotations,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

        body_node = node.child_by_field_name("body")
        if body_node:
            self._walk_type_body(
                body_node,
                code_bytes,
                file_path,
                file_rel_path,
                package_name=package_name,
                scope_chain=scope_chain + [name],
                record_components=None,
                out=out,
            )

    def _handle_enum(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts ENUM declaration and constants (Gate E, LOCK-JAVA-04)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        metadata: dict[str, Any] = {}
        interfaces = node.child_by_field_name("interfaces")
        if interfaces:
            metadata["interfaces"] = interfaces.text.decode("utf-8", errors="replace")

        # Parse enum body for enum constants and declarations
        enum_constants: list[dict[str, Any]] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "enum_constant":
                    c_name_node = child.child_by_field_name("name")
                    if c_name_node:
                        c_name = c_name_node.text.decode("utf-8", errors="replace")
                        args_node = child.child_by_field_name("arguments")
                        c_args = args_node.text.decode("utf-8", errors="replace") if args_node else None
                        _, c_anns = self._extract_modifiers_and_annotations(child)
                        enum_constants.append({
                            "name": c_name,
                            "arguments": c_args,
                            "annotations": c_anns,
                        })

                        # LOCK-JAVA-04: Enum Constant Class Body Recursion
                        c_body = child.child_by_field_name("body")
                        if not c_body:
                            for c_child in child.children:
                                if c_child.type == "class_body":
                                    c_body = c_child
                                    break
                        if c_body:
                            self._walk_type_body(
                                c_body,
                                code_bytes,
                                file_path,
                                file_rel_path,
                                package_name=package_name,
                                scope_chain=scope_chain + [name, c_name],
                                record_components=None,
                                out=out,
                            )

                elif child.type == "enum_body_declarations":
                    # Internal fields, constructors, methods in enum
                    self._walk_type_body(
                        child,
                        code_bytes,
                        file_path,
                        file_rel_path,
                        package_name=package_name,
                        scope_chain=scope_chain + [name],
                        record_components=None,
                        out=out,
                    )

        metadata["enum_constants"] = enum_constants

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.ENUM.value,
            base_symbol_type=SymbolType.ENUM.value,
            modifiers=modifiers,
            annotations=annotations,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

    def _handle_annotation_definition(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts ANNOTATION definition (@interface Foo) (Gate F, Lock 1)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        # Extract annotation elements from annotation_type_body
        elements: list[dict[str, Any]] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "annotation_type_element_declaration":
                    elem_type_node = child.child_by_field_name("type")
                    elem_name_node = child.child_by_field_name("name")
                    if elem_name_node:
                        e_name = elem_name_node.text.decode("utf-8", errors="replace")
                        e_type = elem_type_node.text.decode("utf-8", errors="replace") if elem_type_node else "void"
                        e_val_node = child.child_by_field_name("value")
                        e_default = e_val_node.text.decode("utf-8", errors="replace") if e_val_node else None
                        elements.append({
                            "name": e_name,
                            "type": e_type,
                            "default": e_default,
                        })

        metadata = {"elements": elements}

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.ANNOTATION.value,
            base_symbol_type=SymbolType.ANNOTATION.value,
            modifiers=modifiers,
            annotations=annotations,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

    def _walk_type_body(
        self,
        body_node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        record_components: list[dict[str, Any]] | None,
        out: list[SymbolCandidate],
    ):
        """Walks declarations inside class, interface, record, or enum bodies."""
        for member in body_node.children:
            m_type = member.type

            if m_type == "method_declaration":
                self._handle_method(member, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)
            elif m_type == "constructor_declaration":
                self._handle_constructor(member, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)
            elif m_type == "compact_constructor_declaration":
                self._handle_compact_constructor(
                    member, code_bytes, file_path, file_rel_path, package_name, scope_chain, record_components, out
                )
            elif m_type in ["field_declaration", "constant_declaration"]:
                self._handle_field(member, code_bytes, file_path, file_rel_path, package_name, scope_chain, out)
            elif m_type in [
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "annotation_type_declaration",
                "record_declaration",
            ]:
                self._process_type_declaration(
                    member,
                    code_bytes,
                    file_path,
                    file_rel_path,
                    package_name=package_name,
                    scope_chain=scope_chain,
                    out=out,
                )

    def _handle_method(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts METHOD declaration (Gate G, LOCK-JAVA-02)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        name = name_node.text.decode("utf-8", errors="replace")
        qualified_name = build_qualified_name(name, scope_chain=scope_chain)

        ret_node = node.child_by_field_name("type")
        ret_type = ret_node.text.decode("utf-8", errors="replace") if ret_node else "void"

        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        # Parse parameters & filter receiver_parameter (LOCK-JAVA-02)
        params_meta, raw_sig, canon_sig, receiver_param = self._extract_parameters(node)

        metadata: dict[str, Any] = {
            "return_type": ret_type,
            "parameters": params_meta,
        }
        if receiver_param:
            metadata["receiver_parameter"] = receiver_param

        # Throws clause
        for child in node.children:
            if child.type == "throws":
                ex_types = [
                    c.text.decode("utf-8", errors="replace")
                    for c in child.children
                    if c.type not in ["throws", ","]
                ]
                metadata["throws"] = ex_types
                break

        type_params = node.child_by_field_name("type_parameters")
        if type_params:
            metadata["type_parameters"] = type_params.text.decode("utf-8", errors="replace")

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.METHOD.value,
            base_symbol_type=SymbolType.METHOD.value,
            modifiers=modifiers,
            annotations=annotations,
            signature=raw_sig,
            canonical_signature=canon_sig,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

    def _handle_constructor(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts standard constructor declaration (Gate H, Lock 2)."""
        name_node = node.child_by_field_name("name")
        raw_name = name_node.text.decode("utf-8", errors="replace") if name_node else (scope_chain[-1] if scope_chain else "<init>")
        name = "<init>"
        qualified_name = build_qualified_name("<init>", scope_chain=scope_chain)

        modifiers, annotations = self._extract_modifiers_and_annotations(node)
        params_meta, raw_sig, canon_sig, receiver_param = self._extract_parameters(node)

        metadata: dict[str, Any] = {
            "raw_name": raw_name,
            "method_kind": "CONSTRUCTOR",
            "parameters": params_meta,
        }
        if receiver_param:
            metadata["receiver_parameter"] = receiver_param

        # Throws clause
        for child in node.children:
            if child.type == "throws":
                ex_types = [
                    c.text.decode("utf-8", errors="replace")
                    for c in child.children
                    if c.type not in ["throws", ","]
                ]
                metadata["throws"] = ex_types
                break

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.METHOD.value,
            base_symbol_type=SymbolType.METHOD.value,
            modifiers=modifiers,
            annotations=annotations,
            signature=raw_sig,
            canonical_signature=canon_sig,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

    def _handle_compact_constructor(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        record_components: list[dict[str, Any]] | None,
        out: list[SymbolCandidate],
    ):
        """Extracts Record Compact Constructor (LOCK-JAVA-01, Gate H)."""
        name_node = node.child_by_field_name("name")
        raw_name = name_node.text.decode("utf-8", errors="replace") if name_node else (scope_chain[-1] if scope_chain else "<init>")
        name = "<init>"
        qualified_name = build_qualified_name("<init>", scope_chain=scope_chain)

        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        # LOCK-JAVA-01: Derive canonical signature from record_components
        if record_components:
            comp_types = [comp["type"] for comp in record_components]
            raw_sig = f"({', '.join(comp_types)})"
            canon_sig = canonicalize_java_signature(raw_sig)
        else:
            raw_sig = "()"
            canon_sig = "()"

        metadata: dict[str, Any] = {
            "raw_name": raw_name,
            "method_kind": "CONSTRUCTOR",
            "constructor_form": "compact",
            "parameters": record_components or [],
        }

        candidate = self._build_base_candidate(
            node=node,
            file_path=file_path,
            file_rel_path=file_rel_path,
            name=name,
            qualified_name=qualified_name,
            symbol_type=SymbolType.METHOD.value,
            base_symbol_type=SymbolType.METHOD.value,
            modifiers=modifiers,
            annotations=annotations,
            signature=raw_sig,
            canonical_signature=canon_sig,
            package_name=package_name,
            metadata=metadata,
        )
        out.append(candidate)

    def _handle_field(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        package_name: str | None,
        scope_chain: list[str],
        out: list[SymbolCandidate],
    ):
        """Extracts FIELD declaration, splitting multi-variable declarators (Gate I)."""
        modifiers, annotations = self._extract_modifiers_and_annotations(node)

        type_node = node.child_by_field_name("type")
        type_str = type_node.text.decode("utf-8", errors="replace") if type_node else "Object"

        # If constant_declaration in interface with no explicit modifiers, implicitly public static final
        if node.type == "constant_declaration" and not modifiers:
            modifiers = ["public", "static", "final"]

        # Loop through variable declarators (int a = 1, b = 2;)
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                name = name_node.text.decode("utf-8", errors="replace")
                qualified_name = build_qualified_name(name, scope_chain=scope_chain)

                metadata = {
                    "field_type": type_str,
                    "is_static": "static" in modifiers,
                    "is_final": "final" in modifiers,
                }

                init_val = child.child_by_field_name("value")
                if init_val:
                    metadata["initial_value"] = init_val.text.decode("utf-8", errors="replace")

                candidate = self._build_base_candidate(
                    node=child,
                    file_path=file_path,
                    file_rel_path=file_rel_path,
                    name=name,
                    qualified_name=qualified_name,
                    symbol_type=SymbolType.FIELD.value,
                    base_symbol_type=SymbolType.FIELD.value,
                    modifiers=modifiers,
                    annotations=annotations,
                    signature=type_str,
                    canonical_signature=type_str,
                    signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
                    package_name=package_name,
                    metadata=metadata,
                )
                out.append(candidate)

    def _extract_parameters(
        self, node: Node
    ) -> tuple[list[dict[str, Any]], str, str, dict[str, Any] | None]:
        """Extracts parameters, filtering out receiver_parameter (LOCK-JAVA-02).

        Returns:
            (params_metadata, raw_signature, canonical_signature, receiver_parameter_metadata)
        """
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return [], "()", "()", None

        params_meta: list[dict[str, Any]] = []
        regular_param_strings: list[str] = []
        receiver_param: dict[str, Any] | None = None

        for child in params_node.children:
            if child.type == "receiver_parameter":
                # LOCK-JAVA-02: Receiver parameter e.g. 'MyClass this'
                r_type = ""
                r_name = "this"
                for c in child.children:
                    if c.type in ["type_identifier", "scoped_type_identifier", "generic_type"]:
                        r_type = c.text.decode("utf-8", errors="replace")
                    elif c.type == "this":
                        r_name = "this"
                _, r_anns = self._extract_modifiers_and_annotations(child)
                receiver_param = {
                    "type": r_type,
                    "name": r_name,
                    "annotations": r_anns,
                }

            elif child.type == "formal_parameter":
                p_type_node = child.child_by_field_name("type")
                p_name_node = child.child_by_field_name("name")
                if p_name_node:
                    p_name = p_name_node.text.decode("utf-8", errors="replace")
                    p_type = p_type_node.text.decode("utf-8", errors="replace") if p_type_node else "?"
                    _, p_anns = self._extract_modifiers_and_annotations(child)
                    params_meta.append({
                        "name": p_name,
                        "type": p_type,
                        "annotations": p_anns,
                        "is_varargs": False,
                    })
                    regular_param_strings.append(f"{p_type} {p_name}")

            elif child.type == "spread_parameter":
                # Varargs e.g. 'String... lines'
                p_type = "Object..."
                p_name = "args"
                for sc in child.children:
                    if sc.type in ["type_identifier", "generic_type", "array_type"]:
                        p_type = f"{sc.text.decode('utf-8', errors='replace')}..."
                    elif sc.type == "variable_declarator":
                        name_node = sc.child_by_field_name("name")
                        if name_node:
                            p_name = name_node.text.decode("utf-8", errors="replace")

                _, p_anns = self._extract_modifiers_and_annotations(child)
                params_meta.append({
                    "name": p_name,
                    "type": p_type,
                    "annotations": p_anns,
                    "is_varargs": True,
                })
                regular_param_strings.append(f"{p_type} {p_name}")

        raw_signature = f"({', '.join(regular_param_strings)})"
        canonical_signature = canonicalize_java_signature(raw_signature)

        return params_meta, raw_signature, canonical_signature, receiver_param

    def _extract_modifiers_and_annotations(
        self, node: Node
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Extracts text modifiers and structured annotation metadata attached to a node (Lock 1b)."""
        modifiers: list[str] = []
        annotations: list[dict[str, Any]] = []

        mods_node = node.child_by_field_name("modifiers")
        if not mods_node:
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
                "native",
                "strictfp",
            ]:
                modifiers.append(c_type)

        return modifiers, annotations
