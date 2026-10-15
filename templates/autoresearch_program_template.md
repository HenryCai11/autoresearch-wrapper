# Autoresearch Run: $run_id

Target repo: `$repo_root`
Target part: `$part_id`
Discovery status: `$status`
Suggested metric from scan: `$suggested_metric`

## Locked config

- Metric preset: `$metric_preset`
- Metric: `$metric_name`
- Goal: `$metric_goal`
- Metric command:

```bash
$metric_command
```

- Metric regex: `$metric_regex`
- Execution mode: `$execution_mode`
- Rounds: `$rounds`
- Stop rule: `$stop_rule`
- Parallelism: `$parallelism`

## State

- Canonical JSON: `$state_json`
- Human summary: `$status_md`
- Run directory: `$run_dir`
- Seed worktree: `$seed_worktree`

## Dependency Neighborhood

- Direct dependencies: $direct_dependencies
- Dependents: $dependents
- Unresolved dependencies: $unresolved_dependencies

## Rules

1. Do not optimize in the primary checkout if a worktree can be used.
2. Keep changes focused on `$part_id` and its visible dependency neighborhood unless the metric harness requires a small supporting edit.
3. Record every evaluation and keep or discard decision through the helper CLI.
4. Treat the configured metric as the decision metric unless the user changes the run config.

## Loop

1. Evaluate the baseline:

```bash
python3 $script_path evaluate --run-id $run_id --candidate seed
python3 $script_path record --run-id $run_id --candidate seed --status auto --description "baseline"
```

2. For each new experiment:

```bash
python3 $script_path allocate --run-id $run_id
```

Edit inside the returned worktree, then evaluate and record. `evaluate` commits any pending edits to the candidate branch before measuring (respecting `.gitignore`), and a `keep` makes that branch the base for the next `allocate`, so improvements compound. Do not edit the worktree between `evaluate` and `record`.

```bash
python3 $script_path evaluate --run-id $run_id --candidate candidate-XYZ
python3 $script_path record --run-id $run_id --candidate candidate-XYZ --status auto --description "candidate summary"
```

3. The CLI marks the run `completed` once the rounds target or stop rule is met (or `early_exit` on stall), and `allocate` refuses after that. Check `stop_reason` in the run state.

4. When the run ends, merge the best candidate back and clean up. `--merge` squash-merges into the current checkout and leaves it staged for review:

```bash
python3 $script_path finalize --run-id $run_id --merge
```
