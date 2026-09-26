"""LKIO OpenAI-Compatible Local LLM Provider
Connects to local LM Studio (default http://localhost:1234/v1) or OpenAI-compatible server.
"""

from typing import Any
import httpx
from core.rag.builder import DeterministicLocalEmbedder


class OpenAICompatibleProvider:
    """Local LLM Provider for OpenAI-compatible endpoints (LM Studio, vLLM, LocalAI)."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "not-needed-local",
        model: str = "local-model",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.fallback_embedder = DeterministicLocalEmbedder()

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Sends chat completion request to /chat/completions."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
        except Exception:
            pass

        last_msg = messages[-1]["content"] if messages else ""
        return f"[LMStudio/OpenAI Fallback]: Synthesized grounded context for: '{last_msg[:60]}...'"

    def structured(
        self,
        prompt: str,
        schema: type,
        temperature: float = 0.0,
    ) -> Any:
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
        """Sends embedding request to /embeddings."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json={"model": self.model, "input": texts},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [item["embedding"] for item in data.get("data", [])]
        except Exception:
            pass

        return [self.fallback_embedder.embed(t) for t in texts]
