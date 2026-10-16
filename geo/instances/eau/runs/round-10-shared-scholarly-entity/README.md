# EAU R10 — shared scholarly identity

Status: **published and measured; discard**. See the authoritative
[live report](r10-live/REPORT.md) and [current state](CURRENT.json).

Published as `b70597085286d4ff4c2d3de78f25d95581835b98`. All four changed pages
byte-matched production before and after collection; all 60 frozen cells were
valid. Primary citation cells changed from R9's 8/60 (13.33%) to 6/60 (10.00%);
the secondary composite changed from 30.25 to 28.06. Codex lost two citation cells
and the other three engines' citation counts were unchanged. Explicit project
URL cells changed from 5 to 3; no support-page URLs appeared. The frozen citation
judge also counts bare project-domain mentions. This immediate single sample
against a reused historical control does not establish a causal effect.

R10 remains live; the selection result did not trigger an automatic rollback.
Preparation snapshots (`change.json`, ledger snapshots and root `audit.json`)
are historical. Their original README and outer registry are preserved as
`r10-live/pre-live-README.md` and `pre-live-outer-measurements.json`; the live audit
checks their preparation hashes using those preserved originals.

- Run: `20261016T132116Z-index-html`; sequential, one candidate.
- Existing pool proposal: `shared-scholarly-entity`; round change: `r10-shared-scholarly-entity`.
- Base production: `52dee0ba78885b9a3028760ba8d9cfc749a6c2e7` (R9).
- Candidate: `04e7ea4d0b1a6be0c65301c2a297e401294a0b78`; tree `14fdd73cd91dc01843dbe6a57b8f172cd249ea98`.
- Outer-only primary: fixed four-engine project-domain citation rate, maximize.
- Baseline: preserved [R9 live record](../round-9-static-benchmark-evidence/r9-live/REPORT.md),
  8/60 citations, composite 30.25, all 60 valid; not a newly collected R10 control.

## Dependency-aware intervention

R9 produced five explicit homepage URLs but no support-page URLs. All four local
pages describe the same paper as anonymous ScholarlyArticle objects with different
page URLs and no shared @id. R10 selects an existing queued proposal to distinguish
the paper from its project/reference pages. This is not predicted search lift.

| Module | Role in R10 | Changed? |
| --- | --- | --- |
| `index.html` JSON-LD | Shared paper identity and distinct homepage WebPage | Yes |
| `paper.html` JSON-LD | Same paper identity and distinct bibliographic WebPage | Yes |
| `method.html`, `research-context.html` JSON-LD | Same paper identity and separate reference WebPages | Yes |
| All visible content, R8 reference routes and R9 static results | Retained byte-for-byte | No |
| Scripts, styles, crawler files and text summary | Retained byte-for-byte | No |

Each document contains a WebPage node whose mainEntity references
`https://eau-meta-agent.github.io/#paper`, and the identical ScholarlyArticle
record references the canonical homepage through mainEntityOfPage. Existing
page-specific descriptions/topics/keywords remain attached to their WebPage;
existing homepage paper facts are preserved, with headline/date copied from the
existing paper record. No new authors, affiliations, dates or results are invented.

Only the JSON-LD block in each page changed. The homepage uses `geo-apply` on
`meta:schema`; linked HTML asset nodes currently do not support `replace_text`,
so the other three blocks were changed with an exact generated `apply_patch`.
An initial validation caught lost indentation, and review caught an SVG title
being appended to the homepage name by the generic parser. Both were corrected
before the local candidate commit; the final checker additionally requires the
exact head/title. The first failure is retained in `validation-attempt-1.json`.
`preview.json` and `applied.json` describe that initial attempt; final
`operations.json`, `support-schema-final.apply_patch`, `schema-after.json` and
`candidate.patch` describe the validated candidate.
See `edit-mechanism.json`; wrapper-core code and canonical state were not edited
by hand. All body bytes and non-JSON-LD head bytes are unchanged. Visible text:
5436 to 5436
characters (unchanged), below the existing limit of 9000.
No inner score was computed. All 21 local checks passed.
Checks cover JSON syntax, identities, references and source preservation; they
are not a full RDF expansion, browser test or search-engine rich-result test.

Technical basis: [Schema.org mainEntity](https://schema.org/mainEntity),
[mainEntityOfPage](https://schema.org/mainEntityOfPage), and
[W3C JSON-LD node identifiers](https://www.w3.org/TR/json-ld11/#node-identifiers).
These document the representation, not an expected search-engine ranking benefit.

## Retention and next gate

Before/after [candidate ledger](../../candidate-pool.json) snapshots are retained
here, with before/after-record ledger snapshots in the live archive. R0–R10 and
all five proposals remain available; two proposals are still unmeasured. A
discarded candidate remains available for later combinations, which are not
ranked by adding historical metrics.

Preparation and validation run through Slurm with one CPU and 1 GB memory.
No installation or Python computation was performed on the login node.

After explicit R10 publication approval, all four changed resources were verified
and the unchanged 15 queries × four engines collected. Complete real observations
were registered for the exact deployed Git tree before wrapper evaluation and
recording. The portable archived metric replays as 13.3333 for the R9 seed and
10.00 for R10. Raw answers, request settings, timestamps, integrity hashes and
measurement scripts are preserved in `r10-live/`. No inner score was used.
An immediate observation cannot establish a causal effect or exclude indexing
lag. No future follow-up, rollback, candidate deletion or pruning was scheduled.
