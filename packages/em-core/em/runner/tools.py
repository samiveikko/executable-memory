"""ToolRegistry — register and call external tools with schema validation."""

from __future__ import annotations

from typing import Any, Callable

from em.utils.jsonschema import validate_json


class ToolRegistry:
    """Registry of callable tools with optional schema validation."""

    def __init__(self) -> None:
        self._tools: dict[str, _ToolEntry] = {}

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        args_schema: dict[str, Any] | None = None,
        result_schema: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool by name."""
        self._tools[name] = _ToolEntry(
            fn=fn,
            args_schema=args_schema,
            result_schema=result_schema,
        )

    def has(self, name: str) -> bool:
        return name in self._tools

    def call(self, name: str, args: dict[str, Any]) -> Any:
        """Call a registered tool, validating args and result."""
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        entry = self._tools[name]

        if entry.args_schema:
            errors = validate_json(args, entry.args_schema)
            if errors:
                raise ValueError(f"Tool '{name}' args validation failed: {errors}")

        result = entry.fn(**args)

        if entry.result_schema:
            errors = validate_json(result, entry.result_schema)
            if errors:
                raise ValueError(f"Tool '{name}' result validation failed: {errors}")

        return result

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


class _ToolEntry:
    __slots__ = ("fn", "args_schema", "result_schema")

    def __init__(
        self,
        fn: Callable[..., Any],
        args_schema: dict[str, Any] | None,
        result_schema: dict[str, Any] | None,
    ):
        self.fn = fn
        self.args_schema = args_schema
        self.result_schema = result_schema
