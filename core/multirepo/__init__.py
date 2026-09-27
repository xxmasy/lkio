"""Multi-Repository Reasoning and Cross-Repository Contract Engine."""

from core.multirepo.models import (
    ApiContract,
    ApiEndpoint,
    CrossRepoEdge,
    DtoFieldLineage,
    EvidenceLevel,
    ScopedEntityKey,
)
from core.multirepo.api_matcher import ApiContractMatcher
from core.multirepo.dto_matcher import DtoContractMatcher
from core.multirepo.impact import (
    CrossRepoImpactAnalyzer,
    CrossRepoImpactNode,
    CrossRepoImpactResult,
)

__all__ = [
    "ApiContract",
    "ApiEndpoint",
    "CrossRepoEdge",
    "DtoFieldLineage",
    "EvidenceLevel",
    "ScopedEntityKey",
    "ApiContractMatcher",
    "DtoContractMatcher",
    "CrossRepoImpactAnalyzer",
    "CrossRepoImpactNode",
    "CrossRepoImpactResult",
]
