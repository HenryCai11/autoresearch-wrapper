---
name: autoresearch-wrapper
description: Dependency-aware repo optimization workflow. Use when scanning a repo for optimizable parts, selecting a target, wrapping a repo-local script, configuring metrics and execution settings, or orchestrating a worktree-backed autoresearch run.
---

# Autoresearch Wrapper

## Locating the CLI

Use the launcher next to this skill:

```bash
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/autoresearch-wrapper/run.sh"
elif [ -f ".claude/skills/autoresearch-wrapper/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f ".claude/skills/autoresearch-wrapper/run.sh")"
elif [ -f "skills/autoresearch-wrapper/run.sh" ]; then
  AUTORESEARCH_RUNNER="$(readlink -f "skills/autoresearch-wrapper/run.sh")"
else
  echo "Could not resolve the autoresearch-wrapper launcher" >&2; exit 1
fi
```

Then use `bash "$AUTORESEARCH_RUNNER"` for all commands below. If the skill lives inside the current repo, `python3 scripts/autoresearch_wrapper.py` also works.

When this skill is invoked:

1. If invoked with no arguments or just `/autoresearch-wrapper`, route to the end-to-end wizard:

```bash
bash "$AUTORESEARCH_RUNNER" wizard
```

If you are operating without a real interactive stdin and the CLI cannot complete the prompts directly, emulate the same flow manually:
- Run `bash "$AUTORESEARCH_RUNNER" scan --no-interactive`
- Start from the compact core-functionality summary and focused dependency graph
- Only ask for the full language/directory listing if the user explicitly wants a broader scan
- Ask which functionality area they want to improve first
- Ask which specific part to optimize
- Ask for the metric name, metric command, metric goal
- Ask for execution mode (sequential / parallel / wild) and rounds
- Persist the configuration with `configure`
- Ask if the user wants to start the run immediately

If the user explicitly asks to inspect everything, rerun with:

```bash
bash "$AUTORESEARCH_RUNNER" wizard --full-summary
```

2. If the user provides extra text after `/autoresearch-wrapper`, treat it as the high-level instruction and act accordingly.

3. If the user names a repo-local script path, wrap it with:

```bash
bash "$AUTORESEARCH_RUNNER" wrap <script-path>
```

4. Before starting any run, make sure these are explicit:
- target part
- metric name
- metric goal
- metric command
- sequential, parallel, or wild mode
- rounds or stop rule
- early exit patience (optional)

Persist them with:

```bash
bash "$AUTORESEARCH_RUNNER" configure --part <part> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize> --mode <sequential|parallel|wild> --rounds <n>
```

5. Prefer Git worktrees. Do not optimize in the primary checkout if the helper can create a worktree-backed run.

6. When the user wants to inspect state, start a run, inspect metrics, create features, delete parts, or monitor progress, prefer these companion Claude skills:
- `/autoresearch-wrapper-status`
- `/autoresearch-wrapper-run`
- `/autoresearch-wrapper-flow`
- `/autoresearch-wrapper-create`
- `/autoresearch-wrapper-delete`
- `/autoresearch-wrapper-monitor`

## Examples

- `/autoresearch-wrapper scan this repo and summarize the dependency-aware optimization candidates`
- `/autoresearch-wrapper wrap scripts/bench.py and use the suggested metric preset`
- `/autoresearch-wrapper optimize src/api.py with metric latency_ms, sequential mode, and 5 rounds`

## Guidelines

- Do not start a run if the metric is unclear.
- Keep dependency-aware boundaries explicit.
- Respect the wrapper's persisted state in `.autoresearch-wrapper/state.json`.
- If the user asks to optimize immediately, still confirm or infer the full run gate first.
