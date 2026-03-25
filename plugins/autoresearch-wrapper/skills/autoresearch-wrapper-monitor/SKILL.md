---
name: autoresearch-wrapper-monitor
description: Poll the active autoresearch-wrapper run at a configurable interval. Use when the user wants to watch run progress, check rounds completed, best metric, and early exit status.
---

# Autoresearch Wrapper Monitor

Use the launcher next to this skill:

```bash
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/autoresearch-wrapper-monitor/run.sh"
elif [ -f ".claude/skills/autoresearch-wrapper-monitor/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f ".claude/skills/autoresearch-wrapper-monitor/run.sh")"
elif [ -f "skills/autoresearch-wrapper-monitor/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f "skills/autoresearch-wrapper-monitor/run.sh")"
else
  echo "Could not resolve the autoresearch-wrapper-monitor launcher" >&2; exit 1
fi
```

Use:

```bash
bash "$AUTORESEARCH_RUNNER" monitor --interval <seconds>
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
