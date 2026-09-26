"""Inferred Relations & Confidence Calibration Engine (C-07)
Produces inferred relational candidates with calibrated confidence scores.

Enforces:
- LOCK-GRAPH-03: Static vs Inferred Separation (distinct relation_kind and candidate_discriminator).
- LOCK-GRAPH-04: Layered Inference (pure static facts untouched, inference sits on top).
- LOCK-GRAPH-07: Confidence Calibration Policy v1:
    - Static facts: 1.00000
    - Single polymorphic dispatch: 0.90000
    - Multi polymorphic dispatch: 1.0 / N (e.g. 0.50000 for N=2)
    - Framework convention: 0.70000
"""

from decimal import Decimal
import logging
from typing import Any

from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
    SourceOccurrence,
)

logger = logging.getLogger(__name__)


class InferenceCalibrationEngine:
    """Calibrates and generates inferred relations according to Confidence Calibration Policy v1."""

    CONFIDENCE_STATIC = Decimal("1.00000")
    CONFIDENCE_SINGLE_DISPATCH = Decimal("0.90000")
    CONFIDENCE_FRAMEWORK_CONVENTION = Decimal("0.70000")

    def expand_polymorphic_dispatch(
        self,
        call_candidate: RelationCandidate,
        implementations: list[dict[str, Any]],  # list of {"symbol_key": str, "method_name": str}
    ) -> list[RelationCandidate]:
        """Expands a static interface/abstract invocation into inferred concrete dispatches (LOCK-GRAPH-07)."""
        n = len(implementations)
        if n == 0:
            return []

        if n == 1:
            confidence = self.CONFIDENCE_SINGLE_DISPATCH
        else:
            # 1.0 / N formatted to 5 decimal places
            confidence = Decimal(f"{1.0 / n:.5f}")

        inferred_candidates: list[RelationCandidate] = []
        for idx, impl in enumerate(implementations):
            impl_key = impl["symbol_key"]
            discriminator = f"dispatch_{idx}"

            inferred_c = RelationCandidate(
                project_key=call_candidate.project_key,
                subject_entity_key=call_candidate.subject_entity_key,
                predicate=RelationPredicate.CALLS,
                normalized_raw_target=call_candidate.normalized_raw_target,
                relation_kind=RelationKind.INFERRED,
                confidence=confidence,
                resolution_status=ResolutionStatus.RESOLVED,
                object_entity_key=impl_key,
                candidate_discriminator=discriminator,
                occurrences=call_candidate.occurrences,
                source_file_rel_path=call_candidate.source_file_rel_path,
                metadata={
                    "inference_type": "polymorphic_dispatch",
                    "interface_target": call_candidate.normalized_raw_target,
                    "implementations_count": n,
                    "dispatch_index": idx,
                },
            )
            inferred_candidates.append(inferred_c)

        return inferred_candidates

    def create_framework_convention_relation(
        self,
        project_key: str,
        subject_entity_key: str,
        predicate: RelationPredicate,
        normalized_raw_target: str,
        object_entity_key: str,
        source_file_rel_path: str,
        occurrences: tuple[SourceOccurrence, ...] = (),
        convention_name: str = "framework_convention",
    ) -> RelationCandidate:
        """Creates an inferred relation based on framework naming conventions (e.g. Vue SFC or Spring)."""
        return RelationCandidate(
            project_key=project_key,
            subject_entity_key=subject_entity_key,
            predicate=predicate,
            normalized_raw_target=normalized_raw_target,
            relation_kind=RelationKind.INFERRED,
            confidence=self.CONFIDENCE_FRAMEWORK_CONVENTION,
            resolution_status=ResolutionStatus.RESOLVED,
            object_entity_key=object_entity_key,
            candidate_discriminator=f"convention_{convention_name}",
            occurrences=occurrences,
            source_file_rel_path=source_file_rel_path,
            metadata={"inference_type": "framework_convention", "convention": convention_name},
        )
