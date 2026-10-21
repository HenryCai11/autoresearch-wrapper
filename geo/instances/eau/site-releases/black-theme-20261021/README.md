# Black theme and link icons — user-requested visual release

Published production `da847eb38d09b76a9dc2a50d064ac164b5a038cf`, tree `4cf91286a8bb895bfff0a0aee9196536390f7ca1`,
source branch `codex/black-theme-icons`, source commit `5d1b0d71782ebd06d72d9ad1fb76d0c80b8374bf`.
Explicit authorization: black background, icons such as GitHub, then direct push.
All four changed served resources match the exact production/worktree bytes at
2026-10-21T15:52:48Z. Initial stale CDN checks are retained.

Black page canvas, dark panels, light text and existing warm/sage accents cover
the shared stylesheet. Adapted charts/diagram/citation panels retain all data.
Two Code links use GitHub marks and two alphaXiv buttons use document icons;
text labels, destinations, accessibility and external-link behavior remain.
Icons are local SVG symbols with the official primer/octicons GitHub path and
included MIT license; the document symbol is a simple original outline.
Narrow-screen navigation wraps to keep every link inside the viewport.

22 structural/content/contrast checks passed before narrow-screen polish;
ten palette text contrasts are at least 7.9:1. Final real Chrome desktop and
narrow-screen checks confirm black body, visible code links, valid icon symbols,
default and second-model switching/restoration, no horizontal overflow and
navigation within the viewport. Screenshots are desktop.png, mobile.png and
results.png (full page, including the result area). Initial anchor-scrolled
capture was empty, so final capture uses a full-height viewport; no website
content was changed for screenshotting. Browser jobs run on Slurm CPU nodes,
with ephemeral profiles in SLURM_TMPDIR, durable outputs in scratch. No package
installation, login-node browser/Python/Node or local model inference.

Only index.html, styles.css and the two icon/license assets differ from the
previous measured R22 production. Visible text, link destinations, research
figures, numerical results, metadata/JSON-LD, code URL and all alphaXiv routing
remain unchanged. The six source-code/reading entry labels remain accessible.

This release is **not a GEO measurement**. R22's 12/60 primary and 30.47 composite
belong to the earlier exact tree `1ac57c63402d39d6f7738414ff00bf9837305759` at production
`7eafc96a295ba8c155f7c31368b0d67d800bee20`. The archived metric correctly rejects this
new tree with exit 2. No extra paid search, inner score, new optimization round,
candidate promotion, rollback, pruning or deletion was performed. All 23
historical observations, sixteen proposals and best R18 remain unchanged;
only current deployment pointers and user presentation constraints are updated.
