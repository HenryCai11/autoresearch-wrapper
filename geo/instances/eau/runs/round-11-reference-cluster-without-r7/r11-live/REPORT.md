# EAU R11 — reference cluster without R7 overview, live outer measurement

R11 was approved, merged and published as `c744ba125108d003ea61e8b89807e274ffaa6e4e`.
All four changed pages (`index.html`, `method.html`, `paper.html`,
`research-context.html`) byte-matched the candidate before and after collection.
Verification began at
2026-10-16T14:18:42Z.

R11 restores the overview verbatim from R6 on the best observed R9 seed, while
retaining the R8 reference routes and R9 static benchmark results. Only five
overview lines differ from R9. R10's unkept JSON-LD is not carried forward;
relative to the previous R10 production, four HTML pages differ. No new facts,
measurements, scripts or styles were added. The R9-based candidate was not blindly
merged into R10: an isolated deploy branch based on R10 was patched to the exact
candidate tree before merging. The candidate, deploy and merge commits are
distinct; their deployed file tree is identical and recorded in deployment.json.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R9 control is the preserved live 60-cell
measurement completed at 2026-10-16T13:09:24Z, not a fresh simultaneous control.

| Engine | R9 citations | R11 citations | R11 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 5/15 | 4/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 3/15 | 15/15 |

Primary: **8/60 → 7/60**
(13.33% → 11.67%).
Legacy outer composite: 30.25 → 28.97.
Citation cells gained/lost: 1/2.
Explicit project URL cells: 4/60.
Explicit support-page URL cells: 0/60.
Wrapper decision: **discard** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample, not a causal estimate of the
combination intervention. Indexes may still contain older pages and search
results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R11 remains live; no post-measurement rollback, candidate deletion or pruning was
performed. The previous R10 measurement (6/60, composite 28.06) is context only:
automatic selection compares against the best R9 seed (8/60), not that lower bar.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
Queued combinations remain unmeasured, not assigned scores from their parents.
