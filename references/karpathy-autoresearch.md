# Karpathy Autoresearch Reference

This skill uses `https://github.com/karpathy/autoresearch` as a reference for the run loop shape, not as a runtime dependency.

Use it when you need to remember the upstream design:
- lightweight `program.md` per run
- explicit baseline and experiment loop
- append-only experiment logging

This wrapper intentionally differs from upstream:
- it scans a repo before running experiments
- it classifies parts as `surely optimizable` or `probably optimizable`
- it persists repo-level state in `.autoresearch-wrapper/state.json`
- it isolates experiments in Git worktrees instead of mutating one long-lived branch

To read the upstream code, clone it somewhere outside your target repo:

```bash
git clone https://github.com/karpathy/autoresearch.git
```

