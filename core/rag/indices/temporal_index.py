"""LKIO Temporal Index
Provides chronological Git commit and change history indexing.
"""

from typing import Any
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    IndexType,
    RetrievalCandidate,
)


class TemporalIndex:
    """In-memory chronological index for Git commits and repository history."""

    def __init__(self) -> None:
        self._commits: list[dict[str, Any]] = []
        # file_path -> list of commit records
        self._by_file: dict[str, list[dict[str, Any]]] = {}
        # commit_hash -> commit record
        self._by_hash: dict[str, dict[str, Any]] = {}

    def add_commit(
        self,
        commit_hash: str,
        message: str,
        author: str,
        timestamp: str,
        project_key: str,
        files_changed: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes a Git commit record."""
        rec = {
            "commit_hash": commit_hash,
            "message": message,
            "author": author,
            "timestamp": timestamp,
            "project_key": project_key,
            "files_changed": files_changed or [],
            "metadata": metadata or {},
        }
        self._commits.append(rec)
        self._by_hash[commit_hash] = rec

        for f in files_changed or []:
            norm_f = f.strip().lower()
            self._by_file.setdefault(norm_f, []).append(rec)

    def search_by_file(
        self,
        file_path_query: str,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Finds commits that modified a matching file path."""
        norm_q = file_path_query.strip().lower()
        candidates: list[RetrievalCandidate] = []
        seen_hashes: set[str] = set()

        for indexed_path, commits in self._by_file.items():
            if norm_q in indexed_path or indexed_path in norm_q:
                for c in commits:
                    if project_key and c["project_key"] != project_key:
                        continue
                    if c["commit_hash"] in seen_hashes:
                        continue
                    seen_hashes.add(c["commit_hash"])

                    ev = EvidenceCitation(
                        evidence_type=EvidenceType.GIT_COMMIT,
                        project_key=c["project_key"],
                        file_path=indexed_path,
                        commit_hash=c["commit_hash"],
                        confidence=0.95,
                    )
                    candidates.append(
                        RetrievalCandidate(
                            id=f"commit:{c['commit_hash']}",
                            score=0.9,
                            source_index=IndexType.TEMPORAL,
                            project_key=c["project_key"],
                            name=c["commit_hash"][:8],
                            title=f"Commit [{c['commit_hash'][:8]}] by {c['author']}",
                            summary=f"{c['message']} (Date: {c['timestamp']})",
                            file_path=indexed_path,
                            evidence=ev,
                            metadata=c["metadata"],
                        )
                    )

        return candidates[:limit]

    def search_by_message(
        self,
        keyword: str,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Finds commits containing keywords in the commit message or falls back to recent."""
        # Simple tokenization for matching
        import re
        q_tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", keyword) if len(t) >= 2]
        candidates: list[tuple[float, dict[str, Any]]] = []

        for c in self._commits:
            if project_key and c["project_key"] != project_key:
                continue
            text = f"{c['message']} {c['author']} {' '.join(c['files_changed'])}".lower()
            overlap = sum(1 for t in q_tokens if t in text)
            if overlap > 0:
                score = min(0.95, 0.6 + overlap * 0.1)
                candidates.append((score, c))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            res: list[RetrievalCandidate] = []
            for score, c in candidates[:limit]:
                ev = EvidenceCitation(
                    evidence_type=EvidenceType.GIT_COMMIT,
                    project_key=c["project_key"],
                    file_path=c["files_changed"][0] if c["files_changed"] else "",
                    commit_hash=c["commit_hash"],
                    confidence=score,
                )
                res.append(
                    RetrievalCandidate(
                        id=f"commit:{c['commit_hash']}",
                        score=score,
                        source_index=IndexType.TEMPORAL,
                        project_key=c["project_key"],
                        name=c["commit_hash"][:8],
                        title=f"Commit [{c['commit_hash'][:8]}] by {c['author']}",
                        summary=f"{c['message']} ({c['timestamp']})",
                        file_path=c["files_changed"][0] if c["files_changed"] else None,
                        evidence=ev,
                        metadata=c["metadata"],
                    )
                )
            return res

        # Fallback to recent commits
        return self.search_recent(project_key=project_key, limit=limit)

    def search_recent(
        self,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Returns the most recent commits."""
        candidates: list[RetrievalCandidate] = []
        for c in reversed(self._commits):
            if project_key and c["project_key"] != project_key:
                continue
            ev = EvidenceCitation(
                evidence_type=EvidenceType.GIT_COMMIT,
                project_key=c["project_key"],
                file_path=c["files_changed"][0] if c["files_changed"] else "",
                commit_hash=c["commit_hash"],
                confidence=0.8,
            )
            candidates.append(
                RetrievalCandidate(
                    id=f"commit:{c['commit_hash']}",
                    score=0.8,
                    source_index=IndexType.TEMPORAL,
                    project_key=c["project_key"],
                    name=c["commit_hash"][:8],
                    title=f"Commit [{c['commit_hash'][:8]}] by {c['author']}",
                    summary=f"{c['message']} ({c['timestamp']})",
                    file_path=c["files_changed"][0] if c["files_changed"] else None,
                    evidence=ev,
                    metadata=c["metadata"],
                )
            )
            if len(candidates) >= limit:
                break
        return candidates

    @property
    def total_count(self) -> int:
        return len(self._commits)
