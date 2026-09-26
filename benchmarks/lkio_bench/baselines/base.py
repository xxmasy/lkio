"""Base Interface for LKIO-Bench v1.0 Ablation Baselines.
Defines standard query, retrieval, and impact capabilities for comparison against Full LKIO.
"""

from typing import Any, Protocol


class BaselineSystem(Protocol):
    """Protocol implemented by each of the 8 ablation baseline systems."""

    name: str

    def retrieve_semantic(self, query: str, top_k: int = 10) -> list[str]:
        """Returns list of retrieved file paths ordered by relevance."""
        ...

    def retrieve_symbol(self, query: str, top_k: int = 5) -> list[str]:
        """Returns list of retrieved symbol names ordered by relevance."""
        ...

    def traverse_impact(self, seed: str, max_depth: int = 3) -> dict[str, list[str]]:
        """Returns dict of {'direct': [...], 'indirect': [...], 'potential': [...]}."""
        ...

    def answer_temporal(self, query: dict[str, Any]) -> str:
        """Returns answer for temporal Git reasoning query."""
        ...

    def decide(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        """Returns decision dict with predicted decision and confidence."""
        ...
