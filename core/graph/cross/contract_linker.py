"""Cross-Project Contract Linker (D-03)
Links shared data models, DTOs, and interface contracts across project boundaries.

Enforces:
- LOCK-CROSS-02: Predicate REFERENCES_CONTRACT.
- LOCK-CROSS-04: Grounded contract names with calibrated confidence.
"""

from decimal import Decimal
import logging
from typing import Any

from core.graph.cross.models import CrossProjectCandidate, CrossProjectPredicate
from core.graph.models import RelationKind, ResolutionStatus, SourceOccurrence

logger = logging.getLogger(__name__)


class CrossProjectContractLinker:
    """Discovers and links shared contract references between frontend consumers and backend providers."""

    def __init__(self):
        # Maps contract_name -> list of {"project_key": str, "entity_key": str, "file_rel_path": str}
        self.contract_providers: dict[str, list[dict[str, Any]]] = {}

    def register_contract_provider(
        self,
        project_key: str,
        contract_name: str,
        entity_key: str,
        file_rel_path: str,
    ):
        """Registers a contract/DTO provider (typically from backend service or schema repository)."""
        self.contract_providers.setdefault(contract_name, []).append({
            "project_key": project_key,
            "entity_key": entity_key,
            "file_rel_path": file_rel_path,
        })

    def link_contract_references(
        self,
        consumer_project_key: str,
        references: list[dict[str, Any]],  # list of {"contract_name": str, "subject_key": str, "file_rel_path": str, "occurrences": tuple}
    ) -> list[CrossProjectCandidate]:
        """Resolves references to shared contracts from a consumer project."""
        cross_candidates: list[CrossProjectCandidate] = []

        for ref in references:
            cname = ref["contract_name"]
            providers = self.contract_providers.get(cname, [])

            for p in providers:
                if p["project_key"] == consumer_project_key:
                    continue  # Intra-project handled elsewhere

                tgt_proj = p["project_key"]
                tgt_key = p["entity_key"]

                cand = CrossProjectCandidate(
                    source_project_key=consumer_project_key,
                    target_project_key=tgt_proj,
                    subject_entity_key=ref["subject_key"],
                    predicate=CrossProjectPredicate.REFERENCES_CONTRACT,
                    normalized_raw_target=cname,
                    relation_kind=RelationKind.INFERRED,
                    confidence=Decimal("0.85000"),
                    resolution_status=ResolutionStatus.RESOLVED,
                    object_entity_key=tgt_key,
                    candidate_discriminator="shared_contract_match",
                    occurrences=ref.get("occurrences", ()),
                    source_file_rel_path=ref.get("file_rel_path", ""),
                    metadata={
                        "contract_name": cname,
                        "provider_entity_key": tgt_key,
                    },
                )
                cross_candidates.append(cand)

        return cross_candidates
