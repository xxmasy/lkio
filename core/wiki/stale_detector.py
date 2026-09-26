"""LKIO Wiki Stale Detection Engine
Maps source code/file/entity modifications to affected Wiki sections.
Enforces the inviolable redline: "Regenerate only affected sections" (Baseline Section 26).
"""

from core.models.wiki import StandardWikiSection


class StaleDetector:
    """Detects which Wiki sections become STALE when source files or entities change."""

    # File path pattern -> Affected Wiki Sections
    PATH_RULE_MAPPINGS = [
        # API layer
        (r"(api/|controller/|@requestmapping|@getmapping|@postmapping)", [StandardWikiSection.API, StandardWikiSection.ARCHITECTURE]),
        # Frontend UI & routes
        (r"(\.vue|views/|components/|router/|store/)", [StandardWikiSection.FRONTEND, StandardWikiSection.ARCHITECTURE]),
        # Backend business services
        (r"(service/|impl/|\.java)", [StandardWikiSection.BACKEND, StandardWikiSection.BUSINESS_RULES, StandardWikiSection.BUSINESS_PROCESS]),
        # Database & DTO models
        (r"(dto/|vo/|pojo/|model/|entity/|mapper/|repository/)", [StandardWikiSection.DATABASE, StandardWikiSection.BUSINESS_DOMAIN]),
        # Dependencies & manifests
        (r"(package\.json|pom\.xml|pnpm-lock\.yaml|workspace)", [StandardWikiSection.DEPENDENCIES, StandardWikiSection.ARCHITECTURE]),
        # Docs & questions
        (r"(open_questions|risks|known_risks|todo)", [StandardWikiSection.KNOWN_RISKS, StandardWikiSection.OPEN_DECISIONS]),
        # General business docs
        (r"(business|report|spec|whitepaper)", [StandardWikiSection.BUSINESS_DOMAIN, StandardWikiSection.BUSINESS_RULES]),
    ]

    def detect_stale_sections(
        self,
        modified_files: list[str],
        modified_entity_keys: list[str] | None = None,
        existing_section_evidences: dict[StandardWikiSection, list[str]] | None = None,
    ) -> set[StandardWikiSection]:
        """Calculates the set of StandardWikiSection that must be regenerated."""
        stale_sections: set[StandardWikiSection] = set()

        # Always mark RECENT_CHANGES as stale if any files changed
        if modified_files:
            stale_sections.add(StandardWikiSection.RECENT_CHANGES)

        # 1. Path-based rules
        import re
        for f in modified_files:
            f_lower = f.lower().replace("\\", "/")
            for pattern, affected_secs in self.PATH_RULE_MAPPINGS:
                if re.search(pattern, f_lower):
                    for sec in affected_secs:
                        stale_sections.add(sec)

        # 2. Evidence-based intersection (if existing sections have recorded source files/entities)
        if existing_section_evidences:
            mod_set = set(modified_files) | set(modified_entity_keys or [])
            for sec_name, recorded_sources in existing_section_evidences.items():
                if any(src in mod_set for src in recorded_sources):
                    stale_sections.add(sec_name)

        return stale_sections
