"""CLI — compile, run, and validate routines."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

app = typer.Typer(name="em", help="Executable Memory CLI")


@app.command()
def compile(
    trace_path: Path = typer.Argument(..., help="Path to trace JSON file"),
    output_dir: Path = typer.Option("./routine_out", "-o", "--output", help="Output directory"),
) -> None:
    """Compile an agent trace into a routine package."""
    from em.compiler.compile_trace import compile_trace_file

    try:
        compile_trace_file(trace_path, output_dir)
        typer.echo(f"Routine package written to {output_dir}")
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)


@app.command()
def run(
    routine_dir: Path = typer.Argument(..., help="Path to routine directory"),
    input_file: Path = typer.Option(None, "--input", "-i", help="Input JSON file"),
    output_file: Path = typer.Option(None, "--out", "-o", help="Output JSON file"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Run a routine, handling prompt.user steps interactively."""
    from em.models.prompts import PromptAnswers
    from em.runner.engine import resume_run, run_routine
    from em.runner.state_store import FileStateStore
    from em.runner.tools import ToolRegistry

    input_data = {}
    if input_file:
        with open(input_file) as f:
            input_data = json.load(f)

    state_store = FileStateStore(Path("/tmp/em_state"))
    tool_registry = _build_tool_registry(routine_dir)

    result = run_routine(
        routine_dir=routine_dir,
        input_data=input_data,
        tool_registry=tool_registry,
        state_store=state_store,
    )

    # Handle interactive prompts
    while result.status.value == "needs_input":
        answers = _interactive_prompt(result, routine_dir)
        result = resume_run(
            run_id=result.run_id,
            answers=answers,
            state_store=state_store,
            tool_registry=tool_registry,
        )

    _output_result(result, output_file, json_output)


@app.command()
def validate(
    routine_dir: Path = typer.Argument(..., help="Path to routine directory"),
) -> None:
    """Validate a routine package (YAML, UDF imports, schemas)."""
    from em.utils.yaml_io import RoutinePackage

    errors: list[str] = []
    try:
        pkg = RoutinePackage(routine_dir)
    except Exception as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(1)

    # Check UDF references
    for step in pkg.routine.steps:
        if step.type.value == "udf.call" and step.function:
            try:
                pkg.get_udf(step.function)
            except ValueError as exc:
                errors.append(str(exc))

    # Check tool references are declared
    declared_tools = {t.name for t in pkg.routine.tools}
    for step in pkg.routine.steps:
        if step.type.value == "tool.call" and step.tool:
            if step.tool not in declared_tools:
                errors.append(f"Step '{step.id}' references undeclared tool: {step.tool}")

    if errors:
        typer.echo("Validation errors:", err=True)
        for e in errors:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(1)

    typer.echo("OK — routine is valid")


def _build_tool_registry(routine_dir: Path) -> "ToolRegistry":
    """Build a tool registry with fixture:// support for examples."""
    from em.runner.tools import ToolRegistry

    registry = ToolRegistry()

    # Register a fixture fetch_csv tool that reads local CSV files
    fixtures_dir = routine_dir / "fixtures"

    def fetch_csv(url: str) -> str:
        if url.startswith("fixture://"):
            filename = url.removeprefix("fixture://")
            path = fixtures_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Fixture not found: {path}")
            return path.read_text()
        raise ValueError(f"Unsupported URL scheme: {url}")

    registry.register("fetch_csv", fetch_csv)
    return registry


def _interactive_prompt(result, routine_dir: Path) -> "PromptAnswers":
    """Prompt user interactively in the terminal."""
    from em.models.prompts import PromptAnswers
    from em.utils.yaml_io import RoutinePackage

    pkg = RoutinePackage(routine_dir)
    step = None
    for s in pkg.routine.steps:
        if s.id == result.pending_prompt:
            step = s
            break

    if step is None or step.prompt is None:
        typer.echo("Error: could not find prompt step", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n--- Prompt: {step.prompt.message} ---")
    values: dict = {}
    for field in step.prompt.fields:
        if field.type.value == "confirm":
            val = typer.confirm(field.label, default=field.default or False)
            values[field.name] = val
        elif field.type.value == "select" and field.options:
            typer.echo(f"{field.label}:")
            for i, opt in enumerate(field.options):
                typer.echo(f"  {i + 1}. {opt}")
            choice = typer.prompt("Choose", type=int, default=1)
            values[field.name] = field.options[choice - 1]
        else:
            val = typer.prompt(field.label, default=field.default or "")
            values[field.name] = val

    return PromptAnswers(values=values)


def _output_result(result, output_file: Path | None, json_output: bool) -> None:
    """Output the run result."""
    data = result.model_dump()
    if json_output:
        typer.echo(json.dumps(data, indent=2))
    else:
        if result.status.value == "ok":
            typer.echo(f"Status: {result.status.value}")
            typer.echo(f"Output: {json.dumps(result.output, indent=2)}")
        else:
            typer.echo(f"Status: {result.status.value}", err=True)
            if result.failure:
                typer.echo(f"Error: {result.failure.message}", err=True)

    if output_file:
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    app()
