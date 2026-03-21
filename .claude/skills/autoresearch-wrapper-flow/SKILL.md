---
name: autoresearch-wrapper-flow
description: Show or plot recorded metric flow for an autoresearch-wrapper run. Use when the user wants the chronological metric sequence, best-so-far progression, or a terminal-friendly plot.
---

# Autoresearch Wrapper Flow

Use:

```bash
python3 scripts/autoresearch_wrapper.py flow
```

When this skill is invoked:

1. Show the recorded metric flow for the active run by default.
2. Summarize:
- metric name
- goal
- chronological sequence
- best-so-far sequence
- latest metric
- best metric

3. Include the ASCII plot when presenting the result.

4. If the user asks for raw structured data, use:

```bash
python3 scripts/autoresearch_wrapper.py flow --json
```

## Example

- `/autoresearch-wrapper-flow`
