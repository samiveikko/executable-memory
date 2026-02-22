"""Tests for LLM-powered compilation — parsing, end-to-end with mock client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from em.compiler.llm_compile import llm_compile_trace, llm_compile_trace_file
from em.llm._parsing import (
    extract_python_block,
    extract_yaml_block,
    parse_recovery_json,
    parse_routine_yaml,
)
from em.models.routine import StepType
from em.models.trace import Trace, TraceApp, TraceEvent, TraceEventType, TraceMission
from tests.conftest import MockLLMClient


# --- Parsing tests ---

class TestExtractYamlBlock:
    def test_basic(self):
        text = "Here is the routine:\n```yaml\nname: test\nsteps: []\n```\nDone."
        assert "name: test" in extract_yaml_block(text)

    def test_yml_variant(self):
        text = "```yml\nname: test\nsteps: []\n```"
        assert "name: test" in extract_yaml_block(text)

    def test_no_block(self):
        with pytest.raises(ValueError, match="No.*yaml block"):
            extract_yaml_block("no yaml here")


class TestExtractPythonBlock:
    def test_basic(self):
        text = '```python\ndef foo(): pass\n```'
        assert "def foo" in extract_python_block(text)

    def test_no_block(self):
        with pytest.raises(ValueError, match="No.*python block"):
            extract_python_block("no python here")


class TestParseRoutineYaml:
    def test_valid_routine(self):
        yaml_text = """\
version: "1"
name: test_routine
steps:
  - id: s1
    type: tool.call
    tool: fetch
    args:
      url: "{{ input_url }}"
    save_as: data
  - id: s2
    type: return
    value: "{{ data }}"
"""
        routine = parse_routine_yaml(yaml_text)
        assert routine.name == "test_routine"
        assert len(routine.steps) == 2
        assert routine.steps[0].type == StepType.tool_call
        assert routine.steps[1].type == StepType.return_

    def test_invalid_yaml(self):
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_routine_yaml("{{invalid")

    def test_non_mapping(self):
        with pytest.raises(ValueError, match="Expected YAML mapping"):
            parse_routine_yaml("- item1\n- item2")


class TestParseRecoveryJson:
    def test_modify_args(self):
        result = parse_recovery_json('{"strategy": "modify_args", "new_args": {"x": 1}}')
        assert result["strategy"] == "modify_args"
        assert result["new_args"] == {"x": 1}

    def test_skip(self):
        result = parse_recovery_json('{"strategy": "skip", "default_value": null}')
        assert result["strategy"] == "skip"

    def test_fail(self):
        result = parse_recovery_json('{"strategy": "fail"}')
        assert result["strategy"] == "fail"

    def test_fenced_block(self):
        text = 'Here is the fix:\n```json\n{"strategy": "skip", "default_value": 42}\n```'
        result = parse_recovery_json(text)
        assert result["strategy"] == "skip"
        assert result["default_value"] == 42

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_recovery_json("{broken")

    def test_unknown_strategy(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            parse_recovery_json('{"strategy": "magic"}')

    def test_non_object(self):
        with pytest.raises(ValueError, match="Expected JSON object"):
            parse_recovery_json("[1, 2, 3]")


# --- LLM compile end-to-end (mocked) ---

MOCK_LLM_RESPONSE = """\
Here is the compiled routine:

```yaml
version: "1"
name: csv_report
description: Fetch and summarize CSV data
tools:
  - name: fetch_csv
    description: Fetch CSV from URL
input_schema:
  type: object
  properties:
    url:
      type: string
  required:
    - url
steps:
  - id: fetch
    type: tool.call
    tool: fetch_csv
    args:
      url: "{{ url }}"
    save_as: raw_csv
  - id: parse
    type: udf.call
    function: parse_csv
    args:
      text: "{{ raw_csv }}"
    save_as: rows
  - id: check
    type: assert
    check: "len(rows) > 0"
    message: "No rows parsed"
  - id: result
    type: return
    value: "{{ rows }}"
```

```python
from __future__ import annotations
from typing import Any
import csv
import io

def parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]
```
"""


class TestLLMCompileTrace:
    def _make_trace(self) -> Trace:
        return Trace(
            app=TraceApp(name="test-agent"),
            mission=TraceMission(
                goal="Fetch and summarize CSV",
                input_summary={"url": "fixture://demo.csv"},
            ),
            events=[
                TraceEvent(
                    type=TraceEventType.tool_call,
                    seq=0,
                    tool="fetch_csv",
                    args={"url": "fixture://demo.csv"},
                    result="name,dept\nAlice,Eng",
                ),
                TraceEvent(
                    type=TraceEventType.udf_call,
                    seq=1,
                    function="parse_csv",
                    args={"text": "name,dept\nAlice,Eng"},
                    result=[{"name": "Alice", "dept": "Eng"}],
                ),
            ],
            final_output=[{"name": "Alice", "dept": "Eng"}],
        )

    def test_compile_with_mock(self):
        client = MockLLMClient(MOCK_LLM_RESPONSE)
        trace = self._make_trace()

        routine, udf_source = llm_compile_trace(trace, client)

        assert routine.name == "csv_report"
        assert len(routine.steps) == 4
        assert routine.steps[0].type == StepType.tool_call
        assert routine.steps[1].type == StepType.udf_call
        assert routine.steps[2].type == StepType.assert_
        assert routine.steps[3].type == StepType.return_
        assert "def parse_csv" in udf_source
        assert len(client.calls) == 1

    def test_compile_to_disk(self, tmp_path):
        client = MockLLMClient(MOCK_LLM_RESPONSE)
        trace = self._make_trace()

        # Write trace to file
        trace_path = tmp_path / "trace.json"
        trace_path.write_text(trace.model_dump_json(indent=2))

        out_dir = tmp_path / "out"
        llm_compile_trace_file(trace_path, out_dir, client)

        assert (out_dir / "routine.yaml").exists()
        assert (out_dir / "udf.py").exists()
        assert (out_dir / "schemas" / "input.schema.json").exists()
        assert (out_dir / "input.json").exists()
        assert (out_dir / "expected_output.json").exists()

    def test_compile_bad_response(self):
        client = MockLLMClient("This response has no yaml or python blocks.")
        trace = self._make_trace()

        with pytest.raises(ValueError, match="No.*yaml block"):
            llm_compile_trace(trace, client)
