"""Shared test fixtures — MockLLMClient for testing without API keys."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from em.llm._base import LLMResponse


class MockLLMClient:
    """A configurable mock LLM client for testing.

    Set ``response_text`` before calling ``complete()`` to control what it returns.
    Keeps a log of all calls in ``calls``.
    """

    def __init__(self, response_text: str = "") -> None:
        self.response_text = response_text
        self.calls: list[dict[str, Any]] = []

    def complete(self, prompt: str, *, system: str = "") -> LLMResponse:
        self.calls.append({"prompt": prompt, "system": system})
        return LLMResponse(
            text=self.response_text,
            model="mock-model",
            usage={"input_tokens": 10, "output_tokens": 20},
        )


@pytest.fixture
def mock_llm():
    """Return a fresh MockLLMClient."""
    return MockLLMClient()
