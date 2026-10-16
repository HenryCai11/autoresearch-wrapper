# Autoresearch Run: 20261016T180208Z-index-html

Target repo: `/scratch/henrycai/eau-r14-20261016`
Target part: `index.html`
Discovery status: `surely optimizable`
Suggested metric from scan: `throughput`

## Locked config

- Metric preset: `none`
- Metric: `live_project_citation_rate`
- Goal: `maximize`
- Metric command:

```bash
python3 /scratch/henrycai/geo-runs/eau-r14-20261016/outer_metric.py
```

- Metric regex: `METRIC\s*=\s*(?P<value>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)`
- Execution mode: `sequential`
- Rounds: `1`
- Stop rule: `none`
- Parallelism: `1`

## State

- Canonical JSON: `/scratch/henrycai/eau-r14-20261016/.autoresearch-wrapper/state.json`
- Human summary: `/scratch/henrycai/eau-r14-20261016/.autoresearch-wrapper/STATUS.md`
- Run directory: `/scratch/henrycai/eau-r14-20261016/.autoresearch-wrapper/runs/20261016T180208Z-index-html`
- Seed worktree: `/scratch/henrycai/eau-r14-20261016.autoresearch-worktrees/20261016T180208Z-index-html/seed`

## Dependency Neighborhood

- Direct dependencies: `assets/favicon.svg`, `method.html`, `paper.html`, `research-context.html`, ...
- Dependents: `method.html`, `paper.html`, `research-context.html`
- Unresolved dependencies: none

## Rules

1. Do not optimize in the primary checkout if a worktree can be used.
2. Keep changes focused on `index.html` and its visible dependency neighborhood unless the metric harness requires a small supporting edit.
3. Record every evaluation and keep or discard decision through the helper CLI.
4. Treat the configured metric as the decision metric unless the user changes the run config.

## Loop

1. Evaluate the baseline:

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py evaluate --run-id 20261016T180208Z-index-html --candidate seed
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py record --run-id 20261016T180208Z-index-html --candidate seed --status auto --description "baseline"
```

2. For each new experiment:

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py allocate --run-id 20261016T180208Z-index-html
```

Edit inside the returned worktree, then evaluate and record. `evaluate` commits any pending edits to the candidate branch before measuring (respecting `.gitignore`), and a `keep` makes that branch the base for the next `allocate`, so improvements compound. Do not edit the worktree between `evaluate` and `record`.

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py evaluate --run-id 20261016T180208Z-index-html --candidate candidate-XYZ
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py record --run-id 20261016T180208Z-index-html --candidate candidate-XYZ --status auto --description "candidate summary"
```

3. The CLI marks the run `completed` once the rounds target or stop rule is met (or `early_exit` on stall), and `allocate` refuses after that. Check `stop_reason` in the run state.

4. When the run ends, merge the best candidate back and clean up. `--merge` squash-merges into the current checkout and leaves it staged for review:

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py finalize --run-id 20261016T180208Z-index-html --merge
```
