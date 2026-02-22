# Routine YAML + UDF Format

A routine package is a directory containing:
- `routine.yaml` — the step definitions
- `udf.py` — Python functions referenced by `udf.call` steps
- `schemas/` — optional JSON Schema files for input/output validation

## routine.yaml

```yaml
version: "1"
name: my_routine
description: What this routine does

tools:
  - name: fetch_csv
    description: Fetch CSV from URL
    args_schema: { type: object, properties: { url: { type: string } } }

input_schema:
  type: object
  properties:
    url: { type: string }
  required: [url]

output_schema:
  type: object
  properties:
    total: { type: integer }

steps:
  - id: s1
    type: tool.call
    tool: fetch_csv
    args:
      url: "{{ url }}"
    save_as: raw_data

  - id: s2
    type: udf.call
    function: process_data
    args:
      data: "{{ raw_data }}"
    save_as: result

  - id: s3
    type: assert
    check: "count(result) > 0"
    message: "No data processed"

  - id: s4
    type: return
    value: "{{ result }}"
```

## Step Fields

### Common fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique step identifier |
| `type` | string | Step type (see below) |
| `description` | string | Human-readable description |
| `when` | string | Conditional expression — step runs only if truthy |
| `save_as` | string | Variable name to store the result |

### tool.call

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Tool name (must be declared in `tools:`) |
| `args` | object | Arguments — supports `{{ var }}` templates |

### udf.call

| Field | Type | Description |
|-------|------|-------------|
| `function` | string | Function name in `udf.py` |
| `args` | object | Keyword arguments — supports templates |

### assert

| Field | Type | Description |
|-------|------|-------------|
| `check` | string | Expression that must be truthy |
| `message` | string | Error message on failure |

### prompt.user

| Field | Type | Description |
|-------|------|-------------|
| `prompt.message` | string | Message shown to the user |
| `prompt.fields` | array | Input fields to collect |

### return

| Field | Type | Description |
|-------|------|-------------|
| `value` | any | Output value — supports templates |

## udf.py

Standard Python module. Functions are referenced by name in `udf.call` steps.

```python
def process_data(data: str) -> list[dict]:
    """Parse and process raw data."""
    # Your deterministic logic here
    return parsed_rows

def count(items: list) -> int:
    return len(items)
```

UDF functions are also available in `assert check` and `when` expressions.

## Templates

Step args support Jinja2 templates:
- `{{ variable }}` — reference a context variable (input or save_as)
- Simple variable references (`{{ x }}`) preserve the original Python type
- String interpolation (`Hello {{ name }}!`) produces strings
