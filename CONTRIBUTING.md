# Contributing

Thanks for contributing to `autoresearch-wrapper`.

## Branch Layout

- `main` is the Codex-first branch.
- `claude-code-skill` carries the Claude Code skill packaging experiments and project-local `.claude/skills/` files.
- Shared wrapper behavior should live in the Python CLI, not in platform-specific packaging.

## Scope

This branch contains:
- the Codex skill definition in `SKILL.md`
- Codex metadata in `agents/openai.yaml`
- the helper CLI in `scripts/autoresearch_wrapper.py`
- the main implementation in `autoresearch_wrapper/core.py`
- tests in `tests/`
- user docs in `README.md` and `README.zh-CN.md`

## Local Setup

Clone the repo and work from the repo root.

To test this branch as a local Codex skill:

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/autoresearch-wrapper ~/.codex/skills/autoresearch-wrapper
```

Restart Codex after installing or updating the skill.

If you are working on Claude Code packaging, do that on the `claude-code-skill` branch instead of adding `.claude/skills/` files to `main`.

## Development Workflow

1. Make the smallest coherent change you can.
2. Keep shared behavior in the wrapper CLI and state model.
3. If the CLI or command surface changes, update:
   - `README.md`
   - `README.zh-CN.md`
   - `SKILL.md`
4. If behavior changes, add or update tests in `tests/test_autoresearch_wrapper.py`.
5. Keep the worktree-first design intact. New optimization features should prefer Git worktrees over mutating the primary checkout.
6. Keep dependency-aware behavior explicit. If a new feature affects part discovery, readiness, run gating, or metric flow, update the persisted state and status surfaces accordingly.

## Verification

Run these checks before opening a PR or pushing a branch:

```bash
python3 -m py_compile autoresearch_wrapper/core.py scripts/autoresearch_wrapper.py
python3 -m unittest -q
```

## Documentation Expectations

- Keep the English and Chinese READMEs aligned.
- Keep examples consistent with the actual CLI behavior.
- If you add a new command, status view, generated artifact, or workflow step, document it in both READMEs and in `SKILL.md`.
- Keep upstream attribution current in `THIRD_PARTY_NOTICES.md` when reference usage changes.

## Commit Guidance

- Use clear commit messages that describe the feature or fix.
- Avoid committing runtime state such as `.autoresearch-wrapper/`.
- Do not commit local Codex home changes from `~/.codex/`.
- Keep platform packaging changes scoped. Codex packaging belongs on `main`; Claude Code packaging belongs on `claude-code-skill`.

## Good First Contributions

- Improve dependency extraction for additional languages.
- Add new metric presets or metric-flow views.
- Improve status rendering and planning artifacts.
- Expand tests around run resume, plotting, and script-wrapper flows.
- Improve shared docs while keeping Codex and Claude branch responsibilities clear.
