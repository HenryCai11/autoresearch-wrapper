![Autoresearch Wrapper Banner](./assets/banner.svg)

# Autoresearch Wrapper

`autoresearch-wrapper` is a Codex skill plus helper CLI for running an `autoresearch`-style optimization workflow on an arbitrary repo.

The core idea is:
- scan a repo for optimization candidates
- build a dependency-aware view of each part
- classify each part as `surely optimizable` or `probably optimizable`
- collect the metric and run settings for a selected part
- run or resume optimization in Git worktrees instead of mutating the main checkout

It is inspired by Karpathy's [`autoresearch`](https://github.com/karpathy/autoresearch), but adds repo scanning, dependency graphing, persisted state, planning artifacts, and worktree-backed candidate management.

## Features

### Dependency-aware scanning

- Scans the repo at the module/file level.
- Builds a best-effort direct dependency graph for each part.
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

### Planning workspace

Scan also regenerates:

```text
.autoresearch-wrapper/plans/
```

This planning workspace mirrors repo-relative part paths and creates a directory per part with:
- `metadata.json`
- `dependencies.md`
- `notes.md`

This is a derived workspace for planning and inspection, not the source of truth.

### Dependency-aware run gating

Before a run starts, the wrapper requires:
- selected part
- metric name
- metric command
- metric goal
- execution mode
- rounds or stop rule
- known-enough important direct dependencies

If the selected part has unresolved important dependency boundaries, `run` is blocked until the part is rescanned, narrowed, or clarified.

### Git worktree-based optimization

Optimization uses Git worktrees by default.

That means:
- the main checkout is not used as the experiment workspace
- each run has a seed worktree
- new candidates are allocated into their own worktrees
- candidate branches and paths are persisted for resume/status

### Karpathy-style run program

Each run generates a per-run `program.md` under the run directory. It includes:
- locked metric and stop settings
- dependency neighborhood for the selected part
- references to state and planning artifacts
- helper commands for baseline, candidate allocation, evaluation, and recording

### Reference repo support

The wrapper can clone Karpathy's upstream `autoresearch` repo into the local wrapper state area for reference during implementation:

```bash
python3 scripts/autoresearch_wrapper.py reference
python3 scripts/autoresearch_wrapper.py reference --refresh
```

## Command Surface

The skill exposes three main commands:
- `/autoresearch-wrapper`
- `/autoresearch-wrapper:status`
- `/autoresearch-wrapper:run`

The main command also supports a shorthand script-wrapper form:

```bash
python3 scripts/autoresearch_wrapper.py path/to/script.py
python3 scripts/autoresearch_wrapper.py wrap path/to/script.py
```

This selects the script as the primary part, infers a metric preset, and creates an incomplete config stub in normal wrapper state.

The underlying helper CLI is:

```bash
python3 scripts/autoresearch_wrapper.py
```

CLI subcommands:
- `scan`
- `wrap`
- `configure`
- `status`
- `run`
- `allocate`
- `evaluate`
- `record`
- `reference`
- `preset-metric`

## Typical Workflow

### 1. Scan the repo

```bash
python3 scripts/autoresearch_wrapper.py scan
```

This discovers parts, builds the dependency graph, updates `state.json`, refreshes `STATUS.md`, and regenerates `.autoresearch-wrapper/plans/`.

### 2. Configure the selected part

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

### 3. Inspect status

```bash
python3 scripts/autoresearch_wrapper.py status
python3 scripts/autoresearch_wrapper.py status --json
```

### 4. Start or resume a run

```bash
python3 scripts/autoresearch_wrapper.py run
```

### 5. Manage candidates during the run

```bash
python3 scripts/autoresearch_wrapper.py allocate --run-id <run-id>
python3 scripts/autoresearch_wrapper.py evaluate --run-id <run-id> --candidate seed
python3 scripts/autoresearch_wrapper.py record --run-id <run-id> --candidate seed --status auto --description "baseline"
```

### 6. Use preset-backed script metrics

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
  plans/
    <repo-relative-part-path>/
      metadata.json
      dependencies.md
      notes.md
  runs/
    <run-id>/
      program.md
      results.tsv
      logs/
  reference/
    autoresearch-upstream/
```

## Dependency Graph Notes

The current graph is intentionally simple:
- direct dependencies only
- best-effort extraction
- repo-local edges are preferred
- unresolved imports/includes are recorded when they matter to local optimization boundaries

Current extraction is heuristic across multiple languages and is strongest where local import/include structure is clear.

## Script Wrapper Notes

The new script-wrapper flow is intentionally a shortcut, not a separate mode:
- it still uses normal scan results
- it still persists normal part config and selection state
- it still respects dependency-aware run blocking
- it still uses the same worktree-backed run flow once the metric command is confirmed

## Testing

The repo includes unit tests covering:
- scan classification
- dependency graph extraction
- planning workspace generation
- configure persistence
- worktree-backed run flow
- dependency-aware run blocking

Run them with:

```bash
python3 -m unittest -q
```

## Key Files

- `SKILL.md`
  - skill behavior and command mapping for Codex
- `scripts/autoresearch_wrapper.py`
  - CLI entrypoint
- `autoresearch_wrapper/core.py`
  - scan, dependency graph, state, worktree, and run logic
- `templates/autoresearch_program_template.md`
  - generated per-run instructions
- `references/karpathy-autoresearch.md`
  - upstream reference notes
