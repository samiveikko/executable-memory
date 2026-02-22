"""Tests for the runner engine, templating, eval, tools, and state store."""

import json
import tempfile
from pathlib import Path

import pytest

from em.models.prompts import PromptAnswers
from em.models.results import RunStatus
from em.runner.engine import resume_run, run_routine
from em.runner.eval import safe_eval
from em.runner.state_store import FileStateStore, InMemoryStateStore, RunState
from em.runner.templating import render_value
from em.runner.tools import ToolRegistry


# --- Templating ---

class TestTemplating:
    def test_plain_string(self):
        assert render_value("hello", {}) == "hello"

    def test_simple_variable(self):
        assert render_value("{{ x }}", {"x": 42}) == 42

    def test_string_interpolation(self):
        assert render_value("Hello {{ name }}!", {"name": "World"}) == "Hello World!"

    def test_dict_rendering(self):
        result = render_value({"url": "{{ base }}/api"}, {"base": "http://example.com"})
        assert result == {"url": "http://example.com/api"}

    def test_list_rendering(self):
        result = render_value(["{{ x }}", "{{ y }}"], {"x": 1, "y": 2})
        assert result == [1, 2]

    def test_passthrough_non_string(self):
        assert render_value(42, {}) == 42
        assert render_value(None, {}) is None

    def test_preserves_complex_objects(self):
        data = [{"a": 1}, {"b": 2}]
        result = render_value("{{ items }}", {"items": data})
        assert result == data


# --- Safe eval ---

class TestSafeEval:
    def test_literals(self):
        assert safe_eval("42", {}) == 42
        assert safe_eval("'hello'", {}) == "hello"
        assert safe_eval("True", {}) is True

    def test_comparison(self):
        assert safe_eval("x > 0", {"x": 5}) is True
        assert safe_eval("x == 0", {"x": 0}) is True
        assert safe_eval("x < 0", {"x": 5}) is False

    def test_bool_ops(self):
        assert safe_eval("x > 0 and y > 0", {"x": 1, "y": 2}) is True
        assert safe_eval("x > 0 or y > 0", {"x": -1, "y": 2}) is True

    def test_function_call(self):
        assert safe_eval("len(items)", {"items": [1, 2, 3], "len": len}) == 3

    def test_subscript(self):
        assert safe_eval("data['key']", {"data": {"key": "val"}}) == "val"

    def test_arithmetic(self):
        assert safe_eval("x + y", {"x": 3, "y": 4}) == 7

    def test_unary_not(self):
        assert safe_eval("not x", {"x": False}) is True

    def test_undefined_variable(self):
        with pytest.raises(NameError):
            safe_eval("undefined_var", {})


# --- ToolRegistry ---

class TestToolRegistry:
    def test_register_and_call(self):
        reg = ToolRegistry()
        reg.register("add", lambda a, b: a + b)
        assert reg.call("add", {"a": 1, "b": 2}) == 3

    def test_missing_tool(self):
        reg = ToolRegistry()
        with pytest.raises(KeyError):
            reg.call("nope", {})

    def test_args_validation(self):
        reg = ToolRegistry()
        reg.register(
            "greet",
            lambda name: f"hi {name}",
            args_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        )
        assert reg.call("greet", {"name": "Alice"}) == "hi Alice"
        with pytest.raises(ValueError):
            reg.call("greet", {"name": 123})

    def test_has(self):
        reg = ToolRegistry()
        reg.register("x", lambda: None)
        assert reg.has("x")
        assert not reg.has("y")


# --- State Store ---

class TestStateStore:
    def test_in_memory(self):
        store = InMemoryStateStore()
        state = RunState("r1", "/tmp", 2, {"x": 1}, "s3")
        store.save(state)
        loaded = store.load("r1")
        assert loaded is not None
        assert loaded.step_index == 2
        store.delete("r1")
        assert store.load("r1") is None

    def test_file_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileStateStore(Path(tmpdir))
            state = RunState("r2", "/tmp", 1, {"y": 2}, "s2")
            store.save(state)
            loaded = store.load("r2")
            assert loaded is not None
            assert loaded.context == {"y": 2}
            store.delete("r2")
            assert store.load("r2") is None


# --- Engine: golden test ---

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples" / "csv_report"


