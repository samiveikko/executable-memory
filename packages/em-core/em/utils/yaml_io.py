"""YAML I/O and routine package loading."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from em.models.routine import Routine


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return parsed dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(data: dict[str, Any], path: Path) -> None:
    """Save a dict as YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def load_routine(routine_dir: Path) -> Routine:
    """Load a Routine from a directory containing routine.yaml."""
    routine_path = routine_dir / "routine.yaml"
    if not routine_path.exists():
        raise FileNotFoundError(f"No routine.yaml found in {routine_dir}")
    data = load_yaml(routine_path)
    return Routine.model_validate(data)


def load_udf_module(routine_dir: Path) -> ModuleType | None:
    """Load the udf.py module from a routine package directory."""
    udf_path = routine_dir / "udf.py"
    if not udf_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("udf", udf_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load UDF module from {udf_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["udf"] = module
    spec.loader.exec_module(module)
    return module


def load_schema(routine_dir: Path, name: str) -> dict[str, Any] | None:
    """Load a JSON schema from the schemas/ subdirectory."""
    import json
    schema_path = routine_dir / "schemas" / name
    if not schema_path.exists():
        return None
    with open(schema_path) as f:
        return json.load(f)


class RoutinePackage:
    """A loaded routine package: routine + UDFs + schemas."""

    def __init__(self, routine_dir: Path):
        self.dir = routine_dir
        self.routine = load_routine(routine_dir)
        self.udf_module = load_udf_module(routine_dir)
        self.input_schema = load_schema(routine_dir, "input.schema.json")
        self.output_schema = load_schema(routine_dir, "output.schema.json")

    def get_udf(self, name: str) -> Any:
        """Get a UDF function by name."""
        if self.udf_module is None:
            raise ValueError(f"No UDF module loaded — cannot find '{name}'")
        fn = getattr(self.udf_module, name, None)
        if fn is None:
            raise ValueError(f"UDF '{name}' not found in udf.py")
        return fn
