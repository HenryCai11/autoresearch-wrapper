# EAU R9 — static benchmark evidence, live outer measurement

R9 was approved, merged and published as `52dee0ba78885b9a3028760ba8d9cfc749a6c2e7`.
The changed homepage (`index.html`) byte-matched the candidate before and after
collection. Verification began at
2026-10-16T13:04:32Z.

This candidate pre-renders three existing default Qwen3-4B charts and the existing
nine-method benchmark table in index.html#results. The unchanged JavaScript
renderer generated the HTML. No new measurements or facts were added; scripts,
styles, metadata, other pages and the R8 reference cluster are unchanged.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R8 control is the preserved live 60-cell
measurement completed at 2026-10-16T12:22:48Z, not a fresh simultaneous control.

| Engine | R8 citations | R9 citations | R9 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 3/15 | 5/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 3/15 | 15/15 |

Primary: **6/60 → 8/60**
(10.00% → 13.33%).
Legacy outer composite: 28.64 → 30.25.
Citation cells gained/lost: 2/0.
Explicit project URL cells: 5/60.
Explicit support-page URL cells: 0/60.
Wrapper decision: **keep** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample, not a causal estimate of the
static-evidence intervention. Indexes may still contain older pages and search
results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R9 remains live; no rollback, candidate deletion or branch pruning was performed.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
Queued combinations remain unmeasured, not assigned scores from their parents.
