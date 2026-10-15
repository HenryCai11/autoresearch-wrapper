---
name: autoresearch-wrapper
description: Discover dependency-aware optimization candidates across repo modules or files, classify them as surely or probably optimizable, collect the required metric and run settings, and drive a Git-worktree-backed autoresearch loop with status and resume helpers.
---

# Autoresearch Wrapper

Use this skill when the user wants Codex to scan a repo for optimization candidates, build a dependency graph for each part, lock a metric and run spec, and then run or resume an `autoresearch`-style loop without mutating the main checkout.

The helper CLI lives at:

```bash
python3 scripts/autoresearch_wrapper.py
```

Read [references/karpathy-autoresearch.md](references/karpathy-autoresearch.md) only when you need the upstream reference shape or need to refresh the local reference clone.

## Public interface

Treat these names as the skill's command surface:
- `/autoresearch-wrapper`
- `/autoresearch-wrapper:status`
- `/autoresearch-wrapper:run`
- `/autoresearch-wrapper:flow`
- `/autoresearch-wrapper:create`
- `/autoresearch-wrapper:delete`
- `/autoresearch-wrapper:monitor`

These map to CLI subcommands:
- `/autoresearch-wrapper` -> `wizard`, or `wrap <script-path>` when the user passes a repo-local script path
- `/autoresearch-wrapper:status` -> `status`
- `/autoresearch-wrapper:run` -> `run`
- `/autoresearch-wrapper:flow` -> `flow`
- `/autoresearch-wrapper:create` -> `create`
- `/autoresearch-wrapper:delete` -> `delete`
- `/autoresearch-wrapper:monitor` -> `monitor`

## Core rules

- Use Git worktrees as much as possible.
- Never optimize in the primary checkout if a worktree can be used.
- Treat the optimization unit as a module/file by default.
- Build and use a direct dependency graph for each part during scan.
- Mark a part as `surely optimizable` only when the target, candidate space, and metric are all explicit.
- Mark a part as `probably optimizable` when any of those are unclear, especially the metric or important direct dependencies.
- If the metric is unknown, do not run. Ask the user to define or confirm it first.
- Persist runtime state in `.autoresearch-wrapper/state.json` and human-readable status in `.autoresearch-wrapper/STATUS.md`.
- Regenerate a planning workspace under `.autoresearch-wrapper/plans` that mirrors part paths and initializes per-part planning files.

## Workflow

### `/autoresearch-wrapper`

If invoked with no arguments or just `/autoresearch-wrapper`, route to the end-to-end wizard:

1. Run:

```bash
python3 scripts/autoresearch_wrapper.py wizard
```

If you are operating without a real interactive stdin and the CLI cannot complete the prompts directly, emulate the same flow manually:
- Run `python3 scripts/autoresearch_wrapper.py scan --no-interactive`
- Start from the compact core-functionality summary and focused dependency graph
- Only ask for the full language/directory listing if the user explicitly wants a broader scan
- Ask which functionality area they want to improve first
- Ask which specific part to optimize
- Ask for the metric name, metric command, metric goal
- Ask for execution mode (sequential / parallel / wild) and rounds
- Persist the configuration with `configure`
- Ask if the user wants to start the run immediately

2. Let the wizard:
   - scan the repo and print the compact core-functionality summary
   - propose functionality-oriented slices such as best-defined targets, latency-sensitive paths, or dependency hubs
   - select the target part
   - lock the metric name, command, goal, and execution mode
   - persist the config
   - optionally start the run immediately

If the user explicitly wants the full scan listing first, run:

```bash
python3 scripts/autoresearch_wrapper.py wizard --full-summary
```

If the user provides a repo-local script path directly, use the script-wrapper shortcut:

```bash
python3 scripts/autoresearch_wrapper.py wrap path/to/script.py
```

This should:
- select that script as the primary part
- keep the normal dependency-aware scan/state model
- infer a metric preset and suggested metric command
- create an incomplete config stub until the metric command is confirmed

### `/autoresearch-wrapper:status`

Run:

```bash
python3 scripts/autoresearch_wrapper.py status
```

Report:
- discovered parts
- each part's status
- dependency table and key neighbors
- readiness of the selected part
- active run id
- candidate worktrees and their lifecycle
- compact recorded metric-flow summaries

### `/autoresearch-wrapper:run`

Run:

```bash
python3 scripts/autoresearch_wrapper.py run
```

Behavior:
- refuse to run if any required config field is missing
- create or resume the active run
- generate a Karpathy-style per-run `program.md`
- initialize a seed worktree and additional candidate worktrees for parallel or wild mode

The generated run program will point back to the helper CLI for:
- `allocate`
- `evaluate`
- `record`

### `/autoresearch-wrapper:flow`

Run:

