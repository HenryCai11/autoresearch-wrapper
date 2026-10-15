<div align="center">

![Autoresearch Wrapper Banner](./assets/banner.svg)

# Autoresearch Wrapper

**面向任意代码仓库的 dependency-aware 优化引擎。**

扫描、规划、隔离、测量、迭代 —— 全部在 Git worktree 中自动完成。

基于 [Karpathy 的 autoresearch](https://github.com/karpathy/autoresearch) —— 约束 + 机械化指标 + 自主迭代 = 持续增益。

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-green?logo=openai&logoColor=white)](https://platform.openai.com/docs/codex)
[![Version](https://img.shields.io/badge/version-0.1.1-blue.svg)](https://github.com/HenryCai11/autoresearch-wrapper/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Inspired by](https://img.shields.io/badge/Based_on-Karpathy's_Autoresearch-orange)](https://github.com/karpathy/autoresearch)

<br>

*"扫描仓库 → 选择目标 → 锁定指标 → Claude/Codex 跑循环 → 你醒来看结果"*

<br>

[安装](#安装) · [使用](#使用) · [命令](#命令) · [详细文档](./DETAILS.md) · [English](./README.md)

</div>

---

最近我在用Codex的时候，会让它去针对某些模块写一些相对应的autoresearch脚本。 有一次我想要往系统里面新加一个功能，其中有几个备选项，这时候想要评估每个备选项真正的表现就得同时优化那些和它相关的参数/模块(`autoresearch-wrapper-create`). 就在这个瞬间，我想是时候写一个SKILL来做这件事了（看了一圈好像确实没人实现这个功能，于是我就开始了）。随之而来的一个想法是，或许在优化一个系统之前，搞清楚各个模块之间相互的依赖关系是有用的，所以这成了这个项目的核心————依赖感知的自动科研（优化）引擎。

## 进展

- 2026/10/15: v0.1.1。
  - 新增完整的根目录 `SKILL.md`，涵盖所有命令，可以把仓库根目录作为一个 skill 安装。
  - 只提供建议的代码改为写进 skill 说明：移除了 `resources` 和 `reference` 命令以及 `.autoresearch-wrapper/plans/` 文件（CLI 会提示替代做法）。
  - monitor skill 改为获取进度快照，不再运行阻塞式轮询。
- 2026/10/15: v0.1.0。
  - `create` / `delete` 现在是公平对比：每个方案（或删除方案）和一个不做改动的对照组用相同预算调优，再用 `compare` 按调优后的上限排名。
  - 这些分支的调优被限制在强制执行的文件范围内。
  - 运行会在保留的候选上继续累积，stop rule 真正生效，新的 `finalize` 会把最优结果合并回来并清理 worktree。
  - 新增指标超时、并行记录不再丢失，以及许多小修复。
  - Claude Code 和 Codex 现在共用一套 skill。Codex 用户执行 `ln -s /path/to/autoresearch-wrapper/skills/* ~/.agents/skills/` 即可让每个命令成为独立的 skill；旧的仓库根目录安装方式仍可作为一个完整 skill 使用。
  - **不兼容变更：** 旧版本创建的 create/delete 运行无法再对比，需要重新创建。
- 2026/03/25: 刷新了 Claude marketplace 打包版本，确保 wizard-first 流程和随插件打包的脚本能正确安装到插件缓存中。
- 2026/03/23 北京时间凌晨2:31: 虽然只开发测试到v0.0.2，我决定还是直接开源了！大半夜开始试用之后很激动，想快点和社区分享。虽然时间有限同时也还在确保每一个我想要的功能都已经正确实现，但我觉得它已经做好准备开始干活了（狗头）。


## 安装

<details open>
<summary><b>Claude Code（推荐）</b></summary>

```bash
/plugin marketplace add HenryCai11/autoresearch-wrapper
/plugin install autoresearch-wrapper
```

更新到最新版本：

```bash
/plugin marketplace update autoresearch-wrapper
/plugin update autoresearch-wrapper
```

如果你之前装的是打包结构调整前的旧 `0.0.2` marketplace 版本，请执行：

```bash
/plugin marketplace update autoresearch-wrapper
/plugin remove autoresearch-wrapper
/plugin install autoresearch-wrapper
```

卸载：

```bash
/plugin remove autoresearch-wrapper
```

或手动安装：

```bash
git clone https://github.com/HenryCai11/autoresearch-wrapper.git
```

Claude Code 会自动从 `.claude/skills/` 发现 skill。若想在所有项目中使用，把各个 skill 目录链接到用户级 skill 目录：

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/autoresearch-wrapper/skills/* ~/.claude/skills/
```

Marketplace 打包目录位于 `plugins/autoresearch-wrapper/`，由 `skills/` 生成。

</details>

<details>
<summary><b>Codex</b></summary>

Codex 读取同一套 skill 目录。在本仓库内会从 `.agents/skills/` 自动发现；若想在任何地方使用：

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/autoresearch-wrapper/skills/* ~/.agents/skills/
```

用 `$autoresearch-wrapper`、`$autoresearch-wrapper-run` 等调用（或从 `/skills` 中选择）。安装后重启 Codex。

也可以把仓库根目录作为一个完整的 skill 安装（`ln -s /path/to/autoresearch-wrapper ~/.agents/skills/autoresearch-wrapper`），根目录的 `SKILL.md` 覆盖所有命令。旧的 `~/.codex/skills/autoresearch-wrapper` 安装方式同样可用。两种方式选其一即可：它们都会提供名为 `autoresearch-wrapper` 的 skill。

</details>

<details>
<summary><b>仅 CLI</b></summary>

无需安装，直接运行：

```bash
python3 scripts/autoresearch_wrapper.py scan
```

</details>

## 使用

直接跑
```
/autoresearch-wrapper
```
然后你会进入一个端到端引导界面：先看核心功能模块的紧凑扫描结果，再一步步选择目标、锁定指标与运行参数，最后开始优化你想优化的模块。如果你明确想先看完整仓库列表，可以用 `python3 scripts/autoresearch_wrapper.py wizard --full-summary`。

## Examples

这是我想要优化[Recursive Language Models](https://github.com/alexzhang13/rlm)时候，引导界面的样子（Claude Code）

![example_rlm](assets/example_rlm.png)

## 命令

同一套 skill 同时服务两个工具：在 Claude Code 中用 `/<skill>` 调用，在 Codex 中用 `$<skill>` 调用。

| Skill | CLI | 说明 |
| --- | --- | --- |
| `autoresearch-wrapper` | `wizard` / `wrap` | 运行端到端引导或包装脚本 |
| `autoresearch-wrapper-status` | `status` | 查看状态和就绪情况 |
| `autoresearch-wrapper-run` | `run` | 启动或恢复运行 |
| `autoresearch-wrapper-flow` | `flow` | 指标历史和图表 |
| `autoresearch-wrapper-create` | `create` | 对比多种功能实现，每个都与调优后的对照组同等预算调优 |
| `autoresearch-wrapper-delete` | `delete` | 对比删除与保留某模块（两者都调优） |
| `autoresearch-wrapper-monitor` | `monitor` | 进度快照（CLI 轮询器供终端使用） |

其他 CLI 子命令：`scan`、`configure`、`allocate`、`evaluate`、`record`、`arm-ready`、`compare`、`finalize`、`preset-metric`

运行结束后，`finalize --run-id <id> --merge` 会把最优候选 squash 合并到当前 checkout（只暂存、不提交，便于审阅），并清理该运行的 worktree。

## 测试

```bash
python3 -m unittest -q
```

## 文档

| 文档 | 内容 |
| --- | --- |
| [DETAILS.md](./DETAILS.md) | 功能细节、依赖图说明、生成目录结构、典型工作流 |
| [GEO.md](./GEO.md) | 网页依赖图、节点操作、跨平台真实观测与全局决策 |
| [CORE_FEATURES.md](./CORE_FEATURES.md) | 功能清单 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 开发工作流、分支布局、验证 |
| [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) | 上游归属声明 |


## 致谢

这个项目受到了其他一些autoresearch项目的启发，分别是[Karpathy's autoresearch](https://github.com/karpathy/autoresearch)和[uditgoenka's autoresearch](https://github.com/uditgoenka/autoresearch). 万般感谢！
