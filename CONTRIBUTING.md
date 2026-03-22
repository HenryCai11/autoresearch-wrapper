# Contributing

Thanks for contributing to `autoresearch-wrapper`. Bug reports and feature requests are welcome. Although I have limited bandwidth, I will take a look at the issues/PRs and find a way to resolve/merge them!

## Scope

This repo contains:
- the Codex skill definition in `SKILL.md`
- the Claude Code skill definitions under `.claude/skills/`
- the helper CLI in `scripts/autoresearch_wrapper.py`
- the main implementation in `autoresearch_wrapper/core.py`
- tests in `tests/`
- user docs in `README.md` and `README.zh-CN.md`

## Local Setup

Clone the repo and run from the repo root.

### Codex

To test the skill locally inside Codex, install it as a local skill:

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/autoresearch-wrapper ~/.codex/skills/autoresearch-wrapper
```

Restart Codex after installing or updating the skill.

### Claude Code

Claude Code can load the project-local skills from this repo directly through:

```text
.claude/skills/
```

The current Claude-facing commands are:
- `/autoresearch-wrapper`
- `/autoresearch-wrapper-status`
- `/autoresearch-wrapper-run`
- `/autoresearch-wrapper-flow`
- `/autoresearch-wrapper-create`
- `/autoresearch-wrapper-delete`
- `/autoresearch-wrapper-monitor`

If you change Claude-specific skill behavior, update the corresponding `SKILL.md` files under `.claude/skills/`.

## Development Workflow

1. Make the smallest coherent change you can.
2. If the CLI or command surface changes, update:
   - `README.md`
   - `README.zh-CN.md`
   - `SKILL.md`
   - relevant `.claude/skills/*/SKILL.md` files when the Claude command surface is affected
3. If behavior changes, add or update tests in `tests/test_autoresearch_wrapper.py`.
4. Keep the worktree-first design intact. New optimization features should prefer Git worktrees over mutating the primary checkout.
5. Keep dependency-aware behavior explicit. If a new feature affects part discovery, readiness, or run gating, update the persisted state and status surfaces accordingly.

## Skill Surfaces

### Codex

Codex uses:
- `SKILL.md`
- `agents/openai.yaml`

The Codex-facing command surface is:
- `/autoresearch-wrapper`
- `/autoresearch-wrapper:status`
- `/autoresearch-wrapper:run`
- `/autoresearch-wrapper:flow`
- `/autoresearch-wrapper:create`
- `/autoresearch-wrapper:delete`
- `/autoresearch-wrapper:monitor`

### Claude Code

Claude Code uses:
- `.claude/skills/autoresearch-wrapper/SKILL.md`
- `.claude/skills/autoresearch-wrapper-status/SKILL.md`
- `.claude/skills/autoresearch-wrapper-run/SKILL.md`
- `.claude/skills/autoresearch-wrapper-flow/SKILL.md`
- `.claude/skills/autoresearch-wrapper-create/SKILL.md`
- `.claude/skills/autoresearch-wrapper-delete/SKILL.md`
- `.claude/skills/autoresearch-wrapper-monitor/SKILL.md`

Claude does not use `agents/openai.yaml`, so do not treat the Codex metadata file as shared packaging.

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
- If the change also affects Claude Code usage, update the matching `.claude/skills/` files.

## Commit Guidance

- Use clear commit messages that describe the feature or fix.
- Avoid committing runtime state such as `.autoresearch-wrapper/`.
- Do not commit local Codex home changes from `~/.codex/`.
- Keep Codex-specific and Claude-specific packaging changes scoped and explicit. Shared behavior belongs in the Python CLI; packaging differences belong in the skill files.

## Good First Contributions

- Improve dependency extraction for additional languages.
- Add new metric presets or metric-flow views.
- Improve status rendering and planning artifacts.
- Expand tests around run resume, plotting, and script-wrapper flows.
- Improve parity between Codex and Claude Code skill instructions without forking the shared CLI behavior.
