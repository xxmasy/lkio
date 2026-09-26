"""Pydantic Models and DTOs for MVP7 Impact Analysis Engine
Implements Baseline Section 33 & 34 specifications.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ImpactHopLevel(str, Enum):
    DIRECT = "DIRECT"        # 1-hop
    INDIRECT = "INDIRECT"    # 2-hop
    POTENTIAL = "POTENTIAL"  # 3-hop
    HISTORICAL = "HISTORICAL"


class EvidenceKind(str, Enum):
    CODE_RELATION = "CODE_RELATION"
    DOCUMENT_RELATION = "DOCUMENT_RELATION"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    INFERRED = "INFERRED"
    HISTORICAL = "HISTORICAL"


class ImpactNode(BaseModel):
    """Represents an affected entity reached during graph traversal."""
    entity_key: str
    name: str
    entity_type: str
    project_key: str
    path: str | None = None
    hop: int
    level: ImpactHopLevel
    evidence_sources: list[str] = Field(default_factory=list)


class ImpactEdge(BaseModel):
    """Represents a directional dependency step along the impact trajectory."""
    source_key: str
    target_key: str
    relation_type: str
    confidence: float = 1.0
    evidence_kind: EvidenceKind = EvidenceKind.CODE_RELATION
    evidence_details: dict[str, Any] = Field(default_factory=dict)


class ImpactPath(BaseModel):
    """A traceable path from a seed changed entity to a downstream/upstream entity."""
    nodes: list[str]
    edges: list[ImpactEdge]
    hops: int
    path_confidence: float
    evidence_count: int
    description: str = ""


class ImpactReport(BaseModel):
    """Comprehensive impact analysis output (Baseline Section 33 & 34)."""
    seed_entities: list[str]
    affected_projects: list[str] = Field(default_factory=list)
    affected_pages: list[dict[str, Any]] = Field(default_factory=list)
    affected_components: list[dict[str, Any]] = Field(default_factory=list)
    affected_apis: list[dict[str, Any]] = Field(default_factory=list)
    affected_services: list[dict[str, Any]] = Field(default_factory=list)
    affected_business_rules: list[dict[str, Any]] = Field(default_factory=list)
    affected_nodes: list[ImpactNode] = Field(default_factory=list)
    impact_paths: list[ImpactPath] = Field(default_factory=list)
    shortest_path: ImpactPath | None = None
    critical_path: ImpactPath | None = None
    overall_impact_level: str = "LOW"  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    overall_confidence: float = 1.0
    requires_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
