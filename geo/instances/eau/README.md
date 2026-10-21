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

Historical R0–R21 run directories contain actual GPT web, Codex search, Tavily,
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
seed; R19–R21 tied its primary metric and were not promoted.
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

[R19](runs/round-19-shared-entity-combination/README.md) was published and measured:
**12/60 project-domain citation cells, all 60 valid; discard** against historical
R18's 12/60 because keep requires strict improvement. Primary is 20.00/100 and
secondary legacy composite is 35.19, both tied with R18. The same twelve cells
are cited, with no gains/losses. GPT web / Codex / Tavily / Exa counts are
0 / 4 / 0 / 8; explicit project URL cells are 11/60 and support-page cells 5/60.
R18 remains best_observed. R19 was not automatically rolled back after selection;
it has now been superseded by explicitly approved R20.
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

[R20](runs/round-20-descriptive-reference-headings/README.md) was published and measured:
**12/60 project-domain citation cells, all 60 valid; discard** against historical
R18's 12/60 under the strict-improvement rule. Primary stays 20.00/100;
secondary report-only composite is 34.83 versus R18's 35.19. The same twelve
citation cells remain, with no gains/losses. GPT web / Codex / Tavily / Exa
counts are 0 / 4 / 0 / 8; exact / fuzzy / broad counts are 9 / 2 / 1 (each /20).
Explicit project URL cells are 11/60; support-page URL cells are 5/60.
R18 remains best_observed. R20 was not automatically rolled back after selection;
it has now been superseded by explicitly approved R21.
See the [live report](runs/round-20-descriptive-reference-headings/r20-live/REPORT.md),
[selection](runs/round-20-descriptive-reference-headings/r20-live/best-observed-selection.json)
and [live audit](runs/round-20-descriptive-reference-headings/r20-live/audit.json).

On best R18, R20 changes only two reference-page
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
corrected before committing; both attempts are archived. Before publication the
metric guard refused to score unmeasured R20. After real collection, the original
R18 matrix and new R20 matrix independently replay 12/60; their distinct hashes
and raw results remain preserved.
See its [validation](runs/round-20-descriptive-reference-headings/validation.json)
and [audit](runs/round-20-descriptive-reference-headings/audit.json).

With explicit publication approval, R20 was applied on then-current R19 main as
an isolated deployment branch. Its production diff spans four HTML files:
restore R18 metadata, plus the two new H1s. Both the two-file seed diff and
four-file production diff are archived. The complete candidate/production tree
and all four served resources matched before and after the real 60-cell collection.
The first served check saw old bytes; no searches started until all four matched.

Initial compute-node attempts hit thirty API proxy CONNECT failures and fifteen
Codex missing-Node startup failures; these are retained separately and excluded
from the scored matrix. Loading the verified Node module did not resolve the
compute proxy restriction. Network-only curl/jq and the same installed native
Codex binary acquired the valid replies on the internet-connected login node;
no Python, Node, compilation or local inference ran there. Normalization,
scoring, wrapper CLI and audits used Slurm. No successful response was retried,
including the fifteen GPT samples collected before network recovery.

[R21](runs/round-21-descriptive-static-evidence-combination/README.md) is live and measured:
**12/60 project-domain citation cells, all 60 valid; discard** against original
historical R18's 12/60 under the strict-improvement rule. Primary is 20.00/100.
Secondary report-only composite is 35.89 versus R18's 35.19 and R20's 34.83;
it does not determine keep/discard. GPT web / Codex / Tavily / Exa citation
counts remain 0 / 4 / 0 / 8, but the citation cells are not identical:
one fuzzy Codex cell is gained and one exact Codex cell lost versus R18.
Exact / fuzzy / broad counts are 8 / 3 / 1 (each /20), versus 9 / 2 / 1.
The gained query is “user-centric agents co-evolve environment and user simulator”;
the lost query is “EAU arXiv 2610.16523”. Explicit project URL cells are 11/60
and support-page URL cells 5/60. R18 remains best_observed; R21 remains live
without automatic rollback. See the
[live report](runs/round-21-descriptive-static-evidence-combination/r21-live/REPORT.md),
[selection](runs/round-21-descriptive-static-evidence-combination/r21-live/best-observed-selection.json)
and [live audit](runs/round-21-descriptive-static-evidence-combination/r21-live/audit.json).

