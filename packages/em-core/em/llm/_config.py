"""LLM configuration from environment variables."""

from __future__ import annotations

import os

# Supported providers
PROVIDERS = ("anthropic", "openai")

# Defaults
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OPENAI_MODEL = "gpt-4o"


def get_provider() -> str:
    """Return the configured LLM provider name.

    Reads ``EM_LLM_PROVIDER`` env var.  Falls back to ``anthropic`` if an
    Anthropic API key is found, otherwise ``openai``.

    Raises:
        ValueError: If the provider is not supported.
    """
    provider = os.environ.get("EM_LLM_PROVIDER", "").lower()
    if provider:
        if provider not in PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider!r}. Choose from {PROVIDERS}")
        return provider

    # Auto-detect from available keys
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"

    raise ValueError(
        "No LLM provider configured. Set EM_LLM_PROVIDER and the "
        "corresponding API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)."
    )


def get_model() -> str | None:
    """Return the model override from ``EM_LLM_MODEL``, or *None* for provider default."""
    return os.environ.get("EM_LLM_MODEL") or None


def get_api_key(provider: str) -> str:
    """Return the API key for *provider*.

    Raises:
        ValueError: If the key is missing.
    """
    key_var = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    key = os.environ.get(key_var)
    if not key:
        raise ValueError(f"Missing {key_var} environment variable for provider={provider!r}")
    return key
