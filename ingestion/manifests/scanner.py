"""Manifest Scanner for Dependency and Package Manager Detection
Extracts dependencies from package.json, pom.xml, pyproject.toml, and requirements.txt.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET


@dataclass
class DependencyInfo:
    name: str
    version_spec: str
    ecosystem: str  # npm, maven, pypi
    manifest_path: str
    is_direct: bool = True
    scope: str = "dependencies"  # dependencies, devDependencies, compile, test, etc.


@dataclass
class ManifestInfo:
    relative_path: str
    manifest_type: str
    package_manager: str
    dependencies: list[DependencyInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


def detect_package_manager(project_root: Path) -> tuple[str, list[str]]:
    """Detects primary package manager and flags lockfile conflicts according to Section 21."""
    warnings: list[str] = []
    detected: list[str] = []

    # Node ecosystem
    has_pnpm = (project_root / "pnpm-lock.yaml").exists()
    has_yarn = (project_root / "yarn.lock").exists()
    has_npm = (project_root / "package-lock.json").exists()

    if has_pnpm:
        detected.append("pnpm")
    if has_yarn:
        detected.append("yarn")
    if has_npm:
        detected.append("npm")

    if len(detected) > 1:
        warnings.append(f"Multiple lockfiles found: {', '.join(detected)}; marked as conflict")
        return "conflict", warnings

    if detected:
        return detected[0], warnings

    # Java ecosystem
    if (project_root / "pom.xml").exists():
        return "maven", warnings
    if (project_root / "build.gradle").exists() or (project_root / "build.gradle.kts").exists():
        return "gradle", warnings

    # Python ecosystem
    if (project_root / "uv.lock").exists():
        return "uv", warnings
    if (project_root / "poetry.lock").exists():
        return "poetry", warnings
    if (project_root / "Pipfile.lock").exists():
        return "pipenv", warnings
    if (project_root / "pyproject.toml").exists() or (project_root / "requirements.txt").exists():
        return "pip", warnings

    if (project_root / "package.json").exists():
        return "npm", warnings

    return "unknown", warnings


def parse_package_json(project_root: Path, rel_path: str = "package.json") -> ManifestInfo | None:
    file_path = project_root / rel_path
    if not file_path.is_file():
        return None

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        return ManifestInfo(
            relative_path=rel_path,
            manifest_type="npm_package_json",
            package_manager="npm",
            warnings=[f"Failed to parse package.json: {e}"],
        )

    pkg_manager, mgr_warnings = detect_package_manager(project_root)

    deps: list[DependencyInfo] = []

    for dep_type in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
        dep_dict = data.get(dep_type, {})
        if isinstance(dep_dict, dict):
            for name, ver in dep_dict.items():
                deps.append(
                    DependencyInfo(
                        name=str(name),
                        version_spec=str(ver),
                        ecosystem="npm",
                        manifest_path=rel_path,
                        is_direct=True,
                        scope=dep_type,
                    )
                )

    return ManifestInfo(
        relative_path=rel_path,
        manifest_type="npm_package_json",
        package_manager=pkg_manager,
        dependencies=deps,
        warnings=mgr_warnings,
        raw_metadata={
            "name": data.get("name"),
            "version": data.get("version"),
            "scripts": list(data.get("scripts", {}).keys()),
        },
    )


def parse_pom_xml(project_root: Path, rel_path: str = "pom.xml") -> ManifestInfo | None:
    file_path = project_root / rel_path
    if not file_path.is_file():
        return None

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        return ManifestInfo(
            relative_path=rel_path,
            manifest_type="maven_pom_xml",
            package_manager="maven",
            warnings=[f"Failed to parse pom.xml: {e}"],
        )

    # Strip XML namespaces for tag matching
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    deps: list[DependencyInfo] = []
    dependencies_elem = root.find("dependencies")
    if dependencies_elem is not None:
        for dep in dependencies_elem.findall("dependency"):
            group_id = dep.findtext("groupId", "").strip()
            artifact_id = dep.findtext("artifactId", "").strip()
            version = dep.findtext("version", "managed").strip()
            scope = dep.findtext("scope", "compile").strip()

            dep_name = f"{group_id}:{artifact_id}" if group_id else artifact_id
            deps.append(
                DependencyInfo(
                    name=dep_name,
                    version_spec=version,
                    ecosystem="maven",
                    manifest_path=rel_path,
                    is_direct=True,
                    scope=scope,
                )
            )

    return ManifestInfo(
        relative_path=rel_path,
        manifest_type="maven_pom_xml",
        package_manager="maven",
        dependencies=deps,
        warnings=[],
        raw_metadata={
            "groupId": root.findtext("groupId"),
            "artifactId": root.findtext("artifactId"),
            "version": root.findtext("version"),
        },
    )


def scan_all_manifests(project_root: Path) -> list[ManifestInfo]:
    """Scans all supported manifests present in the project root or first-level subdirectories."""
    manifests: list[ManifestInfo] = []

    # 1. Root package.json
    pkg_info = parse_package_json(project_root, "package.json")
    if pkg_info:
        manifests.append(pkg_info)

    # 2. Root pom.xml
    pom_info = parse_pom_xml(project_root, "pom.xml")
    if pom_info:
        manifests.append(pom_info)

    # 3. Check for monorepo packages/apps package.json (e.g. apps/web-ele/package.json in L2C)
    for sub in ["apps", "packages"]:
        sub_dir = project_root / sub
        if sub_dir.is_dir():
            for child in sub_dir.iterdir():
                child_pkg = child / "package.json"
                if child_pkg.is_file():
                    rel_p = f"{sub}/{child.name}/package.json"
                    sub_info = parse_package_json(project_root, rel_p)
                    if sub_info:
                        manifests.append(sub_info)

    return manifests
