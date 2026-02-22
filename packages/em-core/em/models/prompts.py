"""Prompt models — request/answer flow for prompt.user steps."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from em.models.routine import PromptDef, PromptField, PromptFieldType


class PromptRequest(BaseModel):
    """Sent to the caller when a prompt.user step is reached."""
    run_id: str
    step_id: str
    prompt: PromptDef


class PromptAnswers(BaseModel):
    """Answers submitted by the user for a prompt.user step."""
    values: dict[str, Any] = Field(default_factory=dict)

    def validate_against(self, prompt: PromptDef) -> list[str]:
        """Validate answers against a prompt definition. Returns list of errors."""
        errors: list[str] = []
        field_map: dict[str, PromptField] = {f.name: f for f in prompt.fields}

        for field in prompt.fields:
            if field.required and field.name not in self.values:
                errors.append(f"Missing required field: {field.name}")

        for name, value in self.values.items():
            if name not in field_map:
                errors.append(f"Unknown field: {name}")
                continue
            field = field_map[name]
            if field.type == PromptFieldType.confirm and not isinstance(value, bool):
                errors.append(f"Field '{name}' must be a boolean")
            elif field.type == PromptFieldType.number and not isinstance(value, (int, float)):
                errors.append(f"Field '{name}' must be a number")
            elif field.type == PromptFieldType.select:
                if field.options and value not in field.options:
                    errors.append(
                        f"Field '{name}' must be one of: {', '.join(field.options)}"
                    )

        return errors
