---
name: autoresearch-wrapper-run
description: Start or resume a dependency-aware autoresearch-wrapper run in Git worktrees. Use when the target and metric are already configured and the user wants to initialize or continue the optimization loop.
---

# Autoresearch Wrapper Run

Resolve the CLI path (handles symlinked skills and installed plugins):

```bash
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_ROOT="$CLAUDE_PLUGIN_ROOT"
else
  _SKILL_REAL=$(readlink -f "${CLAUDE_SKILL_DIR:-.claude/skills/autoresearch-wrapper-run}/SKILL.md")
  case "$_SKILL_REAL" in
    */.claude/skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/.claude/skills/*} ;;
    */skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/skills/*} ;;
    *) echo "Could not resolve AUTORESEARCH_ROOT from $_SKILL_REAL" >&2; exit 1 ;;
  esac
fi
```

Use:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" run
```

When this skill is invoked:

1. Start or resume the current run.
2. If the run is blocked, explain whether the missing requirement is:
- target selection
- metric configuration
- execution settings
- dependency-aware readiness

3. If the run starts successfully, summarize:
- run id
- target part
- generated `program.md`
- seed worktree
- any preallocated candidates
- execution mode (sequential, parallel, or wild)

4. Remind the user that the underlying loop uses:
- `allocate`
- `evaluate`
- `record`

5. If early exit is configured, inform the user:
- patience setting (how many rounds without improvement before stopping)
- threshold setting (minimum improvement to count as progress)
- the run will end with status `early_exit` if the patience is exceeded

6. If wild mode is configured, inform the user:
- wild mode performs simultaneous multi-parameter changes
- `wild_max_simultaneous` controls how many parameters change at once
- the search widens automatically when improvement stalls

## Example

- `/autoresearch-wrapper-run`
