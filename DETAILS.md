# Detailed Documentation

Back to [README](./README.md)

## Feature List

- Dependency-aware repo scanning at module or file granularity.
- Direct dependency graph construction with unresolved-edge tracking.
- Part classification into `surely optimizable` and `probably optimizable`.
- Dependency-aware readiness gating before any optimization run starts.
- Persisted canonical state in `.autoresearch-wrapper/state.json`.
- Human-readable status output in `.autoresearch-wrapper/STATUS.md`.
- Git worktree-first candidate allocation and experiment isolation.
- Run resume support with persisted active-run and candidate metadata.
- Karpathy-style per-run `program.md` generation.
- Recorded metric-flow summaries and ASCII metric plots for each run.
- Script-wrapper shortcut for repo-local entrypoints.
- Metric preset scaffolding for common script measurements.
- Preset metric helper command for script-based evaluation.
- Feature-creation comparison runs (`create`): each approach and a no-change control arm are tuned with equal budgets, then compared by tuned ceiling (`compare`).
- Feature-deletion comparison runs (`delete`): the codebase with and without a part, both tuned with equal budgets.
- Progress snapshots via `status --json` / `flow`, plus a blocking terminal poller (`monitor`) for people watching a run.
- Early exit mechanism for stalled optimization runs (`--early-exit-patience`, `--early-exit-threshold`); crashes count as stalled rounds.
- Metric command timeout (`configure --metric-timeout`, `evaluate --timeout`) that kills the whole command tree and records a crash.
- Wild mode (`--mode wild`): candidates are allocated as in parallel mode, and the agent changes several parameters at once (up to `--wild-max-simultaneous`), widening when progress stalls.
- Interactive wizard prompts for all commands when running in a TTY.

## Feature Details

### Dependency-aware scanning

- Scans the repo at the module/file level.
- Builds a best-effort direct dependency graph for each part.
- Defaults to a compact scan view that prioritizes core functionality modules and immediate neighbors.
- Use `scan --full-summary` when you explicitly want the full language/directory listing and full dependency graph.
- Tracks:
  - direct dependencies
  - direct dependents
  - unresolved dependencies
  - dependency clarity
  - key neighbors
- Uses dependency clarity when deciding whether a part is ready to optimize.

### Optimization status classification

Each discovered part is classified as one of:
- `surely optimizable`
  - target, candidate space, metric, and important direct dependencies are clear
- `probably optimizable`
  - one or more of those are unclear, especially the metric or dependency boundary

### Persisted repo state

The wrapper writes canonical state to:

```text
.autoresearch-wrapper/state.json
```

That state includes:
- discovered parts
- dependency graph edges
- metric suggestions
- selected part
- persisted run configuration
- active and past runs
- worktree metadata

### Human-readable status output

The wrapper writes:

```text
.autoresearch-wrapper/STATUS.md
```

This includes:
- selected part and active run
- parts table
- dependency table
- run summary
- candidate worktree lifecycle
- compact recorded metric-flow summaries

### Metric flow plotting

Recorded results can be rendered as a metric flow with:
- chronological metric sequence
- best-so-far sequence
- per-step table
- simple ASCII plot for quick terminal inspection

Use:

```bash
python3 scripts/autoresearch_wrapper.py flow
python3 scripts/autoresearch_wrapper.py flow --run-id <run-id>
python3 scripts/autoresearch_wrapper.py flow --json
```

### Dependency-aware run gating

Before a run starts, the wrapper requires:
- selected part
- metric name
- metric command
- metric goal
- execution mode
- rounds or an enforceable stop rule
- known-enough important direct dependencies

If the selected part has unresolved important dependency boundaries, `run` is blocked until the part is rescanned, narrowed, or clarified.

### Stop rules

`--stop-rule` takes comma-separated clauses; the run is marked `completed` (with a `stop_reason`) as soon as any clause holds, and `allocate` refuses afterwards:

