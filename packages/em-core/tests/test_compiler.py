"""Tests for the trace compiler."""

import json
from pathlib import Path

import pytest

from em.compiler.compile_trace import compile_trace, compile_trace_file
from em.models.trace import Trace, TraceEvent, TraceEventType, TraceMission, TraceApp


EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples" / "csv_report"


class TestCompileTrace:
    def test_compile_csv_report_trace(self):
        with open(EXAMPLES_DIR / "trace.json") as f:
            trace = Trace.model_validate(json.load(f))

        routine, udf_source, fixtures = compile_trace(trace)

        assert routine.name
        assert len(routine.steps) == 5  # fetch, parse, approval, summarize, return
        assert routine.steps[0].type.value == "tool.call"
        assert routine.steps[0].tool == "fetch_csv"
        assert routine.steps[0].args["url"] == "{{ url }}"
        assert routine.steps[1].type.value == "udf.call"
        assert routine.steps[1].args["raw_csv"] == "{{ result_s1 }}"
        assert routine.steps[2].type.value == "prompt.user"
        assert routine.steps[3].type.value == "udf.call"
        assert routine.steps[3].args["rows"] == "{{ result_s2 }}"
        assert routine.steps[4].type.value == "return"

    def test_compile_generates_udf_stubs(self):
        with open(EXAMPLES_DIR / "trace.json") as f:
            trace = Trace.model_validate(json.load(f))

        _, udf_source, _ = compile_trace(trace)

        assert "def parse_and_clean" in udf_source
        assert "def summarize_rows" in udf_source

    def test_compile_to_disk(self, tmp_path):
        compile_trace_file(EXAMPLES_DIR / "trace.json", tmp_path / "out")

        out = tmp_path / "out"
        assert (out / "routine.yaml").exists()
        assert (out / "udf.py").exists()
        assert (out / "schemas" / "input.schema.json").exists()
        assert (out / "schemas" / "output.schema.json").exists()
        assert (out / "input.json").exists()
        assert (out / "expected_output.json").exists()


class TestCompileMinimal:
    def test_tool_only_trace(self):
        trace = Trace(
            app=TraceApp(name="test"),
            mission=TraceMission(goal="just fetch", input_summary={"url": "http://x"}),
            events=[
                TraceEvent(type=TraceEventType.tool_call, seq=0, tool="fetch", args={"url": "http://x"}, result="data"),
            ],
            final_output="data",
        )
        routine, udf_source, fixtures = compile_trace(trace)
        assert len(routine.steps) == 2  # tool call + return
        assert routine.steps[0].tool == "fetch"

    def test_empty_trace(self):
        trace = Trace(
            app=TraceApp(name="test"),
            mission=TraceMission(goal="nothing"),
            events=[],
        )
        routine, udf_source, fixtures = compile_trace(trace)
        assert len(routine.steps) == 0
