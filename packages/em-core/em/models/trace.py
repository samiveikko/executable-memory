"""Trace models — captures what an agent did during a session."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TraceApp(BaseModel):
    """Application that produced the trace."""
    name: str
    version: str | None = None


class TraceMission(BaseModel):
    """High-level description of what the agent was asked to do."""
    goal: str
    input_summary: dict[str, Any] | None = None


class TraceEventType(str, Enum):
    tool_call = "tool_call"
    udf_call = "udf_call"
    approval = "approval"


class TraceEvent(BaseModel):
    """A single event in a trace."""
    type: TraceEventType
    seq: int = Field(..., description="Sequence number (0-based)")
    tool: str | None = Field(None, description="Tool name for tool_call events")
    function: str | None = Field(None, description="Function name for udf_call events")
    args: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    prompt: str | None = Field(None, description="Prompt shown for approval events")
    answer: Any = None
    error: str | None = None


class Trace(BaseModel):
    """Full agent trace — a recorded session to compile into a routine."""
    version: str = "1"
    app: TraceApp
    mission: TraceMission
    events: list[TraceEvent]
    final_output: Any = None
