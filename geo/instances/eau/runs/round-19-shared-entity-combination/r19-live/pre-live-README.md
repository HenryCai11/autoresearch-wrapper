# EAU R19 — retained shared-entity metadata on R18

Status: **validated local candidate; not published or measured**.

- Run: 20261019T131300Z-index-html; sequential, one four-file metadata candidate.
- Candidate: 6ef90e8d0f401312efa9bb59e5a52e2264910bf9.
- Tree: 12b28c84303366ae8e4117709ec0166c1919ae9a.
- Seed: best complete measured R18 dda361dcd45f2eee5cff5402a3d8b8a5421ddd33.
- Primary control: 12/60 citations, 20.00/100; secondary composite 35.19444.
- Production remains unchanged R18 119cd5561e1b26d125eff96ad6cf8cc779dbf17e.
- Keep requires all 60 valid and strictly more than 12/60; ties discard.

## Why revisit a retained candidate

R18 returned explicit project URLs in eleven cells, including five support-page
URL cells: paper.html in three exact-query cells, method.html in one fuzzy cell,
and research-context.html in another fuzzy cell. These are actual saved Exa
source URLs, not inferred graph reach. See observed-entry-surfaces.json and
the linked original R18 raw answers in r18-search-evidence.json.

R19 retests the exact final R10 shared-paper metadata scheme on the current
R18 tree. Each document has one page-specific WebPage and one identical
ScholarlyArticle with @id https://eau-meta-agent.github.io/#paper; each page's
mainEntity references that paper. Titles, topic metadata and descriptions remain
page-specific. This is an identity/relationship experiment on an observed
cross-page entry surface, not a prediction of retrieval or citation lift.

R10 previously measured 6/60 against historical R9 8/60 and remains a discard.
Its old result is untouched. R19 has parents R18 and R10 and will receive a
separate observation. Neither R10's score nor R18's score is added or averaged
to forecast it. module-review.json reviews all ten modules and every retained
proposal, including unselected H1, table, overview and external-link alternatives.

## Exact replay, not a rewrite of the archived proposal

The four replacement blocks come from the final measured R10 commit
04e7ea4d0b1a6be0c65301c2a297e401294a0b78 and match schema-after.json.
The final homepage operation also matches the corrected archived operations.json.
Failed initial R10 attempts are not replayed. The old R9→R10 complete HTML
for all four files was reproduced with only those schema blocks, and R18's
original blocks match that old R9 input exactly. Parent hashes and provenance
are recorded under parents/ and combination-source.json.

Only four JSON-LD blocks differ from R18. All non-JSON-LD bytes, body HTML,
visible text, H1/H2 headings, method reference, result evidence, canonical
links, citation/PDF fields, BibTeX and all alphaXiv reading anchors are unchanged.
README, llms.txt and site-config.js retain R18's alphaXiv destinations.
Scripts, styles, assets, robots and sitemap are unchanged. No new scientific
claim, author, affiliation, year, result or topic was invented; the article facts
and page fields are checked against the existing R10 contract and R18 data.

One homepage meta:schema operation used geo-apply. Three exact support-page
replacements used apply_patch inside the allocated worktree because the existing
graph does not expose them as mutable text-file nodes. There is no wrapper-core
extension or claim of full support-file graph coverage. The complete manifest,
both subsets, patches and candidate snapshots are durably archived.

## Validation, retained history and publication gate

All 38 structural/factual checks passed. Visible homepage text:
6103 → 6103 characters,
below the unchanged 9000 limit. Checks cover exact parent replay,
reversal to R18, shared/per-page identity, title/topic/author/year preservation,
all nine R18 routing operations, links/IDs, hidden text and frozen
map/query/judge/normalizer/settings/control fingerprints. No inner score was
computed. No browser/visual test was performed; unchanged body/scripts/styles
are not described as a browser test. Technical references for the relationships
are [mainEntity](https://schema.org/mainEntity),
[mainEntityOfPage](https://schema.org/mainEntityOfPage), and
[JSON-LD node identifiers](https://www.w3.org/TR/json-ld11/#node-identifiers).

All nineteen R0–R18 observations, twelve older proposals and best_observed R18
remain unchanged. The thirteenth proposal is separate. Only R19 and the
external-authority proposal are unmeasured. Existing candidates remain available
for future combinations; this is an agent-maintained ledger, not a scheduler.

The exact-tree metric rejects R19 until explicitly approved publication and
real live collection. Recheck then-current main, verify the complete candidate
tree and all four changed served HTML resources before and after all requests.
Use the frozen 15 queries × GPT web / Codex / Tavily / Exa; no memory dimension.
R18 is a historical control, not a fresh simultaneous measurement. The copied
settings file retains legacy R9 baseline wording; the actual registered control
is R18. Bare project-domain citations and explicit source URLs remain distinct.
alphaXiv/arXiv URLs are not project citations, and alphaXiv traffic is unmeasured.
Immediate historical-control observations cannot establish causal module effects.

Python, wrapper CLI, seed replay and validation used Slurm (one CPU, 1 GB).
No site publication/push, new paid searches, rollback, pruning, deletion,
automatic follow-up or next-round start was performed.
