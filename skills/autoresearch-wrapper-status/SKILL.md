---
name: autoresearch-wrapper-status
description: Show dependency-aware autoresearch-wrapper state for the current repo. Use when the user wants the selected part, readiness, runs, candidates, or current status summary.
---

# Autoresearch Wrapper Status

Use the launcher next to this skill:

```bash
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/autoresearch-wrapper-status/run.sh"
elif [ -f ".claude/skills/autoresearch-wrapper-status/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f ".claude/skills/autoresearch-wrapper-status/run.sh")"
elif [ -f "skills/autoresearch-wrapper-status/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f "skills/autoresearch-wrapper-status/run.sh")"
else
  echo "Could not resolve the autoresearch-wrapper-status launcher" >&2; exit 1
fi
```

Use:

```bash
bash "$AUTORESEARCH_RUNNER" status
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
bash "$AUTORESEARCH_RUNNER" status --json
```

## Example

- `/autoresearch-wrapper-status`
