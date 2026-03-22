<div align="center">

![Autoresearch Wrapper Banner](./assets/banner.svg)

# Autoresearch Wrapper

**Dependency-aware optimization engine for any codebase.**

Scan, plan, isolate, measure, repeat — all in Git worktrees, hands-free.

Based on [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — constraint + mechanical metric + autonomous iteration = compounding gains.

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-green?logo=openai&logoColor=white)](https://platform.openai.com/docs/codex)
[![Version](https://img.shields.io/badge/version-0.0.2-blue.svg)](https://github.com/HenryCai11/autoresearch-wrapper/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Based on](https://img.shields.io/badge/Based_on-Karpathy's_Autoresearch-orange)](https://github.com/karpathy/autoresearch)

<br>

*"Scan the repo → Pick a target → Lock the metric → Claude/Codex runs the loop → You wake up to results"*

<br>

[Install](#install) · [Usage](#usage) · [Commands](#commands) · [Docs](./DETAILS.md) · [简体中文](./README.zh-CN.md)

</div>

---

## Install

<details open>
<summary><b>Claude Code (recommended)</b></summary>

```bash
/plugin add HenryCai11/autoresearch-wrapper
```

Or install manually:

```bash
git clone https://github.com/HenryCai11/autoresearch-wrapper.git
```

Claude Code discovers skills from `.claude/skills/` automatically. If the repo lives outside your project, symlink:

```bash
mkdir -p /path/to/your-project/.claude/skills
ln -s /path/to/autoresearch-wrapper/.claude/skills/* /path/to/your-project/.claude/skills/
```

</details>

<details>
<summary><b>Codex</b></summary>

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/autoresearch-wrapper ~/.codex/skills/autoresearch-wrapper
```

Restart Codex after installing.

</details>

<details>
<summary><b>CLI only</b></summary>

No installation needed — run directly:

```bash
python3 scripts/autoresearch_wrapper.py scan
```

</details>

## Usage

### 1. Scan

```bash
python3 scripts/autoresearch_wrapper.py scan
```

Or via skill: `/autoresearch-wrapper scan this repo`

### 2. Configure

```bash
python3 scripts/autoresearch_wrapper.py configure \
  --part src/api.py \
  --metric latency_ms \
  --metric-command "python bench.py" \
  --metric-goal minimize \
  --mode sequential \
  --rounds 5
```

Or use the interactive wizard: `--interactive`

### 3. Run

```bash
python3 scripts/autoresearch_wrapper.py run
```

The wrapper creates a seed worktree, generates a `program.md`, and starts the optimization loop.

### 4. Monitor

```bash
python3 scripts/autoresearch_wrapper.py flow          # metric history + ASCII plot
python3 scripts/autoresearch_wrapper.py monitor        # live progress polling
python3 scripts/autoresearch_wrapper.py status         # full state summary
```

## Commands

| Codex | Claude Code | CLI | What it does |
| --- | --- | --- | --- |
| `/autoresearch-wrapper` | `/autoresearch-wrapper` | `scan` / `wrap` | Scan repo or wrap a script |
| `:status` | `-status` | `status` | Show state and readiness |
| `:run` | `-run` | `run` | Start or resume a run |
| `:flow` | `-flow` | `flow` | Metric history and plot |
| `:create` | `-create` | `create` | Multi-candidate feature addition |
| `:delete` | `-delete` | `delete` | Post-deletion optimization |
| `:monitor` | `-monitor` | `monitor` | Live progress polling |

Additional CLI subcommands: `configure`, `allocate`, `evaluate`, `record`, `resources`, `preset-metric`, `reference`

## Testing

```bash
python3 -m unittest -q
```

## Documentation

| Doc | Contents |
| --- | --- |
| [DETAILS.md](./DETAILS.md) | Feature details, dependency graph notes, generated layout, typical workflow |
| [CORE_FEATURES.md](./CORE_FEATURES.md) | Feature checklist (Chinese) |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Development workflow, branch layout, verification |
| [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) | Upstream attribution |
