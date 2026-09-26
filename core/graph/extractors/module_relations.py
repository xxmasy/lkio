"""Static Module Relations Extractor (C-02)
Extracts module-level imports and exports across TypeScript, JavaScript, Java, and Vue SFC.

Enforces:
- LOCK-GRAPH-04: Static explicit relations only (imports/exports), zero call inference.
- LOCK-GRAPH-09: Single Relation edge per module target, occurrences array for multiple import sites.
- LOCK-GRAPH-11: imports/exports is strictly FILE -> FILE. Import specifiers recorded in metadata.
- Vue SFC: Template component references recorded in metadata["template_references"], no premature uses predicate.
"""

from decimal import Decimal
import logging
import re
from typing import Any
from tree_sitter import Node

from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)
from core.parsing.parser_factory import ParserFactory
from core.parsing.sfc_block_slicer import SfcBlockSlicer

logger = logging.getLogger(__name__)


class ModuleRelationExtractor:
    """Extracts explicit imports and exports relationships from source files."""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.parser_factory = parser_factory or ParserFactory()
        self.sfc_slicer = SfcBlockSlicer(preserve_physical_lines=True)

    def extract_from_code(
        self,
        code_bytes: bytes,
        language: str,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        """Extracts module relations from raw file bytes."""
        lang = language.lower()
        if lang == "vue":
            return self._extract_vue_module_relations(code_bytes, project_key, file_rel_path)
        elif lang in {"typescript", "tsx", "javascript", "jsx"}:
            return self._extract_ts_js_module_relations(code_bytes, lang, project_key, file_rel_path)
        elif lang == "java":
            return self._extract_java_module_relations(code_bytes, project_key, file_rel_path)
        else:
            return []

    # =========================================================================
    # TypeScript & JavaScript Module Extraction
    # =========================================================================
    def _extract_ts_js_module_relations(
        self,
        code_bytes: bytes,
        language: str,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        parser = self.parser_factory.get(language)
        tree = parser.parse(code_bytes)
        root = tree.root_node

        subject_key = f"FILE:{project_key}:{file_rel_path}"
        import_candidates: dict[str, RelationCandidate] = {}
        export_candidates: dict[str, RelationCandidate] = {}

        for child in root.children:
            if child.type == "import_statement":
                self._parse_ts_import_statement(
                    child, code_bytes, project_key, subject_key, file_rel_path, import_candidates
                )
            elif child.type == "export_statement":
                self._parse_ts_export_statement(
                    child, code_bytes, project_key, subject_key, file_rel_path, export_candidates
                )

        return list(import_candidates.values()) + list(export_candidates.values())

    def _parse_ts_import_statement(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        subject_key: str,
        file_rel_path: str,
        results: dict[str, RelationCandidate],
    ):
        # Find module source (e.g. from './utils' or 'lodash')
        source_node = node.child_by_field_name("source")
        if not source_node:
            # Check children for string node (dynamic or side-effect import `import 'style.css'`)
            for c in node.children:
                if c.type == "string":
                    source_node = c
                    break

        if not source_node:
            return

        raw_target = code_bytes[source_node.start_byte : source_node.end_byte].decode("utf-8", errors="replace").strip("\"'")
        if not raw_target:
            return

        line = node.start_point.row + 1
        col = node.start_point.column
        occ = SourceOccurrence(line=line, column=col)

        # Inspect import specifiers / type-only
        specifiers = []
        is_type_only = False
        is_default = False
        is_namespace = False

        for c in node.children:
            if c.type == "type":
                is_type_only = True
            elif c.type == "import_clause":
                for ic in c.children:
                    if ic.type == "type":
                        is_type_only = True
                    elif ic.type == "identifier":
                        is_default = True
                        spec_name = code_bytes[ic.start_byte : ic.end_byte].decode("utf-8", errors="replace")
                        specifiers.append({"imported": "default", "local": spec_name})
                    elif ic.type == "namespace_import":
                        is_namespace = True
                        ns_name = code_bytes[ic.start_byte : ic.end_byte].decode("utf-8", errors="replace").replace("* as ", "").strip()
                        specifiers.append({"imported": "*", "local": ns_name})
                    elif ic.type == "named_imports":
                        for spec in ic.children:
                            if spec.type == "import_specifier":
                                name_node = spec.child_by_field_name("name")
                                alias_node = spec.child_by_field_name("alias")
                                imp_name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace") if name_node else ""
                                loc_name = code_bytes[alias_node.start_byte : alias_node.end_byte].decode("utf-8", errors="replace") if alias_node else imp_name
                                specifiers.append({"imported": imp_name, "local": loc_name})

        # Single relation edge per raw_target (LOCK-GRAPH-09)
        if raw_target in results:
            existing = results[raw_target]
            combined_occs = existing.occurrences + (occ,)
            combined_specs = existing.metadata.get("import_specifiers", []) + specifiers
            meta = dict(existing.metadata)
            meta["import_specifiers"] = combined_specs
            results[raw_target] = existing.with_occurrences(combined_occs)
        else:
            cand = RelationCandidate(
                project_key=project_key,
                subject_entity_key=subject_key,
                predicate=RelationPredicate.IMPORTS,
                normalized_raw_target=raw_target,
                relation_kind=RelationKind.STATIC,
                confidence=Decimal("1.00000"),
                resolution_status=ResolutionStatus.UNRESOLVED,
                occurrences=(occ,),
                source_file_rel_path=file_rel_path,
                metadata={
                    "import_specifiers": specifiers,
                    "is_type_only": is_type_only,
                    "is_default": is_default,
                    "is_namespace": is_namespace,
                },
            )
            results[raw_target] = cand

    def _parse_ts_export_statement(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        subject_key: str,
        file_rel_path: str,
        results: dict[str, RelationCandidate],
    ):
        # Look for re-export with source: `export { A } from './utils'`
        source_node = node.child_by_field_name("source")
        if not source_node:
            return

        raw_target = code_bytes[source_node.start_byte : source_node.end_byte].decode("utf-8", errors="replace").strip("\"'")
        if not raw_target:
            return

        line = node.start_point.row + 1
        col = node.start_point.column
        occ = SourceOccurrence(line=line, column=col)

        specifiers = []
        for c in node.children:
            if c.type == "export_clause":
                for spec in c.children:
                    if spec.type == "export_specifier":
                        name_node = spec.child_by_field_name("name")
                        alias_node = spec.child_by_field_name("alias")
                        orig_name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace") if name_node else ""
                        exp_name = code_bytes[alias_node.start_byte : alias_node.end_byte].decode("utf-8", errors="replace") if alias_node else orig_name
                        specifiers.append({"local": orig_name, "exported": exp_name})

        if raw_target in results:
            existing = results[raw_target]
            results[raw_target] = existing.with_occurrences(existing.occurrences + (occ,))
        else:
            cand = RelationCandidate(
                project_key=project_key,
                subject_entity_key=subject_key,
                predicate=RelationPredicate.EXPORTS,
                normalized_raw_target=raw_target,
                relation_kind=RelationKind.STATIC,
                confidence=Decimal("1.00000"),
                resolution_status=ResolutionStatus.UNRESOLVED,
                occurrences=(occ,),
                source_file_rel_path=file_rel_path,
                metadata={
                    "reexport_specifiers": specifiers,
                    "is_reexport": True,
                },
            )
            results[raw_target] = cand

    # =========================================================================
    # Java Module / Package Import Extraction
    # =========================================================================
    def _extract_java_module_relations(
        self,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        parser = self.parser_factory.get("java")
        tree = parser.parse(code_bytes)
        root = tree.root_node

        subject_key = f"FILE:{project_key}:{file_rel_path}"
        results: dict[str, RelationCandidate] = {}

        for child in root.children:
            if child.type == "import_declaration":
                # Check for static keyword
                is_static = any(c.type == "static" for c in child.children)
                is_wildcard = any(c.type == "asterisk" for c in child.children)

                # Extract import target path
                raw_target = ""
                for c in child.children:
                    if c.type in {"scoped_identifier", "identifier"}:
                        raw_target = code_bytes[c.start_byte : c.end_byte].decode("utf-8", errors="replace").strip()
                        break

                if not raw_target:
                    continue

                if is_wildcard:
                    raw_target = f"{raw_target}.*"

                line = child.start_point.row + 1
                col = child.start_point.column
                occ = SourceOccurrence(line=line, column=col)

                if raw_target in results:
                    existing = results[raw_target]
                    results[raw_target] = existing.with_occurrences(existing.occurrences + (occ,))
                else:
                    cand = RelationCandidate(
                        project_key=project_key,
                        subject_entity_key=subject_key,
                        predicate=RelationPredicate.IMPORTS,
                        normalized_raw_target=raw_target,
                        relation_kind=RelationKind.STATIC,
                        confidence=Decimal("1.00000"),
                        resolution_status=ResolutionStatus.UNRESOLVED,
                        occurrences=(occ,),
                        source_file_rel_path=file_rel_path,
                        metadata={
                            "is_static": is_static,
                            "is_wildcard": is_wildcard,
                        },
                    )
                    results[raw_target] = cand

        return list(results.values())

    # =========================================================================
    # Vue SFC Module Extraction (Script + Template references)
    # =========================================================================
    def _extract_vue_module_relations(
        self,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
    ) -> list[RelationCandidate]:
        text = code_bytes.decode("utf-8", errors="replace")
        sfc = self.sfc_slicer.slice_text(text, file_rel_path)

        candidates: dict[str, RelationCandidate] = {}

        # 1. Extract from script blocks
        for block in sfc.script_blocks:
            if block and block.content.strip():
                block_bytes = block.content.encode("utf-8")
                lang = "typescript" if block.lang in {"ts", "tsx"} else "javascript"
                block_cands = self._extract_ts_js_module_relations(
                    block_bytes, lang, project_key, file_rel_path
                )
                for c in block_cands:
                    target = c.normalized_raw_target
                    if target in candidates:
                        existing = candidates[target]
                        candidates[target] = existing.with_occurrences(existing.occurrences + c.occurrences)
                    else:
                        candidates[target] = c

        # 2. Inspect template block for component references
        if sfc.template_block and sfc.template_block.content.strip():
            template_text = sfc.template_block.content
            # Check which imported component names appear in template tags
            for target, cand in list(candidates.items()):
                specifiers = cand.metadata.get("import_specifiers", [])
                template_refs = []
                for s in specifiers:
                    local_name = s.get("local")
                    if local_name and len(local_name) >= 2:
                        # Convert PascalCase to kebab-case
                        kebab_name = re.sub(r"(?<!^)(?=[A-Z])", "-", local_name).lower()
                        # Simple regex for XML/HTML tags
                        tag_pattern = rf"<\s*({re.escape(local_name)}|{re.escape(kebab_name)})[\s/>]"
                        matches = [m.start() for m in re.finditer(tag_pattern, template_text)]
                        if matches:
                            template_refs.append({
                                "component_local_name": local_name,
                                "matched_tags_count": len(matches),
                            })
                if template_refs:
                    meta = dict(cand.metadata)
                    meta["template_references"] = template_refs
                    # Update candidate with metadata
                    candidates[target] = RelationCandidate(
                        project_key=cand.project_key,
                        subject_entity_key=cand.subject_entity_key,
                        predicate=cand.predicate,
                        normalized_raw_target=cand.normalized_raw_target,
                        relation_kind=cand.relation_kind,
                        confidence=cand.confidence,
                        resolution_status=cand.resolution_status,
                        object_entity_key=cand.object_entity_key,
                        candidate_discriminator=cand.candidate_discriminator,
                        occurrences=cand.occurrences,
                        source_file_rel_path=cand.source_file_rel_path,
                        metadata=meta,
                    )

        return list(candidates.values())