```bash
python3 scripts/autoresearch_wrapper.py flow
```

Report:
- recorded metric sequence for the selected run
- best-so-far sequence
- tabular step history
- ASCII plot of metric values

### `/autoresearch-wrapper:create`

Run:

```bash
python3 scripts/autoresearch_wrapper.py create --part <part> --feature "<description>" --candidates <n> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize>
```

Behavior:
- create a comparison run with arms `control` + `approach-A..N`; each arm gets a setup worktree
- `control` (no change) starts tuning immediately, so gains from tuning are not credited to the feature
- implement each approach in its setup worktree, then `arm-ready --run-id <run> --arm approach-A` to commit it and start that arm's tuning run
- every arm is tuned with the same `--rounds` / `--stop-rule` budget; drive the loop with `--arm` (`evaluate`/`record` the `seed` first for the setup score, then `allocate`/`evaluate`/`record`)
- tuning scope: the target's direct dependency neighbours (listed in `program.md`)
- `compare --run-id <run>` reports setup score, tuned ceiling, tuning gain, and delta vs. the tuned control per arm, and picks a winner (ties go to control)
- `finalize --run-id <run> --merge` merges the winning arm's best (confirm with the user first) and cleans up every arm

### `/autoresearch-wrapper:delete`

Run:

```bash
python3 scripts/autoresearch_wrapper.py delete --part <part> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize>
```

Behavior:
- create a comparison run with arms `control` (part kept) and `deleted` (part removed and committed in its setup worktree)
- `control` starts tuning immediately and is the tuned pre-deletion baseline
- fix broken imports/references in the `deleted` setup worktree, then `arm-ready --run-id <run> --arm deleted`
- both arms are tuned with the same budget via `--arm`; `compare` shows whether removing the part costs or gains once dependents are re-tuned
- `finalize --run-id <run> --merge` merges the winner (confirm with the user first) and cleans up

### `/autoresearch-wrapper:monitor`

Run:

```bash
python3 scripts/autoresearch_wrapper.py monitor --interval <seconds>
```

Behavior:
- poll the active run at the configured interval
- report rounds completed, best metric, early exit status
- exit when the run completes or Ctrl-C is pressed

## Helper commands

Use these directly when managing a run:

```bash
python3 scripts/autoresearch_wrapper.py allocate --run-id <run>
python3 scripts/autoresearch_wrapper.py evaluate --run-id <run> --candidate <seed|candidate-001>
python3 scripts/autoresearch_wrapper.py record --run-id <run> --candidate <id> --status auto --description "<summary>"
```

`evaluate` commits pending edits in the candidate worktree before measuring; do not edit between `evaluate` and `record`. The run is marked `completed` when the rounds target or stop rule is met (`--stop-rule "metric<=X, stalled:N, minutes:N"`, any clause ends the run) and `allocate` then refuses.

When the run ends, merge the best candidate back and clean up. Confirm with the user before `--merge` or `--prune-branches`:

```bash
python3 scripts/autoresearch_wrapper.py finalize --run-id <run> --merge
```

`--merge` stages a squash merge without committing; `--prune-branches` deletes all other run branches; `--force` removes dirty worktrees; `--stop` ends a running run first.

Use metric presets to scaffold or confirm a script-based metric command:

```bash
python3 scripts/autoresearch_wrapper.py configure --part path/to/script.py --metric-preset runtime_seconds --use-suggested-command
python3 scripts/autoresearch_wrapper.py preset-metric --preset runtime_seconds --script path/to/script.py
```

Use `reference` to clone or refresh the upstream repo locally:

```bash
python3 scripts/autoresearch_wrapper.py reference
python3 scripts/autoresearch_wrapper.py reference --refresh
```

Use `resources` to detect system resources and set concurrency defaults:

```bash
python3 scripts/autoresearch_wrapper.py resources
```

Use early exit to stop runs that stall:

```bash
python3 scripts/autoresearch_wrapper.py configure --part <part> --early-exit-patience 3 --early-exit-threshold 0.01
```

Crashed or timed-out candidates count as rounds without improvement. Bound each metric evaluation so a hung candidate is killed and recorded as a crash (`evaluate --timeout <s>` overrides it once):

```bash
python3 scripts/autoresearch_wrapper.py configure --part <part> --metric-timeout 1800
```

Use wild mode for multi-parameter search when the search space is large:

```bash
python3 scripts/autoresearch_wrapper.py configure --part <part> --mode wild --wild-max-simultaneous 3
```

## Expected agent behavior inside a run

- Evaluate the baseline seed candidate first.
- Keep or discard later candidates strictly from the configured metric.
- Preserve all candidate history in the run directory.
- Reuse the persisted active run when the user asks to resume instead of starting a fresh run.
