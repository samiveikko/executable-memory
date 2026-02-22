# EM Concepts

## Trace vs Routine

A **trace** is a recording of what an agent actually did — the sequence of tool calls, function invocations, and user interactions that led to a successful outcome.

A **routine** is a deterministic program compiled from a trace. It replays the same sequence of steps without needing an LLM to decide what to do next.

```
Agent Session → Trace (JSON) → Compile → Routine (YAML + UDFs) → Run deterministically
```

## Determinism

Routines are deterministic by design:
- The same input always produces the same output
- Step order is fixed at compile time
- No LLM calls during execution
- Conditional steps (`when:`) use deterministic expressions

The only non-deterministic element is `prompt.user`, which pauses execution and waits for human input.

## Step Types

| Type | Purpose |
|------|---------|
| `tool.call` | Call an external tool (API, database, file system) |
| `udf.call` | Call a local Python function |
| `assert` | Validate data — fail fast if something is wrong |
| `prompt.user` | Pause and collect human input |
| `return` | Produce the final output |

## Context

As a routine executes, each step can save its result to a named variable using `save_as`. Subsequent steps reference these variables using Jinja2 templates: `{{ variable_name }}`.

## Pause and Resume

When a `prompt.user` step is reached:
1. The engine serializes the current execution state
2. Returns a `needs_input` result with the prompt definition
3. The caller collects answers from the user
4. Calls `resume_run()` with the answers
5. Execution continues from where it paused
