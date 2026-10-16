# EAU GEO instance

This instance applies the `geo-fuzzy` knowledge map, discovery probes, and metric-v2 matrix to <https://eau-meta-agent.github.io/>.

The four `gpt-codex-search` records migrate the saved 2026-10-16 observations from the EAU repository. They record project-site discovery as false because the returned source URLs contained the arXiv paper but not the project domain. They do not reinterpret paper retrieval as project-page exposure.

```bash
python3 scripts/geo_eval.py validate --map geo/instances/eau/map.json
python3 scripts/geo_eval.py matrix \
  --map geo/instances/eau/map.json \
  --site /workspace/eau-geo-benchmark-followup \
  --probes geo/instances/eau/probes.jsonl --no-llm
python3 scripts/geo_eval.py discovery \
  --map geo/instances/eau/map.json \
  --probes geo/instances/eau/probes.jsonl
```

Historical R0–R13 run directories contain actual GPT web, Codex search, Tavily,
and Exa observations. Keys are supplied only at runtime; never store them here.

R12 was measured at 6/60 citation cells versus the best R9's 8/60,
so it was discarded for selection. It has since been superseded by R13. See its
[live report](runs/round-12-homepage-descriptive-h1/r12-live/REPORT.md).
[R13](runs/round-13-static-component-reference/README.md) is now live and measured:
7/60 citation cells, all 60 valid; composite 30.14; explicit project URLs 4/60.
It was discarded against R9's 8/60 and remains deployed without an automatic
rollback. Its full outer evidence is in the [live report](runs/round-13-static-component-reference/r13-live/REPORT.md).

[R14](runs/round-14-static-second-backbone-evidence/README.md) is prepared but
unpublished and unmeasured. It adds a separately labelled static reference for
the existing Qwen2.5-7B-Instruct result rows on the best observed R9 seed.
All 27 local checks passed; no inner score or new outer observation exists.

## Cross-module candidate ledger

From R8 onward, consult [`candidate-pool.json`](candidate-pool.json) before
selecting an intervention. It records the module inventory, historical candidate
commits and evidence, explicit combination parents, pending proposals, and the
currently selected candidate. Each round preserves its before/after ledger
snapshot in its own run directory.

The agent maintains this instance-specific ledger when starting and recording
rounds. It is not a background scheduler or an automatic historical-candidate
recombination feature in the wrapper core. `discard` does not remove an old
candidate from consideration for a later combination test.

Selection is outer-only from R6 onward: use the frozen 15-query × four-engine
project-domain citation rate, with complete valid coverage required for automatic
ranking. Keep indexing time, tool failures, explicit URL evidence, and secondary
metrics separate. Historical cumulative rounds do not isolate module effects;
do not add their old scores to predict a combination. Never score unpublished
candidate trees as if their pages had been retrieved from production.
