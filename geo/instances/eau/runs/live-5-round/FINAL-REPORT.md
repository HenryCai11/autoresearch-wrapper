# EAU five-round GEO experiment — final report

## Decision rule

The local inner score is a deployment-readiness proxy. It checks site coverage, snippets, structured data, crawler files, metadata, and guardrails. It does not certify retrieval or citation lift. Live outer observations are the promotion criterion. Tool failures are reported separately from valid-response content metrics.

## Results

| Round | Intervention | Inner | Outer, all scheduled | Outer, valid responses | Answer success | Decision |
|---:|---|---:|---:|---:|---:|---|
| 0 | Pre-GEO baseline | 43.43 | 27.97 | 30.52 | 91.67% | baseline |
| 1 | Machine-readable identity | 74.43 | 28.08 | 31.20 | 90.00% | kept |
| 2 | Capability landing page | 86.83 | **28.25** | 31.39 | 90.00% | best all-cell checkpoint |
| 3 | Research-context page | 92.33 | 27.50 | 31.73 | 86.67% | no demonstrated lift |
| 4 | Bibliographic entity graph | 99.00 | 25.42 | 30.50 | 83.33% | inconclusive |
| 5 | GitHub authority bridge | 99.00 | 25.50 | 28.33 | 90.00% | small paired lift; not yet robust |

## What the experiment shows

1. Inner readiness rose from 43.43 to 99.00, while live exposure did not rise with it. On-site completeness is therefore a useful gate and a poor final objective.
2. The highest all-cell outer score was Round 2 at 28.25. Its gain over baseline was only 0.28 points, below a robust claim of causal lift for this sample size.
3. Rounds 3–5 did not produce a demonstrated live-search improvement at immediate post-deployment measurement time.
4. The failed Round 5 Codex run returned 0/15 and was discarded. The bounded retest returned 11/15. Across the 46 query-engine cells that returned in both R4 and R5, the score changed from 28.70 to 29.02 (+0.33), a small positive delta that is not yet robust.
5. GitHub and new project pages may require recrawling before they can affect retrieval. These T+0 observations should be followed by the same frozen query set after indexing.

## Codex probe incident

Five Codex CLI processes were initially started concurrently with a 60-second per-query timeout. The CLI reported model-list refresh timeouts, and all 15 queries were recorded empty. A single diagnostic query succeeded in 44 seconds. The bounded retest used two workers, low reasoning effort, and 90 seconds per query: 11/15 returned and four timed out. The probe now records per-query logs, elapsed time, status, and exit code.

## Artifacts

- `plot-data.csv`: plotting table for all rounds
- `timing.csv`: measured wall-clock interval and event count per round
- `visualization/eau-geo-autoresearch-frontier.png`: candidate scores plus the non-decreasing best-so-far keep/discard frontier
- `visualization/eau-geo-score-curve.png`: final score, temporal frontier, and decision-tree figure
- `visualization/eau-geo-pareto-frontier.png`: inner/outer Pareto frontier
- `visualization/eau-geo-optimization-loop.mp4`: stepwise animation
- `visualization/score-curve-data.csv`: exact values used by the figure
- each `round-*` directory: raw answers, normalized probes, search matrix, summaries, changes, commits, and timestamped tool events
