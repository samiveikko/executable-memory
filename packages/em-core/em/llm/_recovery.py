"""Runtime recovery — LLM-assisted auto-fix for failed steps."""

from __future__ import annotations

import json
from typing import Any, Callable

from em.llm._base import LLMClient
from em.llm._parsing import parse_recovery_json
from em.llm._prompts import RECOVERY_SYSTEM
from em.models.routine import Routine, Step


# Type alias for the auto-fix callback
AutoFixFn = Callable[
    [Step, Exception, dict[str, Any], Routine],
    dict[str, Any] | None,
]


def make_auto_fix_fn(client: LLMClient) -> AutoFixFn:
    """Create an auto-fix callback powered by an LLM.

    Returns:
        A callable ``(step, exc, context, routine) -> fix_dict | None``.

        The fix_dict has ``{"strategy": "modify_args"|"skip"|"fail", ...}``.
        Returns *None* if the LLM call itself fails (treated as "fail").
    """

    def auto_fix(
        step: Step,
        exc: Exception,
        context: dict[str, Any],
        routine: Routine,
    ) -> dict[str, Any] | None:
        prompt = _build_recovery_prompt(step, exc, context, routine)
        try:
            response = client.complete(prompt, system=RECOVERY_SYSTEM)
            return parse_recovery_json(response.text)
        except Exception:
            # If LLM itself fails, let the original error propagate
            return None

    return auto_fix


def _build_recovery_prompt(
    step: Step,
    exc: Exception,
    context: dict[str, Any],
    routine: Routine,
) -> str:
    """Build the user prompt describing the failure."""
    step_info = {
        "id": step.id,
        "type": step.type.value,
        "tool": step.tool,
        "function": step.function,
        "args": step.args,
    }
    error_info = {
        "error_type": type(exc).__name__,
        "message": str(exc),
    }
    context_keys = list(context.keys())
    routine_steps = [{"id": s.id, "type": s.type.value} for s in routine.steps]

    payload = {
        "failed_step": step_info,
        "error": error_info,
        "context_keys": context_keys,
        "routine_steps": routine_steps,
    }
    return json.dumps(payload, indent=2, default=str)
