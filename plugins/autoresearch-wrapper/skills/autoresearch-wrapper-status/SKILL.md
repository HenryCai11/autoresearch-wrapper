---
name: autoresearch-wrapper-status
description: Show dependency-aware autoresearch-wrapper state for the current repo. Use when the user wants the selected part, readiness, runs, candidates, or current status summary.
---

# Autoresearch Wrapper Status

Resolve the CLI path (handles symlinked skills and installed plugins):

```bash
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_ROOT="$CLAUDE_PLUGIN_ROOT"
else
  _SKILL_REAL=$(readlink -f "${CLAUDE_SKILL_DIR:-.claude/skills/autoresearch-wrapper-status}/SKILL.md")
  case "$_SKILL_REAL" in
    */.claude/skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/.claude/skills/*} ;;
    */skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/skills/*} ;;
    *) echo "Could not resolve AUTORESEARCH_ROOT from $_SKILL_REAL" >&2; exit 1 ;;
  esac
fi
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
