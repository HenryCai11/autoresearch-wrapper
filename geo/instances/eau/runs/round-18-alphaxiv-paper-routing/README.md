# EAU R18 — alphaXiv paper-reading routes

Status: **published, measured, kept**; new best complete observed candidate.

- Production merge: `119cd5561e1b26d125eff96ad6cf8cc779dbf17e`.
- Candidate: `dda361dcd45f2eee5cff5402a3d8b8a5421ddd33`.
- Exact candidate/production tree: `ad41cd32f93433b1be065fc8d1969d8da78f2600`.
- Measured: 2026-10-19T09:14:05Z.
- Run: `20261018T161626Z-index-html`; completed, one candidate.
- Primary: historical R17 **10/60 → R18 12/60** (16.67% → 20.00%).
- All 60 frozen query-engine responses valid; wrapper decision **keep**.
- Secondary legacy composite, report-only: 34.31 → 35.19.
- Explicit project URL cells: 11/60; explicit support-page URL cells: 5/60.

See the [full report](r18-live/REPORT.md),
[60-cell matrix](r18-live/search-matrix.csv),
[deployment verification](r18-live/deployment.json),
[best-observed selection](r18-live/best-observed-selection.json), and
[completed audit](r18-live/audit.json).

| Engine | R17 citations | R18 citations |
| --- | ---: | ---: |
| GPT web | 0/15 | 0/15 |
| Codex search | 3/15 | 4/15 |
| Tavily | 0/15 | 0/15 |
| Exa | 7/15 | 8/15 |

## What was deployed

Exactly nine URL/label replacements in seven files route the six HTML
paper-reading anchors, README/llms.txt Paper entries and site-config.js paperUrl
to the verified alphaXiv EAU page. All arXiv scholarly identifiers, PDF metadata,
JSON-LD identity, CITATION.cff and both BibTeX blocks remain unchanged, as do
R17's static method reference, R16 headings, result data, project self-links,
scripts, styles, assets and crawler files. The existing graph handled five
replacements; four support-file replacements used apply_patch in the worktree.
All 36 local checks passed. No inner score or browser/visual test was performed.

An isolated branch on then-current R17 main was patched to the exact candidate,
with complete tree equality verified before merge. All seven changed served
resources matched that candidate before collection and after all requests
completed. GPT/API request timestamps and both Codex group start/completion
markers were verified within those checks. Python and scoring ran in Slurm;
network-only fetches and remote search probes did not run local inference.

## Interpretation and retained history

Fuzzy-tier citations are 0/20 → 2/20; exact 8/20 → 9/20; broad 2/20 → 1/20.
Three citation cells were gained and one lost. The unchanged judge counts bare
project-domain occurrences, so explicit source URLs are reported separately.
alphaXiv and arXiv URLs are not project-domain citations.

This is one immediate observation against historical R17, not a fresh
simultaneous control or causal proof that the routing change improved GEO.
alphaXiv clicks/visits were not measured; do not infer traffic gains from
this matrix. Future candidates must retain the user's alphaXiv reading routes,
while preserving scholarly arXiv references.

All nineteen R0–R18 observations and twelve proposals are retained; eleven
older proposals are unchanged. Only the external-authority proposal remains
unmeasured. R18 is now best_observed and its exact tree is the next seed.
No next round, rollback, pruning, deletion or automatic follow-up was performed.

Original preparation artifacts remain immutable. The initial README and
baseline registry are preserved under
[r18-live/pre-live-README.md](r18-live/pre-live-README.md) and
[r18-live/pre-live-outer-measurements.json](r18-live/pre-live-outer-measurements.json).
The original [change.json](change.json) remains the preparation snapshot;
[CURRENT.json](CURRENT.json) and
[r18-live/deployed-change.json](r18-live/deployed-change.json) carry live status.
