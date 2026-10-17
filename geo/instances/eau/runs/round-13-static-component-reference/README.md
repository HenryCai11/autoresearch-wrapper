# EAU R13 — static component reference

Current status: **published and measured; discard against R9; superseded by R14**.

R13 was deployed as `c6fa063d86be9e1861b0d79c6d2f7e2c27e3c1aa` and has since
been superseded by [R14](../round-14-static-second-backbone-evidence/README.md). All 60 outer
responses were valid. Primary project-domain citations: R9 **8/60 → R13 7/60**;
secondary composite: **30.25 → 30.14**. Explicit project URL cells: **4/60**;
support-page URL cells: **0/60**. No inner score was computed, and no automatic
rollback was performed. This immediate single sample is not a causal estimate.

See [the live report](r13-live/REPORT.md), [current state](CURRENT.json), and
[deployment and collection timing proof](r13-live/deployment.json).
The complete 60-cell evidence and 14-entry R0–R13 history passed the R13 live audit;
all eight proposals were preserved, with two unmeasured at that recording time.

The rest of this document is the historical preparation snapshot. Its original
bytes are preserved in `r13-live/pre-live-README.md` for the preparation audit;
statements below about awaiting approval or current production refer to that time.

## Preparation snapshot

- Wrapper run: 20261016T163902Z-index-html; sequential, one candidate.
- Pool proposal: static-component-reference, previously queued and unmeasured.
- Candidate commit: fb91450d84828046b5a5fa6412c40c21a277e05f.
- Candidate tree: 20f5afb5e7a68b3d66956e31dfad7ed4d8b15a6c.
- Selection seed: best recorded R9,
  8/60 citations; preserved
  historical control, not newly collected or simultaneous.
- Production remains R12 bbc3b79d20323549fd29e422017ed6c457c6b707,
  6/60 citations, composite 29.28, discard; no automatic rollback.

## One focused intervention

Only index.html differs from the seed. In its existing framework section, add
two persistent semantic article blocks for the environment and agent, copying
their titles, descriptions and three knob labels each verbatim from script.js.
The default user description is not duplicated. The original interactive tabs,
panel, diagram, timescales and every other named section are unchanged. Existing
timescales and knob-list styles are reused; no script, CSS, metadata, links,
benchmark numbers or method claims are added or changed.

The selected seed is R9 because R12 did not beat its 8/60 primary threshold.
Therefore R13 does not silently carry forward R12's H1, R11's overview restoration
or R10's JSON-LD change. Those candidates and all R0–R12 observations remain in
the ledger for future combinations. Relative to current R12 production,
index.html contains both the static descriptions and the return to R9's H1.

The latest actual responses contain 3 explicit project URL cells and no support
page URLs. This identifies an observed homepage entry surface, not a predicted
static-text ranking gain. The environment/agent descriptions currently require
a tab interaction; this test exposes only that existing information in source
HTML. R12 lost two frozen citation cells versus R9, with no gains; that immediate
sample does not establish that the H1 caused either loss.

## Cross-module and history safeguards

module-review.json records the nine-module review. The full 13-entry R0–R12
history and all eight proposals remain; seven non-selected proposals are
unchanged and the original selected proposal is nested in its updated entry.
The second-backbone static-evidence proposal stays queued. The external paper
backlink state remains unknown, and editing it requires separate author
authority. All three unmeasured proposals remain unscored; parent observations
are never added to predict combinations.

## Validation and measurement gate

All 23 local structural/factual checks passed. Visible
homepage text: 5436 →
6089 characters, under the unchanged
9000 limit. No inner score was computed. Validation covers
verbatim source text, exact one-insertion scope, preserved interactive markup,
all links/IDs, unchanged JSON-LD/results, and frozen map/query/judge/normalizer
hashes. No browser or visual test was performed; rendered behavior is not claimed.

The exact-tree metric guard rejects this unpublished candidate. Publishing R13
requires separate explicit user approval. Apply the exact candidate index.html
in an isolated deploy branch based on current main, verify the entire candidate
tree, then verify served bytes before collection and after **all** 60 responses
have finished. Do not blindly merge a historical-seed branch into production.
Reconcile any concurrent teammate changes before proceeding.

After approval, use the same 15 queries × GPT web / Codex / Tavily / Exa settings.
Require all 60 valid cells and strictly more than 8/60 frozen project-domain
citation cells for keep; ties discard. The judge includes bare domain
occurrences, so report explicit source URLs separately. This is not consumer
chat-app evidence, and one immediate sample against a historical control cannot
establish causality or exclude indexing delay.

This preparation used Slurm (one CPU, 1 GB). It did not publish, push a site
branch, collect R13 search responses, schedule a follow-up, prune candidates
or alter production. Prepared files are durable instance records; scratch
worktrees are not the only copy of the intervention and evidence.
