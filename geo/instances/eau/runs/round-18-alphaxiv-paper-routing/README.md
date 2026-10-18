# EAU R18 — alphaXiv paper-reading routes

Status: **validated local candidate; not published or measured**.

- Run: 20261018T161626Z-index-html; sequential, one seven-file routing bundle.
- Candidate: dda361dcd45f2eee5cff5402a3d8b8a5421ddd33.
- Tree: ad41cd32f93433b1be065fc8d1969d8da78f2600.
- Seed: best fully measured R17 dcf0b80e0e0554746e94e3e47034d77174b35417,
  10/60 citations, composite 34.30556; kept against historical R16 9/60.
- Production remains R17 6eb91c2d44003afe248e5e2623a2a6a2f38f5675, unchanged.
- Keep requires strictly more than 10/60 with all 60 responses valid; ties discard.

## User-requested traffic routing, not invented GEO lift

All six static HTML paper-reading anchors now point to
https://www.alphaxiv.org/abs/2610.16523, with matching alphaXiv labels.
The website README Paper entry, llms.txt Paper entry, and site-config.js
paperUrl agree with that destination. This is exactly nine replacements in
seven files, not an additional content-optimization bundle.

The public alphaXiv page returned HTTP 200. Its title, canonical URL and
citation_arxiv_id match EAU and 2610.16523. alphaxiv-verification.json preserves
that minimal identity evidence and the fetched body's SHA-256. Full third-party
HTML remains scratch-only; no external page, account or backlink was edited.

arXiv remains the scholarly identifier/source. All four HTML heads, JSON-LD
sameAs identities, canonical project URLs, arXiv PDF metadata, CITATION.cff and
the two BibTeX blocks are byte-unchanged. Those citation fields are not
paper-reading buttons. All project-site self-links remain unchanged.

There is no alphaXiv click/visit measurement or new tracking. Sending future
clicks there is the requested behavior; a traffic increase is not claimed.
The frozen metric still counts only the project domain, not alphaXiv or arXiv.
No discovery improvement is assumed from replacing the outbound URL.

## Scope, graph limits and retained candidates

module-review.json reviews all ten modules. R17's static method reference,
both R16 H2s, R7 overview, R8 routes, R9 default results and all factual claims
remain. No R12 H1 or R14 second-backbone table is inherited. Scripts, styles,
crawler files and assets are unchanged except the paperUrl configuration value.
Full changes are in candidate.patch and production-to-candidate.patch;
site/ contains snapshots of the seven candidate files.

The existing geo-graph exposes only index.html, README.md and site-config.js
for this bundle. Five replacements used geo-apply on those supported nodes;
four replacements in support HTML and llms.txt used apply_patch inside the
allocated worktree. Both subsets and the complete manifest are archived.
No wrapper-core change or full support-file graph coverage is implied.
Saved actual R17 search-source URLs feed the graph decision/exploration tools;
they are not new searches or a ranking claim for this user-selected candidate.

All eighteen R0–R17 observations, eleven old proposals and best_observed R17
remain unchanged. A twelfth proposal identifies R18 separately, with parent R17.
Only R18 and the authority-gated external-paper proposal are unmeasured.
Prior candidates remain available for combinations without adding their scores.
This is an agent-maintained ledger, not a recombination scheduler.

## Validation and publication gate

All 36 structural/factual checks passed. Visible homepage:
6086 → 6103
characters, below the unchanged 9000 limit. Checks cover exact
operation replay and reversal, six aligned anchors, consistent configuration,
unchanged scholarly metadata/BibTeX, R17 method/results retention, local links,
unique IDs, hidden text and frozen map/query/judge/normalizer/settings/control.
No inner score or browser/visual test was performed. Static validation does not
establish rendered fit or browser navigation behavior.

The exact-tree metric refuses this unpublished candidate. Separate explicit
R18 publication approval is required. Recheck then-current main for teammate
changes, deploy the complete candidate tree, and verify all seven changed
served resources before and after real requests. Do not check only index.html.

After approval, use the frozen 15 queries × GPT web / Codex / Tavily / Exa;
no memory-model dimension. All 60 cells must be valid and citations must exceed
the historical R17 10/60 control for keep. Secondary composite is report-only.
The unchanged judge also counts bare project-domain occurrences, so explicit
source URLs are reported separately. Immediate samples and historical controls
do not establish causal lift or exclude indexing lag. No follow-up is scheduled.

Preparation, seed replay and validation used Slurm, one CPU and 1 GB.
No site publication/push, new paid eval search, rollback, pruning or candidate
deletion was performed. Durable patches, manifests and snapshots live in project
storage; scratch is not the only copy.
