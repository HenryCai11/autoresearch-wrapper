---
name: autoresearch-wrapper-delete
description: Create a feature-deletion run that removes a part and optimizes dependent parameters. Use when the user wants to remove a module or file and find the best post-deletion configuration.
---

# Autoresearch Wrapper Delete

Use the launcher next to this skill:

```bash
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/autoresearch-wrapper-delete/run.sh"
elif [ -f ".claude/skills/autoresearch-wrapper-delete/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f ".claude/skills/autoresearch-wrapper-delete/run.sh")"
elif [ -f "skills/autoresearch-wrapper-delete/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f "skills/autoresearch-wrapper-delete/run.sh")"
else
  echo "Could not resolve the autoresearch-wrapper-delete launcher" >&2; exit 1
fi
```

Use:

```bash
bash "$AUTORESEARCH_RUNNER" delete --part <part> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize>
```

When this skill is invoked:

1. Identify the part to be deleted.
2. The wrapper identifies transitive dependents of the deleted part.
3. Create a seed worktree with the target file removed.
4. Optimize dependent parameters in subsequent candidate worktrees.
5. Summarize:
- run id
- run type (`delete`)
- deleted part
- transitive dependents affected
- candidate worktrees
- generated `program.md` with post-deletion optimization instructions

6. If the user has not scanned yet, run `scan` first.

7. If running interactively, use `--no-interactive` to skip wizard prompts or omit it to use the interactive wizard.

## Example

- `/autoresearch-wrapper-delete --part src/legacy_cache.py --metric throughput --metric-command "python bench.py" --metric-goal maximize`
