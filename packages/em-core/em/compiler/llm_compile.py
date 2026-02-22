"""LLM-powered trace compiler — uses an LLM to produce a clean routine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from em.llm._base import LLMClient
from em.llm._parsing import extract_python_block, extract_yaml_block, parse_routine_yaml
from em.llm._prompts import COMPILE_SYSTEM
from em.models.routine import Routine
from em.models.trace import Trace


def llm_compile_trace(trace: Trace, client: LLMClient) -> tuple[Routine, str]:
    """Compile a Trace into a Routine using an LLM.

    Args:
        trace: The recorded agent trace.
        client: An LLM client satisfying the LLMClient protocol.

    Returns:
        (routine, udf_source) — the validated Routine model and Python UDF source.

    Raises:
        ValueError: If the LLM response cannot be parsed.
    """
    trace_json = trace.model_dump_json(indent=2)
    prompt = f"Compile this agent trace into a routine:\n\n{trace_json}"

    response = client.complete(prompt, system=COMPILE_SYSTEM)

    yaml_text = extract_yaml_block(response.text)
    routine = parse_routine_yaml(yaml_text)

    udf_source = extract_python_block(response.text)

    return routine, udf_source


def llm_compile_trace_file(
    trace_path: Path,
    output_dir: Path,
    client: LLMClient,
) -> None:
    """Compile a trace JSON file into a routine package using an LLM.

    Writes the same directory structure as the deterministic compiler:
    routine.yaml, udf.py, schemas/, input.json, expected_output.json.
    """
    with open(trace_path) as f:
        trace_data = json.load(f)

    trace = Trace.model_validate(trace_data)
    routine, udf_source = llm_compile_trace(trace, client)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write routine.yaml
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

    # Write input.json from mission
    if trace.mission.input_summary:
        with open(output_dir / "input.json", "w") as f:
            json.dump(trace.mission.input_summary, f, indent=2)

    # Write expected_output.json
    if trace.final_output:
        with open(output_dir / "expected_output.json", "w") as f:
            json.dump(trace.final_output, f, indent=2)
