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

Historical R0–R19 run directories contain actual GPT web, Codex search, Tavily,
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

[R18](runs/round-18-alphaxiv-paper-routing/README.md) was published and measured:
**12/60 project-domain citation cells, all 60 valid; keep**, versus historical
R17's 10/60. It remains the best complete observed candidate and next selection
seed; R19 tied it and was not promoted.
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

[R19](runs/round-19-shared-entity-combination/README.md) is live and measured:
**12/60 project-domain citation cells, all 60 valid; discard** against historical
R18's 12/60 because keep requires strict improvement. Primary is 20.00/100 and
secondary legacy composite is 35.19, both tied with R18. The same twelve cells
are cited, with no gains/losses. GPT web / Codex / Tavily / Exa counts are
0 / 4 / 0 / 8; explicit project URL cells are 11/60 and support-page cells 5/60.
R18 remains best_observed; R19 stays live without automatic rollback.
See the [live report](runs/round-19-shared-entity-combination/r19-live/REPORT.md)
and [selection record](runs/round-19-shared-entity-combination/r19-live/best-observed-selection.json).

R19 replays the exact final R10 shared-paper JSON-LD scheme on R18 as a separate
combination with parents R18/R10, motivated by actual R18 support-page source
URLs. R10's original 6/60 discard remains unchanged; no parent scores were added
or averaged. A single immediate historical-control tie does not establish that
the metadata has no longer-term effect.

Only the four HTML JSON-LD blocks change. All non-JSON-LD bytes, visible text,
R17 method reference, R16 headings, result data and every user-required alphaXiv
destination remain unchanged. All 38 structural/factual checks passed; visible
homepage text remains 6103 characters. No inner score or browser test was run.
After explicit publication approval, all four changed served pages matched the
exact candidate before and after collection. The first served check found a
stale page and no searches began until all four matched. A record-script branch
label correction required no resampling; completed scoring/audit used the same
raw sixty responses. See its [parent replay record](runs/round-19-shared-entity-combination/combination-source.json),
[validation](runs/round-19-shared-entity-combination/validation.json) and
[live audit](runs/round-19-shared-entity-combination/r19-live/audit.json).

[R20](runs/round-20-descriptive-reference-headings/README.md) is prepared,
**not published or measured**. On best R18 it changes only two reference-page
H1 headings: method becomes “How EAU adapts the training system.” and context
becomes “EAU as an adaptive training system.” Both use existing site wording;
all paragraphs, metadata/JSON-LD, result data, citation fields and alphaXiv routes
remain unchanged versus R18. The method wording reuses an existing R16 H2 on a
different page, not its operation or score. All ten modules and thirteen prior
proposals were reviewed before selecting this two-heading bundle, motivated by
the actual method/context source URLs in R19's two fuzzy Exa cells.

All 36 structural/factual checks passed, with no inner score or browser test.
Homepage visible text stays 6103 characters. Both graph nodes are fingerprinted
assets without text operations, so the two exact edits used apply_patch in the
allocated worktree. The first validation stopped on a page-key error and was
corrected before committing; both attempts are archived. The metric guard
refuses to score unmeasured R20; the original R18 matrix still replays 12/60.
See its [validation](runs/round-20-descriptive-reference-headings/validation.json)
and [audit](runs/round-20-descriptive-reference-headings/audit.json).

Production stays R19. Since R20 starts from R18 rather than tied/discarded R19,
a future approved deployment differs from current production in four HTML files:
restore the R18 metadata, plus the two new H1s. Both the two-file seed diff and
four-file production diff are archived. Recheck then-current main and verify
the complete tree/all four served files before and after any real collection.
Publication and the frozen 60-cell external evaluation await explicit approval.

All 20 R0–R19 observations and fourteen proposals remain; all thirteen older
proposals and best_observed R18 are unchanged. Only R20 and the external-authority
proposal are unmeasured. Prior candidates remain available
for combinations; their scores are never added to predict a bundle. Immediate
historical-control samples do not establish causal contribution or exclude
stale indexing. No automatic follow-up is scheduled.

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
