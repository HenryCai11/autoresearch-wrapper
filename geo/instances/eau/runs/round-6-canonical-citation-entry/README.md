# EAU R6: canonical citation entry (outer-only, awaiting deployment)

R5 has been pulled into `/project/aip-xiye17/henrycai/eau-meta-agent.github.io` at
`edec9373f0c5d4fcc0eae9308678c582fb719416`. The production homepage SHA-256 matches
that checkout. The R6 candidate is on the EAU repository's
[`codex/geo-live-round-6`](https://github.com/eau-meta-agent/eau-meta-agent.github.io/compare/main...codex/geo-live-round-6)
branch, commit `e277d44`.

R6 is **not deployed** and has **no measured outer result**. Candidate readiness
scores must not be used as evidence of retrieval or citation improvement.

## User-selected objective

From R6 onward, ignore the inner metric in candidate selection. The primary
metric is the project-domain citation rate over the same 15 queries and four
equally weighted engines. Rank, mention, correct attribution, and the previous
outer composite are secondary. Report tool failures separately; do not rank an
incomplete run automatically. Compare matched valid cells as well as scheduled
and valid-response aggregates.

The active wrapper run is `20261016T112235Z-index-html`, with metric
`live_project_citation_rate`. The seed was evaluated from real production
observations. The metric refuses to score a candidate tree without corresponding
live measurements. The earlier readiness-only snapshot is retained as history;
its tie/discard is superseded by the user's outer-only policy.

## Fresh R5 control, before any R6 deployment

Each engine returned 15/15 valid responses. These observations measure the
unchanged deployed R5, not an R6 intervention.

| Engine | Found | Project domain cited |
| --- | ---: | ---: |
| GPT web tool | 11/15 | 0/15 |
| Codex search CLI | 10/15 | 4/15 |
| Tavily basic, 10 results | 6/15 | 0/15 |
| Exa auto, 10 results with highlights | 12/15 | 3/15 |

Primary citation rate: **7/60 = 11.67%**. Legacy outer composite: **29.61**.
On the 43 cells valid in both the original R5 run and this repeat, the composite
changed from **25.81 to 26.05 (+0.23)**. The site did not change; this is a repeat
measurement, and tool/runtime settings and time differ from the original run.

## Candidate and evidence

The candidate changes only `index.html`: make title/Open Graph identity
consistent, describe the official project and paper identifier in the snippet,
and put an explicit project-domain link and arXiv identifier before the hero
heading. The hypothesis is that this makes the official project easier to
identify and cite after retrieval and recrawling. It remains untested.

The saved R5 source URLs also identify an externally controlled paper-link audit
as a possible next experiment. No paper submission or third-party source was
modified. `priorities.json` and `decision.json` preserve the evidence and unknowns.

`candidate.patch`, `operations.json`, graph snapshots, validation, and the
candidate commit are retained even if the experiment eventually fails. This
supports deliberate reuse and combination with future interventions; the wrapper
does not automatically search historical combinations.

## Next measurement

After approval and deployment of this candidate, verify the served version,
collect the frozen 15 queries across the same four engines, and write a new
measurement directory. Compare against `r5-control/` using the outer-only policy.
Preserve both the immediate measurement and any later recrawl measurement.

Raw control answers and per-query status are in `r5-control/`. Older R0–R5
artifacts in `live-5-round/` remain unchanged.
