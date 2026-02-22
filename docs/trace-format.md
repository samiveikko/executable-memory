# Trace JSON Format

A trace captures a complete agent session.

## Structure

```json
{
  "version": "1",
  "app": {
    "name": "my-agent",
    "version": "1.0"
  },
  "mission": {
    "goal": "What the agent was asked to do",
    "input_summary": { "key": "value" }
  },
  "events": [ ... ],
  "final_output": { ... }
}
```

## Event Types

### tool_call

An external tool invocation.

```json
{
  "type": "tool_call",
  "seq": 0,
  "tool": "fetch_csv",
  "args": { "url": "https://example.com/data.csv" },
  "result": "csv,data,here"
}
```

### udf_call

A deterministic function call that can be extracted as a UDF.

```json
{
  "type": "udf_call",
  "seq": 1,
  "function": "parse_and_clean",
  "args": { "raw_csv": "csv,data,here" },
  "result": [{"col": "value"}]
}
```

### approval

A point where the agent asked for human confirmation.

```json
{
  "type": "approval",
  "seq": 2,
  "prompt": "Found 100 rows. Proceed with analysis?",
  "answer": true
}
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | yes | Format version ("1") |
| `app.name` | string | yes | Name of the agent |
| `app.version` | string | no | Agent version |
| `mission.goal` | string | yes | What the agent was asked to do |
| `mission.input_summary` | object | no | Summary of inputs provided |
| `events` | array | yes | Ordered list of trace events |
| `final_output` | any | no | The agent's final result |
