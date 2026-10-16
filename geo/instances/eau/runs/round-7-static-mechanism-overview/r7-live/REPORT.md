# EAU R7 — static mechanism overview, live outer measurement

R7 was explicitly approved, merged, and deployed as `fbd9e100b6ae71704a0cf65b1a1b9b87dbdc4ef7`.
The served homepage was byte-verified against the candidate before and after collection.
Only the homepage overview heading and four paragraphs changed, directly stating the
editable training components, two adaptation timescales, and fixed evaluation boundary.
Metadata, styles, scripts, other pages, knowledge map, queries, and judge are unchanged.
Visible homepage text grew from 4,964 to 5,051 characters (existing limit: 9,000).

Outer-only selection uses project-domain citation rate on 15 frozen queries × 4 engines.
Inner scores were not computed or used. The baseline is the latest R6 repeat
started at 2026-10-16T11:45:24Z, not a newly collected R7 control.

| Engine | R6 citations | R7 citations | R7 valid responses |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 4/15 | 3/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 3/15 | 3/15 | 15/15 |

Primary: **7/60 → 6/60**
(11.67% → 10.00%).
Matched-valid coverage: 60/60.
Legacy outer composite: 29.64 → 29.44.
Citation cells gained/lost: 0/1.
Cells with an explicit project URL: 3/60.
Wrapper decision: **discard** (strict primary-metric improvement required).

This single immediate post-deployment observation is not a causal effect estimate.
Search indexes may still contain R6 or earlier copies. The unchanged R6 13-minute
repeat also had 7/60 citations and cannot establish a refresh timescale.
No future follow-up has been scheduled.

The unchanged judge counts bare project-domain occurrences as `site_cited`;
this is not equivalent to an explicit source URL. Inspect `rank` and `url` in
the matrix. Tool responses are not consumer ChatGPT/other chat-app measurements.

Selection and deployment are separate: R7 remains online. No automatic rollback
or candidate deletion was performed. R5/R6 candidates and observations remain intact.
