"""Tests for LLM-powered runtime recovery — fix strategies and engine integration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from em.llm._recovery import make_auto_fix_fn
from em.models.results import RunStatus
from em.models.routine import Routine, Step, StepType
from em.runner.engine import run_routine
from em.runner.tools import ToolRegistry
from tests.conftest import MockLLMClient


# --- make_auto_fix_fn unit tests ---

class TestMakeAutoFixFn:
    def _make_routine(self) -> Routine:
        return Routine(
            name="test",
            steps=[
                Step(id="s1", type=StepType.tool_call, tool="fetch", args={"url": "http://x"}),
                Step(id="s2", type=StepType.return_, value="{{ result }}"),
            ],
        )

    def test_modify_args_strategy(self):
        client = MockLLMClient('{"strategy": "modify_args", "new_args": {"url": "http://y"}}')
        fix_fn = make_auto_fix_fn(client)

        routine = self._make_routine()
        step = routine.steps[0]
        exc = ConnectionError("timeout")
        context = {"url": "http://x"}

        result = fix_fn(step, exc, context, routine)
        assert result is not None
        assert result["strategy"] == "modify_args"
        assert result["new_args"]["url"] == "http://y"
        assert len(client.calls) == 1

    def test_skip_strategy(self):
        client = MockLLMClient('{"strategy": "skip", "default_value": []}')
        fix_fn = make_auto_fix_fn(client)

        routine = self._make_routine()
        step = routine.steps[0]

        result = fix_fn(step, RuntimeError("err"), {}, routine)
        assert result["strategy"] == "skip"
        assert result["default_value"] == []

    def test_fail_strategy(self):
        client = MockLLMClient('{"strategy": "fail"}')
        fix_fn = make_auto_fix_fn(client)

        routine = self._make_routine()
        step = routine.steps[0]

        result = fix_fn(step, RuntimeError("err"), {}, routine)
        assert result["strategy"] == "fail"

    def test_llm_error_returns_none(self):
        """If the LLM itself errors, return None (let original error propagate)."""
        client = MockLLMClient("not valid json at all {{{")
        fix_fn = make_auto_fix_fn(client)

        routine = self._make_routine()
        step = routine.steps[0]

        result = fix_fn(step, RuntimeError("original"), {}, routine)
        assert result is None


# --- Engine integration with auto_fix_fn ---

class TestEngineAutoFix:
    def _make_routine_dir(self, tmpdir: Path, udf_code: str = "") -> Path:
        routine = {
            "version": "1",
            "name": "autofix_test",
            "steps": [
                {
                    "id": "s1",
                    "type": "udf.call",
                    "function": "divide",
                    "args": {"a": 10, "b": 0},
                    "save_as": "result",
                },
                {"id": "s2", "type": "return", "value": "{{ result }}"},
            ],
        }
        (tmpdir / "routine.yaml").write_text(yaml.dump(routine))
        code = udf_code or (
            "def divide(a: int, b: int) -> float:\n"
            "    return a / b\n"
        )
        (tmpdir / "udf.py").write_text(code)
        return tmpdir

    def test_no_autofix_fails_normally(self, tmp_path):
        self._make_routine_dir(tmp_path)
        result = run_routine(routine_dir=tmp_path)
        assert result.status == RunStatus.failed
        assert "division by zero" in result.failure.message

    def test_modify_args_fixes_step(self, tmp_path):
        self._make_routine_dir(tmp_path)

        def fix_fn(step, exc, context, routine):
            if "division by zero" in str(exc):
                return {"strategy": "modify_args", "new_args": {"a": 10, "b": 2}}
            return None

        result = run_routine(routine_dir=tmp_path, auto_fix_fn=fix_fn)
        assert result.status == RunStatus.ok
        assert result.output == 5.0

    def test_skip_strategy(self, tmp_path):
        self._make_routine_dir(tmp_path)

        def fix_fn(step, exc, context, routine):
            return {"strategy": "skip", "default_value": -1}

        result = run_routine(routine_dir=tmp_path, auto_fix_fn=fix_fn)
        assert result.status == RunStatus.ok
        assert result.output == -1

    def test_fail_strategy_propagates(self, tmp_path):
        self._make_routine_dir(tmp_path)

        def fix_fn(step, exc, context, routine):
            return {"strategy": "fail"}

        result = run_routine(routine_dir=tmp_path, auto_fix_fn=fix_fn)
        assert result.status == RunStatus.failed

    def test_none_from_fix_propagates(self, tmp_path):
        self._make_routine_dir(tmp_path)

        def fix_fn(step, exc, context, routine):
            return None

        result = run_routine(routine_dir=tmp_path, auto_fix_fn=fix_fn)
        assert result.status == RunStatus.failed

    def test_retry_also_fails(self, tmp_path):
        """If modify_args retry also fails, the error propagates."""
        self._make_routine_dir(tmp_path)

        def fix_fn(step, exc, context, routine):
            # Try fixing with b=0 again — will still fail
            return {"strategy": "modify_args", "new_args": {"a": 10, "b": 0}}

        result = run_routine(routine_dir=tmp_path, auto_fix_fn=fix_fn)
        assert result.status == RunStatus.failed
        assert "division by zero" in result.failure.message

    def test_autofix_with_llm_client(self, tmp_path):
        """Integration: MockLLMClient → make_auto_fix_fn → engine."""
        self._make_routine_dir(tmp_path)

        client = MockLLMClient('{"strategy": "modify_args", "new_args": {"a": 10, "b": 5}}')
        fix_fn = make_auto_fix_fn(client)

        result = run_routine(routine_dir=tmp_path, auto_fix_fn=fix_fn)
        assert result.status == RunStatus.ok
        assert result.output == 2.0
        assert len(client.calls) == 1

    def test_fix_fn_exception_treated_as_fail(self, tmp_path):
        """If the fix callback itself throws, treat as no fix."""
        self._make_routine_dir(tmp_path)

        def fix_fn(step, exc, context, routine):
            raise RuntimeError("fix callback broke")

        result = run_routine(routine_dir=tmp_path, auto_fix_fn=fix_fn)
        assert result.status == RunStatus.failed
        assert "division by zero" in result.failure.message
