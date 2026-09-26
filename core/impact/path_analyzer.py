"""Evidence Chain and Path Analyzer for MVP7 Impact Engine
Implements Baseline Section 34 specifications:
- Evidence binding (CODE_RELATION, INFERRED, etc.)
- Shortest Path and Critical Path extraction
- Human-readable narrative generation
"""

from core.impact.models import (
    ImpactPath,
    ImpactReport,
)


class ImpactPathAnalyzer:
    """Analyzes and narrates impact propagation trajectories and evidence chains."""

    def format_narrative(self, path: ImpactPath) -> str:
        """Constructs an explainable human-readable narrative of an impact path."""
        if not path.edges:
            return " -> ".join(path.nodes)

        steps = []
        for i, edge in enumerate(path.edges):
            if i == 0:
                steps.append(edge.source_key)
            rel_label = f"[{edge.relation_type}]"
            steps.append(f"--{rel_label}--> {edge.target_key}")

        return f"{' '.join(steps)} (confidence: {path.path_confidence}, hops: {path.hops})"

    def enrich_report(self, report: ImpactReport) -> ImpactReport:
        """Enriches the ImpactReport with path narratives and summary insights."""
        for path in report.impact_paths:
            path.description = self.format_narrative(path)

        if report.shortest_path:
            report.shortest_path.description = self.format_narrative(report.shortest_path)
        if report.critical_path:
            report.critical_path.description = self.format_narrative(report.critical_path)

        return report
