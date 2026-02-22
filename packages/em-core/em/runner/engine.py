"""Runner engine — execute routine steps sequentially."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from em.models.prompts import PromptAnswers, PromptRequest
from em.models.results import FailureReport, RunResult, RunStatus
from em.models.routine import StepType
from em.runner.eval import safe_eval
from em.runner.state_store import InMemoryStateStore, RunState, StateStore
from em.runner.templating import render_value
from em.runner.tools import ToolRegistry
from em.utils.hashing import generate_run_id
from em.utils.yaml_io import RoutinePackage


def run_routine(
    routine_dir: str | Path,
    input_data: dict[str, Any] | None = None,
    tool_registry: ToolRegistry | None = None,
    state_store: StateStore | None = None,
    auto_fix_fn: Any | None = None,
) -> RunResult:
    """Run a routine from start to finish.

    Args:
        auto_fix_fn: Optional callback ``(step, exc, context, routine) -> fix_dict | None``.
            When a step fails and this is provided, the engine calls it before
            giving up.  See ``em.llm._recovery.make_auto_fix_fn`` for the factory.
    """
    routine_dir = Path(routine_dir)
    pkg = RoutinePackage(routine_dir)
    run_id = generate_run_id()
    context: dict[str, Any] = dict(input_data or {})

    if state_store is None:
        state_store = InMemoryStateStore()

    return _execute_steps(
        pkg=pkg,
        run_id=run_id,
        context=context,
        start_index=0,
        tool_registry=tool_registry or ToolRegistry(),
        state_store=state_store,
        routine_dir=routine_dir,
        auto_fix_fn=auto_fix_fn,
    )


def resume_run(
    run_id: str,
    answers: PromptAnswers,
    state_store: StateStore,
    tool_registry: ToolRegistry | None = None,
) -> RunResult:
    """Resume a paused run after user provides prompt answers."""
    state = state_store.load(run_id)
    if state is None:
        return RunResult(
            run_id=run_id,
            status=RunStatus.failed,
            failure=FailureReport(
                step_id="",
                error_type="StateNotFound",
                message=f"No saved state for run_id={run_id}",
            ),
        )

    routine_dir = Path(state.routine_dir)
    pkg = RoutinePackage(routine_dir)

    # Validate answers against the pending prompt step
    pending_step = None
    for s in pkg.routine.steps:
        if s.id == state.pending_step_id:
            pending_step = s
            break

    if pending_step is None or pending_step.prompt is None:
        return RunResult(
            run_id=run_id,
            status=RunStatus.failed,
            failure=FailureReport(
                step_id=state.pending_step_id,
                error_type="InvalidState",
                message="Pending step is not a prompt.user step",
            ),
        )

    validation_errors = answers.validate_against(pending_step.prompt)
    if validation_errors:
        return RunResult(
            run_id=run_id,
            status=RunStatus.failed,
            failure=FailureReport(
                step_id=state.pending_step_id,
                error_type="ValidationError",
                message="; ".join(validation_errors),
            ),
        )

    # Inject answers into context
    context = state.context
    if pending_step.save_as:
        context[pending_step.save_as] = answers.values
    else:
        context["_prompt_answers"] = answers.values

    state_store.delete(run_id)

    return _execute_steps(
        pkg=pkg,
        run_id=run_id,
        context=context,
        start_index=state.step_index + 1,
        tool_registry=tool_registry or ToolRegistry(),
        state_store=state_store,
        routine_dir=routine_dir,
    )


def _execute_steps(
    pkg: RoutinePackage,
    run_id: str,
    context: dict[str, Any],
    start_index: int,
    tool_registry: ToolRegistry,
    state_store: StateStore,
    routine_dir: Path,
    auto_fix_fn: Any | None = None,
) -> RunResult:
    """Execute steps starting from start_index."""
    steps = pkg.routine.steps

    for i in range(start_index, len(steps)):
        step = steps[i]

        # Check `when` condition
        if step.when:
            try:
                eval_ctx = _build_eval_context(context, pkg)
                condition = safe_eval(step.when, eval_ctx, pkg.udf_module)
                if not condition:
                    continue
            except Exception as exc:
                return RunResult(
                    run_id=run_id,
                    status=RunStatus.failed,
                    failure=FailureReport(
                        step_id=step.id,
                        error_type="ConditionError",
                        message=f"Error evaluating 'when' condition: {exc}",
                        context=dict(context),
                    ),
                )

        try:
            _run_step(step, context, pkg, tool_registry, state_store, routine_dir, run_id, i)
            # prompt.user and return steps produce RunResult directly
        except _StepResult as sr:
            return sr.result

        except Exception as exc:
            # Try auto-fix if callback is provided (max 1 retry per step)
            fix = None
            if auto_fix_fn is not None:
                try:
                    fix = auto_fix_fn(step, exc, context, pkg.routine)
                except Exception:
                    fix = None

            if fix is not None and isinstance(fix, dict):
                strategy = fix.get("strategy")

                if strategy == "modify_args":
                    new_args = fix.get("new_args")
                    if isinstance(new_args, dict):
                        patched_step = step.model_copy(update={"args": new_args})
                        try:
                            _run_step(
                                patched_step, context, pkg, tool_registry,
                                state_store, routine_dir, run_id, i,
                            )
                        except _StepResult as sr:
                            return sr.result
                        except Exception as retry_exc:
                            return RunResult(
                                run_id=run_id,
                                status=RunStatus.failed,
                                failure=FailureReport(
                                    step_id=step.id,
                                    error_type=type(retry_exc).__name__,
                                    message=str(retry_exc),
                                    context=dict(context),
                                ),
                            )
                        continue  # step succeeded after retry

                elif strategy == "skip":
                    default_value = fix.get("default_value")
                    if step.save_as:
                        context[step.save_as] = default_value
                    continue

            # No fix or strategy == "fail" → normal failure
            return RunResult(
                run_id=run_id,
                status=RunStatus.failed,
                failure=FailureReport(
                    step_id=step.id,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    context=dict(context),
                ),
            )

    # No return step — return context
    return RunResult(
        run_id=run_id,
        status=RunStatus.ok,
        output=context,
    )


class _StepResult(Exception):
    """Internal: raised by _run_step when a step produces a RunResult (prompt/return)."""

    def __init__(self, result: RunResult) -> None:
        self.result = result


def _run_step(
    step,
    context: dict[str, Any],
    pkg: RoutinePackage,
    tool_registry: ToolRegistry,
    state_store: StateStore,
    routine_dir: Path,
    run_id: str,
    step_index: int,
) -> None:
    """Execute a single step, updating *context* in place.

    Raises _StepResult for prompt.user and return steps (they produce a RunResult).
    Raises other exceptions on failure.
    """
    if step.type == StepType.tool_call:
        result = _exec_tool_call(step, context, pkg, tool_registry)
        if step.save_as:
            context[step.save_as] = result

    elif step.type == StepType.udf_call:
        result = _exec_udf_call(step, context, pkg)
        if step.save_as:
            context[step.save_as] = result

    elif step.type == StepType.assert_:
        _exec_assert(step, context, pkg)

    elif step.type == StepType.prompt_user:
        state = RunState(
            run_id=run_id,
            routine_dir=str(routine_dir),
            step_index=step_index,
            context=dict(context),
            pending_step_id=step.id,
        )
        state_store.save(state)
        raise _StepResult(RunResult(
            run_id=run_id,
            status=RunStatus.needs_input,
            pending_prompt=step.id,
            context=dict(context),
        ))

    elif step.type == StepType.return_:
        output = render_value(step.value, context, pkg.udf_module)
        raise _StepResult(RunResult(
            run_id=run_id,
            status=RunStatus.ok,
            output=output,
            context=dict(context),
        ))


def _build_eval_context(context: dict[str, Any], pkg: RoutinePackage) -> dict[str, Any]:
    """Build eval context with UDF functions available as top-level names."""
    eval_ctx = dict(context)
    if pkg.udf_module:
        import inspect
        for name, obj in vars(pkg.udf_module).items():
            if not name.startswith("_") and callable(obj) and inspect.isfunction(obj):
                eval_ctx[name] = obj
    return eval_ctx


def _exec_tool_call(step, context, pkg, tool_registry):
    """Execute a tool.call step."""
    rendered_args = render_value(step.args or {}, context, pkg.udf_module)
    return tool_registry.call(step.tool, rendered_args)


def _exec_udf_call(step, context, pkg):
    """Execute a udf.call step."""
    fn = pkg.get_udf(step.function)
    rendered_args = render_value(step.args or {}, context, pkg.udf_module)
    return fn(**rendered_args)


def _exec_assert(step, context, pkg):
    """Execute an assert step."""
    eval_ctx = _build_eval_context(context, pkg)
    result = safe_eval(step.check, eval_ctx, pkg.udf_module)
    if not result:
        msg = step.message or f"Assertion failed: {step.check}"
        raise AssertionError(msg)
