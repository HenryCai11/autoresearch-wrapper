# EAU R14 — static second-backbone evidence, live outer measurement

R14 was approved, merged and published as `c762ead8370159e102c5ea11b1a43b944c71d1bf`.
The changed homepage byte-matched the exact candidate before and after collection.
Verification began at 2026-10-17T05:47:49Z.

Relative to the best R9 seed, R14 adds one default-open reference table inside the
existing results section. All nine Qwen2.5-7B-Instruct method rows and 36 values
are copied from existing script.js data at the same three-decimal precision.
The model label and caption distinguish the reference from the unchanged main
Qwen3 charts/table. Original model-switch markup, renderer selectors, metadata,
scripts, styles, links and every other named section remain unchanged. No new
results, relative gains, tau2 numbers or research claims were added. All 27 local
checks passed; no browser or visual test was performed.

R7 overview, R8 routes and R9 default static results are retained. Relative to
previous R13 production, index.html both adds this table and removes R13's
unkept static component reference. An isolated deploy branch based on R13 was
patched to the exact candidate tree and the entire tree verified before merging;
a blind merge of the historical-seed branch would have retained the wrong block.
Candidate, deploy and production merge commits are distinct; candidate and
production file trees are identical in deployment.json. The final served check
was gated on all 60 responses and both Codex completion markers, with collection
timestamps independently validated.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R9 control is the preserved live 60-cell
measurement completed at 2026-10-16T13:09:24Z, not a fresh simultaneous control.

| Engine | R9 citations | R14 citations | R14 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 5/15 | 3/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 2/15 | 15/15 |

Primary: **8/60 → 5/60**
(13.33% → 8.33%).
Legacy outer composite: 30.25 → 28.89.
Citation cells gained/lost: 0/3.
Explicit project URL cells: 3/60.
Explicit support-page URL cells: 0/60.
Wrapper decision: **discard** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample, not a causal estimate of the
second-backbone static-reference intervention. Indexes may still contain older pages and search
results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R14 remains live; no post-measurement rollback, candidate deletion or pruning was
performed. The previous R13 measurement (7/60, composite 30.14) is context only:
automatic selection compares against the best R9 seed (8/60), not that lower bar.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
Queued combinations remain unmeasured, not assigned scores from their parents.
