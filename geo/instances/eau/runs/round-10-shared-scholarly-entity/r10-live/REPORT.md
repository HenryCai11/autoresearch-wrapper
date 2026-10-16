# EAU R10 — shared scholarly identity, live outer measurement

R10 was approved, merged and published as `b70597085286d4ff4c2d3de78f25d95581835b98`.
All four changed pages (`index.html`, `method.html`, `paper.html`,
`research-context.html`) byte-matched the candidate before and after collection.
Verification began at
2026-10-16T13:48:32Z.

This candidate gives the same paper a stable ScholarlyArticle @id across the
four pages, with a separate WebPage node for each canonical URL and explicit
mainEntity/mainEntityOfPage references. Only JSON-LD changed. All body bytes,
non-JSON-LD head bytes, scripts, styles, R8 reference routes and R9 static results
are unchanged. No new measurements or factual claims were added.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R9 control is the preserved live 60-cell
measurement completed at 2026-10-16T13:09:24Z, not a fresh simultaneous control.

| Engine | R9 citations | R10 citations | R10 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 5/15 | 3/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 3/15 | 15/15 |

Primary: **8/60 → 6/60**
(13.33% → 10.00%).
Legacy outer composite: 30.25 → 28.06.
Citation cells gained/lost: 0/2.
Explicit project URL cells: 3/60.
Explicit support-page URL cells: 0/60.
Wrapper decision: **discard** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample, not a causal estimate of the
shared-identity intervention. Indexes may still contain older pages and search
results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R10 remains live; no rollback, candidate deletion or branch pruning was performed.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
Queued combinations remain unmeasured, not assigned scores from their parents.
