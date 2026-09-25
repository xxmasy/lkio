"""LKIO Vue Single File Component (SFC) Symbol Extractor (B-05 Approved Baseline)
Extracts Vue component symbol, template structural facts, compiler macros, options API facts,
and inner script symbols using SfcBlockSlicer, VueTemplateParser, and TypeScriptExtractor.

Enforces:
- LOCK-VUE-01: Synthetic Component vs AST Native Symbol (synthetic=True, source_kind="vue_sfc_file_context")
- LOCK-VUE-02: Template evidence taxonomy (extraction_method = "static_template")
- LOCK-VUE-03: Structured bindings preservation without premature function call assumptions
- LOCK-VUE-03b: Tag name preservation (raw tag_name + normalized_name in PascalCase)
- LOCK-VUE-04: Options API structural metadata (does not distort B-03 native symbols)
- LOCK-VUE-05: Vue compiler macros v1 collection (defineProps, defineEmits, defineExpose, defineOptions, defineModel, defineSlots)
- LOCK-VUE-06: Preflight parser strategy with graceful degradation for unsupported template preprocessors
- B-02 Criterion 5: Script + Script Setup block scope isolation (script::foo vs script_setup::foo)
"""

import logging
from pathlib import Path
import re
from typing import Any
from tree_sitter import Node

from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import (
    EMPTY_SIGNATURE_DISCRIMINATOR,
    build_qualified_name,
    compute_signature_discriminator,
    normalize_rel_path,
)
from core.extraction.typescript import TypeScriptExtractor
from core.parsing.models import SymbolType
from core.parsing.parser_factory import ParserFactory
from core.parsing.sfc_block_slicer import SfcBlockSlicer
from core.parsing.template_parser import parse_vue_template

logger = logging.getLogger(__name__)

COMPILER_MACROS = {
    "defineProps",
    "defineEmits",
    "defineExpose",
    "defineOptions",
    "defineModel",
    "defineSlots",
}


