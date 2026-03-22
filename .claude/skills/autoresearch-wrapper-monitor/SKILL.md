---
name: autoresearch-wrapper-monitor
description: Poll the active autoresearch-wrapper run at a configurable interval. Use when the user wants to watch run progress, check rounds completed, best metric, and early exit status.
---

# Autoresearch Wrapper Monitor

Resolve the CLI path (handles symlinked skills):

```bash
_SKILL_REAL=$(readlink -f .claude/skills/autoresearch-wrapper-monitor/SKILL.md)
AUTORESEARCH_ROOT=${_SKILL_REAL%%/.claude/*}
```

Use:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" monitor --interval <seconds>
```

When this skill is invoked:

1. Poll the active run at the configured interval (default: 30 seconds).
2. Report on each poll:
- run status
- rounds completed vs total
- best metric so far
- early exit stall count vs patience (if early exit is configured)
3. Exit when the run completes, triggers early exit, or is interrupted with Ctrl-C.

4. If no interval is specified, ask the user or use the default.

5. If no active run exists, inform the user and suggest starting one with `/autoresearch-wrapper-run`.

## Example

- `/autoresearch-wrapper-monitor --interval 60`
