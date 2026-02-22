"""OpenAI LLM client."""

from __future__ import annotations

from em.llm._base import LLMResponse
from em.llm._config import DEFAULT_OPENAI_MODEL


class OpenAIClient:
    """Wrapper around the ``openai`` SDK."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        try:
            import openai  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required.  Install it with: "
                "pip install em-core[openai]"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model or DEFAULT_OPENAI_MODEL

    def complete(self, prompt: str, *, system: str = "") -> LLMResponse:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=4096,
        )
        choice = response.choices[0]
        usage_data = {}
        if response.usage:
            usage_data = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }
        return LLMResponse(
            text=choice.message.content or "",
            model=response.model,
            usage=usage_data,
        )
