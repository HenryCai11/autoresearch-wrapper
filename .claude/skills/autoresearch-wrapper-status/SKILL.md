---
name: autoresearch-wrapper-status
description: Show dependency-aware autoresearch-wrapper state for the current repo. Use when the user wants the selected part, readiness, runs, candidates, or current status summary.
---

# Autoresearch Wrapper Status

Use:

```bash
python3 scripts/autoresearch_wrapper.py status
```

When this skill is invoked:

1. Run the status command for the current repo.
2. Summarize:
- selected part
- readiness
- dependency blockers
- active run
- candidate lifecycle
- compact metric-flow summary if present

3. If the user asks for raw machine-readable output, use:

```bash
python3 scripts/autoresearch_wrapper.py status --json
```

## Example

- `/autoresearch-wrapper-status`
