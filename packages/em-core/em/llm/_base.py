"""LLM client protocol and response model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol that all LLM providers must satisfy."""

    def complete(self, prompt: str, *, system: str = "") -> LLMResponse:
        """Send a prompt and return a response.

        Args:
            prompt: The user message.
            system: Optional system message.

        Returns:
            LLMResponse with the model's text output.
        """
        ...
