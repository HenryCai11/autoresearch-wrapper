# EAU R19 — exact retained shared-entity metadata on R18

Status: **published and measured; discard for best-candidate selection**.

- Production merge: `ab6847afc14de3a9067361b071605de711c96337`.
- Candidate: `6ef90e8d0f401312efa9bb59e5a52e2264910bf9`.
- Exact candidate/production tree: `12b28c84303366ae8e4117709ec0166c1919ae9a`.
- Measured: 2026-10-19T13:39:52Z.
- Run: `20261019T131300Z-index-html`; completed, one candidate.
- Primary: historical R18 **12/60 → R19 12/60**, both 20.00/100.
- All 60 frozen query-engine responses valid.
- Secondary legacy composite: 35.19 → 35.19, report-only.
- Citation cells gained/lost: 0/0; same twelve citation cells.
- Explicit project URL cells: 11/60; support-page URL cells: 5/60.
- Strict improvement was required, so the tie is **discard**, not keep.
- Best observed remains R18. R19 remains live; no automatic rollback occurred.

See the [full report](r19-live/REPORT.md),
[60-cell matrix](r19-live/search-matrix.csv),
[deployment verification](r19-live/deployment.json),
[best-observed selection](r19-live/best-observed-selection.json), and
[completed audit](r19-live/audit.json).

| Engine | R18 citations | R19 citations |
| --- | ---: | ---: |
| GPT web | 0/15 | 0/15 |
| Codex search | 4/15 | 4/15 |
| Tavily | 0/15 | 0/15 |
| Exa | 8/15 | 8/15 |

## Combination and deployment

R19 is separately identified with parents R18/R10. It replays the exact final
measured R10 JSON-LD blocks on R18: one page-specific WebPage and one common
canonical ScholarlyArticle identity in each of the four documents. All
non-JSON-LD bytes, visible text, headings, method/result evidence, alphaXiv
reading routes, non-JSON-LD metadata, citation/PDF/BibTeX fields, machine
summaries, scripts and styles remain unchanged. All 38 local checks passed;
visible homepage text stayed 6103 characters. No inner score or browser test.

The R10 original 6/60 discard is unchanged. Its failed draft was not replayed.
Parent commits, source payloads and hashes are preserved under parents/ and
combination-source.json. Reversing the four replacements recovers R18 exactly.
No parent scores were added or averaged to forecast this combination.

The isolated deploy branch and main merge have the exact candidate tree.
The first served check found an old page; no eval probes ran until all four
changed resources matched. They matched again after all sixty requests finished.
GPT/API timestamps and both Codex group markers are bounded by those checks.

The first recording job stopped on an old branch-label assertion before
metric registration or wrapper evaluation. Only the provenance branch labels
were corrected. The same raw search batch was then successfully scored,
recorded and audited, with no resampling. The failed log and pre-correction
script are preserved in r19-live/, together with Slurm provenance.
The report table received a presentation-only newline correction; the executed
scripts, raw data and metrics remain unchanged.

## Interpretation, current state and retained history

Exact/fuzzy/broad citations are 9/20, 2/20 and 1/20, unchanged from R18.
This immediate historical-control sample did not show a primary improvement;
it does not prove the metadata has no longer-term effect. Search variation and
recrawl delay remain possible. Bare project-domain citations and explicit URLs
are reported separately. alphaXiv/arXiv are not project citations and alphaXiv
clicks/visits were not measured.

All twenty R0–R19 observations and thirteen proposals remain; all twelve older
proposals and best_observed R18 are unchanged. R19's discard remains available
for future combinations. Only the external-authority proposal is unmeasured.
No rollback, pruning, deletion, next round or follow-up schedule was performed.
Future candidates must preserve the user's alphaXiv reading destinations.

Original preparation snapshots remain immutable. See
[r19-live/pre-live-README.md](r19-live/pre-live-README.md) and
[r19-live/pre-live-outer-measurements.json](r19-live/pre-live-outer-measurements.json).
The original change.json remains the preparation record; CURRENT.json and
r19-live/deployed-change.json record the live state.
