"""LKIO Entity Index
Provides exact, prefix, and qualified name lookup over code symbols, files, and projects.
"""

from typing import Any
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    IndexType,
    RetrievalCandidate,
)


class EntityIndex:
    """In-memory fast lookup index for code symbols and architectural entities."""

    def __init__(self) -> None:
        # Key: lower_name -> list of entity records
        self._by_name: dict[str, list[dict[str, Any]]] = {}
        # Key: lower_canonical_name -> list of entity records
        self._by_canonical: dict[str, list[dict[str, Any]]] = {}
        # Key: entity_key -> entity record
        self._by_key: dict[str, dict[str, Any]] = {}
        # Key: (project_key, lower_name) -> list of entity records
        self._by_project_name: dict[tuple[str, str], list[dict[str, Any]]] = {}
        # All records
        self._records: list[dict[str, Any]] = []

    def add_entity(
        self,
        entity_key: str,
        name: str,
        canonical_name: str,
        project_key: str,
        entity_type: str,
        file_path: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes an entity record."""
        record = {
            "entity_key": entity_key,
            "name": name,
            "canonical_name": canonical_name,
            "project_key": project_key,
            "entity_type": entity_type,
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "metadata": metadata or {},
        }
        self._records.append(record)
        self._by_key[entity_key] = record

        lower_name = name.lower()
        self._by_name.setdefault(lower_name, []).append(record)

        lower_canon = canonical_name.lower()
        self._by_canonical.setdefault(lower_canon, []).append(record)

        proj_tuple = (project_key, lower_name)
        self._by_project_name.setdefault(proj_tuple, []).append(record)

    def search_exact(
        self,
        query: str,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Searches for exact entity name or canonical name match."""
        q_lower = query.strip().lower()
        if not q_lower:
            return []

        candidates: list[RetrievalCandidate] = []
        matched_keys: set[str] = set()

        # 1. Exact entity_key match
        if q_lower in [k.lower() for k in self._by_key]:
            for k, rec in self._by_key.items():
                if k.lower() == q_lower and (not project_key or rec["project_key"] == project_key):
                    if rec["entity_key"] not in matched_keys:
                        matched_keys.add(rec["entity_key"])
                        candidates.append(self._to_candidate(rec, score=1.0))

        # 2. Exact name match
        records = self._by_name.get(q_lower, [])
        for rec in records:
            if project_key and rec["project_key"] != project_key:
                continue
            if rec["entity_key"] not in matched_keys:
                matched_keys.add(rec["entity_key"])
                candidates.append(self._to_candidate(rec, score=0.98))

        # 3. Exact canonical match
        records = self._by_canonical.get(q_lower, [])
        for rec in records:
            if project_key and rec["project_key"] != project_key:
                continue
            if rec["entity_key"] not in matched_keys:
                matched_keys.add(rec["entity_key"])
                candidates.append(self._to_candidate(rec, score=0.95))

        return candidates[:limit]

    def search_prefix(
        self,
        prefix: str,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Searches for entity names starting with prefix."""
        p_lower = prefix.strip().lower()
        if not p_lower:
            return []

        candidates: list[RetrievalCandidate] = []
        matched_keys: set[str] = set()

        for name_key, records in self._by_name.items():
            if name_key.startswith(p_lower):
                for rec in records:
                    if project_key and rec["project_key"] != project_key:
                        continue
                    if rec["entity_key"] not in matched_keys:
                        matched_keys.add(rec["entity_key"])
                        # Closer length gets higher score
                        len_diff = len(name_key) - len(p_lower)
                        score = max(0.6, 0.9 - (len_diff * 0.02))
                        candidates.append(self._to_candidate(rec, score=score))
                        if len(candidates) >= limit * 2:
                            break

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:limit]

    def search(
        self,
        query: str,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Unified search combining exact match and prefix lookup."""
        exact = self.search_exact(query, project_key=project_key, limit=limit)
        if len(exact) >= limit:
            return exact

        prefix = self.search_prefix(query, project_key=project_key, limit=limit)
        seen = {c.id for c in exact}
        combined = list(exact)
        for c in prefix:
            if c.id not in seen:
                seen.add(c.id)
                combined.append(c)
                if len(combined) >= limit:
                    break

        return combined

    def get_by_key(self, entity_key: str) -> dict[str, Any] | None:
        """Direct O(1) lookup by entity_key."""
        return self._by_key.get(entity_key)

    @property
    def total_count(self) -> int:
        return len(self._records)

    def _to_candidate(self, rec: dict[str, Any], score: float) -> RetrievalCandidate:
        ev = EvidenceCitation(
            evidence_type=EvidenceType.SYMBOL_DEF,
            project_key=rec["project_key"],
            file_path=rec["file_path"] or "",
            start_line=rec["start_line"],
            end_line=rec["end_line"],
            entity_key=rec["entity_key"],
            confidence=1.0,
        )
        return RetrievalCandidate(
            id=f"entity:{rec['entity_key']}",
            score=score,
            source_index=IndexType.ENTITY,
            project_key=rec["project_key"],
            name=rec["name"],
            title=f"[{rec['entity_type']}] {rec['canonical_name']}",
            summary=f"Entity {rec['name']} of type {rec['entity_type']} in {rec['project_key']} ({rec['file_path'] or 'no file'})",
            file_path=rec["file_path"],
            entity_key=rec["entity_key"],
            evidence=ev,
            metadata=rec["metadata"],
        )
