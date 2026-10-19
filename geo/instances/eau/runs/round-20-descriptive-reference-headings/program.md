# Autoresearch Run: 20261019T171243Z-method-html

Target repo: `/scratch/henrycai/eau-r20-20261019`
Target part: `method.html`
Discovery status: `probably optimizable`
Suggested metric from scan: `unknown`

## Locked config

- Metric preset: `none`
- Metric: `live_project_citation_rate`
- Goal: `maximize`
- Metric command:

```bash
python3 /scratch/henrycai/geo-runs/eau-r20-20261019/outer_metric.py
```

- Metric regex: `METRIC\s*=\s*(?P<value>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)`
- Execution mode: `sequential`
- Rounds: `1`
- Stop rule: `none`
- Parallelism: `1`

## State

- Canonical JSON: `/scratch/henrycai/eau-r20-20261019/.autoresearch-wrapper/state.json`
- Human summary: `/scratch/henrycai/eau-r20-20261019/.autoresearch-wrapper/STATUS.md`
- Run directory: `/scratch/henrycai/eau-r20-20261019/.autoresearch-wrapper/runs/20261019T171243Z-method-html`
- Seed worktree: `/scratch/henrycai/eau-r20-20261019.autoresearch-worktrees/20261019T171243Z-method-html/seed`

## Dependency Neighborhood

- Direct dependencies: `index.html`, `paper.html`, `research-context.html`, `styles.css`
- Dependents: `index.html`, `paper.html`, `research-context.html`
- Unresolved dependencies: none

## Rules

1. Do not optimize in the primary checkout if a worktree can be used.
2. Keep changes focused on `method.html` and its visible dependency neighborhood unless the metric harness requires a small supporting edit.
3. Record every evaluation and keep or discard decision through the helper CLI.
4. Treat the configured metric as the decision metric unless the user changes the run config.

## Loop

1. Evaluate the baseline:

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py evaluate --run-id 20261019T171243Z-method-html --candidate seed
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py record --run-id 20261019T171243Z-method-html --candidate seed --status auto --description "baseline"
```

2. For each new experiment:

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py allocate --run-id 20261019T171243Z-method-html
```

Edit inside the returned worktree, then evaluate and record. `evaluate` commits any pending edits to the candidate branch before measuring (respecting `.gitignore`), and a `keep` makes that branch the base for the next `allocate`, so improvements compound. Do not edit the worktree between `evaluate` and `record`.

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py evaluate --run-id 20261019T171243Z-method-html --candidate candidate-XYZ
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py record --run-id 20261019T171243Z-method-html --candidate candidate-XYZ --status auto --description "candidate summary"
```

3. The CLI marks the run `completed` once the rounds target or stop rule is met (or `early_exit` on stall), and `allocate` refuses after that. Check `stop_reason` in the run state.

4. When the run ends, merge the best candidate back and clean up. `--merge` squash-merges into the current checkout and leaves it staged for review:

```bash
python3 /project/aip-xiye17/henrycai/autoresearch-wrapper/scripts/autoresearch_wrapper.py finalize --run-id 20261019T171243Z-method-html --merge
```
