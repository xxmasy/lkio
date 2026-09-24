"""Pydantic Schemas for Cytoscape Graph Data
"""

from typing import Any
from pydantic import BaseModel, Field


class GraphNodeData(BaseModel):
    id: str
    label: str
    entity_type: str
    entity_key: str
    canonical_name: str
    project_id: str | None = None
    status: str = "ACTIVE"
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    data: GraphNodeData


class GraphEdgeData(BaseModel):
    id: str
    source: str
    target: str
    label: str
    predicate: str
    confidence: float = 1.0
    source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    data: GraphEdgeData


class GraphData(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
