# GEO with autoresearch-wrapper

Generative engine optimization: make a website easier for LLMs and AI search to find, understand, and cite, using the autoresearch loop. The workflow is the `geo-autoresearch` skill (`skills/geo-autoresearch/SKILL.md`).

| Path | What it is |
| --- | --- |
| `geo_eval/` (repo root) | Standalone toolkit: knowledge map, site reader, eval matrix, technical checks, LLM comprehension test, search-probe log, traffic snapshots. Standard library only. |
| `geo/scripts/` | Glue: stage/install Jekyll gems, build a site, `score.sh` (the loop's metric command), `fetch_goatcounter.sh`. |
| `geo/instances/<name>/` | One site's data and config only: `map.json` (knowledge map), `instance.env`, `probes.jsonl`, `ood.jsonl`. |

## The eval matrix

One row per knowledge-map keyword (hop 0 = core identity, hop 1 = papers/areas/organisations, hop 2 = topics), one column per signal:

| column | the keyword... | measured |
| --- | --- | --- |
| `site` | is stated in visible text (homepage for hop 0) | every round |
| `schema` | appears in JSON-LD structured data | every round |
| `llms` | appears in `llms.txt` | every round |
| `llm` | is answered correctly by a model reading only the site | every round (Aleph or any OpenAI-compatible endpoint) |
| `search` | surfaces the entity when searched | after deploys, via recorded probes |

`METRIC = 0.5 × offline + 0.5 × LLM`, where offline is 60% matrix columns (`site`, `schema`, `llms`) and 40% site-wide technical checks (structured data, crawler files, metadata, hygiene). Weights can be overridden with `"scoring"` in the map. Guardrails (map terms only in hidden text, homepage padding past `limits.max_visible_chars`) make the score exit 3 with no METRIC, so the candidate is recorded as a crash.

`search` and real traffic (`ood`) lag by days and are noisy; they confirm gains out of distribution and never drive a round.

## The discovery matrix

The `search` column above is an average across engines. `geo_eval discovery` shows the full **query × engine** matrix: one cell per (query, engine), found or not and the rank of the entity's site. Every engine's answer is judged by the same rule (`geo_eval/discovery.py`): found if the answer cites the site, or names the entity with an attribution term (the affiliation) in the same sentence. Engines so far:

| engine | how | needs |
| --- | --- | --- |
| an agent's own web search tool | the agent searches, saves `{query, text}` answers, `probe-judge` | the agent |
| `codex-search` | `geo/scripts/probe_codex.sh` (Codex CLI `--search`, OpenAI web search) then `probe-judge` | a logged-in Codex CLI and internet |
| `memory:<model>` | `geo_eval probe-memory`: the model answers from memory, no web | any OpenAI-compatible endpoint (Aleph on Vulcan) |
| anything else | `probe-record` or `probe-judge` with your own answers | — |

## Quick start

```bash
python3 scripts/geo_eval.py validate --map geo/instances/<name>/map.json
geo/scripts/stage_gems.sh <site-repo>        # Jekyll sites, once, needs internet
sbatch ... geo/scripts/setup_jekyll.sh       # offline install on a compute node
cd <site-repo> && srun ... ../path/to/geo/scripts/score.sh geo/instances/<name>
```
