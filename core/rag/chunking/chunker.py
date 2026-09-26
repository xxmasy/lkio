"""LKIO Semantic Chunking
Provides chunking for Markdown documents, API contracts, and code semantic blocks.
"""

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class SemanticChunk:
    """Represents a coherent piece of text or code for embedding and retrieval."""
    chunk_id: str
    project_key: str
    file_path: str
    chunk_type: str                      # DOC, CODE, API
    title: str
    content: str
    start_line: int
    end_line: int
    metadata: dict[str, Any] = field(default_factory=dict)


class MarkdownDocChunker:
    """Chunks markdown documents by header sections (#, ##, ###)."""

    def chunk(self, content: str, file_path: str, project_key: str) -> list[SemanticChunk]:
        chunks: list[SemanticChunk] = []
        lines = content.splitlines()
        current_header = "Overview"
        current_lines: list[str] = []
        start_line = 1

        for idx, line in enumerate(lines, start=1):
            header_match = re.match(r"^(#{1,3})\s+(.*)$", line.strip())
            if header_match:
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append(
                            SemanticChunk(
                                chunk_id=f"DOC:{project_key}:{file_path}:{start_line}",
                                project_key=project_key,
                                file_path=file_path,
                                chunk_type="DOC",
                                title=current_header,
                                content=chunk_text,
                                start_line=start_line,
                                end_line=idx - 1,
                                metadata={"header": current_header},
                            )
                        )
                current_header = header_match.group(2).strip()
                current_lines = [line]
                start_line = idx
            else:
                current_lines.append(line)

        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(
                    SemanticChunk(
                        chunk_id=f"DOC:{project_key}:{file_path}:{start_line}",
                        project_key=project_key,
                        file_path=file_path,
                        chunk_type="DOC",
                        title=current_header,
                        content=chunk_text,
                        start_line=start_line,
                        end_line=len(lines),
                        metadata={"header": current_header},
                    )
                )

        return chunks


class CodeSemanticChunker:
    """Chunks code into function/class semantic blocks based on extracted symbols."""

    def chunk_from_symbol(
        self,
        symbol_name: str,
        symbol_kind: str,
        code_snippet: str,
        file_path: str,
        project_key: str,
        start_line: int,
        end_line: int,
        docstring: str | None = None,
    ) -> SemanticChunk:
        content = f"[{symbol_kind}] {symbol_name}\n"
        if docstring:
            content += f"Docstring: {docstring}\n"
        content += f"Source:\n{code_snippet}"

        return SemanticChunk(
            chunk_id=f"CODE:{project_key}:{file_path}:{start_line}",
            project_key=project_key,
            file_path=file_path,
            chunk_type="CODE",
            title=f"{symbol_kind} {symbol_name}",
            content=content,
            start_line=start_line,
            end_line=end_line,
            metadata={"symbol_kind": symbol_kind, "name": symbol_name},
        )
