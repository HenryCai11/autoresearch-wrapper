# EAU R10 — shared scholarly identity

Status: **validated local candidate, not published or measured**.

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
here. Ten historical versions and all five existing proposals remain available;
R10 is unmeasured and has no assigned outer score. Queued combinations are not
ranked by adding historical metrics.

Preparation and validation run through Slurm with one CPU and 1 GB memory.
No installation or Python computation was performed on the login node.

After explicit R10 publication approval, verify all four changed resources against
this candidate, then collect the unchanged 15 queries × four engines. Register
only complete real observations for the exact deployed Git tree before the
wrapper evaluates and records the candidate. Preserve the baseline, failures
and timestamps. An immediate observation cannot establish a causal lift or
exclude indexing lag. No future follow-up or rollback has been scheduled.
