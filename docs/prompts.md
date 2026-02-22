# Prompt.user Specification

The `prompt.user` step type pauses routine execution to collect input from a human.

## Prompt Definition

```yaml
- id: confirm_step
  type: prompt.user
  prompt:
    message: "The data has 100 rows. How should we proceed?"
    fields:
      - name: action
        label: "Choose action"
        type: select
        options: ["summarize", "export", "cancel"]
      - name: limit
        label: "Row limit"
        type: number
        default: 50
      - name: confirm
        label: "Proceed?"
        type: confirm
        default: true
  save_as: user_choices
```

## Field Types

| Type | Input | Value Type |
|------|-------|------------|
| `text` | Free-form text input | `string` |
| `select` | Choose from options | `string` |
| `confirm` | Yes/No toggle | `boolean` |
| `number` | Numeric input | `int` or `float` |

## Field Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | yes | Field identifier (used as key in answers) |
| `label` | string | yes | Display label |
| `type` | string | yes | One of: text, select, confirm, number |
| `required` | boolean | no | Whether the field must be filled (default: true) |
| `default` | any | no | Default value |
| `options` | string[] | no | Choices for select fields |

## Flow

1. Engine reaches a `prompt.user` step
2. Engine saves state and returns `RunResult` with `status: "needs_input"`
3. Caller collects answers from the user
4. Caller calls `resume_run(run_id, PromptAnswers(values={...}))`
5. Answers are validated against field definitions
6. If `save_as` is set, answers are stored in context under that name
7. Execution continues with the next step

## CLI Behavior

When running interactively via `em run`, prompt.user steps are handled in the terminal:
- `text` fields → text prompt
- `select` fields → numbered menu
- `confirm` fields → yes/no prompt
- `number` fields → numeric prompt

## Programmatic Behavior

When using `run_routine()` programmatically:
1. Check `result.status == "needs_input"`
2. Read `result.pending_prompt` to get the step ID
3. Build `PromptAnswers(values={"field_name": value, ...})`
4. Call `resume_run(result.run_id, answers, state_store)`
