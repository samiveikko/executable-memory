"""JSON Schema validation wrapper."""

from __future__ import annotations

from typing import Any

import jsonschema


def validate_json(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Validate a value against a JSON Schema. Returns list of error messages."""
    validator = jsonschema.Draft7Validator(schema)
    return [err.message for err in validator.iter_errors(instance)]
