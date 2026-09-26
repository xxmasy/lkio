"""Unit tests for LLMGatewayFactory and Providers."""

from core.rag.gateway.factory import LLMGatewayFactory
from core.rag.gateway.ollama import OllamaProvider
from core.rag.gateway.openai_compatible import OpenAICompatibleProvider
from core.rag.gateway.provider import MockOfflineLLMProvider


def test_llm_gateway_factory():
    mock_p = LLMGatewayFactory.get_provider("none")
    assert isinstance(mock_p, MockOfflineLLMProvider)

    ollama_p = LLMGatewayFactory.get_provider("ollama")
    assert isinstance(ollama_p, OllamaProvider)

    lmstudio_p = LLMGatewayFactory.get_provider("lmstudio")
    assert isinstance(lmstudio_p, OpenAICompatibleProvider)


def test_ollama_provider_offline_fallback():
    provider = OllamaProvider(timeout=0.1)
    reply = provider.chat([{"role": "user", "content": "Explain lead allocation"}])
    assert "Ollama Offline Fallback" in reply

    embeddings = provider.embed(["test text"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 128


def test_openai_compatible_offline_fallback():
    provider = OpenAICompatibleProvider(timeout=0.1)
    reply = provider.chat([{"role": "user", "content": "Explain architecture"}])
    assert "LMStudio/OpenAI Fallback" in reply

    embeddings = provider.embed(["test text"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 128