class VueExtractor:
    """Extracts symbols and structural metadata from Vue Single File Components (.vue)."""

    def __init__(
        self,
        ts_extractor: TypeScriptExtractor | None = None,
        parser_factory: ParserFactory | None = None,
    ):
        self.slicer = SfcBlockSlicer(preserve_physical_lines=True)
        self.parser_factory = parser_factory or ParserFactory()
        self.ts_extractor = ts_extractor or TypeScriptExtractor(self.parser_factory)

    def extract(
        self,
        code_bytes: bytes,
        file_path: str,
        file_rel_path: str,
        language: str = "vue",
    ) -> list[SymbolCandidate]:
        """Parses a .vue file and extracts the component and all symbols inside its script blocks."""
        code_text = code_bytes.decode("utf-8", errors="replace")
        sfc_result = self.slicer.slice_text(code_text, file_path=file_path)

        candidates: list[SymbolCandidate] = []
        norm_rel_path = normalize_rel_path(file_rel_path)
        comp_name = Path(norm_rel_path).stem
        total_lines = max(1, len(code_text.splitlines()))

        # 1. Template Structural Facts Extraction (LOCK-VUE-02, LOCK-VUE-03)
        template_facts: dict[str, Any] = {
            "component_references": [],
            "event_bindings": [],
            "property_bindings": [],
        }
        if sfc_result.template_block:
            t_block = sfc_result.template_block
            template_facts = parse_vue_template(
                template_content=t_block.content,
                base_line=t_block.start_line,
                lang=t_block.lang,
            )

        # 2. Styles Metadata Extraction (Boundary 4)
        style_metadata: list[dict[str, Any]] = [
            {
                "lang": s_block.lang,
                "scoped": s_block.is_scoped,
                "start_line": s_block.start_line,
                "end_line": s_block.end_line,
                "evidence": {
                    "method": "static_sfc_metadata",
                    "block_type": "style",
                },
            }
            for s_block in sfc_result.style_blocks
        ]

        # 3. Process Script Blocks (<script> and <script setup>)
        macros_metadata: dict[str, Any] = {}
        macro_helpers: list[str] = []
        options_api_metadata: dict[str, Any] = {
            "data": [],
            "computed": [],
            "methods": [],
            "watch": [],
            "props": [],
            "emits": [],
            "components": [],
            "directives": [],
        }

        script_candidates: list[SymbolCandidate] = []

        for script_block in sfc_result.script_blocks:
            lang = "typescript" if script_block.lang in ["ts", "typescript"] else "javascript"
            script_bytes = script_block.content.encode("utf-8")
            block_type = "script_setup" if script_block.is_setup else "script"

            # Parse AST for Macros & Options API
            tree = self.parser_factory.get(lang).parse(script_bytes)
            self._extract_macros_and_options(
                root_node=tree.root_node,
                is_setup=script_block.is_setup,
                macros_out=macros_metadata,
                helpers_out=macro_helpers,
                options_out=options_api_metadata,
            )

            # Reuse B-03 TypeScriptExtractor (Boundary 2, User instruction)
            inner_symbols = self.ts_extractor.extract(
                code_bytes=script_bytes,
                file_path=file_path,
                file_rel_path=norm_rel_path,
                language=lang,
            )

            # B-02 Criterion 5: Block Scope Isolation (script::foo vs script_setup::foo)
            for sym in inner_symbols:
                # Adjust qualified name to include block_scope
                sym.qualified_name = build_qualified_name(sym.qualified_name, block_scope=block_type)
                # Re-calculate deterministic key with updated qualified_name
                sym.metadata["block_scope"] = block_type
                sym.metadata["vue_sfc_block"] = block_type
                script_candidates.append(sym)

        # 4. Create Main Synthetic Component Symbol Candidate (LOCK-VUE-01)
        component_metadata: dict[str, Any] = {
            "synthetic": True,
            "source_kind": "vue_sfc_file_context",
            "component_context": True,
            "extraction_method": "sfc_structure",
            "confidence": 1.0,
            "evidence": {
                "method": "sfc_structure",
                "file": Path(file_path).name,
                "file_stem": comp_name,
            },
            "sfc_blocks": [
                b.block_type
                for b in (
                    sfc_result.script_blocks
                    + ([sfc_result.template_block] if sfc_result.template_block else [])
                    + sfc_result.style_blocks
                )
            ],
            "template": template_facts,
            "styles": style_metadata,
            "macros": macros_metadata,
            "macro_helpers": macro_helpers,
            "options_api": options_api_metadata,
        }

        main_component_symbol = SymbolCandidate(
            file_path=file_path,
            file_rel_path=norm_rel_path,
            name=comp_name,
            qualified_name=comp_name,
            symbol_type=SymbolType.COMPONENT.value,
            base_symbol_type=SymbolType.VARIABLE.value,
            start_line=1,
            end_line=total_lines,
            start_column=0,
            end_column=0,
            signature=None,
            canonical_signature=None,
            signature_discriminator=EMPTY_SIGNATURE_DISCRIMINATOR,
            language="vue",
            classification_method="vue_sfc_rule_v1",
            modifiers=["export", "default"],
            is_exported=True,
            export_kind="default",
            metadata=component_metadata,
        )

        candidates.append(main_component_symbol)
        candidates.extend(script_candidates)

        return candidates

    def _extract_macros_and_options(
        self,
        root_node: Node,
        is_setup: bool,
        macros_out: dict[str, Any],
        helpers_out: list[str],
        options_out: dict[str, Any],
    ):
        """Extracts compiler macros from script setup and options API from plain script."""
        for child in root_node.children:
            self._walk_for_macros(child, macros_out, helpers_out)
            if not is_setup:
                self._check_options_api_export(child, options_out)

    def _walk_for_macros(self, node: Node, macros_out: dict[str, Any], helpers_out: list[str]):
        """Walks AST searching for Vue 3 compiler macro calls."""
        if node.type == "call_expression":
            fn_node = node.child_by_field_name("function")
            if fn_node and fn_node.type == "identifier":
                fn_name = fn_node.text.decode("utf-8", errors="replace")
                if fn_name in COMPILER_MACROS:
                    type_args_node = node.child_by_field_name("type_arguments")
                    args_node = node.child_by_field_name("arguments")
                    macros_out[fn_name] = {
                        "name": fn_name,
                        "raw": node.text.decode("utf-8", errors="replace"),
                        "type_args": type_args_node.text.decode("utf-8", errors="replace") if type_args_node else None,
                        "arguments": args_node.text.decode("utf-8", errors="replace") if args_node else None,
                        "start_line": node.start_point.row + 1,
                        "end_line": node.end_point.row + 1,
                    }
                elif fn_name == "withDefaults":
                    helpers_out.append("withDefaults")

        for child in node.children:
            self._walk_for_macros(child, macros_out, helpers_out)

    def _check_options_api_export(self, node: Node, options_out: dict[str, Any]):
        """Checks if a node is 'export default defineComponent({...})' or 'export default {...}'."""
        if node.type != "export_statement":
            return

        val_node = node.child_by_field_name("value")
        if not val_node:
            return

        obj_node: Node | None = None
        if val_node.type == "object":
            obj_node = val_node
        elif val_node.type == "call_expression":
            fn = val_node.child_by_field_name("function")
            if fn and fn.text.decode("utf-8", errors="replace") == "defineComponent":
                args = val_node.child_by_field_name("arguments")
                if args:
                    for arg in args.children:
                        if arg.type == "object":
                            obj_node = arg
                            break

        if not obj_node:
            return

        # Parse options object properties
        for prop in obj_node.children:
            if prop.type == "method_definition":
                # e.g. data() { ... }
                name_node = prop.child_by_field_name("name")
                if name_node:
                    m_name = name_node.text.decode("utf-8", errors="replace")
                    if m_name in options_out:
                        options_out[m_name].append({
                            "name": m_name,
                            "start_line": prop.start_point.row + 1,
                            "end_line": prop.end_point.row + 1,
                        })
            elif prop.type == "pair":
                key_node = prop.child_by_field_name("key")
                val = prop.child_by_field_name("value")
                if key_node and val:
                    key_name = key_node.text.decode("utf-8", errors="replace")
                    if key_name in options_out:
                        if val.type == "object":
                            for inner in val.children:
                                if inner.type in ["method_definition", "pair"]:
                                    i_name_node = inner.child_by_field_name("name") or inner.child_by_field_name("key")
                                    if i_name_node:
                                        i_name = i_name_node.text.decode("utf-8", errors="replace")
                                        options_out[key_name].append({
                                            "name": i_name,
                                            "start_line": inner.start_point.row + 1,
                                            "end_line": inner.end_point.row + 1,
                                        })
                        elif val.type in ["function_expression", "arrow_function"]:
                            options_out[key_name].append({
                                "name": key_name,
                                "start_line": prop.start_point.row + 1,
                                "end_line": prop.end_point.row + 1,
                            })
