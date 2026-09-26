"""Cross-Project Graph Data Models (MVP2-D)
Defines strongly-typed DTOs for multi-project dependencies and cross-project relations.

Enforces:
- LOCK-CROSS-02: Distinct cross-project predicates.
- LOCK-CROSS-03: Immutable cross-project relation_key.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from core.graph.models import RelationKind, ResolutionStatus, SourceOccurrence


class CrossProjectPredicate(str, Enum):
    """Permitted cross-project relationship predicates (LOCK-CROSS-02)."""
    DEPENDS_ON = "depends_on"
    CROSS_IMPORTS = "cross_imports"
    PROVIDES = "provides"
    REFERENCES_CONTRACT = "references_contract"


@dataclass(frozen=True)
class DeclaredDependency:
    """Represents a declared dependency extracted from package.json or pom.xml."""
    name: str
    version_constraint: str
    dependency_type: str  # "production", "dev", "peer", "compile", "test"
    manifest_rel_path: str


@dataclass(frozen=True)
class PackageManifest:
    """Represents an extracted package/module manifest."""
    project_key: str
    manifest_rel_path: str
    package_name: str
    package_version: str
    ecosystem: str  # "npm", "maven"
    dependencies: tuple[DeclaredDependency, ...] = field(default_factory=tuple)
    workspaces: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CrossProjectCandidate:
    """Strongly-typed immutable Cross-Project Relation DTO (LOCK-CROSS-03)."""
    source_project_key: str
    target_project_key: str
    subject_entity_key: str
    predicate: CrossProjectPredicate
    normalized_raw_target: str
    relation_kind: RelationKind = RelationKind.STATIC
    confidence: Decimal = Decimal("1.00000")
    resolution_status: ResolutionStatus = ResolutionStatus.RESOLVED
    object_entity_key: str = ""
    candidate_discriminator: str = "default"
    occurrences: tuple[SourceOccurrence, ...] = field(default_factory=tuple)
    source_file_rel_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def relation_key(self) -> str:
        """Deterministic global identity for cross-project relations (LOCK-CROSS-03)."""
        pred_val = self.predicate.value if isinstance(self.predicate, Enum) else str(self.predicate)
        kind_val = self.relation_kind.value if isinstance(self.relation_kind, Enum) else str(self.relation_kind)
        return (
            f"RELATION:CROSS:"
            f"{self.source_project_key}:"
            f"{self.target_project_key}:"
            f"{self.subject_entity_key}:"
            f"{pred_val}:"
            f"{self.normalized_raw_target}:"
            f"{kind_val}:"
            f"{self.candidate_discriminator}"
        )
