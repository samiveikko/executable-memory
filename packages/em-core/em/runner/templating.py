"""Jinja2 template rendering for step args with UDF and context support."""

from __future__ import annotations

import re
from types import ModuleType
from typing import Any

import jinja2

# Matches a template that is ONLY a single variable reference: {{ varname }}
_SIMPLE_VAR_RE = re.compile(r"^\{\{\s*(\w+)\s*\}\}$")


class _UDFProxy:
    """Makes udf.* callable inside Jinja2 templates."""

    def __init__(self, module: ModuleType | None):
        self._module = module

    def __getattr__(self, name: str) -> Any:
        if self._module is None:
            raise AttributeError(f"No UDF module loaded — cannot call udf.{name}")
        fn = getattr(self._module, name, None)
        if fn is None:
            raise AttributeError(f"UDF '{name}' not found in udf.py")
        return fn


def render_value(value: Any, context: dict[str, Any], udf_module: ModuleType | None = None) -> Any:
    """Recursively render Jinja2 templates in a value tree.

    Strings containing {{ }} are treated as templates.
    If a string is exactly {{ varname }}, the raw Python object is returned
    (preserving lists, dicts, etc. instead of stringifying).
    Dicts and lists are traversed recursively.
    Other types pass through unchanged.
    """
    if isinstance(value, str):
        if "{{" in value and "}}" in value:
            # Fast path: simple variable reference → return raw object
            m = _SIMPLE_VAR_RE.match(value)
            if m:
                var_name = m.group(1)
                if var_name in context:
                    return context[var_name]

            # General path: render as Jinja2 template
            env = jinja2.Environment(undefined=jinja2.StrictUndefined)
            tmpl = env.from_string(value)
            rendered = tmpl.render(udf=_UDFProxy(udf_module), **context)
            return rendered
        return value
    elif isinstance(value, dict):
        return {k: render_value(v, context, udf_module) for k, v in value.items()}
    elif isinstance(value, list):
        return [render_value(v, context, udf_module) for v in value]
    return value
