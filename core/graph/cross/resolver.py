"""Cross-Project Dependency Resolver (D-02)
Resolves cross-project dependencies and module imports against the global manifest registry.

Enforces:
- LOCK-CROSS-02: Distinct cross-project predicates (depends_on, cross_imports).
- LOCK-CROSS-03: Immutable cross-project relation keys.
- LOCK-CROSS-04: Grounded evidence from package manifests.
"""

from decimal import Decimal
import logging
from typing import Any

from core.graph.cross.manifest import CrossProjectManifestRegistry
from core.graph.cross.models import (
    CrossProjectCandidate,
    CrossProjectPredicate,
    PackageManifest,
)
from core.graph.models import (
    RelationCandidate,
    RelationKind,
    RelationPredicate,
    ResolutionStatus,
)

logger = logging.getLogger(__name__)


class CrossProjectDependencyResolver:
    """Resolves cross-project dependencies and import links using package manifest coordinates."""

    def __init__(self, registry: CrossProjectManifestRegistry):
        self.registry = registry

    def resolve_manifest_dependencies(self) -> list[CrossProjectCandidate]:
        """Resolves declared dependencies between registered projects (depends_on)."""
        cross_candidates: list[CrossProjectCandidate] = []

        for src_proj_key, manifests in self.registry.manifests_by_project.items():
            for m in manifests:
                src_subject = f"FILE:{src_proj_key}:{m.manifest_rel_path}"

                for dep in m.dependencies:
                    provider = self.registry.find_provider(dep.name)
                    if provider and provider.project_key != src_proj_key:
                        tgt_proj_key = provider.project_key
                        tgt_object = f"FILE:{tgt_proj_key}:{provider.manifest_rel_path}"

                        cand = CrossProjectCandidate(
                            source_project_key=src_proj_key,
                            target_project_key=tgt_proj_key,
                            subject_entity_key=src_subject,
                            predicate=CrossProjectPredicate.DEPENDS_ON,
                            normalized_raw_target=dep.name,
                            relation_kind=RelationKind.STATIC,
                            confidence=Decimal("1.00000"),
                            resolution_status=ResolutionStatus.RESOLVED,
                            object_entity_key=tgt_object,
                            candidate_discriminator=f"manifest_dep_{dep.dependency_type}",
                            source_file_rel_path=m.manifest_rel_path,
                            metadata={
                                "dependency_name": dep.name,
                                "version_constraint": dep.version_constraint,
                                "dependency_type": dep.dependency_type,
                                "source_manifest": m.manifest_rel_path,
                                "target_manifest": provider.manifest_rel_path,
                            },
                        )
                        cross_candidates.append(cand)

        return cross_candidates

    def resolve_cross_imports(
        self,
        unresolved_candidates: list[RelationCandidate],
        file_entities_by_project: dict[str, dict[str, str]] | None = None,
    ) -> list[CrossProjectCandidate]:
        """Resolves previously UNRESOLVED intra-project imports across project boundaries (cross_imports)."""
        cross_imports: list[CrossProjectCandidate] = []
        file_map = file_entities_by_project or {}

        for cand in unresolved_candidates:
            if cand.predicate != RelationPredicate.IMPORTS:
                continue

            raw = cand.normalized_raw_target
            src_proj = cand.project_key

            # Check if raw target matches or begins with a known package name
            # e.g. "@vben/core" or "@vben/core/base"
            best_match: PackageManifest | None = None
            for pkg_name, providers in self.registry.manifests_by_package.items():
                if raw == pkg_name or raw.startswith(pkg_name + "/"):
                    for p in providers:
                        if p.project_key != src_proj:
                            best_match = p
                            break
                    if best_match:
                        break

            if best_match:
                tgt_proj = best_match.project_key
                tgt_key = f"FILE:{tgt_proj}:{best_match.manifest_rel_path}"

                cross_cand = CrossProjectCandidate(
                    source_project_key=src_proj,
                    target_project_key=tgt_proj,
                    subject_entity_key=cand.subject_entity_key,
                    predicate=CrossProjectPredicate.CROSS_IMPORTS,
                    normalized_raw_target=cand.normalized_raw_target,
                    relation_kind=RelationKind.STATIC,
                    confidence=Decimal("1.00000"),
                    resolution_status=ResolutionStatus.RESOLVED,
                    object_entity_key=tgt_key,
                    candidate_discriminator="cross_module_import",
                    occurrences=cand.occurrences,
                    source_file_rel_path=cand.source_file_rel_path,
                    metadata={
                        "imported_package": best_match.package_name,
                        "provider_manifest": best_match.manifest_rel_path,
                    },
                )
                cross_imports.append(cross_cand)

        return cross_imports
