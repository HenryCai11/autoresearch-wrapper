# EAU R12 — descriptive homepage H1, live outer measurement

R12 was approved, merged and published as `bbc3b79d20323549fd29e422017ed6c457c6b707`.
The changed homepage byte-matched the exact candidate at collection start.
The authoritative end-of-collection proof is recorded separately in
`post-collection-verification.json` and `served-final/index.html`, after the
complete 60-cell summary. The original `served-after` check was issued while the
last Codex query was still in flight and is retained as an intermediate check.
No search was repeated, and no answer, matrix, metric or verdict changed.
Verification began at 2026-10-16T16:31:12Z.

Relative to the best R9 seed, R12 changes only the visible H1 from “Learning to /
evolve, together.” to “EAU: / Co-evolution.” The full existing research title
remains in the adjacent subtitle and metadata. R7 overview, R8 routes, R9 static
results, scripts, styles and all other bytes are unchanged. Relative to previous
R11 production, index.html also restores the R9 overview. An isolated deploy
branch based on R11 was patched and its entire tree verified before merging;
a blind merge of the R9-based feature branch would have kept the wrong overview.
Candidate, deploy and production merge commits are distinct, with identical
candidate and production file trees recorded in deployment.json. No new facts
or measurements were added.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R9 control is the preserved live 60-cell
measurement completed at 2026-10-16T13:09:24Z, not a fresh simultaneous control.

| Engine | R9 citations | R12 citations | R12 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 5/15 | 3/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 3/15 | 15/15 |

Primary: **8/60 → 6/60**
(13.33% → 10.00%).
Legacy outer composite: 30.25 → 29.28.
Citation cells gained/lost: 0/2.
Explicit project URL cells: 3/60.
Explicit support-page URL cells: 0/60.
Wrapper decision: **discard** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample, not a causal estimate of the
heading intervention. Indexes may still contain older pages and search
results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R12 remains live; no post-measurement rollback, candidate deletion or pruning was
performed. The previous R11 measurement (7/60, composite 28.97) is context only:
automatic selection compares against the best R9 seed (8/60), not that lower bar.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
Queued combinations remain unmeasured, not assigned scores from their parents.
