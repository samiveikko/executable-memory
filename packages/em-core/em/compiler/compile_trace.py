"""Compiler — convert an agent trace into a routine package."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import yaml

from em.models.trace import Trace, TraceEvent, TraceEventType
from em.models.routine import (
    Routine, Step, StepType, ToolDef, PromptDef, PromptField, PromptFieldType,
)


def compile_trace(trace: Trace) -> tuple[Routine, str, dict[str, Any]]:
    """Compile a Trace into a Routine, UDF source code, and fixture data.

    Returns:
        (routine, udf_source, fixtures)
        - routine: the Routine model
        - udf_source: Python source for udf.py
        - fixtures: dict of fixture_name -> content (for golden tests)
    """
    steps: list[Step] = []
    tools: list[ToolDef] = []
    udf_functions: list[str] = []
    udf_names: set[str] = set()
    tool_names: set[str] = set()
    fixtures: dict[str, Any] = {}
    step_counter = 0
    # Map from event result value (as json) to save_as variable name
    result_map: dict[str, str] = {}

    # Seed result_map with input values so args matching inputs get templatized
    if trace.mission.input_summary:
        for k, v in trace.mission.input_summary.items():
            result_map[_json_key(v)] = k

    for event in trace.events:
        step_counter += 1
        step_id = f"s{step_counter}"

        if event.type == TraceEventType.tool_call:
            # Register tool definition
            if event.tool and event.tool not in tool_names:
                tool_names.add(event.tool)
                tools.append(ToolDef(
                    name=event.tool,
                    args_schema=_infer_schema(event.args),
                ))

            # Build args with template references
            args = _templatize_args(event.args, result_map)
            save_as = f"result_{step_id}"

            steps.append(Step(
                id=step_id,
                type=StepType.tool_call,
                tool=event.tool,
                args=args,
                save_as=save_as,
                description=f"Call {event.tool}",
            ))

            # Track result for downstream templatization
            if event.result is not None:
                result_map[_json_key(event.result)] = save_as
                fixtures[f"{step_id}_result"] = event.result

        elif event.type == TraceEventType.udf_call:
            func_name = event.function or f"udf_{step_counter}"

            # Generate UDF stub if new
            if func_name not in udf_names:
                udf_names.add(func_name)
                udf_functions.append(_generate_udf_stub(func_name, event))

            args = _templatize_args(event.args, result_map)
            save_as = f"result_{step_id}"

            steps.append(Step(
                id=step_id,
                type=StepType.udf_call,
                function=func_name,
                args=args,
                save_as=save_as,
                description=f"Call {func_name}",
            ))

            if event.result is not None:
                result_map[_json_key(event.result)] = save_as
                fixtures[f"{step_id}_result"] = event.result

        elif event.type == TraceEventType.approval:
            steps.append(Step(
                id=step_id,
                type=StepType.prompt_user,
                prompt=PromptDef(
                    message=event.prompt or "Please confirm",
                    fields=[PromptField(
                        name="confirm",
                        label=event.prompt or "Proceed?",
                        type=PromptFieldType.confirm,
                        default=True,
                    )],
                ),
                save_as=f"approval_{step_id}",
                description="User confirmation",
            ))

    # Add return step
    if trace.final_output is not None:
        last_save = steps[-1].save_as if steps else None
        if last_save:
            steps.append(Step(
                id=f"s{step_counter + 1}",
                type=StepType.return_,
                value=f"{{{{ {last_save} }}}}",
                description="Return final output",
            ))

    # Build input schema from mission
    input_schema = None
    if trace.mission.input_summary:
        input_schema = _infer_schema(trace.mission.input_summary)

    # Build output schema from final output
    output_schema = None
    if trace.final_output:
        output_schema = _infer_schema(trace.final_output)

    routine = Routine(
        name=_slugify(trace.mission.goal),
        description=trace.mission.goal,
        tools=tools,
        input_schema=input_schema,
        output_schema=output_schema,
        steps=steps,
    )

    udf_source = _build_udf_source(udf_functions)
    return routine, udf_source, fixtures


def compile_trace_file(trace_path: Path, output_dir: Path) -> None:
    """Compile a trace JSON file into a routine package directory."""
    with open(trace_path) as f:
        trace_data = json.load(f)

    trace = Trace.model_validate(trace_data)
    routine, udf_source, fixtures = compile_trace(trace)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write routine.yaml (use mode="json" to avoid Python-specific YAML tags)
    with open(output_dir / "routine.yaml", "w") as f:
        yaml.dump(
            routine.model_dump(mode="json", exclude_none=True),
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    # Write udf.py
    if udf_source.strip():
        with open(output_dir / "udf.py", "w") as f:
            f.write(udf_source)

    # Write schemas
    schemas_dir = output_dir / "schemas"
    schemas_dir.mkdir(exist_ok=True)
    if routine.input_schema:
        with open(schemas_dir / "input.schema.json", "w") as f:
            json.dump(routine.input_schema, f, indent=2)
    if routine.output_schema:
        with open(schemas_dir / "output.schema.json", "w") as f:
            json.dump(routine.output_schema, f, indent=2)

    # Write fixture data
    if fixtures:
        fixtures_dir = output_dir / "fixtures"
        fixtures_dir.mkdir(exist_ok=True)
        for name, data in fixtures.items():
            with open(fixtures_dir / f"{name}.json", "w") as f:
                json.dump(data, f, indent=2)

    # Write input.json from mission
    if trace.mission.input_summary:
        with open(output_dir / "input.json", "w") as f:
            json.dump(trace.mission.input_summary, f, indent=2)

    # Write expected_output.json
    if trace.final_output:
        with open(output_dir / "expected_output.json", "w") as f:
            json.dump(trace.final_output, f, indent=2)


def _json_key(value: Any) -> str:
    """Create a hashable key from a value by serializing to JSON."""
    return json.dumps(value, sort_keys=True, default=str)


def _templatize_args(args: dict[str, Any], result_map: dict[str, str]) -> dict[str, Any]:
    """Convert args to template references where values match prior step results."""
    result = {}
    for key, value in args.items():
        jk = _json_key(value)
        if jk in result_map:
            result[key] = f"{{{{ {result_map[jk]} }}}}"
        else:
            result[key] = value
    return result


def _infer_schema(data: Any) -> dict[str, Any]:
    """Infer a JSON Schema from sample data."""
    if isinstance(data, dict):
        properties = {}
        for key, value in data.items():
            properties[key] = _infer_schema(value)
        return {
            "type": "object",
            "properties": properties,
            "required": list(data.keys()),
        }
    elif isinstance(data, list):
        if data:
            return {"type": "array", "items": _infer_schema(data[0])}
        return {"type": "array"}
    elif isinstance(data, bool):
        return {"type": "boolean"}
    elif isinstance(data, int):
        return {"type": "integer"}
    elif isinstance(data, float):
        return {"type": "number"}
    elif isinstance(data, str):
        return {"type": "string"}
    return {}


def _generate_udf_stub(name: str, event: TraceEvent) -> str:
    """Generate a Python function stub from a trace event."""
    # Infer parameter types from args
    params: list[str] = []
    for pname, pval in event.args.items():
        ptype = type(pval).__name__
        if ptype == "list":
            ptype = "list"
        elif ptype == "dict":
            ptype = "dict"
        params.append(f"{pname}: {ptype}")

    # Infer return type
    ret_type = "Any"
    if event.result is not None:
        ret_type = type(event.result).__name__
        if ret_type == "list":
            ret_type = "list"
        elif ret_type == "dict":
            ret_type = "dict"

    param_str = ", ".join(params) if params else ""
    return textwrap.dedent(f"""\
        def {name}({param_str}) -> {ret_type}:
            \"\"\"TODO: Implement {name} — generated from trace.\"\"\"
            raise NotImplementedError("Implement {name}")
    """)


def _build_udf_source(functions: list[str]) -> str:
    """Build the complete udf.py source."""
    header = '"""UDFs — generated from agent trace. Implement the TODO functions."""\n\nfrom __future__ import annotations\nfrom typing import Any\n\n\n'
    return header + "\n\n".join(functions)


def _slugify(text: str) -> str:
    """Convert text to a simple slug for the routine name."""
    import re
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug[:60]
