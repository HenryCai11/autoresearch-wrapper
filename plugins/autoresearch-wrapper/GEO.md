# GEO profile for websites

The GEO commands extend this wrapper's existing worktree loop. They address three separate questions:

1. `geo-graph` discovers files, HTML metadata, individual `<section id="...">` nodes, assets, external sources, and per-platform retrieval/answer outcomes. Local nodes include SHA-256 content fingerprints, so a text edit remains visible even when the graph topology is unchanged. Edges state dependencies, not proven causal effects.
2. `geo-apply` previews or applies an operation manifest against named graph nodes. `edit`, `add_after`, `move_after`, and `remove` target HTML sections; `replace_text` targets text files. `--apply` is restricted to a Git worktree. Run it inside a candidate allocated by the wrapper; `evaluate` snapshots and measures that candidate.
3. `geo-prioritize` reads **actual returned source URLs** from a saved search-tool response and orders only visible source-to-missing-project entry points for the next test. It does not use hypothetical graph reach, hand-entered gap flags, or costs, and it cannot certify lift. If paired platform observations exist for a candidate, `geo-compare` separately checks weighted global effect and measured regressions. Unknown observations remain unknown.
4. `geo-explore` turns those observations into a query → returned source → intervention → graph node tree. It keeps interventions with no observed source in a separate unranked branch. Optional paired CSV results appear on their candidate branches; missing results display as unmeasured. `--html-out` writes a standalone HTML view with an SVG node-and-edge tree, click-to-expand branches, zoom/pan, and a detailed evidence list below.
5. `geo-decide` builds a **conditional decision tree**: each diamond asks a yes/no/unknown question, follows only the evidence-supported route, and ends at a concrete next test. An intervention may declare `link_state` as `present`, `absent`, or `unknown`; unknown is the default until the source page is independently inspected. `present` can describe a documented multi-hop path from the returned source to the target; use `link_evidence_url` for the page that actually contains the target link. `--svg-out` writes a standalone SVG with the current route highlighted. This is different from the component/evidence hierarchy produced by `geo-explore`.

The configuration below is an example, not a claim that any platform has been measured:

```json
{
  "site_url": "https://example.org/",
  "paper_url": "https://arxiv.org/abs/1234.56789",
  "platforms": {"ChatGPT Search": 0.5, "Doubao App": 0.25, "DeepSeek App": 0.25},
  "queries": [{"id": "Q1", "text": "Recent agent-environment co-evolution papers?"}],
  "interventions": [
    {"id": "readme_link", "nodes": ["file:README.md"], "cost": 1,
     "source_url": "https://github.com/example/repo", "candidate_id": "readme-link"}
  ]
}
```

Commands, from the target website repository:

```bash
WRAPPER=/path/to/autoresearch-wrapper/scripts/autoresearch_wrapper.py
python3 "$WRAPPER" geo-graph --repo . --config geo/config.json > geo/graph.json
python3 "$WRAPPER" geo-prioritize --repo . --config geo/config.json \
  --search-evidence geo/gpt-web-search-observations.json
python3 "$WRAPPER" geo-explore --repo . --config geo/config.json \
  --search-evidence geo/gpt-web-search-observations.json \
  --observations geo/pending_agent_observations.csv \
  --html-out geo/figures/geo-exploration-tree.html > geo/exploration-tree.json
python3 "$WRAPPER" geo-decide --repo . --config geo/config.json \
  --search-evidence geo/gpt-web-search-observations.json \
  --svg-out geo/figures/geo-decision-tree.svg > geo/decision-tree.json
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

## Observed search entry points

`geo-prioritize` requires a saved response from a real search tool, reduced to the source URLs that tool actually returned:

```json
{
  "tool": "GPT/Codex web search",
  "result_scope": "source URLs displayed in the tool response; not a top-10 rank",
  "observations": [
    {"query_id": "Q1", "result_urls": ["https://arxiv.org/abs/1234.56789"],
     "raw_file": "geo/evidence/query-q1.txt"}
  ]
}
```

Each intervention needs a `source_url`. The command counts queries where that source URL was returned and the project URL was absent. It uses no graph-reach count, hand-entered gap flag, cost estimate, or unseen platform. A high count says that the source is a visible place to test a link to the missing project page; it is **not** an estimate of lift. Keep the raw tool response and query settings for audit. `geo-compare` remains the separate route for paired before/after outcomes when real platform data becomes available.

For the explorer, interventions may also declare `change_kind` (`node` or `edge`), `local_state`, `hypothesis`, `owner`, `candidate_id`, and `candidate_arms` (a list of `{id,status,hypothesis}` proposals). These labels explain the proposed experiment; they do not enter the priority calculation. The tree shows graph-supported operations for each named node and expands candidate arms separately. External nodes list their manual operation and owner. If `--observations` is supplied, a candidate receives a global comparison only when at least one after row for that exact `candidate_id` has a measured metric. Otherwise it stays `unmeasured`.

## Global observation contract

`geo-compare` reads a CSV with `phase,provider,query,project_rank,paper_rank,project_cited,answer_accurate` and optional `candidate_id,target_mentioned`. The legacy `eau_mentioned` column is accepted. `phase` is `before` or `after`; rank `0` means absent from the inspected top ten, blank means unknown. Binary outcomes use `1`, `0`, or blank. Keep product names exact: a Codex web search result is not a ChatGPT Search App answer.

The default metric weights are project retrieval 0.30, project citation 0.35, target mention 0.15, paper retrieval 0.10, and answer accuracy 0.10. Platform weights and metric weights are explicit in the config. Comparison pairs the same platform, query, and metric before and after, averages repeat samples within each cell, and calculates a weighted change. The missing cells contribute an interval of possible change instead of an assumed zero. A candidate is certified only when coverage meets `min_comparison_coverage`, the lower bound of the global change is positive, and no observed platform falls below `max_platform_regression`. These are decision settings, not measurements.

For example, a Doubao gain and a larger DeepSeek loss produce a global regression and are not kept even when a local readiness score improved. Without DeepSeek observations, the result is `insufficient_evidence_or_regression`; the tool does not invent that platform's result. Collect independent runs from actual products and preserve full answers or source lists with timestamps. The wrapper never logs into ChatGPT, Doubao, DeepSeek, Claude, or Grok on its own.

`geo-score` is a ten-check, 100-point **local readiness proxy** used to drive cheap edit/measure loops. Its result must always be reported separately from `geo-compare` and real search exposure. After a local run, `finalize --merge` stages the best candidate for review; global evidence remains a separate gate before claiming effectiveness.
