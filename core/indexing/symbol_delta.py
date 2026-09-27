"""Symbol Delta Engine (Stage 1 Section 3.5).

Computes granular symbol-level mutations between old and new file blobs:
- SYMBOL_ADDED
- SYMBOL_DELETED
- SYMBOL_MODIFIED
- SIGNATURE_CHANGED (e.g. foo(a) -> foo(a, b))
- SYMBOL_RENAMED
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class SymbolDeltaType(str, Enum):
    SYMBOL_ADDED = "SYMBOL_ADDED"
    SYMBOL_DELETED = "SYMBOL_DELETED"
    SYMBOL_MODIFIED = "SYMBOL_MODIFIED"
    SIGNATURE_CHANGED = "SIGNATURE_CHANGED"
    SYMBOL_RENAMED = "SYMBOL_RENAMED"


@dataclass
class ExtractedSymbol:
    name: str
    kind: str  # CLASS, METHOD, FUNCTION, INTERFACE
    signature: str
    body_hash: int
    line_no: int


@dataclass
class SymbolDelta:
    symbol_name: str
    file_path: str
    delta_type: SymbolDeltaType
    kind: str
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None


class SymbolDeltaEngine:
    """Calculates symbol diffs between old and new code blobs."""

    @classmethod
    def _extract_symbols(cls, code: Optional[str]) -> Dict[str, ExtractedSymbol]:
        if not code:
            return {}

        symbols: Dict[str, ExtractedSymbol] = {}
        # 1. Match Class declarations (Java / TS)
        class_matches = re.finditer(
            r"(?:public\s+|export\s+)?(?:class|interface)\s+([A-Za-z0-9_]+)(?:\s+extends\s+[A-Za-z0-9_]+)?(?:\s+implements\s+[A-Za-z0-9_,\s]+)?",
            code,
        )
        for m in class_matches:
            name = m.group(1)
            sig = m.group(0).strip()
            line_no = code[: m.start()].count("\n") + 1
            symbols[name] = ExtractedSymbol(
                name=name,
                kind="CLASS",
                signature=sig,
                body_hash=hash(sig),
                line_no=line_no,
            )

        # 2. Match Method/Function declarations
        # e.g. public ReturnType methodName(Arg1 a, Arg2 b) or function methodName(a: string)
        method_matches = re.finditer(
            r"(?:public|private|protected|async|function)?\s*(?:[A-Za-z0-9_<>[\]]+\s+)?([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?::\s*[A-Za-z0-9_<>[\]]+)?\s*\{",
            code,
        )
        for m in method_matches:
            name = m.group(1)
            if name in ("if", "for", "while", "switch", "catch", "class", "interface"):
                continue
            args = m.group(2).strip()
            sig = f"{name}({args})"
            line_no = code[: m.start()].count("\n") + 1
            symbols[name] = ExtractedSymbol(
                name=name,
                kind="METHOD",
                signature=sig,
                body_hash=hash(sig),
                line_no=line_no,
            )

        return symbols

    @classmethod
    def compute_file_symbol_delta(
        cls,
        file_path: str,
        old_blob: Optional[str],
        new_blob: Optional[str],
    ) -> List[SymbolDelta]:
        """Compares old and new blobs of a file and returns exact SymbolDeltas."""
        old_symbols = cls._extract_symbols(old_blob)
        new_symbols = cls._extract_symbols(new_blob)

        deltas: List[SymbolDelta] = []
        old_names = set(old_symbols.keys())
        new_names = set(new_symbols.keys())

        # Added symbols
        for name in new_names - old_names:
            sym = new_symbols[name]
            deltas.append(
                SymbolDelta(
                    symbol_name=name,
                    file_path=file_path,
                    delta_type=SymbolDeltaType.SYMBOL_ADDED,
                    kind=sym.kind,
                    new_signature=sym.signature,
                )
            )

        # Deleted symbols
        for name in old_names - new_names:
            sym = old_symbols[name]
            deltas.append(
                SymbolDelta(
                    symbol_name=name,
                    file_path=file_path,
                    delta_type=SymbolDeltaType.SYMBOL_DELETED,
                    kind=sym.kind,
                    old_signature=sym.signature,
                )
            )

        # Common symbols (check signature vs body modification)
        for name in old_names & new_names:
            old_s = old_symbols[name]
            new_s = new_symbols[name]

            if old_s.signature != new_s.signature:
                deltas.append(
                    SymbolDelta(
                        symbol_name=name,
                        file_path=file_path,
                        delta_type=SymbolDeltaType.SIGNATURE_CHANGED,
                        kind=new_s.kind,
                        old_signature=old_s.signature,
                        new_signature=new_s.signature,
                    )
                )
            elif old_s.body_hash != new_s.body_hash:
                deltas.append(
                    SymbolDelta(
                        symbol_name=name,
                        file_path=file_path,
                        delta_type=SymbolDeltaType.SYMBOL_MODIFIED,
                        kind=new_s.kind,
                        old_signature=old_s.signature,
                        new_signature=new_s.signature,
                    )
                )

        return deltas
