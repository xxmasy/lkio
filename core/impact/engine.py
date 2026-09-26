"""Unified Impact Analysis Engine for LKIO MVP7
Orchestrates graph traversal, architectural propagation, path analysis, and review flow.
"""

from typing import Any
from core.impact.graph_traversal import ImpactGraphTraversal
from core.impact.models import ImpactReport
from core.impact.path_analyzer import ImpactPathAnalyzer
from core.impact.propagator import FullStackImpactPropagator
from core.impact.review_flow import HumanReviewFlow


class ImpactAnalysisEngine:
    """Master engine for full-stack, multi-hop impact analysis."""

    def __init__(
        self,
        traversal: ImpactGraphTraversal | None = None,
        propagator: FullStackImpactPropagator | None = None,
        path_analyzer: ImpactPathAnalyzer | None = None,
        review_flow: HumanReviewFlow | None = None,
    ):
        self.traversal = traversal or ImpactGraphTraversal(max_depth=3)
        self.propagator = propagator or FullStackImpactPropagator()
        self.path_analyzer = path_analyzer or ImpactPathAnalyzer()
        self.review_flow = review_flow or HumanReviewFlow()

    def analyze_impact(
        self,
        seed_keys: list[str],
        entities_by_key: dict[str, dict[str, Any]],
        relations: list[dict[str, Any]],
        direction: str = "both",
    ) -> ImpactReport:
        """Runs complete end-to-end impact analysis pipeline starting from changed entities."""
        # 1. Multi-hop Graph Traversal (1~3 hops)
        affected_nodes, raw_paths = self.traversal.traverse(
            seed_keys=seed_keys,
            entities_by_key=entities_by_key,
            relations=relations,
            direction=direction,
        )

        # 2. Architectural Categorization & Severity Propagation
        report = self.propagator.propagate(
            seed_keys=seed_keys,
            affected_nodes=affected_nodes,
            impact_paths=raw_paths,
        )

        # 3. Path & Narrative Enrichment
        enriched_report = self.path_analyzer.enrich_report(report)

        return enriched_report

    def generate_review_checklist(self, report: ImpactReport) -> dict[str, Any]:
        """Produces structured Human Review audit checklist."""
        return self.review_flow.generate_review_payload(report)
