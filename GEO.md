# GEO profile for websites

The GEO commands extend this wrapper's existing worktree loop. They address three separate questions:

1. `geo-graph` discovers files, HTML metadata, individual `<section id="...">` nodes, assets, external sources, and per-platform retrieval/answer outcomes. Edges state dependencies, not proven causal effects.
2. `geo-apply` previews or applies an operation manifest against named graph nodes. `edit`, `add_after`, `move_after`, and `remove` target HTML sections; `replace_text` targets text files. `--apply` is restricted to a Git worktree. Run it inside a candidate allocated by the wrapper; `evaluate` snapshots and measures that candidate.
3. `geo-prioritize` orders open interventions by graph reach and cost as **hypotheses**. If paired platform observations exist for a candidate, `geo-compare` checks the weighted global effect and measured regressions. Unknown observations remain unknown. A local score cannot certify search exposure.

The configuration below is an example, not a claim that any platform has been measured:

```json
{
  "site_url": "https://example.org/",
  "paper_url": "https://arxiv.org/abs/1234.56789",
  "platforms": {"ChatGPT Search": 0.5, "Doubao App": 0.25, "DeepSeek App": 0.25},
  "queries": [{"id": "Q1", "text": "Recent agent-environment co-evolution papers?"}],
  "interventions": [
    {"id": "readme_link", "nodes": ["file:README.md"], "cost": 1,
     "current_gap": true, "candidate_id": "readme-link"}
  ]
}
```

Commands, from the target website repository:

```bash
WRAPPER=/path/to/autoresearch-wrapper/scripts/autoresearch_wrapper.py
python3 "$WRAPPER" geo-graph --repo . --config geo/config.json > geo/graph.json
python3 "$WRAPPER" geo-prioritize --repo . --config geo/config.json
python3 "$WRAPPER" geo-score --repo . --config geo/config.json
python3 "$WRAPPER" scan --repo . --no-interactive
python3 "$WRAPPER" configure --repo . --part README.md --metric geo_readiness \
  --metric-goal maximize --metric-command "python3 $WRAPPER geo-score --repo . --config geo/config.json" \
  --mode sequential --rounds 2 --no-interactive
python3 "$WRAPPER" run --repo . --part README.md --no-interactive
python3 "$WRAPPER" evaluate --repo . --candidate seed
python3 "$WRAPPER" record --repo . --candidate seed --status auto --description baseline
python3 "$WRAPPER" allocate --repo .
# In the allocated candidate worktree:
python3 "$WRAPPER" geo-apply --repo . --config geo/config.json --operations geo/operations/change.json
python3 "$WRAPPER" geo-apply --repo . --config geo/config.json --operations geo/operations/change.json --apply
# Back in the run checkout: evaluate and record the candidate.
python3 "$WRAPPER" evaluate --repo . --candidate candidate-001
python3 "$WRAPPER" record --repo . --candidate candidate-001 --status auto --description 'README link'
```

An operation manifest looks like:

```json
{"operations": [{"op": "replace_text", "node": "file:README.md",
                 "before": "Old text", "after": "New text"}]}
```

For a section, use `{"op":"edit","node":"section:overview","html":"<section id=\"overview\">...</section>"}`; `add_after` supplies a new section with a unique ID; `move_after` supplies `after_node`; `remove` deletes the section. Validate the resulting page before recording the candidate.

## Global observation contract

`geo-compare` reads a CSV with `phase,provider,query,project_rank,paper_rank,project_cited,answer_accurate` and optional `candidate_id,target_mentioned`. The legacy `eau_mentioned` column is accepted. `phase` is `before` or `after`; rank `0` means absent from the inspected top ten, blank means unknown. Binary outcomes use `1`, `0`, or blank. Keep product names exact: a Codex web search result is not a ChatGPT Search App answer.

The default metric weights are project retrieval 0.30, project citation 0.35, target mention 0.15, paper retrieval 0.10, and answer accuracy 0.10. Platform weights and metric weights are explicit in the config. Comparison pairs the same platform, query, and metric before and after, averages repeat samples within each cell, and calculates a weighted change. The missing cells contribute an interval of possible change instead of an assumed zero. A candidate is certified only when coverage meets `min_comparison_coverage`, the lower bound of the global change is positive, and no observed platform falls below `max_platform_regression`. These are decision settings, not measurements.

For example, a Doubao gain and a larger DeepSeek loss produce a global regression and are not kept even when a local readiness score improved. Without DeepSeek observations, the result is `insufficient_evidence_or_regression`; the tool does not invent that platform's result. Collect independent runs from actual products and preserve full answers or source lists with timestamps. The wrapper never logs into ChatGPT, Doubao, DeepSeek, Claude, or Grok on its own.

`geo-score` is a ten-check, 100-point **local readiness proxy** used to drive cheap edit/measure loops. Its result must always be reported separately from `geo-compare` and real search exposure. After a local run, `finalize --merge` stages the best candidate for review; global evidence remains a separate gate before claiming effectiveness.
