---
name: autoresearch-wrapper-status
description: Show dependency-aware autoresearch-wrapper state for the current repo. Use when the user wants the selected part, readiness, runs, candidates, or current status summary.
---

# Autoresearch Wrapper Status

Resolve the CLI path (handles symlinked skills):

```bash
_SKILL_REAL=$(readlink -f .claude/skills/autoresearch-wrapper-status/SKILL.md)
AUTORESEARCH_ROOT=${_SKILL_REAL%%/.claude/*}
```

Use:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" status
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
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" status --json
```

## Example

- `/autoresearch-wrapper-status`
