"""Entity and Edge Identity Specification (Stage 0 Baseline Section 2.2.3).

Standardizes URI namespace format:
    repo://<repo_id>/<file_path>#<qualified_symbol_name>
Example:
    repo://hello-be/src/service/LeadService.java#LeadService.computeMetrics
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EntityIdentity:
    repo_id: str
    file_path: str
    symbol_name: Optional[str] = None

    @property
    def uri(self) -> str:
        base = f"repo://{self.repo_id}/{self.file_path.lstrip('/')}"
        if self.symbol_name:
            return f"{base}#{self.symbol_name}"
        return base

    def __str__(self) -> str:
        return self.uri


_URI_PATTERN = re.compile(r"^repo://([^/]+)/([^#]+)(?:#(.*))?$")


def build_entity_uri(
    repo_id: str,
    file_path: str,
    symbol_name: Optional[str] = None,
) -> str:
    """Builds a canonical repository namespaced Entity URI."""
    norm_path = file_path.replace("\\", "/").lstrip("/")
    identity = EntityIdentity(repo_id=repo_id, file_path=norm_path, symbol_name=symbol_name)
    return identity.uri


def parse_entity_uri(uri: str) -> EntityIdentity:
    """Parses a canonical Entity URI into its constituent parts."""
    match = _URI_PATTERN.match(uri.strip())
    if not match:
        raise ValueError(f"Invalid Entity URI format: '{uri}'. Expected: 'repo://<repo_id>/<file_path>[#<symbol>]'")
    repo_id, file_path, symbol_name = match.groups()
    return EntityIdentity(
        repo_id=repo_id,
        file_path=file_path,
        symbol_name=symbol_name if symbol_name else None,
    )


def build_edge_key(source_uri: str, predicate: str, target_uri: str) -> str:
    """Builds a deterministic unique edge identifier."""
    return f"edge://{source_uri}->{predicate}->{target_uri}"