Parents are R18/R14: replay the exact retained
R14 second-backbone table on best R18, under its kept R16 results heading and
alongside the R17 static method reference. One insertion in index.html exposes
nine Qwen2.5-7B-Instruct method rows and 36 already-reported values. The original
Qwen3 display, default selection, switch, all other homepage bytes, reference
pages, metadata/JSON-LD and alphaXiv routes are unchanged versus R18.

All 39 structural/factual checks passed; visible homepage text is 6103 → 6676
characters, under the locked 9000 limit. Independent parsing verifies both
backbone tables against unchanged script.js. Existing geo-apply performs the
one supported file:index.html operation; preview/applied diffs and graph
fingerprints match the actual bytes. No inner score or browser test was run.
See its [validation](runs/round-21-descriptive-static-evidence-combination/validation.json)
and [audit](runs/round-21-descriptive-static-evidence-combination/audit.json).

All ten modules and fourteen older proposals were reviewed using complete R20
evidence. R20 returned the homepage URL in nine cells; broad citations were
1/20. This motivates a static-evidence test, not a predicted retrieval gain.
R14's original 5/60 discard and R15's 6/60 multi-bundle discard remain unchanged;
R21 is not a replay of R15's H1/method/table bundle. No old scores are added.
See its [exact parent provenance](runs/round-21-descriptive-static-evidence-combination/combination-source.json).

After explicit publication approval, an isolated branch on then-current R20
main applied the exact R21 tree. Three pages differ from R20: add the table
to index.html and restore R18 method/context H1s, without inheriting R20's
discarded heading bundle. Both the one-file seed diff and three-file production
diff are archived. The complete candidate/production tree and all three changed
served resources matched before and after the completed 60-cell collection.
The first served check saw old content; no searches began until all three matched.

All sixty first-pass samples were valid, with no successful response resampled.
Network-only curl/jq and the same preinstalled native Codex CLI acquired the
replies; all Python, normalization, scoring, wrapper CLI and audits used Slurm.
No Python, Node, compilation or local inference ran on the login node. The
already documented compute proxy restriction was not bypassed or retried.
The immediate historical-control observation does not isolate the table's
causal contribution or rule out search variation/stale indexing.

All 22 R0–R21 observations and fifteen proposals remain; all fourteen older
proposals and best_observed R18 are unchanged. Only the external-authority
proposal is unmeasured. Prior candidates remain available
for combinations; their scores are never added to predict a bundle. Immediate
historical-control samples do not establish causal contribution or exclude
stale indexing. No automatic follow-up is scheduled.

[R22](runs/round-22-paper-project-entry/README.md) is prepared locally,
**not published or measured**, with a user-requested
[code-release revision](runs/round-22-paper-project-entry/code-release/README.md).
Latest candidate is `fae44609023fddc240a13502f77abcfcd925c95d`, not the original
`aa3c0ea` snapshot. It retains the R18 seed and original paper-paragraph move,
then enables two visible static Code links to
https://github.com/StringNLPLAB/meta-agent, sets codeUrl, removes outdated
coming-soon labels and adds the Code resource to README and llms.txt. The exact
public repository was verified through GitHub's API; its code was not audited.

All 28 amendment checks passed; home visible text is 6055 characters under the
9000 cap. Original R22's 34-check snapshot, original commit, all 22 measured
historical records, fifteen other proposals and best R18 remain preserved.
The original experiment moved an already-present official-home paragraph into
the paper introduction, motivated by three actual R21 Exa paper-page sources.
The user-requested release is an additional bundle, so later historical-control
scores cannot isolate that relocation or the new code-link effect.

No inner score or browser execution. AlphaXiv routes and scholarly arXiv
identifiers remain unchanged; the metric guard refuses the unpublished tree.
Follow CURRENT.json and the revised
[change record](runs/round-22-paper-project-entry/code-release/change.json),
[validation](runs/round-22-paper-project-entry/code-release/validation.json),
[production diff](runs/round-22-paper-project-entry/code-release/production-to-candidate.patch)
and [audit](runs/round-22-paper-project-entry/code-release/audit.json).
The original audit is verifiable with README/CURRENT preimages; all other
original hash-covered files remain untouched.

Production remains R21, unchanged. A separately approved R22 publication now
changes FIVE resources relative to R21: README.md, index.html, llms.txt,
paper.html and site-config.js. The index still restores R18 by removing R21's
unkept table. Verify all five served resources, not the previous two, alongside
the full tree. Sixteen proposals remain; R22 and external-authority are
unmeasured. Keep still requires all sixty valid and strictly more than 12/60
citations; ties discard, composite report-only. No new searches, publication,
rollback, cleanup or automatic next round ran during this amendment.

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
