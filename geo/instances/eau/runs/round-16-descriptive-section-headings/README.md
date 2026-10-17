# EAU R16 — descriptive section headings

Status: **validated local candidate; not published or measured**.

- Run: 20261017T095913Z-index-html; sequential, one index.html candidate.
- New pool proposal: descriptive-section-headings; unmeasured.
- Candidate: 18c0ae3d6af0baf151487681aac40d7a09dd475c.
- Tree: 692b95a10e27de1e9c84011fb839cba3b0eb6b15.
- Seed: best fully measured R9 52dee0ba78885b9a3028760ba8d9cfc749a6c2e7,
  8/60 citations and composite 30.25; historical, not newly collected.
- Production remains R15 596ccda6c33a4bb2ea9cac3daa7d489e856f264d,
  6/60 citations and composite 29.75, discard; not the selection threshold.

## One small intervention

Replace exactly two existing visible H2 labels on R9:

| Section | Before | After |
| --- | --- | --- |
| Framework | A feedback loop. / With room to change. | How EAU adapts / the training system. |
| Results | Better interactions. / Stronger agents. | EAU results on / UserGym and ColBench. |

Both IDs, their aria-labelledby references, and br/em structure are preserved.
The terms are supported by the unchanged knowledge map and existing visible
project passages, recorded in heading-source.json. No new factual claim,
number, link, metadata, result row, body paragraph or keyword block is added.
The results heading highlights the existing main tables; the tau2 subsection
and its evidence boundary remain unchanged.

The hypothesis is clearer method/benchmark context for passages on the
homepage. R15 had 6/60 domain-citation cells, all in exact queries, zero in
fuzzy/broad queries, and four explicit homepage URL cells with zero support-page
URL cells. That locates an observed entry surface; it does not predict heading
lift. R16 has no outer score. Immediate historical samples cannot isolate causal
module effects or exclude stale indexes.

## Scope and retained history

Only index.html differs from R9, by two heading replacements. The original R9
H1 and subtitle, R7 overview, R8 routes, R9 static default results, all other
sections, pages, scripts, styles, links and metadata remain unchanged.
Relative to current R15 production, the candidate also removes R15's unkept H1,
static component reference and second-backbone table. This full difference is
in production-to-candidate.patch; do not blindly merge the R9-based branch into
R15 and accidentally retain those deltas.

All 16 R0–R15 history entries and all nine old proposals remain unchanged. A
tenth proposal records this new heading test. Both it and the external-authority
proposal remain unmeasured. R12/R13/R14/R15 operations and observations are
retained for later combinations; their scores are not added to predict R16.
module-review.json covers all ten inventory modules and retained alternatives.
The external paper backlink state is still unknown, and any edit requires
separate author authority. This ledger is agent-maintained instance data, not an
automatic wrapper-core recombination scheduler.

## Validation and publication gate

All 31 structural/factual checks passed. Visible homepage:
5436 → 5433
characters, below the unchanged 9000 limit. Reversing the two
operations recovers the complete R9 HTML exactly. IDs, links, reference order,
source facts, default table bytes, unchanged JSON-LD/scripts/styles and frozen
map/query/judge/normalizer hashes are independently checked.
No inner score was computed. No browser/visual test was performed: preserving
markup and styles does not establish rendered heading wrapping or layout.

The exact-tree metric guard rejects this unpublished candidate. Separate
explicit R16 publication approval is required. Use an isolated deploy branch
based on then-current main, apply the exact candidate index.html, verify its
complete tree, and reconcile teammate changes. Verify served bytes before
collection and after all real requests complete.

After approval, use the same 15 queries × GPT web / Codex / Tavily / Exa,
without a memory-model dimension. Require 60 valid cells and strictly more than
R9's 8/60 citation cells for keep; ties discard. The frozen judge counts bare
project-domain occurrences, so explicit source URLs must be reported separately.
The R9 control is historical, not simultaneous. No follow-up is scheduled.

Preparation and replay used Slurm, one CPU and 1 GB. No site publication/push,
rollback, new R16 paid searches, candidate deletion or branch pruning was
performed. Source evidence and the candidate patch are archived in durable
project storage, not only temporary scratch.
