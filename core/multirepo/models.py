"""Multi-Repo Identity and Cross-Repository Contract Models (Stage 2 Section 4.3 & 4.4).

Implements:
- ScopedEntityKey: (repo_id, snapshot_id, entity_id)
- EvidenceLevel: EXACT, STRONG, HEURISTIC, UNKNOWN
- CrossRepoEdge: records source_repo, target_repo, evidence, confidence
- ApiContract: HTTP route contract bridging frontend and backend
- DtoFieldLineage: Cross-stack field mapping between DTOs and TS interfaces
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field as PydanticField


class EvidenceLevel(str, Enum):
    EXACT = "EXACT"
    STRONG = "STRONG"
    HEURISTIC = "HEURISTIC"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ScopedEntityKey:
    repo_id: str
    snapshot_id: str
    entity_id: str

    def __str__(self) -> str:
        return f"{self.repo_id}@{self.snapshot_id}::{self.entity_id}"


@dataclass
class CrossRepoEdge:
    edge_key: str
    source_repo: str
    source_snapshot: str
    source_entity: str
    edge_type: str
    target_repo: str
    target_snapshot: str
    target_entity: str
    evidence_level: EvidenceLevel = EvidenceLevel.STRONG
    confidence: float = 1.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)


class ApiEndpoint(BaseModel):
    repo_id: str
    file_path: str
    http_method: str  # GET, POST, PUT, DELETE
    path: str  # /api/v1/lead/daily-metrics
    symbol_name: str
    line_no: int


class ApiContract(BaseModel):
    contract_id: str
    frontend_endpoint: ApiEndpoint
    backend_endpoint: ApiEndpoint
    evidence_level: EvidenceLevel
    confidence: float
    matched_path: str


class DtoFieldLineage(BaseModel):
    frontend_field: str
    frontend_type: str
    backend_field: str
    backend_type: str
    frontend_entity_key: str
    backend_entity_key: str
    confidence: float = 1.0


class CandidateMatch(BaseModel):
    backend_endpoint: ApiEndpoint
    confidence: float
    evidence_level: EvidenceLevel
    evidence_rationale: str


class RankedApiContract(BaseModel):
    frontend_endpoint: ApiEndpoint
    is_ambiguous: bool = False
    candidates: List[CandidateMatch] = PydanticField(default_factory=list)
    primary_candidate: Optional[CandidateMatch] = None
    ambiguity_details: Optional[str] = None

