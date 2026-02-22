"""LLM abstraction — provider-agnostic interface for Anthropic & OpenAI."""

from __future__ import annotations

from em.llm._base import LLMClient, LLMResponse
from em.llm._config import get_api_key, get_model, get_provider

__all__ = ["LLMClient", "LLMResponse", "get_llm_client"]


def get_llm_client() -> LLMClient:
    """Create an LLM client from environment configuration.

    Uses ``EM_LLM_PROVIDER`` (or auto-detects), ``EM_LLM_MODEL``, and the
    provider-specific API key env var.
    """
    provider = get_provider()
    api_key = get_api_key(provider)
    model = get_model()

    if provider == "anthropic":
        from em.llm._anthropic import AnthropicClient

        return AnthropicClient(api_key=api_key, model=model)

    from em.llm._openai import OpenAIClient

    return OpenAIClient(api_key=api_key, model=model)
