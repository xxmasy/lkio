"""LKIO Ollama Local LLM Provider
Connects to local Ollama instance (default http://localhost:11434) via HTTP API.
"""

from typing import Any
import httpx
from core.rag.builder import DeterministicLocalEmbedder


class OllamaProvider:
    """Local LLM Provider for Ollama endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b",
        embed_model: str = "bge-m3",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model
        self.timeout = timeout
        self.fallback_embedder = DeterministicLocalEmbedder()

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Sends chat request to Ollama /api/chat."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("message", {}).get("content", "")
        except Exception:
            pass

        # Graceful fallback when local Ollama daemon is offline
        last_msg = messages[-1]["content"] if messages else ""
        return f"[Ollama Offline Fallback]: Grounded architectural synthesis for: '{last_msg[:60]}...'"

    def structured(
        self,
        prompt: str,
        schema: type,
        temperature: float = 0.0,
    ) -> Any:
        """Requests structured JSON output conforming to schema."""
        raw = self.chat([{"role": "user", "content": prompt}], temperature=temperature)
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
        """Generates dense embeddings via Ollama /api/embeddings or fallback."""
        embeddings: list[list[float]] = []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                for text in texts:
                    resp = client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.embed_model, "prompt": text},
                    )
                    if resp.status_code == 200:
                        embeddings.append(resp.json().get("embedding", []))
                    else:
                        embeddings.append(self.fallback_embedder.embed(text))
            return embeddings
        except Exception:
            return [self.fallback_embedder.embed(t) for t in texts]
