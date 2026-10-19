# EAU R18 — alphaXiv paper-reading routes, live outer measurement

R18 was explicitly approved, merged and published as `119cd5561e1b26d125eff96ad6cf8cc779dbf17e`.
All seven changed served files byte-matched the candidate before and after every
search request. Initial verification: 2026-10-19T09:07:46Z.
Final verification: 2026-10-19T09:14:03Z.

## Intervention and validation

This user-requested routing bundle changes exactly nine URL/label occurrences
in seven files on the best observed R17 tree. The six static HTML paper-reading
anchors, README/llms.txt Paper entries and site-config.js paperUrl now point to
https://www.alphaxiv.org/abs/2610.16523. The public target's title, canonical URL
and arXiv identifier were verified independently during preparation.

arXiv identifiers, PDF metadata, all HTML heads and JSON-LD identity, CITATION.cff
and both BibTeX blocks are unchanged. All factual claims, the R17 persistent
method reference, R16 headings, R9 result evidence, project-site self-links,
script.js, styles, assets and crawler files remain unchanged.
All 36 local structural/factual checks passed; visible homepage
text changed 6086 → 6103
characters (limit 9000). No inner score or browser/visual test was performed.

Five replacements used the existing graph-supported file nodes; four support-file
replacements used apply_patch in the allocated worktree. The full operation
manifest and both subsets are preserved. No wrapper-core extension was made.
Candidate, isolated deploy and main merge commits differ, but complete candidate
and production trees match. Request timestamps and both Codex completion markers
are bounded by the served checks, which include all seven changed resources.

## Frozen four-engine comparison

The control is the preserved R17 60-cell observation at 2026-10-18T15:48:02Z,
not a fresh simultaneous control. Keep requires strictly more than 10/60 with
all 60 responses valid; ties discard. No memory-model or inner-metric dimension.
The copied collection-settings.json retains historical R9 baseline wording;
the actual registered control is R17, as shown in the matrix fingerprint,
outer-measurements.json, deployment record and this report.

| Engine | R17 citations | R18 citations | R18 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 3/15 | 4/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 7/15 | 8/15 | 15/15 |

Primary: **10/60 → 12/60**
(16.67% → 20.00%).
Legacy outer composite, report-only: 34.31 → 35.19.
Citation cells gained/lost: 3/1.
Explicit project URL cells: 11/60.
Explicit support-page URL cells: 5/60.
Wrapper decision: **keep**.

The existing judge also counts bare project-domain occurrences as citations;
those are not necessarily explicit source links. Inspect rank/url and
explicit-project-urls.json separately. alphaXiv and arXiv URLs are not counted
as project-domain citations. Tool responses are not consumer chat-app results.

## Traffic goal, selection and limitations

alphaXiv clicks and visits are **not measured**. Routing future paper clicks to
alphaXiv is the requested behavior, not evidence of a traffic increase.
The matrix measures project-site discovery only; it does not score that traffic
goal. This is one immediate sample against a historical control, not an isolated
causal estimate of routing. Stale indexes, time and search variation may matter.

Selection and publication remain separate: R18 stays live, including the user's
alphaXiv routing request, regardless of this metric decision. No automatic
rollback, candidate deletion, branch pruning, next round or follow-up schedule
was performed. Future candidate preparation must preserve the user's alphaXiv
reading destinations; an older best_observed entry is not permission to restore
arXiv reading buttons. All nineteen R0–R18 observations and twelve proposals
remain available for later combinations, without adding their old scores.
Only the external-authority proposal remains unmeasured; external backlink
state stays unknown, and no external page was edited.
