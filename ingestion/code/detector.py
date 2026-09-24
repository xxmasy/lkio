"""Code and Framework Detector
Performs rule-based, deterministic language and framework detection with audit evidence.
Strictly prohibits LLM hallucination and Tree-sitter in MVP1.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ingestion.manifests.scanner import ManifestInfo

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".vue": "Vue",
    ".java": "Java",
    ".py": "Python",
    ".go": "Go",
    ".rs": "Rust",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".sh": "Shell",
    ".bat": "Batch",
    ".ps1": "PowerShell",
}


@dataclass
class LanguageStats:
    primary_language: str
    languages: list[dict[str, Any]]  # [{"name": "TypeScript", "file_count": 120, "percentage": 0.65}, ...]


@dataclass
class FrameworkDetection:
    name: str
    confidence: float
    method: str  # package_manifest, config_file, directory_structure
    evidence: str
    version: str | None = None


def detect_languages(relative_file_paths: list[str]) -> LanguageStats:
    """Computes language distribution across all scanned files."""
    counter: Counter[str] = Counter()

    for fp in relative_file_paths:
        suffix = Path(fp).suffix.lower()
        if suffix in EXTENSION_LANGUAGE_MAP:
            lang = EXTENSION_LANGUAGE_MAP[suffix]
            counter[lang] += 1
        elif suffix:
            # Keep unknown extensions grouped as 'Other'
            counter["Other"] += 1

    total_files = sum(counter.values())
    if total_files == 0:
        return LanguageStats(primary_language="unknown", languages=[])

    sorted_langs = []
    for lang, count in counter.most_common():
        sorted_langs.append({
            "name": lang,
            "file_count": count,
            "percentage": round(count / total_files, 4),
        })

    # Pick top non-config language if possible, else most common
    primary = sorted_langs[0]["name"]
    code_candidates = [l["name"] for l in sorted_langs if l["name"] not in {"JSON", "YAML", "Markdown", "XML", "Other"}]
    if code_candidates:
        primary = code_candidates[0]

    return LanguageStats(primary_language=primary, languages=sorted_langs)


def detect_frameworks(
    project_root: Path,
    manifests: list[ManifestInfo],
    scanned_files: list[str],
) -> list[FrameworkDetection]:
    """Detects frameworks present in the project with explicit evidence according to Section 20."""
    frameworks: list[FrameworkDetection] = []
    seen = set()

    def add_framework(name: str, confidence: float, method: str, evidence: str, version: str | None = None):
        if name not in seen:
            seen.add(name)
            frameworks.append(
                FrameworkDetection(
                    name=name,
                    confidence=confidence,
                    method=method,
                    evidence=evidence,
                    version=version,
                )
            )

    # 1. Manifest dependencies inspection
    for m in manifests:
        for dep in m.dependencies:
            name_lower = dep.name.lower()

            # Vue
            if name_lower == "vue":
                add_framework("Vue", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.vue = {dep.version_spec}", dep.version_spec)
            elif name_lower == "vue-router":
                add_framework("Vue Router", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.vue-router = {dep.version_spec}", dep.version_spec)
            elif name_lower == "pinia":
                add_framework("Pinia", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.pinia = {dep.version_spec}", dep.version_spec)
            elif name_lower == "element-plus":
                add_framework("Element Plus", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.element-plus = {dep.version_spec}", dep.version_spec)
            elif name_lower == "vite":
                add_framework("Vite", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.vite = {dep.version_spec}", dep.version_spec)
            elif name_lower == "react":
                add_framework("React", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.react = {dep.version_spec}", dep.version_spec)
            elif name_lower == "next":
                add_framework("Next.js", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.next = {dep.version_spec}", dep.version_spec)
            elif name_lower == "axios":
                add_framework("Axios", 0.99, "package_manifest", f"{m.relative_path} -> {dep.scope}.axios = {dep.version_spec}", dep.version_spec)

            # Java / Spring Boot
            if "spring-boot" in name_lower:
                add_framework("Spring Boot", 0.99, "maven_pom_xml", f"{m.relative_path} -> dependency {dep.name} = {dep.version_spec}", dep.version_spec)
            elif "mybatis" in name_lower:
                add_framework("MyBatis", 0.99, "maven_pom_xml", f"{m.relative_path} -> dependency {dep.name}", dep.version_spec)
            elif "mysql-connector" in name_lower:
                add_framework("MySQL Connector", 0.99, "maven_pom_xml", f"{m.relative_path} -> dependency {dep.name}", dep.version_spec)

            # Python
            if name_lower == "fastapi":
                add_framework("FastAPI", 0.99, "python_manifest", f"{m.relative_path} -> dependency {dep.name}", dep.version_spec)
            elif name_lower == "django":
                add_framework("Django", 0.99, "python_manifest", f"{m.relative_path} -> dependency {dep.name}", dep.version_spec)

    # 2. Config files fallback detection
    file_set = set(scanned_files)
    if "vite.config.ts" in file_set or "vite.config.js" in file_set:
        add_framework("Vite", 0.95, "config_file", "Found vite.config.(js/ts)")
    if "tsconfig.json" in file_set:
        add_framework("TypeScript", 0.95, "config_file", "Found tsconfig.json")

    return frameworks
