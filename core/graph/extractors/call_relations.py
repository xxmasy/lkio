"""Invocation Relations Extractor (C-06)
Extracts function, method, and constructor calls across TypeScript, JavaScript, Java, and Vue SFC.

Enforces:
- LOCK-GRAPH-04: Static Syntactic Extraction (pure AST call expressions, zero inference mixing).
- LOCK-GRAPH-09: Relational Edge Granularity (multiple call sites aggregated into single RelationCandidate).
- LOCK-GRAPH-11: Subject is enclosing function/method symbol or file; target is callee name.
"""

from decimal import Decimal
import logging
from typing import Any
from tree_sitter import Node

from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_qualified_name,
)
from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)
from core.graph.persistence import merge_relation_candidates
from core.parsing.parser_factory import ParserFactory
from core.parsing.sfc_block_slicer import SfcBlockSlicer

logger = logging.getLogger(__name__)


class InvocationRelationExtractor:
    """Extracts syntactic invocation (call) relations from source code ASTs."""

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
    ) -> list[RelationCandidate]:
        """Extracts call relations and returns candidates aggregated per logical edge (LOCK-GRAPH-09)."""
        lang = language.lower()
        raw_candidates: list[RelationCandidate] = []

        if lang == "java":
            raw_candidates = self._extract_java_calls(code_bytes, project_key, file_rel_path)
        elif lang in {"typescript", "javascript", "tsx", "jsx"}:
            raw_candidates = self._extract_ts_calls(code_bytes, lang, project_key, file_rel_path)
        elif lang == "vue":
            raw_candidates = self._extract_vue_calls(code_bytes, project_key, file_rel_path)
        else:
            return []

        # Merge occurrences for identical edges (LOCK-GRAPH-09)
        return merge_relation_candidates(raw_candidates)

    # =========================================================================
    # Java Invocation Extraction
    # =========================================================================
    def _extract_java_calls(
        self,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        parser = self.parser_factory.get("java")
        tree = parser.parse(code_bytes)
        root = tree.root_node

        file_subject_key = f"FILE:{project_key}:{file_rel_path}"
        results: list[RelationCandidate] = []

        self._traverse_java_calls(
            root, code_bytes, project_key, file_rel_path, file_subject_key, [], results
        )
        return results

    def _traverse_java_calls(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        current_subject_key: str,
        scope_prefix: list[str],
        results: list[RelationCandidate],
    ):
        for child in node.children:
            next_subject = current_subject_key
            next_scope = scope_prefix

            if child.type in {"class_declaration", "interface_declaration", "record_declaration", "enum_declaration"}:
                name_node = child.child_by_field_name("name")
                if name_node:
                    cname = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                    next_scope = scope_prefix + [cname]

            elif child.type in {"method_declaration", "constructor_declaration"}:
                name_node = child.child_by_field_name("name")
                if name_node:
                    mname = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                    qual_parts = scope_prefix + [mname]
                    qual_name = ".".join(qual_parts)
                    entity_type = "CONSTRUCTOR" if child.type == "constructor_declaration" else "METHOD"
                    next_subject = f"SYMBOL:{project_key}:{file_rel_path}:{entity_type}:{qual_name}:{EMPTY_SIGNATURE_DISCRIMINATOR}"
                    next_scope = qual_parts

            elif child.type == "method_invocation":
                self._record_java_method_invocation(child, code_bytes, project_key, file_rel_path, current_subject_key, results)

            elif child.type == "object_creation_expression":
                self._record_java_constructor_call(child, code_bytes, project_key, file_rel_path, current_subject_key, results)

            # Recurse
            if child.child_count > 0:
                self._traverse_java_calls(
                    child, code_bytes, project_key, file_rel_path, next_subject, next_scope, results
                )

    def _record_java_method_invocation(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        subject_key: str,
        results: list[RelationCandidate],
    ):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        method_name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
        obj_node = node.child_by_field_name("object")
        if obj_node:
            obj_name = code_bytes[obj_node.start_byte : obj_node.end_byte].decode("utf-8", errors="replace")
            raw_target = f"{obj_name}.{method_name}"
        else:
            raw_target = method_name

        args_node = node.child_by_field_name("arguments")
        arg_count = self._count_args(args_node)

        occ = SourceOccurrence(
            line=name_node.start_point.row + 1,
            column=name_node.start_point.column,
            argument_count=arg_count,
        )

        results.append(
            RelationCandidate(
                project_key=project_key,
                subject_entity_key=subject_key,
                predicate=RelationPredicate.CALLS,
                normalized_raw_target=raw_target,
                relation_kind=RelationKind.STATIC,
                confidence=Decimal("1.00000"),
                resolution_status=ResolutionStatus.UNRESOLVED,
                occurrences=(occ,),
                source_file_rel_path=file_rel_path,
                metadata={"call_type": "method_invocation"},
            )
        )

    def _record_java_constructor_call(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        subject_key: str,
        results: list[RelationCandidate],
    ):
        type_node = node.child_by_field_name("type")
        if not type_node:
            return

        type_name = code_bytes[type_node.start_byte : type_node.end_byte].decode("utf-8", errors="replace")
        type_name = type_name.split("<")[0].strip()
        args_node = node.child_by_field_name("arguments")
        arg_count = self._count_args(args_node)

        occ = SourceOccurrence(
            line=type_node.start_point.row + 1,
            column=type_node.start_point.column,
            argument_count=arg_count,
        )

        results.append(
            RelationCandidate(
                project_key=project_key,
                subject_entity_key=subject_key,
                predicate=RelationPredicate.CALLS,
                normalized_raw_target=type_name,
                relation_kind=RelationKind.STATIC,
                confidence=Decimal("1.00000"),
                resolution_status=ResolutionStatus.UNRESOLVED,
                occurrences=(occ,),
                source_file_rel_path=file_rel_path,
                metadata={"call_type": "constructor_invocation"},
            )
        )

    # =========================================================================
    # TypeScript / JavaScript Invocation Extraction
    # =========================================================================
    def _extract_ts_calls(
        self,
        code_bytes: bytes,
        language: str,
        project_key: str,
        file_rel_path: str,
        line_offset: int = 0,
    ) -> list[RelationCandidate]:
        parser = self.parser_factory.get(language)
        tree = parser.parse(code_bytes)
        root = tree.root_node

        file_subject_key = f"FILE:{project_key}:{file_rel_path}"
        results: list[RelationCandidate] = []

        self._traverse_ts_calls(
            root, code_bytes, project_key, file_rel_path, file_subject_key, [], line_offset, results
        )
        return results

    def _traverse_ts_calls(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        current_subject_key: str,
        scope_prefix: list[str],
        line_offset: int,
        results: list[RelationCandidate],
    ):
        for child in node.children:
            next_subject = current_subject_key
            next_scope = scope_prefix

            if child.type in {"class_declaration", "abstract_class_declaration"}:
                name_node = child.child_by_field_name("name")
                if name_node:
                    cname = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                    next_scope = scope_prefix + [cname]

            elif child.type in {"function_declaration", "method_definition"}:
                name_node = child.child_by_field_name("name")
                if name_node:
                    fname = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                    qual_parts = scope_prefix + [fname]
                    qual_name = ".".join(qual_parts)
                    entity_type = "METHOD" if child.type == "method_definition" else "FUNCTION"
                    next_subject = f"SYMBOL:{project_key}:{file_rel_path}:{entity_type}:{qual_name}:{EMPTY_SIGNATURE_DISCRIMINATOR}"
                    next_scope = qual_parts

            elif child.type == "call_expression":
                self._record_ts_call_expression(
                    child, code_bytes, project_key, file_rel_path, current_subject_key, line_offset, results
                )

            elif child.type == "new_expression":
                self._record_ts_new_expression(
                    child, code_bytes, project_key, file_rel_path, current_subject_key, line_offset, results
                )

            # Recurse
            if child.child_count > 0:
                self._traverse_ts_calls(
                    child, code_bytes, project_key, file_rel_path, next_subject, next_scope, line_offset, results
                )

    def _record_ts_call_expression(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        subject_key: str,
        line_offset: int,
        results: list[RelationCandidate],
    ):
        fn_node = node.child_by_field_name("function")
        if not fn_node:
            return

        target_name = code_bytes[fn_node.start_byte : fn_node.end_byte].decode("utf-8", errors="replace").strip()
        args_node = node.child_by_field_name("arguments")
        arg_count = self._count_args(args_node)

        occ = SourceOccurrence(
            line=fn_node.start_point.row + 1 + line_offset,
            column=fn_node.start_point.column,
            argument_count=arg_count,
        )

        results.append(
            RelationCandidate(
                project_key=project_key,
                subject_entity_key=subject_key,
                predicate=RelationPredicate.CALLS,
                normalized_raw_target=target_name,
                relation_kind=RelationKind.STATIC,
                confidence=Decimal("1.00000"),
                resolution_status=ResolutionStatus.UNRESOLVED,
                occurrences=(occ,),
                source_file_rel_path=file_rel_path,
                metadata={"call_type": "call_expression"},
            )
        )

    def _record_ts_new_expression(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        subject_key: str,
        line_offset: int,
        results: list[RelationCandidate],
    ):
        ctor_node = node.child_by_field_name("constructor")
        if not ctor_node:
            return

        target_name = code_bytes[ctor_node.start_byte : ctor_node.end_byte].decode("utf-8", errors="replace").strip()
        args_node = node.child_by_field_name("arguments")
        arg_count = self._count_args(args_node)

        occ = SourceOccurrence(
            line=ctor_node.start_point.row + 1 + line_offset,
            column=ctor_node.start_point.column,
            argument_count=arg_count,
        )

        results.append(
            RelationCandidate(
                project_key=project_key,
                subject_entity_key=subject_key,
                predicate=RelationPredicate.CALLS,
                normalized_raw_target=target_name,
                relation_kind=RelationKind.STATIC,
                confidence=Decimal("1.00000"),
                resolution_status=ResolutionStatus.UNRESOLVED,
                occurrences=(occ,),
                source_file_rel_path=file_rel_path,
                metadata={"call_type": "new_expression"},
            )
        )

    # =========================================================================
    # Vue SFC Invocation Extraction
    # =========================================================================
    def _extract_vue_calls(
        self,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        text = code_bytes.decode("utf-8", errors="replace")
        sfc_result = self.sfc_slicer.slice_text(text, file_rel_path)

        all_cands: list[RelationCandidate] = []
        for script_block in sfc_result.script_blocks:
            if not script_block or not script_block.content.strip():
                continue
            script_bytes = script_block.content.encode("utf-8")
            script_lang = "typescript" if script_block.lang in {"ts", "tsx", "typescript"} else "javascript"
            cands = self._extract_ts_calls(
                script_bytes,
                language=script_lang,
                project_key=project_key,
                file_rel_path=file_rel_path,
                line_offset=script_block.start_line - 1,
            )
            all_cands.extend(cands)

        return all_cands

    # =========================================================================
    # Helpers
    # =========================================================================
    def _count_args(self, args_node: Node | None) -> int:
        if not args_node:
            return 0
        count = 0
        for child in args_node.children:
            if child.type not in {"(", ")", ",", "{", "}"}:
                count += 1
        return count
