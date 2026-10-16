# EAU five-round live GEO experiment

This directory is the append-only record for the sequential production experiment.
Each numbered directory represents one deployed state, not an unmerged local
candidate.

## Round layout

```text
round-N-name/
├── run.json                 # commit, deployment time, query-set hash, tool versions
├── offline-report.json      # metric-v2 report for the exact deployed tree
├── search-probes.jsonl      # raw answer/result record from every search engine
├── discovery.json           # normalized query × engine judgement
├── search-matrix.csv        # one row per query and engine
└── summary.json             # plotting-ready aggregate metrics
```

Round 0 is the restored pre-GEO production baseline. Rounds 1–5 are measured
only after their PR has merged and GitHub Pages serves the corresponding commit.
Existing files are never overwritten; a repeated measurement gets a timestamped
file and is referenced from `run.json`.

## Required plotting fields

- round and label
- production commit and deployed URL
- measured timestamp and recrawl age
- local metric, matrix-offline, and technical score
- per-engine found/probed counts
- per-tier exact/fuzzy/broad counts
- per-query found, rank, cited URL, attribution, and answer correctness

The final chart must keep offline structural scores and live discovery metrics on
separate axes.
