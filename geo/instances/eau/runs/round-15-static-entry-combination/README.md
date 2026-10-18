# EAU R15 — retained static-entry combination

Current status: **measured and superseded by R16; discard against R9**.

R15 was published as `596ccda6c33a4bb2ea9cac3daa7d489e856f264d` and has since
been superseded by [R16](../round-16-descriptive-section-headings/README.md).
All 60 outer
responses were valid. Primary project-domain citations: R9 **8/60 → R15 6/60**
(13.33% → 10.00%); secondary composite: **30.25 → 29.75**.
Explicit project URL cells: **4/60**; support-page URL cells: **0/60**.
The frozen judge also counts bare project-domain occurrences as citations.
No inner score was computed. No automatic rollback was performed.

See [the live report](r15-live/REPORT.md), [current state](CURRENT.json), and
[deployment and collection timing proof](r15-live/deployment.json).
Both served checks matched the exact candidate; all collection timestamps
fell between them. The live audit passed complete-cell, archived-metric replay,
preparation-hash, parent-operation and history-retention checks.

All 16 R0–R15 history entries and nine proposals remain; all eight old proposals
are unchanged. The combination has its own measured observation. Only the
external-authority proposal remains unmeasured. R12/R13/R14 observations were
not added to predict R15, and this immediate sample against historical R9 does
not isolate any parent's causal contribution or exclude stale indexes.
No R15 follow-up was scheduled automatically. R16 has now superseded R15.

The rest of this document is the historical preparation snapshot. Its original
bytes are preserved in `r15-live/pre-live-README.md` for the preparation audit;
statements below about awaiting approval or current production refer to that time.
Root change.json, audit.json, results.tsv and program.md remain preparation
snapshots; the current measurement and wrapper record are under r15-live/.

## Preparation snapshot

Status: **validated local candidate; not published or measured**.

- Run: 20261017T090803Z-index-html; sequential, one index.html candidate.
- New pool proposal: static-entry-combination, explicitly unmeasured.
- Candidate: ca8936282e047ee302c315c3eecc016db45cd79b.
- Tree: 13982678cdeb9efc1bb4ea871f6f150a9a5f16ce.
- Seed: best complete historical R9 52dee0ba78885b9a3028760ba8d9cfc749a6c2e7,
  8/60 citations and composite 30.25; not newly collected or simultaneous.
- Production remains R14 c762ead8370159e102c5ea11b1a43b944c71d1bf,
  5/60 citations and composite 28.89, discard; not the selection threshold.

## What is being combined

R15 replays exactly three retained archived operations on R9:

| Historical candidate | Exact reused intervention |
| --- | --- |
| R12 | Existing EAU/co-evolution identity in the visible H1 |
| R13 | Static environment/agent descriptions and knob labels |
| R14 | Separately captioned, default-open Qwen2.5 result reference |

Each individual operation first reproduced its original parent's entire HTML
byte-for-byte from R9. Their original commit/tree IDs and operation hashes are
in combination-source.json, with copies under parents/. No content is newly
paraphrased or invented. This is an intentional new bundle, not a silent
inheritance of unkept deltas or an edit to the old candidates.

R12, R13 and R14 observed 6/60, 7/60 and 5/60 respectively and were discarded
against R9. Those are historical single samples of entire candidates, not
isolated component effects. They are not added, averaged or otherwise used to
predict the combination. R15 has no outer score. An eventual result would rank
this bundle only, not prove which component caused a gain or loss.

The hypothesis is initial-HTML completeness: existing identity, method
descriptions and evidence might interact differently when present together.
R14 returned three explicit homepage URL cells and no support-page URL cells;
that is source evidence, not a forecast of this bundle's lift.

## Scope and retained history

Only index.html differs from R9. The H1 exactly matches R12, the framework
section exactly matches R13, and the results section exactly matches R14.
Everything else remains on R9, including R7 overview, R8 reference routes,
metadata, all other pages, scripts and styles. Existing default result rows and
switch targets remain; the second-backbone table is not a renderer target.

Relative to current R14 production, its entire results section stays unchanged;
the H1 and component descriptions are the production delta. The full diff is
production-to-candidate.patch. No new facts, model values, metrics, gains,
affiliations or external links are introduced.

All 15 R0–R14 history entries and all eight old proposals are unchanged. A ninth
proposal records this combination separately. Both this proposal and the
external-authority proposal remain unmeasured. The external paper backlink state
is unknown; any edit requires separate author authority. module-review.json
covers all ten inventory modules. This ledger is agent-maintained instance data,
not an automatic global recombination scheduler in wrapper core.

## Validation and publication gate

All 32 structural/factual checks passed. Visible homepage:
5436 → 6651
characters, below the existing 9000 limit. Checks independently
validate component text and six knobs against JS, both nine-row result tables
against JS, exact parent fragments, all IDs/links, no hidden text, unchanged
schema/scripts/styles and frozen map/query/judge/normalizer hashes.
No inner score was computed. No browser/visual test was performed; rendered
layout and runtime behavior are not claimed as browser-tested.

The exact-tree metric guard rejects this unpublished combination. Separate
explicit R15 publication approval is required. Use an isolated deploy branch
based on current main, apply exact candidate index.html, verify the whole tree,
and reconcile any teammate changes. Verify served bytes before collection and
after all requests finish. Never score an unpublished tree as if it were live.

After approval, use the frozen 15 queries × GPT web / Codex / Tavily / Exa,
without a memory-model dimension. Require 60 valid cells and strictly more than
8/60 project-domain citation cells for keep; ties discard. The frozen judge also
counts bare-domain occurrences, so explicit URLs must be reported separately.
Historical controls and immediate samples cannot establish causality or exclude
indexing lag; no follow-up is scheduled automatically.

Preparation and replay used Slurm, one CPU and 1 GB. No site publication/push,
rollback, paid R15 searches, candidate deletion or branch pruning was performed.
The patch, parent operations and evidence are archived in durable project
storage, not only in temporary scratch worktrees.
