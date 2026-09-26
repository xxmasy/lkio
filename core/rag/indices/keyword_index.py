"""LKIO Keyword / BM25 Index
Provides fast lexical search over code symbols, documents, file paths, and comments.
Supports English (camelCase/snake_case splitting) and Chinese character/bigram tokenization.
"""

import math
import re
from typing import Any
from core.rag.models import (
    EvidenceCitation,
    EvidenceType,
    IndexType,
    RetrievalCandidate,
)


def tokenize_text(text: str) -> list[str]:
    """Tokenizes text into normalized lexical terms.
    Splits camelCase, snake_case, punctuation, and extracts CJK characters & bigrams.
    """
    if not text:
        return []

    tokens: list[str] = []
    # 1. Split on whitespace and common delimiters
    parts = re.split(r"[\s\-_/\\.:,;=()\[\]{}'\"`<>?!@#$%^&*+]+", text)

    for part in parts:
        if not part:
            continue

        # Check for CJK characters
        cjk_chars = [ch for ch in part if "\u4e00" <= ch <= "\u9fff"]
        if cjk_chars:
            # Emit individual CJK chars and bigrams
            for i, ch in enumerate(cjk_chars):
                tokens.append(ch)
                if i + 1 < len(cjk_chars):
                    tokens.append(ch + cjk_chars[i + 1])

        # CamelCase splitting for Latin identifiers
        sub_tokens = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z]|\b)", part)
        if sub_tokens:
            for st in sub_tokens:
                lower = st.lower()
                if len(lower) >= 2:
                    tokens.append(lower)
            # Also keep full word if multi-token
            if len(sub_tokens) > 1:
                tokens.append(part.lower())
        else:
            lower = part.lower()
            if len(lower) >= 2:
                tokens.append(lower)

    return tokens


class KeywordIndex:
    """In-process BM25 lexical index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

        self._doc_count: int = 0
        self._doc_lengths: dict[str, int] = {}
        self._avg_doc_len: float = 0.0

        # Term -> doc_id -> term_frequency
        self._inverted_index: dict[str, dict[str, int]] = {}
        # doc_id -> list of tokens
        self._doc_tokens: dict[str, list[str]] = {}
        # doc_id -> document payload
        self._doc_records: dict[str, dict[str, Any]] = {}

    def add_document(
        self,
        doc_id: str,
        text: str,
        project_key: str,
        name: str,
        title: str,
        summary: str,
        file_path: str | None = None,
        entity_key: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        evidence_type: EvidenceType = EvidenceType.FILE_PATH,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Indexes a document or code snippet."""
        tokens = tokenize_text(text)
        if not tokens:
            return

        doc_len = len(tokens)
        self._doc_lengths[doc_id] = doc_len
        self._doc_tokens[doc_id] = tokens
        self._doc_count += 1

        # Update average doc length
        total_len = sum(self._doc_lengths.values())
        self._avg_doc_len = total_len / self._doc_count

        # Count frequencies
        tf_map: dict[str, int] = {}
        for token in tokens:
            tf_map[token] = tf_map.get(token, 0) + 1

        for token, freq in tf_map.items():
            if token not in self._inverted_index:
                self._inverted_index[token] = {}
            self._inverted_index[token][doc_id] = freq

        self._doc_records[doc_id] = {
            "doc_id": doc_id,
            "project_key": project_key,
            "name": name,
            "title": title,
            "summary": summary,
            "file_path": file_path,
            "entity_key": entity_key,
            "start_line": start_line,
            "end_line": end_line,
            "evidence_type": evidence_type,
            "metadata": metadata or {},
        }

    def search(
        self,
        query: str,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalCandidate]:
        """Calculates BM25 relevance scores for the query."""
        q_tokens = tokenize_text(query)
        if not q_tokens or self._doc_count == 0:
            return []

        doc_scores: dict[str, float] = {}

        for token in q_tokens:
            if token not in self._inverted_index:
                continue

            posting = self._inverted_index[token]
            df = len(posting)
            # Standard Lucene/BM25 IDF
            idf = math.log(1.0 + (self._doc_count - df + 0.5) / (df + 0.5))
            if idf <= 0:
                idf = 0.1

            for doc_id, tf in posting.items():
                rec = self._doc_records[doc_id]
                if project_key and rec["project_key"] != project_key:
                    continue

                doc_len = self._doc_lengths[doc_id]
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self._avg_doc_len or 1.0)))
                term_score = idf * ((tf * (self.k1 + 1.0)) / denom)
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + term_score

        if not doc_scores:
            return []

        # Normalize score into (0.0, 1.0]
        max_score = max(doc_scores.values()) or 1.0
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        candidates: list[RetrievalCandidate] = []
        for doc_id, raw_score in sorted_docs:
            rec = self._doc_records[doc_id]
            norm_score = min(1.0, max(0.1, raw_score / (max_score * 1.05)))
            ev = EvidenceCitation(
                evidence_type=rec["evidence_type"],
                project_key=rec["project_key"],
                file_path=rec["file_path"] or "",
                start_line=rec["start_line"],
                end_line=rec["end_line"],
                entity_key=rec["entity_key"],
                confidence=round(norm_score, 4),
            )
            candidates.append(
                RetrievalCandidate(
                    id=f"kw:{doc_id}",
                    score=round(norm_score, 4),
                    source_index=IndexType.KEYWORD,
                    project_key=rec["project_key"],
                    name=rec["name"],
                    title=rec["title"],
                    summary=rec["summary"],
                    file_path=rec["file_path"],
                    entity_key=rec["entity_key"],
                    evidence=ev,
                    metadata=rec["metadata"],
                )
            )

        return candidates

    @property
    def total_count(self) -> int:
        return self._doc_count
