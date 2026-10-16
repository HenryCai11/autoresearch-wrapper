# EAU R12 — descriptive homepage H1

Current status: **published and measured; discard against R9**.

R12 is live as `bbc3b79d20323549fd29e422017ed6c457c6b707`. All 60 outer
responses were valid. Primary citations: R9 **8/60 → R12 6/60**; secondary
composite: **30.25 → 29.28**. Explicit project URL cells: **3/60**. No inner
score was computed and no automatic production rollback was performed.

See [the live report](r12-live/REPORT.md), [current state](CURRENT.json), and
[post-collection version proof](r12-live/post-collection-verification.json).
The original after-check was intermediate; the supplemental final check is
the authoritative end-of-collection proof. Original evidence is preserved.

The rest of this document is the historical preparation snapshot. Its original
bytes are retained in `r12-live/pre-live-README.md` for the preparation audit;
statements below about awaiting approval or production refer to preparation time.

## Preparation snapshot

- Run: `20261016T144122Z-index-html`; sequential, one candidate, explicit index.html target.
- Selected pool proposal: `homepage-descriptive-h1`.
- Candidate: `95940d50088176ada54ea4ed829bbf4ced9c1135`; tree `c2e643d4d1462b72bc4914de9222cfb200be07e3`.
- Selection seed: R9 `52dee0ba78885b9a3028760ba8d9cfc749a6c2e7`, recorded 8/60 citations
  and composite 30.25, all 60 valid; a reused historical control, not new searches.
- Current production: R11 `c744ba125108d003ea61e8b89807e274ffaa6e4e`, recorded 7/60
  and composite 28.97; unchanged, and not the selection threshold.

## Intervention and dependency review

Only one line differs from R9: the visible primary heading changes from
“Learning to / evolve, together.” to “EAU: / Co-evolution.” The existing full
research title remains in the adjacent hero subtitle and document metadata.
The h1 id, single line break and emphasis markup remain. No new facts, results,
styles, scripts, links or metadata are introduced. All other R9 bytes remain,
including its R7 overview, R8 reference routes and R9 static benchmark data.
R10 and R11's unkept deltas and observations are retained in history, not silently
carried forward onto the best recorded seed.

R11 returned four explicit homepage URL cells and no support-page URLs. That
locates an observed entry page; it does not predict an H1 ranking benefit. The
existing h1 is a slogan without EAU, although the subtitle already names the
work. This candidate tests whether changing that one visible identity surface
affects the unchanged outer protocol. No lift is assumed.

The nine-module review is preserved in `module-review.json`. The five existing
proposals and R0–R11 history are unchanged. Three new hypotheses are appended:

| Proposal | State | Scope |
| --- | --- | --- |
| `homepage-descriptive-h1` | selected, unmeasured | Visible homepage identity |
| `static-second-backbone-evidence` | queued, unmeasured | Separately labelled existing Qwen2.5-7B-Instruct rows |
| `static-component-reference` | queued, unmeasured | Existing non-default explorer descriptions |

The external paper backlink proposal remains unknown and requires separate
author authority for an edit. None of the new hypotheses receives an inferred
score. Parent scores are not summed and discarded candidates are not deleted.

All 19 local checks passed. Visible homepage text:
5436 → 5425
characters, below the unchanged 9000 limit. No inner score was
computed. Checks cover exact scope, heading structure, IDs/links, unchanged
schema/static results and source hashes. They are not a browser or visual test;
actual rendered layout fit has not been verified.

## Publication and measurement gate

R12 has no registered live observation; its exact-tree metric guard refuses to
score it. A keep requires strictly more than R9's 8/60 citation cells with all
60 responses valid, using the same 15 queries and GPT web / Codex / Tavily / Exa
settings. The frozen judge counts bare project-domain mentions as citations;
explicit source URLs must be reported separately. A historical control and one
immediate sample cannot establish causality or exclude indexing delay.

After explicit publication approval, prepare an isolated deploy branch based on
current main and apply the exact candidate index.html. Do not blindly merge this
R9-based feature branch into R11, because that would retain the unkept R11
overview. Relative to R11, index.html differs in both the h1 and the restoration
of R9's overview; `production-to-candidate.patch` records the full change.
Verify the complete tree equals `c2e643d4d1462b72bc4914de9222cfb200be07e3` before publishing,
then verify served homepage bytes before and after collection. Reconcile any
concurrent teammate edits before proceeding. Only real, complete observations
for that exact tree may be evaluated and recorded through the CLI.

Preparation, local checks and metric replay run through Slurm with one CPU and
1 GB memory. No publication, push, rollback, branch pruning, candidate deletion,
paid search collection or future follow-up was performed by this preparation.
