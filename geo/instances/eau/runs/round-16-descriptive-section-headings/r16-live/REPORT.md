# EAU R16 — descriptive section headings, live outer measurement

R16 was approved, merged and published as `ff79a10c4e93906cad803be5e23580f60bd98412`.
The changed homepage byte-matched the exact candidate before and after collection.
Verification began at 2026-10-18T06:27:35Z.

Relative to the best R9 seed, only two existing H2 texts are replaced:
the framework title becomes “How EAU adapts / the training system.” and the
results title becomes “EAU results on / UserGym and ColBench.” Both IDs,
aria-labelledby references and br/em structure are preserved. These concepts
are supported by the frozen knowledge map and existing visible project passages
in heading-source.json. No new claims, facts, data, paragraphs, links, metadata,
scripts or styles were added. All 31 local structural/factual checks passed;
visible homepage text changed 5436 → 5433 characters (limit 9000).
No browser/visual test was performed; heading wrapping and layout are unverified.

R7 overview, R8 routes, R9 default static result data, the original H1/subtitle,
all other sections and all other files remain on R9. Relative to previous R15
production, the discarded H1/static-component/second-backbone bundle is removed
and the two R9 headings changed. An isolated branch based on R15 was patched to
the exact candidate; its full tree was verified before merging. Candidate,
deploy and production merge commits are distinct, with identical candidate and
production file trees in deployment.json. The final served check required all
60 valid responses and both Codex completion markers; collection timestamps
were independently checked against the before/after served checks.

The decision metric remains the frozen four-engine project-domain citation rate.
Inner scores were not computed. The R9 control is the preserved live 60-cell
measurement completed at 2026-10-16T13:09:24Z, not a fresh simultaneous control.

| Engine | R9 citations | R16 citations | R16 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 5/15 | 3/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 6/15 | 15/15 |

Primary: **8/60 → 9/60**
(13.33% → 15.00%).
Legacy outer composite: 30.25 → 31.86.
Citation cells gained/lost: 3/2.
Explicit project URL cells: 8/60.
Explicit support-page URL cells: 0/60.
Wrapper decision: **keep** (strict improvement in the primary required).

The existing judge counts bare project-domain occurrences as citations. These
are not necessarily explicit source links; inspect `rank`, `url`, and
`explicit-project-urls.json`. Tool responses are not consumer chat-app results.

This is one immediate post-deployment sample of the candidate, not an isolated
causal estimate of heading effects. Indexes may still contain older pages and
search results vary; the historical control does not isolate causal contribution.
No later follow-up has been scheduled. Selection and deployment are separate:
R16 remains live; no post-measurement rollback, candidate deletion or pruning was
performed. The previous R15 measurement (6/60, composite 29.75) is context only:
automatic selection compares against the best R9 seed (8/60), not that lower bar.

The maintained instance candidate ledger now records this observation and keeps
the candidate available for later combinations regardless of keep/discard.
All prior observations and exact archived candidate operations remain retained;
none of their scores was added or averaged to predict R16. Only the external-authority proposal
remains unmeasured, with backlink state unknown and separate authority required.
