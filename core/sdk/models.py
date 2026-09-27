"""Unified LKIO SDK Data Models (Stage 0 Baseline Section 2.2.4).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    file_path: str
    score: float
    snippet: str
    entity_key: Optional[str] = None


class SymbolDef(BaseModel):
    name: str
    kind: str
    uri: str
    file_path: str
    line_start: int
    line_end: int
    signature: Optional[str] = None


class Reference(BaseModel):
    source_uri: str
    target_uri: str
    line_no: int
    reference_type: str = "CALLS"


class DependencySubGraph(BaseModel):
    seed: str
    max_depth: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class ImpactReport(BaseModel):
    direct: List[str]
    indirect: List[str]
    potential: List[str]
    evidence_paths: List[List[str]] = Field(default_factory=list)
    risk_level: str = "LOW"


class CommitEvent(BaseModel):
    commit_id: str
    author: str
    date: str
    message: str
    changed_files: List[str] = Field(default_factory=list)


class SnapshotGraph(BaseModel):
    snapshot_id: str
    repo_id: str
    commit_id: str
    node_count: int
    edge_count: int
    status: str = "PUBLISHED"


class ArchitecturalExplanation(BaseModel):
    entity_key: str
    role: str
    summary: str
    dependencies: List[str] = Field(default_factory=list)


class CalibratedDecision(BaseModel):
    decision: str
    confidence: float
    requires_human_review: bool
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
