# EAU R6 — deployed, outer-only measurement

Production merge: `e6b74d333b09c30619d5c3c61c95fa066ee50188`.
Verified served homepage bytes match the merged R6 candidate before collection.
This measurement uses the same 15 queries, four engines, provider settings,
Codex two-worker/90-second/low-reasoning settings, and judgement rules as the fresh R5 control.
Inner scores are ignored.

| Engine | Valid responses | Found | Project domain cited |
| --- | ---: | ---: | ---: |
| gpt-web | 15/15 | 11/15 | 0/15 |
| codex-search | 15/15 | 10/15 | 4/15 |
| tavily-search | 15/15 | 6/15 | 0/15 |
| exa-search | 15/15 | 12/15 | 3/15 |

All scheduled cells: 7/60 project-domain
citations (11.67%), legacy outer composite
29.56, with 60/60 valid responses.

Matched-valid comparison (60 cells): R5 11.67% →
R6 11.67%, delta +0.00 percentage points.
The matched composite changed from 29.61 to 29.56.

Wrapper selection result: **discard**. Complete coverage: **True**.
This is a single immediate post-deployment observation, not evidence of a robust
causal improvement. Search engines may still return older indexed content.
A delayed repeat after recrawling is still needed.

The metric is the existing `geo_eval` site-citation judgement, which accepts a
project-domain occurrence even if it appears as bare text. `rank`/`url` additionally
show when the judge found an explicit project URL; these are not consumer chat-app measurements.

The candidate remains in Git even if discarded by the outer metric. Deployment
and selection are separate: this report does not automatically roll production
back or delete the R6 branch.
