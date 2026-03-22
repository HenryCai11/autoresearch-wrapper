---
name: autoresearch-wrapper
description: Dependency-aware repo optimization workflow. Use when scanning a repo for optimizable parts, selecting a target, wrapping a repo-local script, configuring metrics and execution settings, or orchestrating a worktree-backed autoresearch run.
---

# Autoresearch Wrapper

Use the repo-local helper CLI:

```bash
python3 scripts/autoresearch_wrapper.py
```

When this skill is invoked:

1. Treat the user text after `/autoresearch-wrapper` as the high-level instruction.
2. If the user did not specify a target yet, run:

```bash
python3 scripts/autoresearch_wrapper.py scan
```

Then summarize:
- discovered parts
- each part's status
- dependency-aware blockers
- likely optimization targets

3. If the user names a repo-local script path, wrap it with:

```bash
python3 scripts/autoresearch_wrapper.py wrap <script-path>
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
python3 scripts/autoresearch_wrapper.py configure --part <part> --metric <metric> --metric-command "<cmd>" --metric-goal <minimize|maximize> --mode <sequential|parallel|wild> --rounds <n>
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
