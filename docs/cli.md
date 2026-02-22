# CLI Reference

## Installation

```bash
cd packages/em-core
pip install -e .
```

This installs the `em` command.

## Commands

### `em compile`

Compile an agent trace into a routine package.

```bash
em compile <trace.json> -o <output_dir> [--llm]
```

**Arguments:**
- `trace.json` — Path to the trace JSON file

**Options:**
- `-o`, `--output` — Output directory (default: `./routine_out`)
- `--llm` — Use an LLM to compile (requires API key, see [Configuration](#configuration))

**Output:**
Creates a directory containing:
- `routine.yaml` — compiled routine
- `udf.py` — UDF function stubs (deterministic) or full implementations (`--llm`)
- `schemas/input.schema.json` — inferred input schema
- `schemas/output.schema.json` — inferred output schema
- `input.json` — input data from the trace
- `expected_output.json` — expected output for golden testing
- `fixtures/` — intermediate result fixtures (deterministic mode only)

**LLM mode (`--llm`):**
- Extracts the happy path from messy traces (removes errors, retries, dead-ends)
- Generates fully implemented UDFs instead of stubs
- Falls back to deterministic compilation if the LLM call fails

### `em run`

Run a routine with input data.

```bash
em run <routine_dir> --input <input.json> [--out output.json] [--json] [--auto-fix]
```

**Arguments:**
- `routine_dir` — Path to the routine package directory

**Options:**
- `-i`, `--input` — Input JSON file
- `-o`, `--out` — Write result to JSON file
- `--json` — Output raw JSON to stdout
- `--auto-fix` — Use an LLM to recover from step failures (requires API key)

**Behavior:**
- Runs the routine step by step
- If a `prompt.user` step is reached, prompts interactively in the terminal
- Prints status and output when complete

**Auto-fix (`--auto-fix`):**
When a step fails, the LLM analyzes the error and returns a recovery strategy:
- **modify_args** — retry the step with corrected arguments (max 1 retry)
- **skip** — skip the step and use a default value
- **fail** — no recovery possible, propagate the error

### `em validate`

Validate a routine package without running it.

```bash
em validate <routine_dir>
```

**Checks:**
- YAML syntax and schema validity
- UDF function references resolve to actual functions
- Tool references are declared in the tools section
- Schema files are valid JSON Schema

**Exit codes:**
- `0` — valid
- `1` — validation errors found

## Configuration

LLM features (`--llm`, `--auto-fix`) require environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EM_LLM_PROVIDER` | Provider name (`anthropic` or `openai`) | Auto-detected from API key |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `EM_LLM_MODEL` | Model override | Provider default |

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
export EM_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
```

Install the corresponding optional dependency:

```bash
pip install em-core[anthropic]   # or [openai] or [llm] for both
```
