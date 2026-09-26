"""LKIO Local LLM Gateway Protocol and Providers
Defines LLMProvider Protocol and deterministic offline fallback implementation.
"""

from typing import Any, Protocol, runtime_checkable
from core.rag.builder import DeterministicLocalEmbedder


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM interactions in LKIO, decoupled from specific vendors."""

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Sends chat messages to model and returns response string."""
        ...

    def structured(
        self,
        prompt: str,
        schema: type,
        temperature: float = 0.0,
    ) -> Any:
        """Generates structured output conforming to a Pydantic schema or type."""
        ...

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generates dense vector embeddings for input texts."""
        ...


class MockOfflineLLMProvider:
    """Deterministic offline LLM Provider for unit tests and zero-dependency local environments."""

    def __init__(self, dimension: int = 128) -> None:
        self.embedder = DeterministicLocalEmbedder(dimension=dimension)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        return f"[LKIO Grounded Response]: Processed query based on verified evidences. Target query: '{last_msg[:60]}...'"

    def structured(
        self,
        prompt: str,
        schema: type,
        temperature: float = 0.0,
    ) -> Any:
        # Return default instance of schema if possible
        if hasattr(schema, "__call__"):
            try:
                return schema()
            except Exception:
                pass
        return {}

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [self.embedder.embed(t) for t in texts]
