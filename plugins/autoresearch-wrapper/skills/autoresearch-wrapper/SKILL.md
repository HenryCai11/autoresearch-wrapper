---
name: autoresearch-wrapper
description: Dependency-aware repo optimization workflow. Use when scanning a repo for optimizable parts, selecting a target, wrapping a repo-local script, configuring metrics and execution settings, or orchestrating a worktree-backed autoresearch run.
---

# Autoresearch Wrapper

## Locating the CLI

The helper CLI may live outside the current repo, either because this skill is symlinked into a project or because it was installed as a plugin. Resolve the path first:

```bash
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_ROOT="$CLAUDE_PLUGIN_ROOT"
else
  _SKILL_REAL=$(readlink -f "${CLAUDE_SKILL_DIR:-.claude/skills/autoresearch-wrapper}/SKILL.md")
  case "$_SKILL_REAL" in
    */.claude/skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/.claude/skills/*} ;;
    */skills/*) AUTORESEARCH_ROOT=${_SKILL_REAL%%/skills/*} ;;
    *) echo "Could not resolve AUTORESEARCH_ROOT from $_SKILL_REAL" >&2; exit 1 ;;
  esac
fi
```

Then use `python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py"` for all commands below. If the skill lives inside the current repo, `python3 scripts/autoresearch_wrapper.py` also works.

When this skill is invoked:

1. If invoked with no arguments or just `/autoresearch-wrapper`, prefer the end-to-end wizard when a real interactive terminal is available:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" wizard
```

If you are operating without a real interactive stdin, emulate the same flow manually:
- Run `scan --no-interactive`
- Start from the compact core-functionality summary and focused dependency graph
- Only ask for the full language/directory listing if the user explicitly wants a broader scan
- Ask which kind of files (language or directory) they want to focus on
- Ask which specific part to optimize
- Ask for the metric name, metric command, metric goal
- Ask for execution mode (sequential / parallel / wild) and rounds
- Persist the configuration with `configure`
- Ask if the user wants to start the run immediately

If the user explicitly asks to inspect everything, rerun with:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" wizard --full-summary
```

2. If the user provides extra text after `/autoresearch-wrapper`, treat it as the high-level instruction and act accordingly.

3. If the user names a repo-local script path, wrap it with:

```bash
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" wrap <script-path>
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
python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" configure --part <part> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize> --mode <sequential|parallel|wild> --rounds <n>
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
