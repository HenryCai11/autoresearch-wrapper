# EAU R13 — static component reference, live outer measurement

R13 was approved, merged and published as `c6fa063d86be9e1861b0d79c6d2f7e2c27e3c1aa`.
The changed homepage byte-matched the exact candidate before and after collection.
Verification began at 2026-10-16T17:43:09Z.

Relative to the best R9 seed, R13 inserts one two-article block in the existing
framework section. The environment and agent titles, descriptions and six knob
labels are copied verbatim from existing script.js data. The default user
description is not duplicated. Interactive explorer markup, all other named
sections, metadata, scripts, styles, links and benchmark values remain unchanged.
R7 overview, R8 routes and R9 static results are retained. Relative to previous
R12 production, index.html also restores R9's H1. No new facts or numerical
results were introduced. Local checks passed, but no browser test was performed.

An isolated deploy branch based on R12 was patched to the exact candidate tree
and the complete tree was verified before merging. A blind merge would have
retained the unkept R12 H1. Candidate, deploy and production merge commits are
distinct; candidate and production file trees are identical in deployment.json.
The end-of-collection served proof is gated on all 60 responses and both Codex
completion markers, with timestamps independently checked in deployment.json.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R9 control is the preserved live 60-cell
measurement completed at 2026-10-16T13:09:24Z, not a fresh simultaneous control.

| Engine | R9 citations | R13 citations | R13 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 5/15 | 4/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 3/15 | 15/15 |

Primary: **8/60 → 7/60**
(13.33% → 11.67%).
Legacy outer composite: 30.25 → 30.14.
Citation cells gained/lost: 1/2.
Explicit project URL cells: 4/60.
Explicit support-page URL cells: 0/60.
Wrapper decision: **discard** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample, not a causal estimate of the
static-reference intervention. Indexes may still contain older pages and search
results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R13 remains live; no post-measurement rollback, candidate deletion or pruning was
performed. The previous R12 measurement (6/60, composite 29.28) is context only:
automatic selection compares against the best R9 seed (8/60), not that lower bar.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
Queued combinations remain unmeasured, not assigned scores from their parents.
