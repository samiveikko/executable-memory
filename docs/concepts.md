# EM Concepts

## Trace vs Routine

A **trace** is a recording of what an agent actually did — the sequence of tool calls, function invocations, and user interactions that led to a successful outcome.

A **routine** is a deterministic program compiled from a trace. It replays the same sequence of steps without needing an LLM to decide what to do next.

```
Agent Session → Trace (JSON) → Compile → Routine (YAML + UDFs) → Run deterministically
```

## Compilation Modes

**Deterministic (default):** Copies the trace 1:1 into a routine. UDFs are generated as stubs that need manual implementation. Fast and predictable, but doesn't handle messy traces.

**LLM-powered (`--llm`):** An LLM analyzes the trace, extracts the happy path, removes errors/retries/dead-ends, and generates fully implemented UDFs. The LLM is only called once at compile time — the resulting routine is still deterministic.

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

## Runtime Recovery (Auto-fix)

When running with `--auto-fix`, the engine can recover from step failures using an LLM:

1. A step fails with an exception
2. The engine sends the error context to the LLM (step definition, error type, context keys)
3. The LLM returns a recovery strategy:
   - **modify_args** — retry with corrected arguments (max 1 retry per step)
   - **skip** — skip the step and use a default value
   - **fail** — no recovery possible
4. Credential/auth errors always result in "fail" (cannot fix at runtime)

Auto-fix is optional and requires an LLM API key. Without it, errors propagate normally.
