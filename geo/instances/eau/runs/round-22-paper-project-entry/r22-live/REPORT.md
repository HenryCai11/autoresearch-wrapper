# EAU R22 code release — live outer test

Measured candidate `fae44609023fddc240a13502f77abcfcd925c95d`, production
`7eafc96a295ba8c155f7c31368b0d67d800bee20`, tree `1ac57c63402d39d6f7738414ff00bf9837305759`.
This is the latest amended R22, not the original aa3c0ea paragraph-only tree.
All five changed resources matched before 2026-10-21T15:27:03Z
and after 2026-10-21T15:33:32Z; the first stale README
check gated every eval request. All request/group times lie inside these bounds.

## Result

Primary: 12/60,
20.00/100 versus original R18 12/60, 20.00.
Report-only composite: 30.47 versus R18 35.19
and R21 35.89. Valid: 60/60. Decision: **discard**.

| Engine | R18 citations | R22 citations | Valid |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 4/15 | 5/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 8/15 | 7/15 | 15/15 |

Exact / fuzzy / broad citations: 9 / 3 / 0 (each /20).
Gained/lost citation cells: 1/1.
Explicit project URL cells: 12/60;
support-page URL cells: 5/60.
Full transitions and URL evidence are in summary.json/explicit-project-urls.json.

## Scope and limitations

On R18: move the existing official-project paragraph inside paper.html; enable
two static homepage Code anchors; remove stale coming-soon labels; set codeUrl
and add Code resources to README and llms.txt. All five complete served files
are archived. Relative to previous R21, the discarded second-backbone table is
also removed to recover the selected R18 homepage. All paper/alphaXiv reading
routes, scholarly arXiv fields, facts, data, runtime and styles are preserved.
Original R22's 34-check snapshot and code-release revision's 28-check snapshot
remain intact. No inner metric or browser test.

Frozen 15 queries × GPT web / Codex search / Tavily / Exa; no memory dimension.
Strictly greater primary is required; a tie discards regardless of composite.
R18 is the original historical control, not a fresh simultaneous measurement.
The settings file retains legacy R9 wording; the actual registered control is R18.
The primary judge includes bare project-domain occurrences; explicit URLs remain
separate. Neither alphaXiv, arXiv nor GitHub code counts as a project citation.
No traffic was measured and no isolated paragraph/code-link effect is established.

One first-pass response per cell, no successful response selectively retried.
6 GPT responses explicitly reported no results; those real
nonempty tool responses are retained unchanged and count as no discovery, not
an excuse to resample. All 30 API requests returned HTTP 200. Original GPT raw
text, API JSON, Codex answers and request/group times are preserved. Network-only
curl/jq and the preinstalled native Codex binary collected responses; all Python,
normalization, scoring, wrapper CLI and archival work used Slurm. No login-node
Python, Node, compilation or local model inference. No compute proxy retry.

All 23 measured histories and 16 proposals remain; 15 other proposals and
their decisions are unchanged. Best R18 remains selected.
Code links stay published regardless of the GEO tie. A user-requested black
theme/icon release will follow only after this exact measured version is locked;
that later tree is not measured by this matrix and must not inherit its score.
No automatic optimization round, pruning, deletion or rollback occurred.
