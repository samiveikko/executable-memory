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
em compile <trace.json> -o <output_dir>
```

**Arguments:**
- `trace.json` — Path to the trace JSON file

**Options:**
- `-o`, `--output` — Output directory (default: `./routine_out`)

**Output:**
Creates a directory containing:
- `routine.yaml` — compiled routine
- `udf.py` — UDF function stubs (implement TODO functions)
- `schemas/input.schema.json` — inferred input schema
- `schemas/output.schema.json` — inferred output schema
- `input.json` — input data from the trace
- `expected_output.json` — expected output for golden testing
- `fixtures/` — intermediate result fixtures

### `em run`

Run a routine with input data.

```bash
em run <routine_dir> --input <input.json> [--out output.json] [--json]
```

**Arguments:**
- `routine_dir` — Path to the routine package directory

**Options:**
- `-i`, `--input` — Input JSON file
- `-o`, `--out` — Write result to JSON file
- `--json` — Output raw JSON to stdout

**Behavior:**
- Runs the routine step by step
- If a `prompt.user` step is reached, prompts interactively in the terminal
- Prints status and output when complete

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
