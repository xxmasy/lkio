"""LKIO LLM Gateway Factory
Loads and configures the active LLM Provider.
"""

from core.config.settings import get_settings
from core.rag.gateway.ollama import OllamaProvider
from core.rag.gateway.openai_compatible import OpenAICompatibleProvider
from core.rag.gateway.provider import LLMProvider, MockOfflineLLMProvider


class LLMGatewayFactory:
    """Factory creating LLMProvider instances."""

    @staticmethod
    def get_provider(provider_type: str | None = None) -> LLMProvider:
        """Returns the configured LLMProvider instance."""
        settings = get_settings()
        ptype = (provider_type or settings.LLM_PROVIDER or "none").lower()

        if ptype == "ollama":
            return OllamaProvider()
        elif ptype in ("lmstudio", "openai", "openai-compatible"):
            return OpenAICompatibleProvider()
        else:
            return MockOfflineLLMProvider()
