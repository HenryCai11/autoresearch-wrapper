---
name: autoresearch-wrapper-delete
description: Create a feature-deletion run that removes a part and optimizes dependent parameters. Use when the user wants to remove a module or file and find the best post-deletion configuration.
---

# Autoresearch Wrapper Delete

Resolve the CLI path (handles symlinked skills):

```bash
_SKILL_REAL=$(readlink -f skills/autoresearch-wrapper-delete/SKILL.md)
AUTORESEARCH_ROOT=${_SKILL_REAL%%/skills/*}
```

Use:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" delete --part <part> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize>
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
