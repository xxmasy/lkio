"""LKIO RAG Index Hub and Builder
Orchestrates indexing across the 5 retrieval indices (entity, keyword, vector, graph, temporal).
Provides an offline deterministic embedder and batch indexing pipelines.
"""

import hashlib
import math
from typing import Any, Callable
from core.rag.chunking.chunker import MarkdownDocChunker, SemanticChunk
from core.rag.indices import (
    EntityIndex,
    GraphIndex,
    KeywordIndex,
    TemporalIndex,
    VectorIndex,
)
from core.rag.models import EvidenceType


class DeterministicLocalEmbedder:
    """Offline deterministic dense embedder using character/word n-gram hashing.
    Generates reproducible 128-dimensional dense vectors with semantic overlap properties.
    Requires ZERO external models or internet access, ideal for CI and offline local testing.
    """

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        """Maps arbitrary text to a normalized dense vector."""
        vec = [0.0] * self.dimension
        if not text:
            return vec

        cleaned = text.lower().strip()
        # Word-level n-grams and char 3-grams
        words = cleaned.split()
        tokens = list(words)
        for w in words:
            for i in range(len(w) - 2):
                tokens.append(w[i : i + 3])

        for t in tokens:
            # Deterministic bucket index
            h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            # Sign hash for balanced projections
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            vec[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [x / norm for x in vec]
        return vec


class RAGIndexHub:
    """Unified container and manager of all 5 RAG indices."""

    def __init__(
        self,
        embedder: Callable[[str], list[float]] | None = None,
        dimension: int = 128,
    ) -> None:
        self.embedder = embedder or DeterministicLocalEmbedder(dimension=dimension).embed
        self.dimension = dimension

        self.entity_index = EntityIndex()
        self.keyword_index = KeywordIndex()
        self.vector_index = VectorIndex(dimension=dimension)
        self.graph_index = GraphIndex()
        self.temporal_index = TemporalIndex()

        self.doc_chunker = MarkdownDocChunker()

    def index_entity(
        self,
        entity_key: str,
        name: str,
        canonical_name: str,
        project_key: str,
        entity_type: str,
        file_path: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        docstring: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes an entity into entity_index, keyword_index, and vector_index."""
        meta = metadata or {}
        # 1. Entity index
        self.entity_index.add_entity(
            entity_key=entity_key,
            name=name,
            canonical_name=canonical_name,
            project_key=project_key,
            entity_type=entity_type,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            metadata=meta,
        )

        # 2. Keyword index
        kw_text = f"{name} {canonical_name} {file_path or ''} {docstring or ''}"
        self.keyword_index.add_document(
            doc_id=f"ent:{entity_key}",
            text=kw_text,
            project_key=project_key,
            name=name,
            title=f"[{entity_type}] {canonical_name}",
            summary=docstring or f"Entity {name} ({entity_type})",
            file_path=file_path,
            entity_key=entity_key,
            start_line=start_line,
            end_line=end_line,
            evidence_type=EvidenceType.SYMBOL_DEF,
            metadata=meta,
        )

        # 3. Vector index (for major entities like classes, services, components)
        if entity_type in ("CLASS", "SERVICE", "COMPONENT", "PAGE", "MODULE", "INTERFACE"):
            vec_text = f"{entity_type} {name} {canonical_name}. {docstring or ''}"
            vec = self.embedder(vec_text)
            self.vector_index.add_chunk(
                chunk_id=f"ent:{entity_key}",
                vector=vec,
                project_key=project_key,
                name=name,
                title=f"[{entity_type}] {canonical_name}",
                summary=docstring or f"{entity_type} {name}",
                file_path=file_path,
                entity_key=entity_key,
                start_line=start_line,
                end_line=end_line,
                evidence_type=EvidenceType.CODE_CHUNK,
                metadata=meta,
            )

    def index_document(
        self,
        file_path: str,
        content: str,
        project_key: str,
    ) -> list[SemanticChunk]:
        """Chunks a markdown document and adds chunks to keyword and vector indices."""
        chunks = self.doc_chunker.chunk(content, file_path=file_path, project_key=project_key)
        for c in chunks:
            # Keyword index
            self.keyword_index.add_document(
                doc_id=c.chunk_id,
                text=f"{c.title}\n{c.content}",
                project_key=project_key,
                name=c.title,
                title=f"[{c.project_key}] {c.title}",
                summary=c.content[:200] + ("..." if len(c.content) > 200 else ""),
                file_path=file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                evidence_type=EvidenceType.DOC_CHUNK,
                metadata=c.metadata,
            )

            # Vector index
            vec = self.embedder(f"{c.title}\n{c.content}")
            self.vector_index.add_chunk(
                chunk_id=c.chunk_id,
                vector=vec,
                project_key=project_key,
                name=c.title,
                title=f"[{c.project_key}] {c.title}",
                summary=c.content[:200] + ("..." if len(c.content) > 200 else ""),
                file_path=file_path,
                start_line=c.start_line,
                end_line=c.end_line,
                evidence_type=EvidenceType.DOC_CHUNK,
                metadata=c.metadata,
            )

        return chunks

    def index_relation(
        self,
        relation_key: str,
        subject_key: str,
        predicate: str,
        project_key: str,
        object_key: str | None = None,
        raw_target: str | None = None,
        confidence: float = 1.0,
        file_path: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes a structural graph relation into graph_index."""
        self.graph_index.add_relation(
            relation_key=relation_key,
            subject_key=subject_key,
            predicate=predicate,
            project_key=project_key,
            object_key=object_key,
            raw_target=raw_target,
            confidence=confidence,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            metadata=metadata,
        )

    def index_api_trace(
        self,
        trace_id: str,
        http_method: str,
        http_path: str,
        frontend_call_site: str,
        frontend_project: str,
        backend_controller: str | None = None,
        backend_service: str | None = None,
        backend_project: str | None = None,
        file_path: str | None = None,
        start_line: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes an API contract trace into graph_index, keyword_index, and vector_index."""
        self.graph_index.add_api_trace(
            trace_id=trace_id,
            http_method=http_method,
            http_path=http_path,
            frontend_call_site=frontend_call_site,
            frontend_project=frontend_project,
            backend_controller=backend_controller,
            backend_service=backend_service,
            backend_project=backend_project,
            file_path=file_path,
            start_line=start_line,
            metadata=metadata,
        )

        trace_text = (
            f"API {http_method} {http_path} "
            f"callsite: {frontend_call_site} "
            f"controller: {backend_controller or ''} "
            f"service: {backend_service or ''}"
        )
        proj = backend_project or frontend_project

        # Keyword index
        self.keyword_index.add_document(
            doc_id=f"api:{trace_id}",
            text=trace_text,
            project_key=proj,
            name=f"{http_method} {http_path}",
            title=f"API Contract: {http_method} {http_path}",
            summary=f"Endpoint {http_method} {http_path} -> {backend_controller or 'N/A'}",
            file_path=file_path,
            start_line=start_line,
            evidence_type=EvidenceType.API_CONTRACT,
            metadata=metadata,
        )

        # Vector index
        vec = self.embedder(trace_text)
        self.vector_index.add_chunk(
            chunk_id=f"api:{trace_id}",
            vector=vec,
            project_key=proj,
            name=f"{http_method} {http_path}",
            title=f"API Contract: {http_method} {http_path}",
            summary=f"Endpoint {http_method} {http_path} -> {backend_controller or 'N/A'}",
            file_path=file_path,
            start_line=start_line,
            evidence_type=EvidenceType.API_CONTRACT,
            metadata=metadata,
        )

    def index_commit(
        self,
        commit_hash: str,
        message: str,
        author: str,
        timestamp: str,
        project_key: str,
        files_changed: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes a Git commit into temporal_index and keyword_index."""
        self.temporal_index.add_commit(
            commit_hash=commit_hash,
            message=message,
            author=author,
            timestamp=timestamp,
            project_key=project_key,
            files_changed=files_changed,
            metadata=metadata,
        )
        self.keyword_index.add_document(
            doc_id=f"commit:{commit_hash}",
            text=f"{commit_hash} {author} {message} {' '.join(files_changed or [])}",
            project_key=project_key,
            name=commit_hash[:8],
            title=f"Commit [{commit_hash[:8]}] by {author}",
            summary=f"{message} ({timestamp})",
            file_path=files_changed[0] if files_changed else None,
            evidence_type=EvidenceType.GIT_COMMIT,
            metadata=metadata,
        )
