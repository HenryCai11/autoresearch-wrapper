# EAU R11 — retained reference cluster without R7 overview

Status: **validated local candidate; not published or measured**.

- Run: `20261016T140844Z-index-html`; sequential, one candidate.
- Existing pool proposal: `reference-cluster-without-r7`.
- Candidate: `8e9ed309a7a60fb31cef6649f12374ad801f2a4b`; tree `ccf91bf07379aae81ec4ba3c698803d0bd69368c`.
- Selection seed: R9 `52dee0ba78885b9a3028760ba8d9cfc749a6c2e7`, the best fully
  observed checkpoint under the current outer protocol: 8/60, composite 30.25.
- Current production: R10 `b70597085286d4ff4c2d3de78f25d95581835b98`, still live,
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
6. The frozen judge also counts bare project-domain mentions. R11 currently has
no registered live observation; the metric guard refuses to score its tree.

Publishing requires new explicit approval. Relative to current R10, the full
candidate differs in **four** files: `index.html`, `method.html`, `paper.html`,
`research-context.html`, because R10's JSON-LD must also be excluded. A blind
Git merge of this R9-based branch into R10 would retain that delta and would NOT
publish the measured candidate tree. After approval, prepare an isolated deploy
branch from current main, apply the saved `production-to-candidate.patch`, and
verify the entire tree equals `ccf91bf07379aae81ec4ba3c698803d0bd69368c` before merging and
pushing. Never overwrite concurrent teammate edits without inspecting them.

Then verify all four served pages before and after real collection; register the
exact tree and frozen query/matrix hashes, evaluate and record through the CLI.
Selection, deployment and causal inference are separate. A historical control
and immediate sample cannot exclude index lag or search variance.

Eleven historical versions (R0–R10) and all five existing proposals are preserved.
Preparation, checks and metric replay run through Slurm (one CPU, 1 GB).
No publishing, wrapper push, rollback, branch pruning, candidate deletion or
future follow-up was performed or scheduled by this preparation.
