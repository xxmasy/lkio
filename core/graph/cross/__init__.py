"""Cross-Project Graph Subsystem (MVP2-D)
Manages multi-project dependency networks, shared module linkages, and contract cross-references.
"""

from core.graph.cross.models import (
    CrossProjectCandidate,
    CrossProjectPredicate,
    DeclaredDependency,
    PackageManifest,
)

__all__ = [
    "CrossProjectCandidate",
    "CrossProjectPredicate",
    "DeclaredDependency",
    "PackageManifest",
]