- `metric<=X`, `metric>=X`, `metric<X`, `metric>X` — the best metric so far crosses a threshold
- `stalled:N` — N recordings in a row without beating the best (crashes count)
- `minutes:N` — wall-clock minutes since the run started

```bash
python3 scripts/autoresearch_wrapper.py configure --part <part> --rounds 50 --stop-rule "metric<=120, stalled:8, minutes:240"
```

Unparseable rules are rejected at configure time.

### Git worktree-based optimization

Optimization uses Git worktrees by default.

That means:
- the main checkout is not used as the experiment workspace
- each run has a seed worktree
- new candidates are allocated into their own worktrees
- candidate branches and paths are persisted for resume/status

### Comparison runs (create / delete)

Adding or removing a module changes what the best settings of its neighbours are, so a fair comparison tunes every option, including "no change", with the same budget:

```text
comparison run
├── control     setup: nothing                     → tuning run (budget B)
├── approach-A  setup: implement A                 → tuning run (budget B)
├── approach-B  setup: implement B                 → tuning run (budget B)
└── deleted     setup: remove part + fix imports   → tuning run (budget B)   (delete runs)
```

- `create` / `delete` create the arms, each with a setup worktree; `control` starts tuning immediately
- `arm-ready --run-id <run> --arm <arm>` commits an arm's setup and starts its tuning run (an ordinary optimize run seeded from the setup commit, with the shared `--rounds` / `--stop-rule`)
- `allocate` / `evaluate` / `record` / `flow` take `--arm <arm>` to act on that arm's tuning run; record the `seed` first to capture the setup score
- the tuning scope is enforced: `evaluate` rejects a candidate that changes files outside it before running the metric, and `record` re-checks (e.g. manual `--metric-value`). Default: the target plus its direct neighbours (create) or the deleted part's direct dependents (delete); `--tune-scope "a.py,src/"` overrides; files an arm changes during setup join that arm's scope. `--allow-out-of-scope` accepts an exception and `compare` flags it
- `compare --run-id <run>` reports setup score, tuned ceiling, tuning gain, and delta vs. the tuned control per arm; ties go to control; unfinished arms are flagged as provisional
- `finalize --run-id <run> [--merge]` merges the winning arm's best (or `--arm <arm>`) and removes every arm's worktrees; `--stop` ends unfinished arms first

Create/delete runs made before this design have no arms; `compare` refuses them.

### Karpathy-style run program

Each run generates a per-run `program.md` under the run directory. It includes:
- locked metric and stop settings
- dependency neighborhood for the selected part
- references to the state files and run directory
- helper commands for baseline, candidate allocation, evaluation, and recording

## Typical Workflow

### 1. Run the end-to-end wizard

```bash
python3 scripts/autoresearch_wrapper.py wizard
```

This scans the repo, starts from the compact core-functionality summary, lets you choose the target part, captures the metric and execution settings, persists the config, and can start the run immediately.

If you explicitly want the full scan listing before choosing, use:

```bash
python3 scripts/autoresearch_wrapper.py wizard --full-summary
```

### 2. Scan the repo manually

```bash
python3 scripts/autoresearch_wrapper.py scan
```

This discovers parts, builds the dependency graph, updates `state.json`, and refreshes `STATUS.md`.

### 3. Configure the selected part

```bash
python3 scripts/autoresearch_wrapper.py configure \
  --part path/to/module.py \
  --metric latency_ms \
  --metric-command "python -c \"print('METRIC=123.4')\"" \
  --metric-goal minimize \
  --mode sequential \
  --rounds 5
```

Or use interactive prompts:

```bash
python3 scripts/autoresearch_wrapper.py configure --part path/to/module.py --interactive
```

For a script entrypoint, you can scaffold from the shorthand wrapper first:

```bash
python3 scripts/autoresearch_wrapper.py path/to/script.py
```

