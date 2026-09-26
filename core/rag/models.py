"""LKIO RAG Data Models
Defines query intents, retrieval candidates, evidence citations, and fusion structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QueryIntent(str, Enum):
    """Classified user query intents for multi-index routing."""
    ENTITY_LOOKUP = "ENTITY_LOOKUP"      # Direct symbol, class, function, file lookup
    CODE_LOOKUP = "CODE_LOOKUP"          # Implementation details, code blocks, algorithms
    RELATION_QUERY = "RELATION_QUERY"    # Calls, imports, extends, API contract traces
    BUSINESS_QUERY = "BUSINESS_QUERY"    # Business domains, rules, processes, workflows
    HISTORY_QUERY = "HISTORY_QUERY"      # Git commits, authors, change timelines
    SEMANTIC_QUERY = "SEMANTIC_QUERY"    # High-level architecture, conceptual questions
    IMPACT_QUERY = "IMPACT_QUERY"        # Impact analysis, downstream dependents
    UNKNOWN = "UNKNOWN"                  # Fallback


class IndexType(str, Enum):
    """Subsystem index channels."""
    ENTITY = "entity_index"
    KEYWORD = "keyword_index"
    VECTOR = "vector_index"
    GRAPH = "graph_index"
    TEMPORAL = "temporal_index"


class EvidenceType(str, Enum):
    """Types of grounding evidence attached to retrieval candidates."""
    SYMBOL_DEF = "SYMBOL_DEF"            # AST Code symbol definition
    FILE_PATH = "FILE_PATH"              # Physical source file
    GRAPH_EDGE = "GRAPH_EDGE"            # Structural graph relation (imports, calls, etc.)
    API_CONTRACT = "API_CONTRACT"        # Frontend-to-backend API contract trace
    DOC_CHUNK = "DOC_CHUNK"              # Markdown or design document chunk
    CODE_CHUNK = "CODE_CHUNK"            # Code semantic snippet chunk
    GIT_COMMIT = "GIT_COMMIT"            # Git commit log / author / message


@dataclass(frozen=True)
class EvidenceCitation:
    """Grounding proof backing a retrieval result."""
    evidence_type: EvidenceType
    project_key: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    entity_key: str | None = None
    relation_key: str | None = None
    commit_hash: str | None = None
    snippet: str | None = None
    confidence: float = 1.0


@dataclass
class RetrievalCandidate:
    """Individual candidate retrieved from an index channel."""
    id: str
    score: float                         # Channel-specific score (0.0 ~ 1.0)
    source_index: IndexType
    project_key: str
    name: str
    title: str
    summary: str
    file_path: str | None = None
    entity_key: str | None = None
    evidence: EvidenceCitation | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FusedResult:
    """Multi-channel fused and reranked final search result."""
    id: str
    fused_score: float                   # Overall RRF or weighted score (0.0 ~ 1.0)
    channel_scores: dict[str, float]     # Scores per index channel
    channel_ranks: dict[str, int]        # Rank positions per index channel
    project_key: str
    name: str
    title: str
    summary: str
    file_path: str | None = None
    entity_key: str | None = None
    evidences: list[EvidenceCitation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
