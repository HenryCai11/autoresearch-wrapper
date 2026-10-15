---
name: autoresearch-wrapper
description: Dependency-aware repo optimization workflow. Use when scanning a repo for optimizable parts, selecting a target, wrapping a repo-local script, configuring metrics and execution settings, or orchestrating a worktree-backed autoresearch run.
---

# Autoresearch Wrapper

This skill set works in both Claude Code and Codex. Skills are invoked as `/<name>` in Claude Code and `$<name>` in Codex (e.g. `/autoresearch-wrapper-run` or `$autoresearch-wrapper-run`); examples below use the Claude Code form.

## Locating the CLI

Use the `run.sh` launcher in this skill's folder (the folder containing this `SKILL.md`). This block finds it in the standard Claude Code and Codex install locations:

```bash
AUTORESEARCH_RUNNER=""
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/autoresearch-wrapper/run.sh"
else
  for dir in skills/autoresearch-wrapper .agents/skills/autoresearch-wrapper .claude/skills/autoresearch-wrapper "$HOME/.agents/skills/autoresearch-wrapper" "$HOME/.claude/skills/autoresearch-wrapper"; do
    if [ -f "$dir/run.sh" ]; then AUTORESEARCH_RUNNER="$(readlink -f "$dir/run.sh")"; break; fi
  done
fi
[ -n "$AUTORESEARCH_RUNNER" ] || { echo "Could not resolve the autoresearch-wrapper launcher" >&2; exit 1; }
```

Then use `bash "$AUTORESEARCH_RUNNER"` for all commands below. If the skill lives inside the current repo, `python3 scripts/autoresearch_wrapper.py` also works.

When this skill is invoked:

1. If invoked with no arguments (just `/autoresearch-wrapper` or `$autoresearch-wrapper`), route to the end-to-end wizard:

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

2. If the user provides extra text after the skill name, treat it as the high-level instruction and act accordingly.

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

6. When the user wants to inspect state, start a run, inspect metrics, create features, delete parts, or monitor progress, prefer these companion skills:
- `autoresearch-wrapper-status`: state, readiness, runs, candidates
- `autoresearch-wrapper-run`: start or resume a run, then finalize it
- `autoresearch-wrapper-flow`: metric history and plot
- `autoresearch-wrapper-create`: compare feature approaches, each tuned against a tuned control
- `autoresearch-wrapper-delete`: compare deleting a part against keeping it, both tuned
- `autoresearch-wrapper-monitor`: poll progress

## Core rules

- Use Git worktrees; never optimize in the primary checkout if a worktree can be used.
- Treat the optimization unit as a module/file by default, and use the direct dependency graph from `scan`.
- A part is `surely optimizable` only when the target, candidate space, and metric are all explicit; otherwise it is `probably optimizable`.
- If the metric is unknown, do not run. Ask the user to define or confirm it first.
- Runtime state lives in `.autoresearch-wrapper/state.json` (human-readable: `.autoresearch-wrapper/STATUS.md`); planning files under `.autoresearch-wrapper/plans`.

## Helper commands

The run loop (see each run's `program.md`):

```bash
bash "$AUTORESEARCH_RUNNER" allocate --run-id <run>
bash "$AUTORESEARCH_RUNNER" evaluate --run-id <run> --candidate <seed|candidate-001>
bash "$AUTORESEARCH_RUNNER" record --run-id <run> --candidate <id> --status auto --description "<summary>"
```

`evaluate` commits pending edits in the candidate worktree before measuring; do not edit between `evaluate` and `record`. A run is marked `completed` when its rounds target or stop rule is met (`--stop-rule "metric<=X, stalled:N, minutes:N"`, any clause ends it), and `allocate` then refuses. Merge back and clean up with `finalize --run-id <run> --merge`; confirm with the user before `--merge` or `--prune-branches`.

Other settings and helpers:

```bash
bash "$AUTORESEARCH_RUNNER" configure --part <part> --early-exit-patience 3 --early-exit-threshold 0.01
bash "$AUTORESEARCH_RUNNER" configure --part <part> --metric-timeout 1800   # hung candidates are killed and recorded as crashes
bash "$AUTORESEARCH_RUNNER" configure --part <part> --mode wild --wild-max-simultaneous 3
bash "$AUTORESEARCH_RUNNER" configure --part path/to/script.py --metric-preset runtime_seconds --use-suggested-command
bash "$AUTORESEARCH_RUNNER" preset-metric --preset runtime_seconds --script path/to/script.py
bash "$AUTORESEARCH_RUNNER" resources        # detect CPUs/GPUs/scheduler and set concurrency defaults
bash "$AUTORESEARCH_RUNNER" reference        # clone Karpathy's upstream autoresearch for reference
```

Inside a run: evaluate the baseline `seed` first, keep or discard strictly by the configured metric, and resume the persisted active run when the user asks to continue.

## Examples

- `/autoresearch-wrapper scan this repo and summarize the dependency-aware optimization candidates`
- `/autoresearch-wrapper wrap scripts/bench.py and use the suggested metric preset`
- `/autoresearch-wrapper optimize src/api.py with metric latency_ms, sequential mode, and 5 rounds`

## Guidelines

- Do not start a run if the metric is unclear.
- Keep dependency-aware boundaries explicit.
- Respect the wrapper's persisted state in `.autoresearch-wrapper/state.json`.
- If the user asks to optimize immediately, still confirm or infer the full run gate first.
