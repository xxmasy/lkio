"""Core Domain Models for MVP2-C Code Structural Graph
Defines:
- RelationKind, ResolutionStatus, RelationPredicate enums (LOCK-GRAPH-03, LOCK-GRAPH-05)
- SourceOccurrence value object for evidence preservation (LOCK-GRAPH-09)
- RelationCandidate DTO with deterministic, stable relation_key (LOCK-GRAPH-02, LOCK-GRAPH-10)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class RelationKind(str, Enum):
    STATIC = "STATIC"        # AST explicit syntax facts (confidence == 1.00000)
    INFERRED = "INFERRED"    # Polymorphic dispatch / heuristic calls (confidence < 1.00000)


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"    # Resolved to known project entity
    UNRESOLVED = "UNRESOLVED"# External package/dependency or unindexed entity


class RelationPredicate(str, Enum):
    IMPORTS = "imports"
    EXPORTS = "exports"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"


@dataclass(frozen=True)
class SourceOccurrence:
    """Specific line/column occurrence of a relation in source code (LOCK-GRAPH-09)."""
    line: int
    column: int
    argument_count: int | None = None
    snippet_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {"line": self.line, "column": self.column}
        if self.argument_count is not None:
            d["argument_count"] = self.argument_count
        if self.snippet_hint is not None:
            d["snippet_hint"] = self.snippet_hint
        return d


@dataclass(frozen=True)
class RelationCandidate:
    """Strongly-typed immutable Relation DTO produced by Graph Extractors (LOCK-GRAPH-05)."""
    project_key: str
    subject_entity_key: str
    predicate: RelationPredicate
    normalized_raw_target: str
    relation_kind: RelationKind = RelationKind.STATIC
    confidence: Decimal = Decimal("1.00000")
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    object_entity_key: str | None = None
    candidate_discriminator: str = "default"
    occurrences: tuple[SourceOccurrence, ...] = field(default_factory=tuple)
    source_file_rel_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def relation_key(self) -> str:
        """Global deterministic logical key based on immutable source anchor (LOCK-GRAPH-02, LOCK-GRAPH-10).
        Remains 100% stable when resolution_status transitions UNRESOLVED -> RESOLVED.
        """
        pred_val = self.predicate.value if isinstance(self.predicate, Enum) else str(self.predicate)
        kind_val = self.relation_kind.value if isinstance(self.relation_kind, Enum) else str(self.relation_kind)
        return (
            f"RELATION:{self.project_key}:"
            f"{self.subject_entity_key}:"
            f"{pred_val}:"
            f"{self.normalized_raw_target}:"
            f"{kind_val}:"
            f"{self.candidate_discriminator}"
        )

    def with_resolution(self, object_entity_key: str) -> "RelationCandidate":
        """Returns a resolved copy with object_entity_key set.
        Guarantees that relation_key does NOT mutate (LOCK-GRAPH-10).
        """
        return RelationCandidate(
            project_key=self.project_key,
            subject_entity_key=self.subject_entity_key,
            predicate=self.predicate,
            normalized_raw_target=self.normalized_raw_target,
            relation_kind=self.relation_kind,
            confidence=self.confidence,
            resolution_status=ResolutionStatus.RESOLVED,
            object_entity_key=object_entity_key,
            candidate_discriminator=self.candidate_discriminator,
            occurrences=self.occurrences,
            source_file_rel_path=self.source_file_rel_path,
            metadata=self.metadata,
        )

    def with_occurrences(self, occurrences: tuple[SourceOccurrence, ...]) -> "RelationCandidate":
        """Returns a copy with merged occurrences."""
        return RelationCandidate(
            project_key=self.project_key,
            subject_entity_key=self.subject_entity_key,
            predicate=self.predicate,
            normalized_raw_target=self.normalized_raw_target,
            relation_kind=self.relation_kind,
            confidence=self.confidence,
            resolution_status=self.resolution_status,
            object_entity_key=self.object_entity_key,
            candidate_discriminator=self.candidate_discriminator,
            occurrences=occurrences,
            source_file_rel_path=self.source_file_rel_path,
            metadata=self.metadata,
        )
