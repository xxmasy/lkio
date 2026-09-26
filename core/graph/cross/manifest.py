"""Cross-Project Manifest & Package Registry (D-01)
Discovers and indexes declared package manifests across npm (package.json) and Maven (pom.xml).

Enforces:
- LOCK-CROSS-04: Zero Guessing (links based strictly on parsed package coordinates).
- LOCK-CROSS-06: Read-only access to filesystem.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from core.graph.cross.models import DeclaredDependency, PackageManifest

logger = logging.getLogger(__name__)

PRUNED_DIRS = {".git", "node_modules", "target", "dist", ".idea", ".vscode", "build", "out", ".output"}


class CrossProjectManifestRegistry:
    """Discovers, parses, and indexes package manifests across multiple software projects."""

    def __init__(self):
        self.manifests_by_package: dict[str, list[PackageManifest]] = {}
        self.manifests_by_project: dict[str, list[PackageManifest]] = {}

    def register_manifest(self, manifest: PackageManifest):
        """Registers a parsed manifest into global index."""
        self.manifests_by_package.setdefault(manifest.package_name, []).append(manifest)
        self.manifests_by_project.setdefault(manifest.project_key, []).append(manifest)

    def scan_project_manifests(self, project_key: str, project_root: Path) -> list[PackageManifest]:
        """Traverses project root safely, locating and parsing all package.json and pom.xml files."""
        discovered: list[PackageManifest] = []
        if not project_root.exists():
            return discovered

        for dirpath, dirnames, filenames in os.walk(project_root):
            dirnames[:] = [d for d in dirnames if d not in PRUNED_DIRS and not d.startswith(".")]

            for fname in filenames:
                fpath = Path(dirpath) / fname
                rel_path = fpath.relative_to(project_root).as_posix()

                if fname == "package.json":
                    manifest = self._parse_package_json(project_key, fpath, rel_path)
                    if manifest:
                        discovered.append(manifest)
                        self.register_manifest(manifest)

                elif fname == "pom.xml":
                    manifest = self._parse_pom_xml(project_key, fpath, rel_path)
                    if manifest:
                        discovered.append(manifest)
                        self.register_manifest(manifest)

        return discovered

    def _parse_package_json(self, project_key: str, file_path: Path, rel_path: str) -> PackageManifest | None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(content)
            pkg_name = data.get("name")
            if not pkg_name:
                return None

            pkg_version = data.get("version", "0.0.0")

            deps: list[DeclaredDependency] = []
            for dep_name, ver in data.get("dependencies", {}).items():
                deps.append(DeclaredDependency(
                    name=dep_name,
                    version_constraint=str(ver),
                    dependency_type="production",
                    manifest_rel_path=rel_path,
                ))
            for dep_name, ver in data.get("devDependencies", {}).items():
                deps.append(DeclaredDependency(
                    name=dep_name,
                    version_constraint=str(ver),
                    dependency_type="dev",
                    manifest_rel_path=rel_path,
                ))

            workspaces = []
            ws_raw = data.get("workspaces")
            if isinstance(ws_raw, list):
                workspaces = ws_raw
            elif isinstance(ws_raw, dict) and "packages" in ws_raw:
                workspaces = ws_raw["packages"]

            return PackageManifest(
                project_key=project_key,
                manifest_rel_path=rel_path,
                package_name=pkg_name,
                package_version=pkg_version,
                ecosystem="npm",
                dependencies=tuple(deps),
                workspaces=tuple(workspaces),
                metadata={"private": data.get("private", False)},
            )
        except Exception as e:
            logger.warning("Failed to parse package.json at %s: %s", file_path, e)
            return None

    def _parse_pom_xml(self, project_key: str, file_path: Path, rel_path: str) -> PackageManifest | None:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            # Strip XML namespace if present
            ns = ""
            if "}" in root.tag:
                ns = root.tag.split("}")[0] + "}"

            group_id_el = root.find(f"{ns}groupId")
            if group_id_el is None:
                parent_el = root.find(f"{ns}parent")
                if parent_el is not None:
                    group_id_el = parent_el.find(f"{ns}groupId")

            artifact_id_el = root.find(f"{ns}artifactId")
            version_el = root.find(f"{ns}version")
            if version_el is None:
                parent_el = root.find(f"{ns}parent")
                if parent_el is not None:
                    version_el = parent_el.find(f"{ns}version")

            group_id = group_id_el.text.strip() if group_id_el is not None and group_id_el.text else "unknown"
            artifact_id = artifact_id_el.text.strip() if artifact_id_el is not None and artifact_id_el.text else "unknown"
            version = version_el.text.strip() if version_el is not None and version_el.text else "0.0.0"

            pkg_name = f"{group_id}:{artifact_id}"

            deps: list[DeclaredDependency] = []
            deps_el = root.find(f"{ns}dependencies")
            if deps_el is not None:
                for d in deps_el.findall(f"{ns}dependency"):
                    d_gid = d.find(f"{ns}groupId")
                    d_aid = d.find(f"{ns}artifactId")
                    d_ver = d.find(f"{ns}version")
                    d_scope = d.find(f"{ns}scope")

                    if d_gid is not None and d_aid is not None and d_gid.text and d_aid.text:
                        d_name = f"{d_gid.text.strip()}:{d_aid.text.strip()}"
                        v_str = d_ver.text.strip() if d_ver is not None and d_ver.text else "managed"
                        scope = d_scope.text.strip() if d_scope is not None and d_scope.text else "compile"
                        deps.append(DeclaredDependency(
                            name=d_name,
                            version_constraint=v_str,
                            dependency_type=scope,
                            manifest_rel_path=rel_path,
                        ))

            return PackageManifest(
                project_key=project_key,
                manifest_rel_path=rel_path,
                package_name=pkg_name,
                package_version=version,
                ecosystem="maven",
                dependencies=tuple(deps),
                metadata={"groupId": group_id, "artifactId": artifact_id},
            )
        except Exception as e:
            logger.warning("Failed to parse pom.xml at %s: %s", file_path, e)
            return None

    def find_provider(self, package_name: str) -> PackageManifest | None:
        """Finds a project manifest that provides the given package name."""
        manifests = self.manifests_by_package.get(package_name)
        if manifests:
            return manifests[0]
        return None
