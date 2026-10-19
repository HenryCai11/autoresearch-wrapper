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

Historical R0–R18 run directories contain actual GPT web, Codex search, Tavily,
and Exa observations. Keys are supplied only at runtime; never store them here.

R12 was measured at 6/60 citation cells versus the best R9's 8/60,
so it was discarded for selection. It has since been superseded by R13. See its
[live report](runs/round-12-homepage-descriptive-h1/r12-live/REPORT.md).
[R13](runs/round-13-static-component-reference/README.md) was measured at:
7/60 citation cells, all 60 valid; composite 30.14; explicit project URLs 4/60.
It was discarded against R9's 8/60 and has since been superseded by R14.
Its full outer evidence is in the [live report](runs/round-13-static-component-reference/r13-live/REPORT.md).

[R14](runs/round-14-static-second-backbone-evidence/README.md) was measured at
5/60 citation cells, all 60 valid; composite 28.89; explicit project URLs 3/60.
It was discarded against R9's 8/60 and has been superseded by R15. It adds a
separately labelled static reference for the existing Qwen2.5-7B-Instruct rows
on the R9 seed. No inner score was computed.
See its [live report](runs/round-14-static-second-backbone-evidence/r14-live/REPORT.md).

[R15](runs/round-15-static-entry-combination/README.md) was measured at:
6/60 citation cells, all 60 valid; composite 29.75; explicit project URLs 4/60.
It was discarded against R9's 8/60 and has since been superseded by R16.
It intentionally replays the retained R12 H1, R13 static method
descriptions and R14 second-backbone table together on R9. All 32 local checks
and the completed live audit passed. No inner score was computed.
See its [live report](runs/round-15-static-entry-combination/r15-live/REPORT.md).

[R16](runs/round-16-descriptive-section-headings/README.md) was measured at:
9/60 project-domain citation cells, all 60 valid; composite 31.86; explicit
project URLs 8/60. It was **kept** against historical R9's 8/60 and became the
R17 selection seed. It has since been superseded by R17; the R9 control and every
previous result remain preserved.
See its [live report](runs/round-16-descriptive-section-headings/r16-live/REPORT.md)
and [best-observed promotion](runs/round-16-descriptive-section-headings/r16-live/best-observed-promotion.json).

R16 changes only framework/results H2 text on R9, without adding factual claims,
data or content blocks. All 31 local checks and the live audit passed; no inner
score or browser/visual test was performed. Citation counts by GPT web / Codex /
Tavily / Exa are 0 / 3 / 0 / 6, so engines did not improve uniformly.

[R17](runs/round-17-descriptive-heading-static-method/README.md) is now live and measured:
10/60 project-domain citation cells, all 60 valid; composite 34.31; explicit
project URLs 9/60. It was **kept** against historical R16's 9/60 and became the
R18 selection seed. It has now been superseded by R18.
See its [live report](runs/round-17-descriptive-heading-static-method/r17-live/REPORT.md)
and [best-observed selection](runs/round-17-descriptive-heading-static-method/r17-live/best-observed-selection.json).

R17 keeps both R16 headings and replays the exact retained R13 static method
reference. All 31 local checks and the live audit passed; no inner score or
browser/visual test was performed. GPT web / Codex / Tavily / Exa citation counts
are 0 / 3 / 0 / 7. The additional cell is Exa's broad “editable training systems
for tool-using agents” query, with no lost citation cell versus R16. R17 fuzzy-tier
citations remained zero. The frozen judge includes bare project-domain mentions;
explicit source URLs are reported separately.

[R18](runs/round-18-alphaxiv-paper-routing/README.md) is live and measured:
**12/60 project-domain citation cells, all 60 valid; keep**, versus historical
R17's 10/60. It is the new best complete observed candidate and next seed.
Legacy composite is 35.19 versus 34.31; explicit project URLs are 11/60 and
explicit support-page URL cells are 5/60. GPT web / Codex / Tavily / Exa citation
counts are 0 / 4 / 0 / 8. Fuzzy-tier citations increased 0/20 → 2/20, while broad
citations fell 2/20 → 1/20; three citation cells were gained and one lost.
See the [live report](runs/round-18-alphaxiv-paper-routing/r18-live/REPORT.md)
and [best-observed selection](runs/round-18-alphaxiv-paper-routing/r18-live/best-observed-selection.json).

R18 routes the six HTML paper-reading anchors,
the README/llms.txt Paper entries and the paperUrl configuration to the verified
[alphaXiv EAU page](https://www.alphaxiv.org/abs/2610.16523): nine exact URL/label
replacements in seven files. arXiv identifiers, PDF metadata, JSON-LD identity,
CITATION.cff and BibTeX remain unchanged. This user-requested routing bundle is
the R18 intervention; no unrelated content optimization is mixed in.

R18 used exact R17 as its seed and historical 10/60 control. All seven changed
served resources matched the exact candidate before and after the completed
collection. All 36 local checks and the completed live audit passed; no inner
score or browser/visual test was performed. alphaXiv clicks and visits remain
unmeasured; do not infer traffic or causal GEO uplift from this matrix. Future
candidates must retain the user's alphaXiv reading routes and scholarly arXiv
references. See the [live audit](runs/round-18-alphaxiv-paper-routing/r18-live/audit.json).

All 19 R0–R18 observations and twelve proposals remain; all eleven older proposals
are unchanged. Only the external-authority proposal is unmeasured. Prior
candidates remain available for combinations; their scores
are never added to predict a bundle. Immediate historical-control samples do not
establish causal contribution or exclude stale indexing. No automatic follow-up
is scheduled.

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
