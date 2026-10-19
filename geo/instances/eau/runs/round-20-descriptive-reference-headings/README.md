# EAU R20 — descriptive reference-page H1s

Status: **validated local candidate; not published or measured**.

- Run: 20261019T171243Z-method-html; sequential, one two-heading candidate.
- Candidate: 65e2486e3639d55cad24d9e780b6b20864f22722.
- Tree: 8261df22ebbcfa2edc6031f32e2fb51214822ad3.
- Selection seed: best complete measured R18 dda361dcd45f2eee5cff5402a3d8b8a5421ddd33.
- Historical control: original R18 12/60 citations, primary 20.00/100;
  secondary composite 35.19444. This is not a fresh simultaneous control.
- Production remains unchanged R19 ab6847afc14de3a9067361b071605de711c96337.
- Keep requires all 60 valid and strictly more than 12/60; ties discard.

## Cross-module selection and wording provenance

The latest complete R19 observation tied R18 in the same twelve citation cells.
Its source URLs still include method.html in one fuzzy Exa cell and
research-context.html in another. Paper.html appears in three exact-query cells.
These actual returned source URLs motivate a visible-heading test, not a claim
that the earlier schema bundle or these headings caused retrieval. See
observed-entry-surfaces.json and r19-search-evidence.json, which points to the
unchanged archived R19 raw answers. No new R20 searches were made.

R20 changes exactly two H1 elements relative to R18:

| Page | Before | After |
| --- | --- | --- |
| method.html | What does EAU adapt? | How EAU adapts the training system. |
| research-context.html | Where does EAU fit? | EAU as an adaptive training system. |

The method wording exactly reuses R16's existing framework H2 still present on
the R18 homepage; the context wording uses its existing lead description.
This is a new support-page H1 bundle, not replay of the R16 homepage operation,
and no R16 score is inherited. Parent is R18 only. There are no new scientific,
performance, author, affiliation, benchmark or identity claims.

All paragraphs, secondary headings, evidence tables and citation/PDF/BibTeX
fields remain byte-identical to R18. All four HTML heads and JSON-LD blocks,
the complete homepage/paper page, scripts, styles, assets, crawler files,
README, llms.txt and site-config.js are unchanged versus R18. All nine R18
alphaXiv routing operations, including six HTML reading anchors, are retained.
Scholarly arXiv references are unchanged. Neither external domain counts as a
project citation; alphaXiv traffic remains unmeasured.

module-review.json reviews all ten modules and thirteen older proposals. All
twenty R0–R19 observations, all thirteen older proposals and best_observed R18
remain unchanged. Fourteen proposals now exist; only R20 and the external-paper
authority proposal are unmeasured. Discarded candidates remain available for
future combinations. Parent scores are never summed or used as isolated effects.
This is an agent-maintained ledger, not a background scheduler.

## Seed scope versus production scope

R19 remains live, but its tied schema experiment was discarded for selection.
It is NOT the R20 seed, and its distinct matrix is NOT relabelled as the R18
control. Candidate.patch contains only the two H1 replacements relative to R18.
production-to-candidate.patch spans FOUR HTML files: restore the R18 metadata
in index/method/paper/context, then change the two reference H1s. The unchanged
production snapshot is under served-r19/. Reversing the two new H1s and
reapplying the four exact archived R19 JSON-LD operations reproduces current
production byte-for-byte. This deployment scope is explicit, not a claim that
only two files differ from the currently live site. No rollback is performed now.

## Validation and publication gate

All 36 structural/factual checks passed, including
exact two-replacement replay/reversal, four-file production reconstruction,
existing wording provenance, alphaXiv routing, JSON-LD parsing, local paths,
fragments, unique IDs, hidden text and frozen matrix/query/map/judge/normalizer/
engine settings. The homepage remains 6103
visible characters under the unchanged 9000 limit. Reference
page text lengths before/after are recorded in validation.json.

Both edited files are content-fingerprinted linked asset graph nodes with empty
operation lists. Main-agent apply_patch made the exact two replacements in the
allocated worktree; no geo-apply support or wrapper-core extension is claimed.
The before/after graph snapshots and edit-mechanism.json preserve that limitation.
No inner score was computed and no browser/visual test was performed; heading
wrapping and layout are not described as tested.

Python, wrapper CLI, seed replay and validation ran through CPU Slurm jobs.
The first validation stopped on a URL-key error before validation output or
commit; it was corrected without site publication, resampling or metric changes.
See slurm-provenance.json and logs/ for the failed and successful attempts.

The portable exact-tree metric replays only the original registered R18 result
and rejects this unmeasured R20 tree with exit 2. No candidate metric, crash
record or fabricated 60-cell result is registered. Explicit publication approval
is required next. Recheck then-current main for teammate changes, verify the
complete candidate tree and all FOUR changed served HTML files before and after
the frozen 15-query × GPT web / Codex / Tavily / Exa collection. The unchanged
settings file retains legacy R9 wording; actual registered control is R18.
There is no memory dimension. Bare project-domain citation cells and explicit
source URLs remain separate. Immediate historical-control measurements cannot
establish causal module contributions or exclude stale indexing.

No site publication/push, new paid searches, rollback, pruning, deletion,
automatic follow-up or next-round start was performed.
