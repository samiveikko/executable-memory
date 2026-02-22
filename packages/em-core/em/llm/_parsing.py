"""Parse LLM responses — extract YAML/Python blocks, parse recovery JSON."""

from __future__ import annotations

import json
import re
from typing import Any

import yaml

from em.models.routine import Routine


def extract_yaml_block(text: str) -> str:
    """Extract the first ```yaml ... ``` block from *text*.

    Raises:
        ValueError: If no YAML block is found.
    """
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        raise ValueError("No ```yaml block found in LLM response")
    return m.group(1).strip()


def extract_python_block(text: str) -> str:
    """Extract the first ```python ... ``` block from *text*.

    Raises:
        ValueError: If no Python block is found.
    """
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        raise ValueError("No ```python block found in LLM response")
    return m.group(1).strip()


def parse_routine_yaml(yaml_text: str) -> Routine:
    """Parse YAML text into a validated ``Routine`` model.

    Raises:
        ValueError: If YAML is invalid or doesn't match the Routine schema.
    """
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping, got {type(data).__name__}")

    return Routine.model_validate(data)


def parse_recovery_json(text: str) -> dict[str, Any]:
    """Parse a recovery strategy JSON from LLM response.

    Accepts either raw JSON or a ```json fenced block.

    Returns:
        A dict with at least ``{"strategy": "..."}``

    Raises:
        ValueError: If parsing fails or strategy is unknown.
    """
    # Try to extract from fenced block first
    m = re.search(r"```json\s*\n(.*?)```", text, re.DOTALL)
    raw = m.group(1).strip() if m else text.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in recovery response: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    strategy = data.get("strategy")
    valid_strategies = ("modify_args", "skip", "fail")
    if strategy not in valid_strategies:
        raise ValueError(f"Unknown strategy {strategy!r}, expected one of {valid_strategies}")

    return data
