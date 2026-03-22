<div align="center">

![Autoresearch Wrapper Banner](./assets/banner.svg)

# Autoresearch Wrapper

**Dependency-aware optimization engine for any codebase.**

Scan, plan, isolate, measure, repeat — all in Git worktrees, hands-free.

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) — constraint + mechanical metric + autonomous iteration = compounding gains.

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-green?logo=openai&logoColor=white)](https://platform.openai.com/docs/codex)
[![Version](https://img.shields.io/badge/version-0.0.2-blue.svg)](https://github.com/HenryCai11/autoresearch-wrapper/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Inspired by](https://img.shields.io/badge/Based_on-Karpathy's_Autoresearch-orange)](https://github.com/karpathy/autoresearch)

<br>

*"Scan the repo → Pick a target → Lock the metric → Claude/Codex runs the loop → You wake up to results"*

<br>

[Install](#install) · [Usage](#usage) · [Commands](#commands) · [Docs](./DETAILS.md) · [简体中文](./README.zh-CN.md)

</div>

---

Recently, I've been asking Codex to write autoresearch wrappers for the modules that I want to optimize. There's a concrete use case where I want to add a feature or module, and I have several candidates. But each time you add one, you need to optimize all the other related parts to get a sense of how helpful the module is (`autoresearch-wrapper-create`). That's when I wanted to implement a SKILL for this, and I thought that at the very beginning, before optimizing a system, we should understand the dependencies. So here it comes: a Dependency-aware Autoresearch Engine that wraps your modules, scripts, and more.

## News

- 2026/03/23 2:31 AM, Beijing Time: I've decided to release it at v0.0.2! Just feel excited to share it with the community. Although I'm still going through all the features to make sure they are everything I want, I think it is ready to play with.

## Install

<details open>
<summary><b>Claude Code (recommended)</b></summary>

```bash
/plugin marketplace add HenryCai11/autoresearch-wrapper
```

To update to the latest version:

```bash
/plugin update autoresearch-wrapper
```

To uninstall:

```bash
/plugin remove autoresearch-wrapper
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

Just run
```
/autoresearch-wrapper
```
This will start a wizard guiding you to start your optimization step-by-step.

## Examples

An example of the wizard for optimizing [Recursive Language Models](https://github.com/alexzhang13/rlm)

![example_rlm](assets/example_rlm.png)

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


## Acknowledgment

I'm inspired by several autoresearch projects. They are [Karpathy's autoresearch](https://github.com/karpathy/autoresearch), and [uditgoenka's autoresearch](https://github.com/uditgoenka/autoresearch). Thanks!