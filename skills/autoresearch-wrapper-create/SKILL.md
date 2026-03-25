---
name: autoresearch-wrapper-create
description: Create a feature-addition run with multiple candidate implementations. Use when the user wants to add a new feature and compare approaches to find the best capability ceiling.
---

# Autoresearch Wrapper Create

Use the launcher next to this skill:

```bash
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/autoresearch-wrapper-create/run.sh"
elif [ -f ".claude/skills/autoresearch-wrapper-create/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f ".claude/skills/autoresearch-wrapper-create/run.sh")"
elif [ -f "skills/autoresearch-wrapper-create/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f "skills/autoresearch-wrapper-create/run.sh")"
else
  echo "Could not resolve the autoresearch-wrapper-create launcher" >&2; exit 1
fi
```

Use:

```bash
bash "$AUTORESEARCH_RUNNER" create --part <part> --feature "<description>" --candidates <n> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize>
```

When this skill is invoked:

1. Identify the target part and the feature to be added.
2. The wrapper identifies affected parts via the dependency graph.
3. Create N candidate worktrees, each for a different implementation approach.
4. Summarize:
- run id
- run type (`create`)
- feature description
- affected parts
- candidate worktrees (seed + approach-A, approach-B, ...)
- generated `program.md` with comparison instructions

5. The user then uses `evaluate` and `record` against each approach to find the best capability ceiling.

6. If the user has not scanned yet, run `scan` first.

7. If running interactively, use `--no-interactive` to skip wizard prompts or omit it to use the interactive wizard.

## Example

- `/autoresearch-wrapper-create --part src/api.py --feature "add response caching" --candidates 3 --metric latency_ms --metric-command "python bench.py" --metric-goal minimize`
