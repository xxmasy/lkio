"""Static Hierarchy Relations Extractor (C-03)
Extracts extends and implements relationships across Java and TypeScript.

Enforces:
- LOCK-GRAPH-04: Static explicit relations only, zero call/polymorphic assumptions.
- LOCK-GRAPH-11: Subject is CLASS/INTERFACE Symbol, target is raw type identifier.
- relation_kind = STATIC, confidence = 1.00000.
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
from core.parsing.parser_factory import ParserFactory

logger = logging.getLogger(__name__)


class HierarchyRelationExtractor:
    """Extracts extends and implements hierarchy relations from source code."""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.parser_factory = parser_factory or ParserFactory()

    def extract_from_code(
        self,
        code_bytes: bytes,
        language: str,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        lang = language.lower()
        if lang == "java":
            return self._extract_java_hierarchy(code_bytes, project_key, file_rel_path)
        elif lang in {"typescript", "tsx", "javascript", "jsx"}:
            return self._extract_ts_hierarchy(code_bytes, lang, project_key, file_rel_path)
        else:
            return []

    # =========================================================================
    # Java Hierarchy Extraction
    # =========================================================================
    def _extract_java_hierarchy(
        self,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        parser = self.parser_factory.get("java")
        tree = parser.parse(code_bytes)
        root = tree.root_node

        results: list[RelationCandidate] = []
        self._traverse_java_node(root, code_bytes, project_key, file_rel_path, [], results)
        return results

    def _traverse_java_node(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        parent_scope: list[str],
        results: list[RelationCandidate],
    ):
        for child in node.children:
            if child.type in {"class_declaration", "interface_declaration", "enum_declaration", "record_declaration"}:
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue

                type_name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                current_scope = parent_scope + [type_name]
                qual_name = ".".join(current_scope)
                base_type = "INTERFACE" if child.type == "interface_declaration" else "CLASS"
                if child.type == "enum_declaration":
                    base_type = "ENUM"

                subject_key = f"SYMBOL:{project_key}:{file_rel_path}:{base_type}:{qual_name}:{EMPTY_SIGNATURE_DISCRIMINATOR}"

                # 1. Check superclass (extends)
                superclass_node = child.child_by_field_name("superclass")
                if superclass_node:
                    self._parse_java_extends(
                        superclass_node, code_bytes, project_key, subject_key, file_rel_path, results
                    )

                # 2. Check super interfaces (implements / extends_interfaces)
                for sub in child.children:
                    if sub.type == "super_interfaces":
                        self._parse_java_interfaces(
                            sub, RelationPredicate.IMPLEMENTS, code_bytes, project_key, subject_key, file_rel_path, results
                        )
                    elif sub.type == "extends_interfaces":
                        self._parse_java_interfaces(
                            sub, RelationPredicate.EXTENDS, code_bytes, project_key, subject_key, file_rel_path, results
                        )

                # Recurse for nested classes
                body = child.child_by_field_name("body")
                if body:
                    self._traverse_java_node(body, code_bytes, project_key, file_rel_path, current_scope, results)

            elif child.type in {"class_body", "interface_body"}:
                self._traverse_java_node(child, code_bytes, project_key, file_rel_path, parent_scope, results)

    def _parse_java_extends(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        subject_key: str,
        file_rel_path: str,
        results: list[RelationCandidate],
    ):
        raw_text = code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
        target_name = raw_text.replace("extends", "").strip().split("<")[0].strip()
        if target_name:
            results.append(
                RelationCandidate(
                    project_key=project_key,
                    subject_entity_key=subject_key,
                    predicate=RelationPredicate.EXTENDS,
                    normalized_raw_target=target_name,
                    relation_kind=RelationKind.STATIC,
                    confidence=Decimal("1.00000"),
                    resolution_status=ResolutionStatus.UNRESOLVED,
                    occurrences=(SourceOccurrence(line=node.start_point.row + 1, column=node.start_point.column),),
                    source_file_rel_path=file_rel_path,
                    metadata={"ast_node": "superclass"},
                )
            )

    def _parse_java_interfaces(
        self,
        node: Node,
        predicate: RelationPredicate,
        code_bytes: bytes,
        project_key: str,
        subject_key: str,
        file_rel_path: str,
        results: list[RelationCandidate],
    ):
        # interfaces node contains type_list
        target_nodes = []
        for c in node.children:
            if c.type == "type_list":
                target_nodes.extend(c.children)
            else:
                target_nodes.append(c)

        for c in target_nodes:
            if c.type in {"type_identifier", "scoped_type_identifier", "generic_type"}:
                raw = code_bytes[c.start_byte : c.end_byte].decode("utf-8", errors="replace")
                target_name = raw.split("<")[0].strip()
                if target_name:
                    results.append(
                        RelationCandidate(
                            project_key=project_key,
                            subject_entity_key=subject_key,
                            predicate=predicate,
                            normalized_raw_target=target_name,
                            relation_kind=RelationKind.STATIC,
                            confidence=Decimal("1.00000"),
                            resolution_status=ResolutionStatus.UNRESOLVED,
                            occurrences=(SourceOccurrence(line=c.start_point.row + 1, column=c.start_point.column),),
                            source_file_rel_path=file_rel_path,
                            metadata={"ast_node": node.type},
                        )
                    )

    # =========================================================================
    # TypeScript & JavaScript Hierarchy Extraction
    # =========================================================================
    def _extract_ts_hierarchy(
        self,
        code_bytes: bytes,
        language: str,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        parser = self.parser_factory.get(language)
        tree = parser.parse(code_bytes)
        root = tree.root_node

        results: list[RelationCandidate] = []
        self._traverse_ts_node(root, code_bytes, project_key, file_rel_path, [], results)
        return results

    def _traverse_ts_node(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        parent_scope: list[str],
        results: list[RelationCandidate],
    ):
        for child in node.children:
            # Handle export default class / export class
            actual_node = child
            if child.type == "export_statement":
                decl = child.child_by_field_name("declaration")
                if decl:
                    actual_node = decl

            if actual_node.type in {"class_declaration", "abstract_class_declaration", "interface_declaration"}:
                name_node = actual_node.child_by_field_name("name")
                if not name_node:
                    continue

                type_name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
                current_scope = parent_scope + [type_name]
                qual_name = ".".join(current_scope)
                base_type = "INTERFACE" if actual_node.type == "interface_declaration" else "CLASS"

                subject_key = f"SYMBOL:{project_key}:{file_rel_path}:{base_type}:{qual_name}:{EMPTY_SIGNATURE_DISCRIMINATOR}"

                # Check class heritage (extends / implements)
                for c in actual_node.children:
                    if c.type == "class_heritage":
                        for clause in c.children:
                            if clause.type == "extends_clause":
                                self._parse_ts_clause(
                                    clause, RelationPredicate.EXTENDS, code_bytes, project_key, subject_key, file_rel_path, results
                                )
                            elif clause.type == "implements_clause":
                                self._parse_ts_clause(
                                    clause, RelationPredicate.IMPLEMENTS, code_bytes, project_key, subject_key, file_rel_path, results
                                )
                    elif c.type == "extends_type_clause":
                        self._parse_ts_clause(
                            c, RelationPredicate.EXTENDS, code_bytes, project_key, subject_key, file_rel_path, results
                        )

            elif actual_node.type in {"statement_block", "class_body"}:
                self._traverse_ts_node(actual_node, code_bytes, project_key, file_rel_path, parent_scope, results)

    def _parse_ts_clause(
        self,
        node: Node,
        predicate: RelationPredicate,
        code_bytes: bytes,
        project_key: str,
        subject_key: str,
        file_rel_path: str,
        results: list[RelationCandidate],
    ):
        for c in node.children:
            if c.type in {"identifier", "type_identifier", "generic_type"}:
                raw = code_bytes[c.start_byte : c.end_byte].decode("utf-8", errors="replace")
                target_name = raw.split("<")[0].strip()
                if target_name and target_name not in {"extends", "implements"}:
                    results.append(
                        RelationCandidate(
                            project_key=project_key,
                            subject_entity_key=subject_key,
                            predicate=predicate,
                            normalized_raw_target=target_name,
                            relation_kind=RelationKind.STATIC,
                            confidence=Decimal("1.00000"),
                            resolution_status=ResolutionStatus.UNRESOLVED,
                            occurrences=(SourceOccurrence(line=c.start_point.row + 1, column=c.start_point.column),),
                            source_file_rel_path=file_rel_path,
                            metadata={"ast_node": node.type},
                        )
                    )
