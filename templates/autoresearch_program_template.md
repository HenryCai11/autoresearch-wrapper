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
- Planning workspace: `$plans_root`
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

Edit inside the returned worktree, then evaluate and record:

```bash
python3 $script_path evaluate --run-id $run_id --candidate candidate-XYZ
python3 $script_path record --run-id $run_id --candidate candidate-XYZ --status auto --description "candidate summary"
```

3. Stop when the configured rounds or stop rule is satisfied.
