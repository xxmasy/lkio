"""Full-Stack and Multi-Project Impact Propagator for MVP7
Categorizes affected nodes across projects, layers (Pages, APIs, Services, Rules), and severity.
"""

from typing import Any
from core.impact.models import (
    ImpactNode,
    ImpactPath,
    ImpactReport,
)


class FullStackImpactPropagator:
    """Classifies graph-traversed entities into full-stack architectural categories."""

    PAGE_KEYWORDS = {"view", "page", "views", "pages", "layout"}
    COMPONENT_KEYWORDS = {"component", "components", "panel", "modal", "drawer", "table", "button"}
    API_KEYWORDS = {"api", "controller", "endpoint", "client", "request"}
    SERVICE_KEYWORDS = {"service", "manager", "handler", "helper", "util"}
    RULE_KEYWORDS = {"rule", "validator", "policy", "business", "leadconversion"}

    def propagate(
        self,
        seed_keys: list[str],
        affected_nodes: list[ImpactNode],
        impact_paths: list[ImpactPath],
    ) -> ImpactReport:
        """Categorizes affected nodes and determines overall impact severity."""
        affected_projects: set[str] = set()
        affected_pages: list[dict[str, Any]] = []
        affected_components: list[dict[str, Any]] = []
        affected_apis: list[dict[str, Any]] = []
        affected_services: list[dict[str, Any]] = []
        affected_rules: list[dict[str, Any]] = []

        # Collect seed projects
        for s in seed_keys:
            parts = s.split(":")
            if len(parts) >= 2:
                affected_projects.add(parts[1])

        for node in affected_nodes:
            affected_projects.add(node.project_key)
            lower_name = node.name.lower()
            lower_path = str(node.path or "").lower()
            ent_type = node.entity_type.upper()

            item_summary = {
                "entity_key": node.entity_key,
                "name": node.name,
                "project_key": node.project_key,
                "path": node.path,
                "hop": node.hop,
                "level": node.level.value,
            }

            # 1. Pages
            if (
                ent_type in ("PAGE", "VIEW")
                or any(k in lower_path for k in self.PAGE_KEYWORDS)
                or lower_path.endswith((".vue", ".tsx"))
            ):
                affected_pages.append(item_summary)

            # 2. Components
            if (
                ent_type == "COMPONENT"
                or any(k in lower_path for k in self.COMPONENT_KEYWORDS)
                or "components/" in lower_path
            ):
                affected_components.append(item_summary)

            # 3. APIs
            if (
                ent_type in ("API", "CONTROLLER", "ENDPOINT")
                or any(k in lower_path for k in self.API_KEYWORDS)
                or any(k in lower_name for k in self.API_KEYWORDS)
            ):
                affected_apis.append(item_summary)

            # 4. Services
            if (
                ent_type == "SERVICE"
                or any(k in lower_path for k in self.SERVICE_KEYWORDS)
                or any(k in lower_name for k in self.SERVICE_KEYWORDS)
            ):
                affected_services.append(item_summary)

            # 5. Business Rules
            if (
                ent_type == "BUSINESS_RULE"
                or any(k in lower_path for k in self.RULE_KEYWORDS)
                or any(k in lower_name for k in self.RULE_KEYWORDS)
            ):
                affected_rules.append(item_summary)

        # Calculate Shortest & Critical Path
        shortest_path = None
        critical_path = None

        if impact_paths:
            # Shortest path = minimum hops
            shortest_path = min(impact_paths, key=lambda p: p.hops)
            # Critical path = maximum hops with cross-project edge or highest node count
            critical_path = max(impact_paths, key=lambda p: (p.hops, p.evidence_count))

        # Severity classification (Baseline Section 33)
        has_cross_project = len(affected_projects) > 1
        has_apis = len(affected_apis) > 0
        has_services = len(affected_services) > 0
        has_rules = len(affected_rules) > 0

        review_reasons = []

        if len(affected_nodes) == 0:
            severity = "NONE"
            conf = 1.0
            requires_review = False
        elif (has_cross_project and has_apis) or (has_services and has_rules):
            severity = "CRITICAL"
            conf = 0.92
            requires_review = True
            review_reasons.append(f"Cross-project boundary propagation ({', '.join(sorted(affected_projects))}) affecting APIs and business rules.")
        elif has_apis or has_services or has_rules or has_cross_project:
            severity = "HIGH"
            conf = 0.88
            requires_review = True
            review_reasons.append("High-level API contract or core business service impacted.")
        elif len(affected_pages) > 2 or len(affected_components) > 3 or len(affected_nodes) > 4:
            severity = "MEDIUM"
            conf = 0.85
            requires_review = True
            review_reasons.append("Multiple UI components and pages impacted.")
        else:
            severity = "LOW"
            conf = 0.90
            requires_review = False

        return ImpactReport(
            seed_entities=seed_keys,
            affected_projects=sorted(list(affected_projects)),
            affected_pages=affected_pages,
            affected_components=affected_components,
            affected_apis=affected_apis,
            affected_services=affected_services,
            affected_business_rules=affected_rules,
            affected_nodes=affected_nodes,
            impact_paths=impact_paths,
            shortest_path=shortest_path,
            critical_path=critical_path,
            overall_impact_level=severity,
            overall_confidence=conf,
            requires_human_review=requires_review,
            review_reasons=review_reasons,
        )