class TestGoldenCSVReport:
    def test_run_csv_report(self):
        """Golden test: run the csv_report routine and compare output."""
        with open(EXAMPLES_DIR / "input.json") as f:
            input_data = json.load(f)
        with open(EXAMPLES_DIR / "expected_output.json") as f:
            expected = json.load(f)

        # Build tool registry with fixture support
        fixtures_dir = EXAMPLES_DIR / "fixtures"

        def fetch_csv(url: str) -> str:
            if url.startswith("fixture://"):
                filename = url.removeprefix("fixture://")
                return (fixtures_dir / filename).read_text()
            raise ValueError(f"Unsupported: {url}")

        reg = ToolRegistry()
        reg.register("fetch_csv", fetch_csv)

        result = run_routine(
            routine_dir=EXAMPLES_DIR,
            input_data=input_data,
            tool_registry=reg,
        )

        assert result.status == RunStatus.ok
        assert result.output == expected


# --- Engine: prompt.user test ---

class TestPromptPauseResume:
    def _make_prompt_routine(self, tmpdir: Path):
        """Create a minimal routine with a prompt.user step."""
        routine = {
            "version": "1",
            "name": "prompt_test",
            "steps": [
                {"id": "s1", "type": "udf.call", "function": "greet", "args": {"name": "{{ name }}"}, "save_as": "greeting"},
                {
                    "id": "s2",
                    "type": "prompt.user",
                    "prompt": {
                        "message": "Please confirm",
                        "fields": [{"name": "ok", "label": "Proceed?", "type": "confirm", "required": True}],
                    },
                    "save_as": "user_input",
                },
                {"id": "s3", "type": "return", "value": "{{ greeting }}"},
            ],
        }
        import yaml
        (tmpdir / "routine.yaml").write_text(yaml.dump(routine))
        (tmpdir / "udf.py").write_text("def greet(name: str) -> str:\n    return f'Hello {name}'\n")

    def test_pause_and_resume(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            self._make_prompt_routine(tmpdir)

            state_store = InMemoryStateStore()
            result = run_routine(
                routine_dir=tmpdir,
                input_data={"name": "Alice"},
                state_store=state_store,
            )
            assert result.status == RunStatus.needs_input
            assert result.pending_prompt == "s2"

            # Resume with answers
            result2 = resume_run(
                run_id=result.run_id,
                answers=PromptAnswers(values={"ok": True}),
                state_store=state_store,
            )
            assert result2.status == RunStatus.ok
            assert result2.output == "Hello Alice"


# --- Engine: failure cases ---

class TestFailureCases:
    def test_missing_tool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            import yaml
            routine = {
                "version": "1",
                "name": "fail_test",
                "tools": [{"name": "missing_tool"}],
                "steps": [
                    {"id": "s1", "type": "tool.call", "tool": "missing_tool", "args": {}},
                ],
            }
            (tmpdir / "routine.yaml").write_text(yaml.dump(routine))
            result = run_routine(routine_dir=tmpdir)
            assert result.status == RunStatus.failed
            assert "not registered" in result.failure.message

    def test_assertion_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            import yaml
            routine = {
                "version": "1",
                "name": "assert_test",
                "steps": [
                    {"id": "s1", "type": "assert", "check": "1 == 2", "message": "math is broken"},
                ],
            }
            (tmpdir / "routine.yaml").write_text(yaml.dump(routine))
            result = run_routine(routine_dir=tmpdir)
            assert result.status == RunStatus.failed
            assert "math is broken" in result.failure.message

    def test_udf_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            import yaml
            routine = {
                "version": "1",
                "name": "udf_err",
                "steps": [
                    {"id": "s1", "type": "udf.call", "function": "boom", "args": {}},
                ],
            }
            (tmpdir / "routine.yaml").write_text(yaml.dump(routine))
            (tmpdir / "udf.py").write_text("def boom():\n    raise RuntimeError('kaboom')\n")
            result = run_routine(routine_dir=tmpdir)
            assert result.status == RunStatus.failed
            assert "kaboom" in result.failure.message

    def test_template_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            import yaml
            routine = {
                "version": "1",
                "name": "tmpl_err",
                "steps": [
                    {"id": "s1", "type": "return", "value": "{{ undefined_var }}"},
                ],
            }
            (tmpdir / "routine.yaml").write_text(yaml.dump(routine))
            result = run_routine(routine_dir=tmpdir)
            assert result.status == RunStatus.failed
