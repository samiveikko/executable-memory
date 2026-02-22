"""Routine models — the deterministic YAML DSL that replaces the LLM loop."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PromptFieldType(str, Enum):
    text = "text"
    select = "select"
    confirm = "confirm"
    number = "number"


class PromptField(BaseModel):
    """A single input field in a prompt.user step."""
    name: str
    label: str
    type: PromptFieldType = PromptFieldType.text
    required: bool = True
    default: Any = None
    options: list[str] | None = Field(None, description="For select fields")


class PromptDef(BaseModel):
    """Definition for a prompt.user step — pause and collect input."""
    message: str
    fields: list[PromptField]


class ToolDef(BaseModel):
    """External tool definition referenced by tool.call steps."""
    name: str
    description: str | None = None
    args_schema: dict[str, Any] | None = None
    result_schema: dict[str, Any] | None = None


class StepType(str, Enum):
    tool_call = "tool.call"
    udf_call = "udf.call"
    assert_ = "assert"
    prompt_user = "prompt.user"
    return_ = "return"


class Step(BaseModel):
    """A single step in a routine."""
    id: str
    type: StepType
    description: str | None = None

    # tool.call
    tool: str | None = None
    args: dict[str, Any] | None = None

    # udf.call
    function: str | None = None

    # Both tool.call and udf.call
    save_as: str | None = Field(None, description="Context variable to store result")

    # assert
    check: str | None = Field(None, description="Expression to evaluate — must be truthy")
    message: str | None = Field(None, description="Error message on assertion failure")

    # prompt.user
    prompt: PromptDef | None = None

    # return
    value: Any = None

    # Conditional execution
    when: str | None = Field(None, description="Expression — step runs only if truthy")


class Routine(BaseModel):
    """A deterministic routine compiled from an agent trace."""
    version: str = "1"
    name: str
    description: str | None = None
    tools: list[ToolDef] = Field(default_factory=list)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    steps: list[Step]
