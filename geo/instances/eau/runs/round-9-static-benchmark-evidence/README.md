# EAU R9 — static default benchmark evidence

Status: **published and measured; keep**. See the authoritative
[live report](r9-live/REPORT.md) and [current state](CURRENT.json).

Published as `52dee0ba78885b9a3028760ba8d9cfc749a6c2e7`; served homepage
bytes verified before and after collection. All 60 frozen cells were valid.
Project-domain citation cells increased from R8's 6/60 (10.00%) to 8/60
(13.33%); the secondary composite changed from 28.64 to 30.25. The two gained
cells were Codex search; GPT web, Tavily and Exa citation counts were unchanged.
Explicit project URL cells increased from 3 to 5; the frozen citation judge also
counts bare project-domain mentions. This immediate single sample against a
reused historical control does not establish a causal effect.

Preparation snapshots (`change.json`, `candidate-pool-before.json`,
`candidate-pool-selected.json`, `candidate-pool-after.json`) remain unchanged;
their pre-publication states are historical, not the current status.

- Run: `20261016T125445Z-index-html`; sequential, one candidate.
- Existing pool proposal: `static-benchmark-evidence`; round change: `r9-static-benchmark-evidence`.
- Base production: `4147abc262bbb69df7a170eb403bf1b6807869f4` (R8).
- Candidate: `9bb531cc09d8b7dda5a3148c5df3c5e62107892b`; tree `5ebd5d1c28e00690d58caafa0edfe066ae5307d7`.
- Outer-only primary: fixed four-engine project-domain citation rate, maximize.
- Baseline: preserved [R8 live record](../round-8-reference-cluster/r8-live/REPORT.md),
  6/60 citations, composite 28.64, all 60 valid; not a newly collected R9 control.

## Dependency-aware intervention

R8 produced no explicit support-page URLs. The homepage did appear in three
cells, but its default chart grid and full result-table body were empty before
JavaScript ran. R9 selects a queued candidate to test evidence availability on
that observed entry surface. Source visibility is not predicted intervention lift.

| Module | Role in R9 | Changed? |
| --- | --- | --- |
| `index.html#results` | Pre-render three Qwen3-4B chart cards and the existing nine-method table | Yes |
| `script.js` | Authoritative existing data and unchanged interactive renderer | No |
| `paper.html` | Cross-check overlapping EAU headline results and their scope | No |
| R8 reference cluster | Retained context and citation routes | No |

The HTML is generated from the actual existing `renderResults` output, not
retyped or newly invented measurements. The JavaScript still initializes and
handles switching models as before. A minimal DOM-stub test exercises the
unchanged renderer for both models and a switch back; it is **not** a full-browser
test. The default static cards/table exactly match that renderer output.

Only `section:results` was edited via `geo-apply` in an allocated worktree.
The no-JavaScript message now explains that default results are available and
JavaScript enables switching. Default HTML text grew from
5051 to 5436
characters, below the existing limit of 9000. No inner score
was computed. Styles, scripts, metadata, all other pages, facts, query set,
knowledge map and scorer are unchanged.

## Retention and measurement record

Before/after [candidate ledger](../../candidate-pool.json) snapshots are retained
here. The live archive adds before/after-record snapshots. R0–R9 and all five
existing proposals remain available; three proposals remain unmeasured. Queued
combinations are not ranked by adding historical metrics.

The login-node Node executable was unavailable on compute. Discovery used
`module spider nodejs` and `module spider nodejs/20.16.0`; the Slurm validation
job explicitly loaded `StdEnv/2023 nodejs/20.16.0`. No installation or compute
was performed on the login node.

After explicit R9 publication approval, the homepage was byte-verified and the
unchanged 15 queries × four engines were collected. Complete real observations
were registered for the exact deployed Git tree before the wrapper evaluated
and recorded the candidate. The portable archived metric replays as 10.00 for
the seed and 13.3333 for R9. The baseline, raw responses, statuses, timestamps,
integrity hashes and operational scripts are preserved in `r9-live/`.
An immediate observation cannot establish a causal lift or exclude indexing lag.
R9 remains live. No future follow-up, rollback or pruning has been scheduled.
