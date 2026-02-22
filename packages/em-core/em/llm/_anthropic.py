"""Anthropic LLM client."""

from __future__ import annotations

from em.llm._base import LLMResponse
from em.llm._config import DEFAULT_ANTHROPIC_MODEL


class AnthropicClient:
    """Wrapper around the ``anthropic`` SDK."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        try:
            import anthropic  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required.  Install it with: "
                "pip install em-core[anthropic]"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or DEFAULT_ANTHROPIC_MODEL

    def complete(self, prompt: str, *, system: str = "") -> LLMResponse:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return LLMResponse(text=text, model=response.model, usage=usage)
