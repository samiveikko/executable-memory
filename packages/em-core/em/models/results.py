"""Run result models — what comes back after executing a routine."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    ok = "ok"
    failed = "failed"
    needs_input = "needs_input"


class FailureReport(BaseModel):
    """Details about why a run failed."""
    step_id: str
    error_type: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    """Result of running a routine."""
    run_id: str
    status: RunStatus
    output: Any = None
    failure: FailureReport | None = None
    pending_prompt: str | None = Field(
        None, description="Step ID of the prompt.user step awaiting input"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution context snapshot (for debugging/resume)",
    )
