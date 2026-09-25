"""LKIO Vue Single File Component (SFC) Symbol Extractor
Extracts Vue component symbol and inner script symbols using SfcBlockSlicer and TypeScriptExtractor.
Enforces:
- Physical line alignment (0 coordinate drift)
- Lock 2: COMPONENT classification has base_symbol_type = VARIABLE, classification_method = "vue_sfc_rule"
- Inner script symbols preserve exact physical line numbers.
"""

from pathlib import Path
from core.extraction.dto import SymbolCandidate
from core.extraction.normalizer import compute_signature_discriminator, normalize_rel_path
from core.extraction.typescript import TypeScriptExtractor
from core.parsing.models import SymbolType
from core.parsing.sfc_block_slicer import SfcBlockSlicer


class VueExtractor:
    """Extracts symbols from Vue 2 and Vue 3 Single File Components."""

    def __init__(self, ts_extractor: TypeScriptExtractor | None = None):
        self.slicer = SfcBlockSlicer(preserve_physical_lines=True)
        self.ts_extractor = ts_extractor or TypeScriptExtractor()

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

        # 1. Create the Component Symbol Candidate representing the SFC itself
        comp_name = Path(norm_rel_path).stem
        total_lines = max(1, len(code_text.splitlines()))

        candidates.append(
            SymbolCandidate(
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
                signature_discriminator=compute_signature_discriminator(None),
                language="vue",
                classification_method="vue_sfc_rule",
                modifiers=["export", "default"],
                is_exported=True,
                metadata={
                    "has_template": sfc_result.template_block is not None,
                    "has_script": len(sfc_result.script_blocks) > 0,
                    "styles_count": len(sfc_result.style_blocks),
                },
            )
        )

        # 2. Extract script block symbols with exact physical coordinates
        for script_block in sfc_result.script_blocks:
            lang = "typescript" if script_block.lang in ["ts", "typescript"] else "javascript"
            script_bytes = script_block.content.encode("utf-8")

            # Extract symbols from script content
            inner_symbols = self.ts_extractor.extract(
                code_bytes=script_bytes,
                file_path=file_path,
                file_rel_path=norm_rel_path,
                language=lang,
            )

            # Prepend component name to qualified_name if not already qualified
            for sym in inner_symbols:
                if "." not in sym.qualified_name:
                    sym.qualified_name = f"{comp_name}.{sym.name}"
                candidates.append(sym)

        return candidates
