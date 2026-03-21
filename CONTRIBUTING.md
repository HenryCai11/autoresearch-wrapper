# Contributing

Thanks for contributing to `autoresearch-wrapper`.

## Scope

This repo contains:
- the Codex skill definition in `SKILL.md`
- the helper CLI in `scripts/autoresearch_wrapper.py`
- the main implementation in `autoresearch_wrapper/core.py`
- tests in `tests/`
- user docs in `README.md` and `README.zh-CN.md`

## Local Setup

Clone the repo and run from the repo root.

To test the skill locally inside Codex, install it as a local skill:

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/autoresearch-wrapper ~/.codex/skills/autoresearch-wrapper
```

Restart Codex after installing or updating the skill.

## Development Workflow

1. Make the smallest coherent change you can.
2. If the CLI or command surface changes, update:
   - `README.md`
   - `README.zh-CN.md`
   - `SKILL.md`
3. If behavior changes, add or update tests in `tests/test_autoresearch_wrapper.py`.
4. Keep the worktree-first design intact. New optimization features should prefer Git worktrees over mutating the primary checkout.
5. Keep dependency-aware behavior explicit. If a new feature affects part discovery, readiness, or run gating, update the persisted state and status surfaces accordingly.

## Verification

Run these checks before opening a PR or pushing a branch:

```bash
python3 -m py_compile autoresearch_wrapper/core.py scripts/autoresearch_wrapper.py
python3 -m unittest -q
```

## Documentation Expectations

- Keep the English and Chinese READMEs aligned.
- Keep examples consistent with the actual CLI behavior.
- If you add a new command, status view, or generated artifact, document it in both READMEs and in `SKILL.md`.

## Commit Guidance

- Use clear commit messages that describe the feature or fix.
- Avoid committing runtime state such as `.autoresearch-wrapper/`.
- Do not commit local Codex home changes from `~/.codex/`.

## Good First Contributions

- Improve dependency extraction for additional languages.
- Add new metric presets or metric-flow views.
- Improve status rendering and planning artifacts.
- Expand tests around run resume, plotting, and script-wrapper flows.
