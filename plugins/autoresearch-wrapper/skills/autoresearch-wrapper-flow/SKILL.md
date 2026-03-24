---
name: autoresearch-wrapper-flow
description: Show or plot recorded metric flow for an autoresearch-wrapper run. Use when the user wants the chronological metric sequence, best-so-far progression, or a terminal-friendly plot.
---

# Autoresearch Wrapper Flow

Resolve the CLI path (handles symlinked skills and installed plugins):

```bash
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_ROOT="$CLAUDE_PLUGIN_ROOT"
else
  _SKILL_REAL=$(readlink -f "${CLAUDE_SKILL_DIR:-.claude/skills/autoresearch-wrapper-flow}/SKILL.md")
  case "$_SKILL_REAL" in
    */.claude/skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/.claude/skills/*} ;;
    */skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/skills/*} ;;
    *) echo "Could not resolve AUTORESEARCH_ROOT from $_SKILL_REAL" >&2; exit 1 ;;
  esac
fi
```

Use:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" flow
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
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" flow --json
```

## Example

- `/autoresearch-wrapper-flow`
