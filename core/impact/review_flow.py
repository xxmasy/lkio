"""Human Review Flow Generator for MVP7
Transforms raw impact graph results into structured, actionable engineering review checklists.
"""

from typing import Any
from core.impact.models import ImpactHopLevel, ImpactReport


class HumanReviewFlow:
    """Produces structured Human Review audit checklists and mitigation recommendations."""

    def generate_review_payload(self, report: ImpactReport) -> dict[str, Any]:
        """Generates an executive review packet for engineering teams."""
        direct_nodes = [n for n in report.affected_nodes if n.level == ImpactHopLevel.DIRECT]
        indirect_nodes = [n for n in report.affected_nodes if n.level == ImpactHopLevel.INDIRECT]
        potential_nodes = [n for n in report.affected_nodes if n.level == ImpactHopLevel.POTENTIAL]

        # Recommended verification actions
        recommended_actions = []
        if report.affected_pages:
            recommended_actions.append(
                f"Verify UI rendering and routing on affected pages: {', '.join(p['name'] for p in report.affected_pages[:3])}."
            )
        if report.affected_apis:
            recommended_actions.append(
                f"Run contract and integration smoke tests on APIs: {', '.join(a['name'] for a in report.affected_apis[:3])}."
            )
        if report.affected_business_rules:
            recommended_actions.append(
                f"Audit domain business invariants for rules: {', '.join(r['name'] for r in report.affected_business_rules[:3])}."
            )
        if len(report.affected_projects) > 1:
            recommended_actions.append(
                f"Conduct cross-project alignment check between: {', '.join(report.affected_projects)}."
            )

        return {
            "status": "REQUIRES_HUMAN_REVIEW" if report.requires_human_review else "AUTO_APPROVED",
            "overall_impact_level": report.overall_impact_level,
            "overall_confidence": report.overall_confidence,
            "review_reasons": report.review_reasons,
            "scope": {
                "affected_projects": report.affected_projects,
                "direct_impact_count": len(direct_nodes),
                "indirect_impact_count": len(indirect_nodes),
                "potential_impact_count": len(potential_nodes),
                "total_affected_entities": len(report.affected_nodes),
            },
            "summary_counts": {
                "pages": len(report.affected_pages),
                "components": len(report.affected_components),
                "apis": len(report.affected_apis),
                "services": len(report.affected_services),
                "business_rules": len(report.affected_business_rules),
            },
            "critical_path": report.critical_path.description if report.critical_path else None,
            "shortest_path": report.shortest_path.description if report.shortest_path else None,
            "recommended_actions": recommended_actions,
        }
