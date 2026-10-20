# EAU R20 — descriptive reference H1s, live outer measurement

Published as `27f252b85a6e9c3ff83d5ff815f6a704e3db51bc`. Complete candidate and
production trees match. All four changed served HTML resources matched before
collection (2026-10-20T03:45:25Z) and after all requests
finished (2026-10-20T03:56:26Z). The initial served
check saw old content; no valid samples were requested until all four matched.

## Intervention and scope

Seed is best R18, not tied/discarded R19. Relative to R18, exactly two H1s change:
method: “How EAU adapts the training system.”; research context: “EAU as an
adaptive training system.” The first exactly reuses the existing R16 homepage
H2 wording on a new page/heading level; the second uses its existing lead phrase.
Parent is R18 only. No existing paragraph, secondary heading, result, citation,
PDF/BibTeX, HTML head or JSON-LD differs from R18. All alphaXiv reading routes,
machine summaries, scripts, styles, assets and crawler files are retained.

Since R19 was live before deployment, the approved production diff spans four
HTML pages: remove the discarded R19 schema bundle and apply the two H1s.
This is not a two-file change versus live R19. The exact candidate and full
four-file production patches are preserved in the preparation archive.
All 36 structural/factual checks passed; homepage remains 6103 visible chars.
Both files are graph-fingerprinted assets without text operations; exact edits
used apply_patch in an allocated worktree, not a wrapper-core extension.
No inner metric or browser/visual test was performed.

## Frozen historical comparison

Control is original R18 12/60, measured 2026-10-19T09:14:05Z; it is not a fresh
simultaneous control or the distinct tied R19 matrix. Same 15 queries × GPT web,
Codex search, Tavily and Exa, no memory dimension. Keep requires all 60 valid
and strictly more than 12/60 citation cells; ties discard. The unchanged
settings file retains legacy R9 wording; the registry specifies actual R18.

| Engine | R18 citations | R20 citations | R20 valid |
| --- | ---: | ---: | ---: |
| gpt-web | 0/15 | 0/15 | 15/15 |
| codex-search | 4/15 | 4/15 | 15/15 |
| tavily-search | 0/15 | 0/15 | 15/15 |
| exa-search | 8/15 | 8/15 | 15/15 |

Primary: **12/60 → 12/60**
(20.00% → 20.00%).
Secondary legacy composite, report-only: 35.19 → 34.83.
Citation cells gained/lost: 0/0.
Explicit project URL cells: 11/60;
explicit support-page URL cells: 5/60.
Wrapper decision: **discard**.

The frozen judge includes bare project-domain occurrences; they are not always
explicit source links. See URL/rank fields and explicit-project-urls.json.
alphaXiv/arXiv are not the project domain; no alphaXiv traffic was measured.
These four search tools are not interchangeable with consumer chat apps.

## Execution failures and retained evidence

The first compute-node API attempt had thirty proxy CONNECT failures (HTTP 000,
curl exit 56) and no API responses. The first fifteen Codex processes failed
before startup because Node was missing. Failed attempts are retained separately,
never scored as successful absent-project answers. recovery-notes.json records
the recovery route. The fifteen successful GPT samples were never retried.
No successful answer from any provider was selectively resampled. Network-only
API acquisition uses curl/jq; Python normalization, scoring and wrapper CLI use
Slurm. All sixty accepted samples must fall within the successful served checks.

This immediate observation against a historical control cannot isolate heading
effects, interactions, search variation or indexing lag. R20 remains live
without automatic rollback regardless of selection. All twenty older R0–R19
observations, thirteen older proposals and their original decisions are retained;
R20 adds the twenty-first observation without rewriting them. Fourteen proposals
remain, with only the external-authority proposal unmeasured. All candidates
remain available for future combinations; parent scores are not added.
No external page edit, pruning, cleanup, next round or follow-up was performed.
