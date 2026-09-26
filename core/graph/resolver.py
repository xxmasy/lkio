"""Intra-Project Symbol Resolver (C-05)
Resolves normalized_raw_target to concrete object_entity_key within the project boundary.

Enforces:
- LOCK-GRAPH-06: Strict Intra-Project Boundary (zero cross-project or external synthetic ghost entities).
- LOCK-GRAPH-10: Identity Invariance Across Resolution (relation_key is strictly immutable).
- LOCK-GRAPH-11: Relational Anchor Rigor (object is Entity key).
"""

from dataclasses import dataclass, field
import logging
import os
import posixpath
from typing import Any

from core.graph.models import (
    RelationCandidate,
    RelationPredicate,
    ResolutionStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ResolverContext:
    """Pre-indexed project symbol and file index for fast intra-project resolution."""
    project_key: str
    file_entities_by_path: dict[str, str] = field(default_factory=dict)  # rel_path -> file_entity_key
    symbols_by_fqn: dict[str, list[str]] = field(default_factory=dict)  # fqn -> list[symbol_entity_key]
    symbols_by_file_and_name: dict[tuple[str, str], list[str]] = field(default_factory=dict)  # (rel_path, name) -> list[keys]
    symbols_by_package_and_name: dict[tuple[str, str], list[str]] = field(default_factory=dict)  # (pkg, name) -> list[keys]
    file_imports_map: dict[str, dict[str, str]] = field(default_factory=dict)  # source_file -> {imported_name -> target_rel_path/fqn}
    alias_map: dict[str, str] = field(default_factory=lambda: {"@/": "src/", "~/": "src/"})

    def register_file(self, rel_path: str, entity_key: str):
        norm_path = posixpath.normpath(rel_path.replace("\\", "/"))
        self.file_entities_by_path[norm_path] = entity_key

    def register_symbol(
        self,
        entity_key: str,
        file_rel_path: str,
        symbol_name: str,
        qualified_name: str | None = None,
        package_name: str | None = None,
    ):
        norm_path = posixpath.normpath(file_rel_path.replace("\\", "/"))
        # Index by file and name
        self.symbols_by_file_and_name.setdefault((norm_path, symbol_name), []).append(entity_key)

        # Index by FQN if available
        if qualified_name:
            self.symbols_by_fqn.setdefault(qualified_name, []).append(entity_key)

        # Index by package and name
        if package_name:
            self.symbols_by_package_and_name.setdefault((package_name, symbol_name), []).append(entity_key)
            fqn = f"{package_name}.{symbol_name}"
            self.symbols_by_fqn.setdefault(fqn, []).append(entity_key)


class IntraProjectSymbolResolver:
    """Resolves static and call relation targets against the intra-project symbol index."""

    def __init__(self, context: ResolverContext | None = None):
        self.context = context

    def resolve_candidates(
        self,
        candidates: list[RelationCandidate],
        context: ResolverContext | None = None,
    ) -> list[RelationCandidate]:
        """Resolves targets for a list of RelationCandidate DTOs.
        Returns a new list of RelationCandidates with resolution_status updated to RESOLVED
        when an internal target is found.
        """
        ctx = context or self.context
        if not ctx:
            return candidates

        resolved_list: list[RelationCandidate] = []
        for cand in candidates:
            # If already resolved, preserve
            if cand.resolution_status == ResolutionStatus.RESOLVED and cand.object_entity_key:
                resolved_list.append(cand)
                continue

            target_key: str | None = None

            if cand.predicate in {RelationPredicate.IMPORTS, RelationPredicate.EXPORTS}:
                target_key = self._resolve_module_target(cand, ctx)
            elif cand.predicate in {RelationPredicate.EXTENDS, RelationPredicate.IMPLEMENTS}:
                target_key = self._resolve_hierarchy_target(cand, ctx)
            elif cand.predicate == RelationPredicate.CALLS:
                target_key = self._resolve_call_target(cand, ctx)

            if target_key:
                resolved = cand.with_resolution(target_key)
                # LOCK-GRAPH-10: Invariance verification
                if resolved.relation_key != cand.relation_key:
                    raise AssertionError(
                        f"LOCK-GRAPH-10 Violation: relation_key mutated upon resolution! "
                        f"Before: {cand.relation_key} != After: {resolved.relation_key}"
                    )
                resolved_list.append(resolved)
            else:
                # Remains UNRESOLVED (e.g. external library or unresolved intra-project)
                resolved_list.append(cand)

        return resolved_list

    def _resolve_module_target(self, cand: RelationCandidate, ctx: ResolverContext) -> str | None:
        raw = cand.normalized_raw_target
        source_file = posixpath.normpath(cand.source_file_rel_path.replace("\\", "/"))
        source_dir = posixpath.dirname(source_file)

        # Handle alias paths
        norm_target = raw
        for alias, prefix in ctx.alias_map.items():
            if raw.startswith(alias):
                norm_target = posixpath.join(prefix, raw[len(alias):])
                break

        # If relative path, join with source_dir
        if raw.startswith("./") or raw.startswith("../"):
            norm_target = posixpath.normpath(posixpath.join(source_dir, raw))

        # Check candidate file extensions
        possible_paths = [
            norm_target,
            norm_target + ".ts",
            norm_target + ".tsx",
            norm_target + ".js",
            norm_target + ".jsx",
            norm_target + ".vue",
            norm_target + ".d.ts",
            posixpath.join(norm_target, "index.ts"),
            posixpath.join(norm_target, "index.tsx"),
            posixpath.join(norm_target, "index.js"),
            posixpath.join(norm_target, "index.jsx"),
            posixpath.join(norm_target, "index.vue"),
        ]

        for p in possible_paths:
            cleaned = posixpath.normpath(p)
            if cleaned in ctx.file_entities_by_path:
                return ctx.file_entities_by_path[cleaned]

        # For Java imports, e.g. org.example.service.OrderService
        # Check if the class symbol or file exists
        if "." in raw and not raw.startswith("."):
            # Check FQN symbols
            if raw in ctx.symbols_by_fqn:
                return ctx.symbols_by_fqn[raw][0]

            # Convert FQN to potential Java file path: org.example.Foo -> org/example/Foo.java
            java_path_suffix = raw.replace(".", "/") + ".java"
            for fpath, fkey in ctx.file_entities_by_path.items():
                if fpath.endswith(java_path_suffix):
                    return fkey

        return None

    def _resolve_hierarchy_target(self, cand: RelationCandidate, ctx: ResolverContext) -> str | None:
        raw = cand.normalized_raw_target
        source_file = posixpath.normpath(cand.source_file_rel_path.replace("\\", "/"))

        # 1. Check FQN if target contains dot
        if "." in raw:
            if raw in ctx.symbols_by_fqn:
                return ctx.symbols_by_fqn[raw][0]

        # 2. Check same file symbols
        if (source_file, raw) in ctx.symbols_by_file_and_name:
            return ctx.symbols_by_file_and_name[(source_file, raw)][0]

        # 3. Check explicit file imports map
        if source_file in ctx.file_imports_map:
            imports = ctx.file_imports_map[source_file]
            if raw in imports:
                target_loc = imports[raw]
                # Could be target_rel_path or FQN
                if (target_loc, raw) in ctx.symbols_by_file_and_name:
                    return ctx.symbols_by_file_and_name[(target_loc, raw)][0]
                if target_loc in ctx.symbols_by_fqn:
                    return ctx.symbols_by_fqn[target_loc][0]

        # 4. Check Java package matching
        # Extract package from source_file if possible
        # e.g. src/main/java/org/example/service/Foo.java -> org.example.service
        parts = source_file.replace("\\", "/").split("/")
        if "java" in parts:
            idx = parts.index("java")
            pkg_parts = parts[idx + 1 : -1]
            pkg = ".".join(pkg_parts)
            if (pkg, raw) in ctx.symbols_by_package_and_name:
                return ctx.symbols_by_package_and_name[(pkg, raw)][0]

        return None

    def _resolve_call_target(self, cand: RelationCandidate, ctx: ResolverContext) -> str | None:
        raw = cand.normalized_raw_target
        source_file = posixpath.normpath(cand.source_file_rel_path.replace("\\", "/"))

        # Check same file
        if (source_file, raw) in ctx.symbols_by_file_and_name:
            return ctx.symbols_by_file_and_name[(source_file, raw)][0]

        # Check imports
        if source_file in ctx.file_imports_map:
            imports = ctx.file_imports_map[source_file]
            if raw in imports:
                target_loc = imports[raw]
                if (target_loc, raw) in ctx.symbols_by_file_and_name:
                    return ctx.symbols_by_file_and_name[(target_loc, raw)][0]

        return None
