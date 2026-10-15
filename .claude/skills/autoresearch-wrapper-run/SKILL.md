---
name: autoresearch-wrapper-run
description: Start or resume a dependency-aware autoresearch-wrapper run in Git worktrees. Use when the target and metric are already configured and the user wants to initialize or continue the optimization loop.
---

# Autoresearch Wrapper Run

Use the launcher next to this skill:

```bash
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/autoresearch-wrapper-run/run.sh"
elif [ -f ".claude/skills/autoresearch-wrapper-run/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f ".claude/skills/autoresearch-wrapper-run/run.sh")"
elif [ -f "skills/autoresearch-wrapper-run/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f "skills/autoresearch-wrapper-run/run.sh")"
else
  echo "Could not resolve the autoresearch-wrapper-run launcher" >&2; exit 1
fi
```

Use:

```bash
bash "$AUTORESEARCH_RUNNER" run
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
- `evaluate` (commits pending worktree edits before measuring, so kept candidates compound)
- `record`

The run is marked `completed` when the rounds target or stop rule is met (or `early_exit` on stall); its `stop_reason` says why, and `allocate` refuses afterwards. Stop rules are comma-separated clauses, any of which ends the run: `metric<=X` / `metric>=X` / `metric<X` / `metric>X`, `stalled:N`, `minutes:N`.

5. When the run has ended, offer to merge back and clean up:

```bash
bash "$AUTORESEARCH_RUNNER" finalize --run-id <run> --merge
```

Confirm with the user before `--merge` (stages a squash merge of the best branch in their checkout, not committed) or `--prune-branches` (deletes all other run branches). Dirty worktrees are skipped unless `--force`; `--stop` ends a running run first. Without `--merge`, relay the printed `git diff` / `git merge --squash` commands.

6. If early exit is configured, inform the user:
- patience setting (how many rounds without improvement before stopping)
- threshold setting (minimum improvement to count as progress)
- the run will end with status `early_exit` if the patience is exceeded

7. If wild mode is configured, inform the user:
- wild mode performs simultaneous multi-parameter changes
- `wild_max_simultaneous` controls how many parameters change at once
- the search widens automatically when improvement stalls

## Example

- `/autoresearch-wrapper-run`
