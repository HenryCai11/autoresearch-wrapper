# EAU R14 — static second-backbone evidence

Current status: **published and measured; discard against R9**.

R14 is live as `c762ead8370159e102c5ea11b1a43b944c71d1bf`. All 60 outer
responses were valid. Primary project-domain citations: R9 **8/60 → R14 5/60**;
secondary composite: **30.25 → 28.89**. Explicit project URL cells: **3/60**;
support-page URL cells: **0/60**. No inner score was computed and no automatic
rollback was performed. This immediate single sample is not a causal estimate.

See [the live report](r14-live/REPORT.md), [current state](CURRENT.json), and
[deployment and collection timing proof](r14-live/deployment.json).
The complete 60-cell evidence and 15-entry R0–R14 history passed the live audit;
all eight proposals remain. Only the external-authority proposal is unmeasured.

The rest of this document is the historical preparation snapshot. Its original
bytes are preserved in `r14-live/pre-live-README.md` for the preparation audit;
statements below about awaiting approval or current production refer to that time.

## Preparation snapshot

- Wrapper run: 20261016T180208Z-index-html; sequential, one candidate, index.html target.
- Existing pool proposal: static-second-backbone-evidence.
- Candidate commit: fd5681ce5d3146f3ec42081fef3d89ee0f0f5e7a.
- Candidate tree: 1d987f64d620a79a9db3c354c50f89d4ce8ae164.
- Selection seed: R9 52dee0ba78885b9a3028760ba8d9cfc749a6c2e7, best preserved complete
  outer measurement: 8/60 citations, composite 30.25.
- Current production remains R13 c6fa063d86be9e1861b0d79c6d2f7e2c27e3c1aa,
  7/60 citations, composite 30.14, discard. It is not the keep threshold.
- No new R14 search response or inner score exists.

## One coherent change

Add a separately captioned Qwen2.5-7B-Instruct reference table in the existing
results section. It is a default-open semantic details/table block, so its
content does not require JavaScript or a model-switch click. Its nine method
rows and 36 values are copied from the existing results.qwen25 object in
script.js, preserving three-decimal precision, column order and model label.
No new results, relative gains, tau2 numbers or research claims are introduced.

The existing Qwen3 charts/table, switch buttons, default selection, original
noscript fallback and all other homepage bytes remain. The existing fallback
still describes the main default Qwen3 display; the new reference is separately
captioned. The new table uses unique IDs that are not renderer targets; the
switch above continues to control the main charts and main comparison table.
All scripts, styles, metadata, links and other pages are unchanged. Existing
table-scroll and result-table-details styling is reused.

The latest R13 measurement returned four explicit homepage URL cells and no
support-page URLs. This locates an observed entry surface, not a prediction
that another table will improve rankings. R9's kept static default results
provide a reusable implementation parent; its old score is not added to
anything to predict this candidate's score.

## Cross-module and retained-candidate review

module-review.json reviews all ten inventory modules, including reference-page
routing and the author-owned external paper entry. All 14 R0–R13 history entries
and all eight proposals remain. Seven non-selected proposal entries are
unchanged; the original queued proposal is retained inside the selected entry.
The external backlink remains unknown and any edit needs separate authority.

R10 scholarly metadata, R11 overview restoration, R12 H1 and R13 static component
description candidates remain available for later combinations but are not
silently inherited. R14 starts from the best observed R9 tree, retaining its R7
overview, R8 reference routes and R9 default static results. Relative to current
R13 production, index.html both adds this table and removes R13's unkept static
component block. That full difference is in production-to-candidate.patch.

## Validation and outer gate

All 27 local checks passed. Homepage visible text:
5436 → 6009
characters, below the unchanged 9000 limit. Independent HTML
parsing verifies all nine table rows and 36 values against the existing JS, and
separately verifies the default Qwen3 rows. Exact insertion scope, labels, IDs,
links, no hidden text, unchanged schema/scripts/styles and frozen
map/query/judge/normalizer hashes were checked. No inner score was computed.

No browser or visual test was performed. Preserved markup/selectors and reused
styles are structural checks, not proof of rendered behavior or layout.

The exact-tree metric guard refuses to score this unpublished candidate.
Separate explicit R14 publication approval is required. After approval, apply
the exact candidate index.html in an isolated deploy branch based on current
main and verify the entire tree. A blind merge into R13 would retain the wrong
component block. Reconcile concurrent teammate changes before proceeding.
Verify served bytes before collection and after all requests have completed.

Use the same 15 queries × GPT web / Codex / Tavily / Exa settings, with no memory
model dimension. Require 60 valid cells and strictly more than R9's 8/60
project-domain citation cells for keep; ties discard. The judge counts bare
domain occurrences, so explicit URLs must be reported separately. The control
is historical, not freshly collected or simultaneous. One immediate sample
cannot establish causality or exclude stale search indexes.

Preparation and metric replay used Slurm with one CPU and 1 GB. No site push,
publication, rollback, branch pruning, candidate deletion, R14 paid searches or
future follow-up was performed. The patch, source data and history live in this
durable instance archive, not only in temporary scratch worktrees.
