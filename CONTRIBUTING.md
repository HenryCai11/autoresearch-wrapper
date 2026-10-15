# Contributing

Thanks for contributing to `autoresearch-wrapper`. Bug reports and feature requests are welcome. Although I have limited bandwidth, I will take a look at the issues/PRs and find a way to resolve/merge them!

## Scope

This repo contains:
- one skill set under `skills/`, shared by Claude Code and Codex (one directory per command)
- `.claude/skills` and `.agents/skills`, symlinks to `skills/` for project-local discovery
- the Claude marketplace manifest in `.claude-plugin/marketplace.json`
- the packaged Claude plugin under `plugins/autoresearch-wrapper/` (generated)
- the helper CLI in `scripts/autoresearch_wrapper.py`
- the main implementation in `autoresearch_wrapper/core.py`
- tests in `tests/`
- user docs in `README.md` and `README.zh-CN.md`

## Local Setup

Clone the repo and run from the repo root. Inside the repo, both tools find the skills without any install step:
- Claude Code reads `.claude/skills/` (invoke as `/autoresearch-wrapper-run`)
- Codex reads `.agents/skills/` (invoke as `$autoresearch-wrapper-run`)

To use your working copy from other projects, symlink the skill folders into your user directory (`~/.claude/skills/` and/or `~/.agents/skills/`):

```bash
ln -s /path/to/autoresearch-wrapper/skills/* ~/.agents/skills/
```

Restart Codex after installing or updating skills.

## Development Workflow

1. Make the smallest coherent change you can.
2. If the CLI or command surface changes, update:
   - `README.md` and `README.zh-CN.md`
   - the affected `skills/*/SKILL.md` files
   - `plugins/autoresearch-wrapper/` by running `python3 scripts/sync_claude_plugin.py`
3. If behavior changes, add or update tests in `tests/test_autoresearch_wrapper.py`.
4. Keep the worktree-first design intact. New optimization features should prefer Git worktrees over mutating the primary checkout.
5. Keep dependency-aware behavior explicit. If a new feature affects part discovery, readiness, or run gating, update the persisted state and status surfaces accordingly.

## Skills

`skills/` is the only place skill instructions are written. Both tools load the same `SKILL.md` format (`name` + `description` frontmatter), so:
- Write instructions that work in both tools. Refer to companion skills by name (`autoresearch-wrapper-run`); where invocation syntax matters, give both forms (`/name` in Claude Code, `$name` in Codex).
- Each skill's launcher block must find its own `run.sh` in Claude Code locations (`CLAUDE_SKILL_DIR`, `CLAUDE_PLUGIN_ROOT`, `.claude/skills`) and Codex locations (`.agents/skills`, `~/.agents/skills`). `run.sh` resolves symlinks before searching for the CLI, so symlinked installs work.
- Tool-specific packaging stays separate from the instructions:
  - Codex UI metadata: `skills/autoresearch-wrapper/agents/openai.yaml`
  - Claude marketplace: `.claude-plugin/marketplace.json` and `plugins/autoresearch-wrapper/.claude-plugin/plugin.json`

Two generated copies exist, and both are written only by `python3 scripts/sync_claude_plugin.py`:
- `plugins/autoresearch-wrapper/skills/`: the marketplace package
- the root `SKILL.md`: a copy of `skills/autoresearch-wrapper/SKILL.md`, so the repo root can be installed as one comprehensive skill (with the root `run.sh` symlink as its launcher)

Never edit those copies by hand. `test_skills_have_a_single_source` fails if either drifts from `skills/`, if the symlinks change, or if a launcher block misses a location.

## Verification

Run these checks before opening a PR or pushing a branch:

```bash
python3 scripts/sync_claude_plugin.py
python3 -m py_compile autoresearch_wrapper/core.py scripts/autoresearch_wrapper.py
python3 -m unittest -q
claude plugin validate .
```

## Documentation Expectations

- Keep the English and Chinese READMEs aligned.
- Keep examples consistent with the actual CLI behavior.
- If you add a new command, status view, or generated artifact, document it in both READMEs and in the relevant `skills/*/SKILL.md`.

## Commit Guidance

- Use clear commit messages that describe the feature or fix.
- Avoid committing runtime state such as `.autoresearch-wrapper/`.
- Do not commit local tool home changes from `~/.codex/`, `~/.agents/`, or `~/.claude/`.
- Shared behavior belongs in the Python CLI and the shared skills; only packaging differs per tool.

## Good First Contributions

- Improve dependency extraction for additional languages.
- Add new metric presets or metric-flow views.
- Improve status rendering.
- Expand tests around run resume, plotting, and script-wrapper flows.
