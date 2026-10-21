R22 code-release was published and measured: 12/60, discard; composite 30.47. See [live report](r22-live/REPORT.md) and CURRENT.json. A later user-requested visual release is separate and unmeasured. The preparation record below is retained verbatim in r22-live/pre-live-README.md.

# EAU R22 — project entry beside the paper identity

Current revision: [code release](code-release/README.md), candidate
`fae44609023fddc240a13502f77abcfcd925c95d`. The user supplied the public code
repository https://github.com/StringNLPLAB/meta-agent after the preparation
below. Two static homepage code links, codeUrl, README and llms.txt now point
there; stale coming-soon labels are removed. The paper-paragraph relocation
remains unchanged. The revised candidate passed 28 amendment checks and is
still unpublished and unmeasured. Follow CURRENT.json and code-release/change.json
for publication; the full diff now spans FIVE files, not the original two.
The original snapshot below and original commit are retained for audit, not
the current deployment target. Historical README/CURRENT hashes resolve through
code-release/preimages; all other original audit-covered files are untouched.
See code-release/original-integrity.json and code-release/audit.json.

Status: **validated local candidate; not published or measured**.

- Run: 20261021T090905Z-paper-html; target paper.html, sequential, one candidate.
- Candidate: aa3c0ea81c62f6a3cc263432ea625f69030d9edd.
- Tree: 1b179b5a7fae7708eba3f60a7d8038b58f413e4d.
- Seed: best observed R18 dda361dcd45f2eee5cff5402a3d8b8a5421ddd33.
- Original R18 historical control: 12/60 project-domain citation cells,
  primary 20.00/100, report-only composite 35.19444. Not a fresh control.
- Production remains R21 3f0c8143e9e23eb351e1727425ce1ed05606d4ec, unchanged:
  12/60, primary 20.00, report-only composite 35.88889, discard tie.
- Keep requires all sixty valid and strictly more than 12/60; ties discard.

## Entry evidence and selected experiment

R19, R20 and R21 tied R18 on the locked primary metric. R21 gained one fuzzy
Codex cell and lost one exact Codex cell (8/3/1 exact/fuzzy/broad, versus 9/2/1
for R18). Its higher secondary score and fuzzy count do not make it the seed.

The saved R21 Exa answers explicitly return paper.html in three cells: paper
identifier, meta-agent identity and benchmark queries. Their actual displayed
paper snippets include identity/results text, not the official-project paragraph
in the footer. observed-entry-surfaces.json preserves those snippets and exact
source cells; r21-search-evidence.json reduces actual URLs from all four engines,
with pointers to original answers. source-evidence-manifest.json hashes the
complete prior raw files and distinct R21/R18 matrices. No new R22 probes ran.

The official-home link already exists and was independently inspected in the
served R21 paper page. This is **not a missing edge** or external backlink fix.
Move that single existing paragraph, verbatim, from the references footer into
the identity overview-copy immediately after the existing evaluation sentence.
Placement nearer the paper identity may make the existing route easier to
extract; snippet omission does not establish a cause or predict improvement.
The paper URL itself already counts as a project-domain citation when returned.
Do not count the relocation as a new citation without a new real observation.

The new candidate's parent is R18. R18 includes the prior reference routes,
R16 headings, R17 static method and user-requested alphaXiv routing. All fifteen
old proposals remain unchanged, including R21's original primary tie/fuzzy
gain/exact loss, R14/R15 discards and the unverified external-authority proposal.
Old candidates remain available for future explicit combinations; no parent
scores are added, averaged or promoted by a secondary metric.

## Exact scope and production difference

Only paper.html differs from R18. Two text spans implement one paragraph move;
the inverse recovers every seed byte. The paragraph's text, href, class and
number of occurrences stay unchanged. The head/JSON-LD, bibliographic fields,
authors, affiliations, evidence values, headings, navigation, three footer
support links and all other page content remain unchanged. No new fact, result,
keyword padding, link, hidden text, script, style, identifier or URL is added.
The graph identifies file:paper.html as an asset with operations:[]; the main
agent used apply_patch in the allocated worktree after reading program.md.
No unsupported geo-apply operation or wrapper-core modification is claimed.

Every other tracked website file is byte-identical to R18, including index,
method/context pages, scripts/styles, default model/switch data, llms.txt,
README, citations, robots and sitemap. All nine R18 alphaXiv routing operations
and six HTML reading anchors remain; scholarly arXiv IDs/PDF/BibTeX/JSON-LD
references are unchanged. Neither external domain is a project citation, and
alphaXiv traffic remains unmeasured.

Production is R21, not the best seed. A future separately approved deployment
therefore changes TWO pages relative to current main: restore the R18 homepage
by removing the discarded R21 second-backbone table, and move the paper-page
paragraph. No R19 schema or R20 H1 bundle is inherited. candidate.patch is the
one-file seed diff; production-to-candidate.patch preserves the full two-file
production diff. This preparation did not roll back or change production.

## Validation, state and next gate

All 34 structural/factual checks passed. Homepage visible
text stays 6103 characters under the locked
9000 cap; paper visible text stays
1122 characters, with an identical word
multiset and identical href counts. Checks cover exact reversal, correct
identity/footer placement, balanced paper HTML, local paths/fragments, unique
IDs, JSON-LD, alphaXiv routing, whole-tree scope and unchanged frozen
map/query/judge/normalizer/settings/original R18 matrix. The graph paper content
fingerprint matches actual bytes and is the only changed node fingerprint.
No inner metric or browser/visual test was run; structural checks and unchanged
classes do not establish rendered layout or search behavior.

module-review.json reviews all ten inventory modules and fifteen older
proposals. All twenty-two R0–R21 historical observations and best R18 remain
unchanged. Sixteen proposals now exist, fourteen measured and two unmeasured
(R22 and external-authority). The agent maintains the ledger; no background
scheduler or automatic candidate-recombination behavior is implied.

The archived scorer replays the original R18 12/60 and rejects the exact R22
tree with exit 2, without registering an unpublished candidate score or crash.
The CLI run remains active with one allocated, locally committed candidate;
after explicit publication approval, resume that same run, recheck then-current
main and teammate changes, verify the full candidate tree and BOTH changed
served resources before/after the frozen 15-query × GPT web / Codex / Tavily /
Exa collection. No memory dimension. The byte-identical settings file retains
legacy R9 wording; the actual registered historical control is R18.

Bare-domain citation cells and explicit source URLs are distinct. A single
immediate historical comparison cannot isolate module contribution, rule out
search variance/indexing lag or establish traffic changes. No site push/merge,
paid queries, rollback, deletion/pruning, finalization, automatic follow-up or
next-round start occurred. All Python, CLI, parsing, validation and archival
work ran as Slurm jobs, with scratch job I/O.

The first archive job stopped at its final CLI-status assertion: it expected
"active" and a candidate dictionary, while the actual output uses "running"
and a candidate list. Candidate validation was already complete and no outer
evaluation was affected. The original script, failure log and provenance remain
preserved. finish_archive_r22.py completes the archive append-only, rechecking
existing artifact bytes, actual status and both metric guards; see
archive-recovery.json for the two job records.
