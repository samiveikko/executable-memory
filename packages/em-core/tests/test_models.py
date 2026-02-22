"""Tests for Pydantic models."""

import pytest
from em.models.trace import Trace, TraceEvent, TraceEventType, TraceMission, TraceApp
from em.models.routine import Routine, Step, StepType, ToolDef, PromptDef, PromptField, PromptFieldType
from em.models.results import RunResult, RunStatus, FailureReport
from em.models.prompts import PromptAnswers


class TestTrace:
    def test_minimal_trace(self):
        t = Trace(
            app=TraceApp(name="test"),
            mission=TraceMission(goal="test goal"),
            events=[],
        )
        assert t.version == "1"
        assert t.app.name == "test"

    def test_trace_with_events(self):
        t = Trace(
            app=TraceApp(name="test", version="1.0"),
            mission=TraceMission(goal="do stuff"),
            events=[
                TraceEvent(type=TraceEventType.tool_call, seq=0, tool="fetch", args={"url": "http://x"}, result="ok"),
                TraceEvent(type=TraceEventType.udf_call, seq=1, function="parse", args={"data": "x"}, result=[1, 2]),
                TraceEvent(type=TraceEventType.approval, seq=2, prompt="proceed?", answer=True),
            ],
            final_output={"result": 42},
        )
        assert len(t.events) == 3
        assert t.events[0].type == TraceEventType.tool_call
        assert t.events[2].answer is True


class TestRoutine:
    def test_minimal_routine(self):
        r = Routine(
            name="test",
            steps=[Step(id="s1", type=StepType.return_, value=42)],
        )
        assert r.name == "test"
        assert len(r.steps) == 1

    def test_full_routine(self):
        r = Routine(
            name="full",
            description="A full routine",
            tools=[ToolDef(name="fetch", description="fetch data")],
            steps=[
                Step(id="s1", type=StepType.tool_call, tool="fetch", args={"url": "x"}, save_as="data"),
                Step(id="s2", type=StepType.udf_call, function="parse", args={"raw": "{{ data }}"}, save_as="parsed"),
                Step(id="s3", type=StepType.assert_, check="len(parsed) > 0", message="no data"),
                Step(
                    id="s4",
                    type=StepType.prompt_user,
                    prompt=PromptDef(
                        message="Confirm?",
                        fields=[PromptField(name="ok", label="Proceed?", type=PromptFieldType.confirm)],
                    ),
                ),
                Step(id="s5", type=StepType.return_, value="{{ parsed }}"),
            ],
        )
        assert len(r.steps) == 5


class TestRunResult:
    def test_ok_result(self):
        r = RunResult(run_id="abc", status=RunStatus.ok, output={"x": 1})
        assert r.status == RunStatus.ok

    def test_failed_result(self):
        r = RunResult(
            run_id="abc",
            status=RunStatus.failed,
            failure=FailureReport(step_id="s1", error_type="ValueError", message="bad"),
        )
        assert r.failure.step_id == "s1"


class TestPromptAnswers:
    def test_valid_answers(self):
        prompt = PromptDef(
            message="test",
            fields=[
                PromptField(name="name", label="Name", type=PromptFieldType.text),
                PromptField(name="age", label="Age", type=PromptFieldType.number),
            ],
        )
        answers = PromptAnswers(values={"name": "Alice", "age": 30})
        errors = answers.validate_against(prompt)
        assert errors == []

    def test_missing_required(self):
        prompt = PromptDef(
            message="test",
            fields=[PromptField(name="name", label="Name", required=True)],
        )
        answers = PromptAnswers(values={})
        errors = answers.validate_against(prompt)
        assert len(errors) == 1
        assert "Missing required" in errors[0]

    def test_wrong_type(self):
        prompt = PromptDef(
            message="test",
            fields=[PromptField(name="ok", label="OK?", type=PromptFieldType.confirm)],
        )
        answers = PromptAnswers(values={"ok": "yes"})
        errors = answers.validate_against(prompt)
        assert len(errors) == 1

    def test_invalid_select(self):
        prompt = PromptDef(
            message="test",
            fields=[PromptField(name="color", label="Color", type=PromptFieldType.select, options=["red", "blue"])],
        )
        answers = PromptAnswers(values={"color": "green"})
        errors = answers.validate_against(prompt)
        assert len(errors) == 1