Then confirm the suggested preset-backed metric command:

```bash
python3 scripts/autoresearch_wrapper.py configure \
  --part path/to/script.py \
  --metric-preset runtime_seconds \
  --use-suggested-command
```

### 4. Inspect status

```bash
python3 scripts/autoresearch_wrapper.py status
python3 scripts/autoresearch_wrapper.py status --json
```

### 5. Start or resume a run

```bash
python3 scripts/autoresearch_wrapper.py run
```

### 6. Manage candidates during the run

```bash
python3 scripts/autoresearch_wrapper.py allocate --run-id <run-id>
python3 scripts/autoresearch_wrapper.py evaluate --run-id <run-id> --candidate seed
python3 scripts/autoresearch_wrapper.py record --run-id <run-id> --candidate seed --status auto --description "baseline"
```

`evaluate` commits pending edits in the candidate worktree before measuring, so a kept candidate's branch becomes the base for the next `allocate`.

### 7. Inspect the metric flow

```bash
python3 scripts/autoresearch_wrapper.py flow
python3 scripts/autoresearch_wrapper.py flow --run-id <run-id>
```

### 8. Merge back and clean up

```bash
python3 scripts/autoresearch_wrapper.py finalize --run-id <run-id> --merge
```

- `--merge` squash-merges the best branch into the current checkout and leaves it staged (requires no uncommitted changes to tracked files; a conflicting merge is rolled back before anything is removed)
- worktrees are removed; dirty ones are skipped unless `--force`
- `--keep-best-worktree` leaves the winner's worktree in place
- `--prune-branches` deletes every run branch except the best
- `--stop` ends a still-running run first
- without `--merge`, the output lists the `git diff` / `git merge --squash` commands to do it by hand

### 9. Use preset-backed script metrics

Available preset helpers:
- `runtime_seconds`
- `latency_ms`
- `throughput`
- `memory_mb`

You can run a preset directly:

```bash
python3 scripts/autoresearch_wrapper.py preset-metric --preset runtime_seconds --script path/to/script.py
```

Or let `wrap` create a suggested command and confirm it through `configure --use-suggested-command`.

## Generated Layout

```text
.autoresearch-wrapper/
  state.json
  STATUS.md
  runs/
    <run-id>/
      program.md
      results.tsv
      logs/
```

Runs' worktrees live next to the repo in `<repo>.autoresearch-worktrees/<run-id>/`.

## Dependency Graph Notes

The current graph is intentionally simple:
- direct dependencies only
- best-effort extraction
- repo-local edges are preferred
- unresolved imports/includes are recorded when they matter to local optimization boundaries

Current extraction is heuristic across multiple languages and is strongest where local import/include structure is clear.

## Script Wrapper Notes

The script-wrapper flow is intentionally a shortcut, not a separate mode:
- it still uses normal scan results
- it still persists normal part config and selection state
- it still respects dependency-aware run blocking
- it still uses the same worktree-backed run flow once the metric command is confirmed

## Key Files

- `skills/` — the single skill set for Claude Code and Codex (one directory per command; `skills/autoresearch-wrapper/agents/openai.yaml` holds Codex UI metadata)
- `.claude/skills`, `.agents/skills` — symlinks to `skills/` so Claude Code and Codex discover the skills inside this repo
- `SKILL.md`, `run.sh` (repo root) — generated copy of the main skill plus a launcher symlink, for installing the repo root as one skill
- `.claude-plugin/marketplace.json` — Claude marketplace manifest at the repo root
- `plugins/autoresearch-wrapper/` — packaged Claude plugin root used by the marketplace
- `scripts/autoresearch_wrapper.py` — CLI entrypoint
- `autoresearch_wrapper/core.py` — scan, dependency graph, state, worktree, and run logic
- `templates/autoresearch_program_template.md` — generated per-run instructions
- `references/karpathy-autoresearch.md` — upstream reference notes
