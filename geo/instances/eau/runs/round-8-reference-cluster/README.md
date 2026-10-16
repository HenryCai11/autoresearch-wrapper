# EAU R8 — cross-module reference cluster

Status: **deployed and measured**. See [live results](r8-live/REPORT.md).
Production merge: `4147abc262bbb69df7a170eb403bf1b6807869f4`.
All 60 responses were valid; project-domain citations tied R7 at 6/60 (10%).
The legacy outer composite changed from 29.44 to 28.64; selection was `discard`.
R8 remains online. The paragraphs below document the original preparation plan;
`change.json` preserves that snapshot, while `CURRENT.json` and `r8-live/` are
the authoritative deployed result and decision records.

- Run: `20261016T120835Z-index-html`; sequential, one candidate.
- Logical dependency root: `index.html`; actual editable scope is the four files below.
- Base production: `fbd9e100b6ae71704a0cf65b1a1b9b87dbdc4ef7` (R7).
- Candidate: `a2e3d0163fa55384c1f949b6da6c6fef1ea486fc`; tree `b3d011a5256d81aac31840cc7183b8fb5fa7a405`.
- Primary metric: unchanged four-engine project-domain citation rate; inner ignored.
- Seed: reused [R7 live observation](../round-7-static-mechanism-overview/r7-live/REPORT.md),
  6/60 citations (10%), 60/60 valid responses; not a fresh R8 control search.

| Module | R8 change | Historical components reused |
| --- | --- | --- |
| `method.html` | Visible links to paper evidence, context, text summary and canonical homepage | R2 + R6 |
| `research-context.html` | Visible links to method, paper evidence, text summary and homepage | R3 + R2 + R4 + R6 |
| `paper.html` | Visible links to method, context, text summary and homepage | R4 + R2 + R3 + R6 |
| `llms.txt` | Complete the canonical resource list; avoid a duplicate context URL | R1 + R2 + R3 + R4 |

The homepage, existing main content, metadata, authors, results, stylesheet,
scripts, crawler files and repository authority record are unchanged.
This tests the reference-route bundle, not the isolated effect of any one page.
No unmeasured combination is ranked by adding historical scores.

The [instance ledger](../../candidate-pool.json) preserves eight historical
versions before R8 and five proposals, including discarded candidates and queued combinations.
After recording R8 it contains nine historical versions and four still-unmeasured proposals.
This is agent-maintained instance data, not an automatic wrapper-core scheduler.

`module-graph-before.json`, `module-graph-after.json`, and the edge delta record
the complete local reference graph. The generic graph helper exposes support HTML
without edit operations and omits `llms.txt`, so the four-file patch was applied
explicitly inside the allocated worktree; scorer code was not changed.

After explicit publication approval, **all four changed resources** were verified
against the candidate bytes before and after searching. The unchanged homepage
was not used as proof of R8 deployment. The same 15 queries × four engines were
collected, raw attempts retained, and matched valid cells compared. The candidate
was evaluated and recorded only after complete real observations for its exact
Git tree had been registered.
Publishing, measurement and keep/discard are separate actions. No automatic
rollback, cleanup, or future measurement has been scheduled.
