# EAU R11 — retained reference cluster without R7 overview

Status: **published and measured; discard**. See the authoritative
[live report](r11-live/REPORT.md) and [current state](CURRENT.json).

Published as `c744ba125108d003ea61e8b89807e274ffaa6e4e`, using deploy commit
`41b1311b2d37314d5bf67419e628a6bf71782470`. Candidate, deploy and production
trees are identical. All four pages matched before and after collection; all
60 responses were valid. Primary citation cells changed from the R9 control's
8/60 (13.33%) to 7/60 (11.67%); secondary composite 30.25 → 28.97. The previously
deployed R10 had 6/60 and 28.06, but that lower result is not the keep threshold.
Explicit project URL cells: 4/60; support-page URLs: 0. The frozen citation judge
also counts bare project-domain mentions. This single immediate observation
against a historical control is not a causal estimate.

Preparation snapshots (`change.json`, ledger snapshots and root `audit.json`)
remain historical. The original README and registry are preserved in
`r11-live/pre-live-README.md` and `pre-live-outer-measurements.json`; the live
audit verifies preparation hashes using those originals.

- Run: `20261016T140844Z-index-html`; sequential, one candidate.
- Existing pool proposal: `reference-cluster-without-r7`.
- Candidate: `8e9ed309a7a60fb31cef6649f12374ad801f2a4b`; tree `ccf91bf07379aae81ec4ba3c698803d0bd69368c`.
- Selection seed: R9 `52dee0ba78885b9a3028760ba8d9cfc749a6c2e7`, the best fully
  observed checkpoint under the current outer protocol: 8/60, composite 30.25.
- Previous production: R10 `b70597085286d4ff4c2d3de78f25d95581835b98`,
  recorded discard at 6/60, composite 28.06. It is context, not the keep threshold.
- Both observations are preserved historical samples; no fresh control was run.

## Candidate and module reuse

The original queued proposal tested the R8 reference cluster without the R7
overview, based on R6. R11 rebases that idea on the stronger R9 seed, retaining
the R9 static benchmark evidence. The original proposal is preserved in the
ledger's `original_proposal` and before-round snapshot. No parent score is added
or treated as a combination score.

Only `index.html#overview` differs from R9: it is restored verbatim from R6
`e6b74d333b09c30619d5c3c61c95fa066ee50188` through `geo-apply`. R8 reference routes,
R9 static results, metadata, scripts, styles, other sections and all other files
remain byte-identical to R9. No new facts or data are introduced. R10's unkept
JSON-LD delta is not carried forward, but its commit, proposal and measurements
are retained. This is a fixed combination test, not a tuned module-deletion
comparison or proof of a causal R7 effect.

All 17 local checks passed. Homepage visible text:
5436 → 5349
characters, below the unchanged 9000 limit. No inner score was
computed. This was a structural/source-preservation check, not a browser test.

## Selection and publication gate

The unchanged 15 queries × four engines (GPT web, Codex search, Tavily, Exa)
remain the outer metric. All 60 responses must be valid. A keep requires strictly
more than the R9 seed's 8 project-domain citation cells, not just beating R10's
6. The frozen judge also counts bare project-domain mentions. The completed live
observation is now registered for the exact R11 tree. Portable metric replays are
13.3333 for the R9 seed and 11.6667 for R11; no inner score was used.

The user explicitly approved publishing and measuring R11. Relative to R10, the full
candidate differs in **four** files: `index.html`, `method.html`, `paper.html`,
`research-context.html`, because R10's JSON-LD must also be excluded. A blind
Git merge of this R9-based branch into R10 would retain that delta. Publication
therefore used an isolated deploy branch based on R10, with exact candidate file
content applied through `apply_patch`. The entire tree was verified as
`ccf91bf07379aae81ec4ba3c698803d0bd69368c` before merging and pushing. The original
candidate branch and the separate deploy branch are both preserved. No concurrent
teammate edits were overwritten.

All four served pages were verified before and after real collection. The exact
tree and frozen query/matrix hashes were registered before CLI evaluation and
recording. Raw responses, request settings, timestamps, integrity hashes and
operational scripts are preserved in `r11-live/`.
Selection, deployment and causal inference are separate. A historical control
and immediate sample cannot exclude index lag or search variance.

Twelve historical versions (R0–R11) and all five existing proposals are preserved;
the external-paper proposal remains unmeasured and requires separate authority.
Preparation, checks and metric replay run through Slurm (one CPU, 1 GB).
R11 remains live despite the selection discard. No post-measurement rollback,
branch pruning, candidate deletion or future follow-up was performed or scheduled.
