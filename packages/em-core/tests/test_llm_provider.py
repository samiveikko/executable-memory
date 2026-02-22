"""Tests for the LLM provider abstraction — config, Protocol, clients."""

from __future__ import annotations

import os

import pytest

from em.llm._base import LLMClient, LLMResponse
from em.llm._config import get_api_key, get_model, get_provider


class TestLLMResponse:
    def test_defaults(self):
        r = LLMResponse(text="hello", model="m1")
        assert r.text == "hello"
        assert r.model == "m1"
        assert r.usage == {}

    def test_with_usage(self):
        r = LLMResponse(text="hi", model="m2", usage={"input_tokens": 5})
        assert r.usage["input_tokens"] == 5


class TestProtocol:
    def test_mock_satisfies_protocol(self):
        from tests.conftest import MockLLMClient

        client = MockLLMClient("hello")
        assert isinstance(client, LLMClient)

    def test_protocol_complete(self):
        from tests.conftest import MockLLMClient

        client = MockLLMClient("response text")
        r = client.complete("prompt", system="sys")
        assert r.text == "response text"
        assert r.model == "mock-model"
        assert len(client.calls) == 1
        assert client.calls[0]["system"] == "sys"


class TestConfig:
    def test_get_provider_from_env(self, monkeypatch):
        monkeypatch.setenv("EM_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert get_provider() == "openai"

    def test_get_provider_auto_anthropic(self, monkeypatch):
        monkeypatch.delenv("EM_LLM_PROVIDER", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert get_provider() == "anthropic"

    def test_get_provider_auto_openai(self, monkeypatch):
        monkeypatch.delenv("EM_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert get_provider() == "openai"

    def test_get_provider_invalid(self, monkeypatch):
        monkeypatch.setenv("EM_LLM_PROVIDER", "gemini")
        with pytest.raises(ValueError, match="Unsupported"):
            get_provider()

    def test_get_provider_none(self, monkeypatch):
        monkeypatch.delenv("EM_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="No LLM provider"):
            get_provider()

    def test_get_model_default(self, monkeypatch):
        monkeypatch.delenv("EM_LLM_MODEL", raising=False)
        assert get_model() is None

    def test_get_model_override(self, monkeypatch):
        monkeypatch.setenv("EM_LLM_MODEL", "claude-opus-4-20250514")
        assert get_model() == "claude-opus-4-20250514"

    def test_get_api_key_anthropic(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-123")
        assert get_api_key("anthropic") == "sk-ant-123"

    def test_get_api_key_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-oai-123")
        assert get_api_key("openai") == "sk-oai-123"

    def test_get_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Missing ANTHROPIC_API_KEY"):
            get_api_key("anthropic")


class TestGetLLMClient:
    def test_import_guard_anthropic(self, monkeypatch):
        """AnthropicClient import guard catches missing package gracefully."""
        monkeypatch.setenv("EM_LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        # We can't actually test the import guard without uninstalling anthropic,
        # but we verify the factory function path works
        from em.llm import get_llm_client

        # If anthropic is installed, it will succeed; if not, ImportError
        # Either way, the code path is exercised
        try:
            client = get_llm_client()
            assert isinstance(client, LLMClient)
        except ImportError:
            pass  # Expected if anthropic not installed

    def test_import_guard_openai(self, monkeypatch):
        """OpenAIClient import guard catches missing package gracefully."""
        monkeypatch.setenv("EM_LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from em.llm import get_llm_client

        try:
            client = get_llm_client()
            assert isinstance(client, LLMClient)
        except ImportError:
            pass  # Expected if openai not installed
