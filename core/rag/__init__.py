"""LKIO RAG (Hybrid Retrieval-Augmented Generation) Subsystem."""

from core.rag.builder import DeterministicLocalEmbedder, RAGIndexHub
from core.rag.engine import RAGEngine, RAGQueryResult
from core.rag.fusion import HybridReranker
from core.rag.gateway import GroundedAnswerSynthesizer, LLMProvider, MockOfflineLLMProvider
from core.rag.indices import (
    EntityIndex,
    GraphIndex,
    KeywordIndex,
    TemporalIndex,
    VectorIndex,
)
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    FusedResult,
    IndexType,
    QueryIntent,
    RetrievalCandidate,
)
from core.rag.router import QueryPlan, QueryRouter

__all__ = [
    "RAGEngine",
    "RAGQueryResult",
    "RAGIndexHub",
    "DeterministicLocalEmbedder",
    "QueryRouter",
    "QueryPlan",
    "QueryIntent",
    "IndexType",
    "EvidenceType",
    "EvidenceCitation",
    "RetrievalCandidate",
    "FusedResult",
    "HybridReranker",
    "LLMProvider",
    "MockOfflineLLMProvider",
    "GroundedAnswerSynthesizer",
    "EntityIndex",
    "KeywordIndex",
    "VectorIndex",
    "GraphIndex",
    "TemporalIndex",
]
