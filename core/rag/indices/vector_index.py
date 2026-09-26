"""LKIO Vector Index
Provides dense vector storage, normalized cosine similarity search for document and semantic code chunks.
"""

import math
from typing import Any
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    IndexType,
    RetrievalCandidate,
)


def normalize_vector(v: list[float]) -> list[float]:
    """L2 normalizes a dense vector."""
    norm = math.sqrt(sum(x * x for x in v))
    if norm < 1e-9:
        return v
    return [x / norm for x in v]


def dot_product(u: list[float], v: list[float]) -> float:
    """Computes dot product between two vectors."""
    return sum(x * y for x, y in zip(u, v))


class VectorIndex:
    """In-memory cosine similarity dense vector index."""

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension
        self._chunks: list[dict[str, Any]] = []
        self._vectors: list[list[float]] = []

    def add_chunk(
        self,
        chunk_id: str,
        vector: list[float],
        project_key: str,
        name: str,
        title: str,
        summary: str,
        file_path: str | None = None,
        entity_key: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        evidence_type: EvidenceType = EvidenceType.DOC_CHUNK,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Stores a chunk and its normalized embedding."""
        norm_v = normalize_vector(vector)
        chunk_rec = {
            "chunk_id": chunk_id,
            "project_key": project_key,
            "name": name,
            "title": title,
            "summary": summary,
            "file_path": file_path,
            "entity_key": entity_key,
            "start_line": start_line,
            "end_line": end_line,
            "evidence_type": evidence_type,
            "metadata": metadata or {},
        }
        self._chunks.append(chunk_rec)
        self._vectors.append(norm_v)

    def search(
        self,
        query_vector: list[float],
        project_key: str | None = None,
        limit: int = 10,
        min_similarity: float = 0.2,
    ) -> list[RetrievalCandidate]:
        """Performs cosine similarity search against stored vectors."""
        if not self._vectors or not query_vector:
            return []

        norm_q = normalize_vector(query_vector)
        scored: list[tuple[float, int]] = []

        for idx, doc_v in enumerate(self._vectors):
            rec = self._chunks[idx]
            if project_key and rec["project_key"] != project_key:
                continue

            sim = dot_product(norm_q, doc_v)
            # Map cosine [-1.0, 1.0] to [0.0, 1.0]
            mapped_sim = max(0.0, min(1.0, (sim + 1.0) / 2.0))
            if mapped_sim >= min_similarity:
                scored.append((mapped_sim, idx))

        scored.sort(key=lambda x: x[0], reverse=True)

        candidates: list[RetrievalCandidate] = []
        for score, idx in scored[:limit]:
            rec = self._chunks[idx]
            ev = EvidenceCitation(
                evidence_type=rec["evidence_type"],
                project_key=rec["project_key"],
                file_path=rec["file_path"] or "",
                start_line=rec["start_line"],
                end_line=rec["end_line"],
                entity_key=rec["entity_key"],
                confidence=round(score, 4),
            )
            candidates.append(
                RetrievalCandidate(
                    id=f"vec:{rec['chunk_id']}",
                    score=round(score, 4),
                    source_index=IndexType.VECTOR,
                    project_key=rec["project_key"],
                    name=rec["name"],
                    title=rec["title"],
                    summary=rec["summary"],
                    file_path=rec["file_path"],
                    entity_key=rec["entity_key"],
                    evidence=ev,
                    metadata=rec["metadata"],
                )
            )

        return candidates

    @property
    def total_count(self) -> int:
        return len(self._chunks)
