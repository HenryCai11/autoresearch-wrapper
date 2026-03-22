<div align="center">

![Autoresearch Wrapper Banner](./assets/banner.svg)

# Autoresearch Wrapper

**面向任意代码仓库的 dependency-aware 优化引擎。**

扫描、规划、隔离、测量、迭代 —— 全部在 Git worktree 中自动完成。

基于 [Karpathy 的 autoresearch](https://github.com/karpathy/autoresearch) —— 约束 + 机械化指标 + 自主迭代 = 持续增益。

[![Claude Code Skill](https://img.shields.io/badge/Claude_Code-Skill-blue?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-green?logo=openai&logoColor=white)](https://platform.openai.com/docs/codex)
[![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)](https://github.com/HenryCai11/autoresearch-wrapper/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Based on](https://img.shields.io/badge/Based_on-Karpathy's_Autoresearch-orange)](https://github.com/karpathy/autoresearch)

<br>

*"扫描仓库 → 选择目标 → 锁定指标 → Claude/Codex 跑循环 → 你醒来看结果"*

<br>

[快速开始](#快速开始) · [命令接口](#命令接口) · [功能列表](#详细功能列表) · [测试](#测试)

语言: [English](./README.md) | [简体中文](./README.zh-CN.md)

</div>

---

贡献说明: [CONTRIBUTING.md](./CONTRIBUTING.md) · 第三方声明: [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)

核心思路是：
- 扫描仓库中的优化候选部分
- 为每个部分构建 dependency-aware 视图
- 将每个部分分类为 `surely optimizable` 或 `probably optimizable`
- 为选中的部分收集指标与运行配置
- 在 Git worktree 中启动或恢复优化，而不是直接修改主工作区

它受 Karpathy 的 [`autoresearch`](https://github.com/karpathy/autoresearch) 启发，但额外增加了仓库扫描、依赖图构建、状态持久化、规划产物以及基于 worktree 的候选管理。

## 快速开始

<details>
<summary><b>Claude Code</b></summary>

1. 克隆或拷贝此仓库到你的项目中（或磁盘任意位置）：

```bash
git clone https://github.com/<owner>/autoresearch-wrapper.git
```

2. Claude Code 会自动从项目根目录的 `.claude/skills/` 发现 skill。如果你把本仓库克隆到了目标项目内部，skill 已经可用。如果在别的位置，用符号链接：

```bash
mkdir -p /path/to/your-project/.claude/skills
ln -s /path/to/autoresearch-wrapper/.claude/skills/* /path/to/your-project/.claude/skills/
```

3. 在想要优化的仓库中，通过 Claude Code 使用 skill：

```text
/autoresearch-wrapper scan this repo, summarize the dependency-aware optimization candidates, and wait for my choice
/autoresearch-wrapper-status
/autoresearch-wrapper-flow
```

4. 锁定优化目标和运行配置，启动运行：

```text
/autoresearch-wrapper optimize src/your_module.py with metric latency_ms, sequential mode, and 5 rounds
/autoresearch-wrapper-run
```

5. 使用新功能命令：

```text
/autoresearch-wrapper-create --part src/api.py --feature "add response caching" --candidates 3
/autoresearch-wrapper-delete --part src/legacy.py
/autoresearch-wrapper-monitor --interval 30
```

</details>

<details>
<summary><b>Codex</b></summary>

1. 把这个仓库安装成一个本地 Codex skill：

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/autoresearch-wrapper ~/.codex/skills/autoresearch-wrapper
```

如果你是从 GitHub 安装，可以使用 Codex 自带的安装脚本：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo <owner>/<repo> \
  --path . \
  --name autoresearch-wrapper
```

你也可以直接让 Codex 使用预装的 `skill-installer` skill，帮你从 GitHub 安装这个仓库。

2. 重启 Codex，让它重新发现这个 skill。

3. 在想要优化的仓库中，通过 Codex 扫描并查看候选：

```text
/autoresearch-wrapper scan this repo, summarize the dependency-aware optimization candidates, and wait for my choice
/autoresearch-wrapper:status
/autoresearch-wrapper:flow
```

4. 锁定优化目标和运行配置，启动运行：

```text
/autoresearch-wrapper optimize src/your_module.py with metric latency_ms, sequential mode, and 5 rounds
/autoresearch-wrapper:run
```

</details>

<details>
<summary><b>直接使用 CLI（不依赖 Codex 或 Claude Code）</b></summary>

如果你想直接针对仓库内脚本，可以使用 script-wrapper 快捷方式：

```bash
python3 scripts/autoresearch_wrapper.py path/to/script.py
```

这会把脚本包装进常规的 dependency-aware 流程，自动建议一个 metric preset，并在启动基于 worktree 的运行之前让你确认指标命令。

底层辅助 CLI 全部命令：

```bash
python3 scripts/autoresearch_wrapper.py scan
python3 scripts/autoresearch_wrapper.py status
python3 scripts/autoresearch_wrapper.py run
python3 scripts/autoresearch_wrapper.py resources
python3 scripts/autoresearch_wrapper.py monitor --interval 60
python3 scripts/autoresearch_wrapper.py create --part <part> --feature "<描述>"
python3 scripts/autoresearch_wrapper.py delete --part <part>
```

</details>

## 详细功能列表

- 以模块或文件粒度进行 dependency-aware 仓库扫描。
- 构建直接依赖图，并记录未解析边。
- 将 part 分类为 `surely optimizable` 或 `probably optimizable`。
- 在运行前执行 dependency-aware readiness gating。
- 将规范状态持久化到 `.autoresearch-wrapper/state.json`。
- 将人类可读状态输出到 `.autoresearch-wrapper/STATUS.md`。
- 在 `.autoresearch-wrapper/plans/` 下生成 planning workspace。
- 为每个 part 初始化 `metadata.json`、`dependencies.md` 和 `notes.md`。
- 以 Git worktree 为优先机制分配 candidate 并隔离实验。
- 持久化 active run 与 candidate 元数据，支持恢复运行。
- 生成 Karpathy 风格的每次运行 `program.md`。
- 为每次运行提供已记录 metric flow 摘要和 ASCII 指标图。
- 为仓库内脚本提供 script-wrapper 快捷入口。
- 为常见脚本测量场景提供 metric preset 脚手架。
- 提供 preset metric helper 命令来执行脚本指标评估。
- 支持克隆 Karpathy 上游 `autoresearch` 作为参考仓库。
- 功能创建运行：多候选对比，寻找最优能力上限（`create`）。
- 功能删除运行：删除后自动优化依赖参数（`delete`）。
- 系统资源检测（CPU、GPU、内存、调度器：slurm/pbs），通过 `resources` 命令。
- 可配置间隔的进度监控（`monitor`）。
- 早退机制：优化停滞时自动终止运行（`--early-exit-patience`、`--early-exit-threshold`）。
- 狂野模式：搜索空间较大时同步修改多个参数（`--mode wild`）。
- 所有命令在 TTY 环境下支持交互式 wizard 提示。

## 功能细节

### Dependency-aware 扫描

- 以模块或文件粒度扫描仓库。
- 为每个部分构建尽力而为的直接依赖图。
- 跟踪：
  - 直接依赖
  - 直接被依赖者
  - 未解析依赖
  - dependency clarity
  - 关键邻居
- 在判断一个部分是否已经准备好进入优化时，会使用 dependency clarity。

### 优化状态分类

每个发现的部分都会被分类为以下之一：
- `surely optimizable`
  - 目标、候选空间、指标以及重要的直接依赖都足够清晰
- `probably optimizable`
  - 以上信息中有一项或多项不够清晰，尤其是指标或依赖边界不明确时

### 持久化仓库状态

wrapper 会将规范状态写入：

```text
.autoresearch-wrapper/state.json
```

该状态包括：
- 已发现的部分
- 依赖图边
- 指标建议
- 当前选中的部分
- 持久化的运行配置
- 当前和历史运行
- worktree 元数据

### 人类可读状态输出

wrapper 会写入：

```text
.autoresearch-wrapper/STATUS.md
```

其中包括：
- 当前选中的部分和活跃运行
- parts 表格
- dependency 表格
- 运行摘要
- candidate worktree 生命周期
- 紧凑的已记录 metric flow 摘要

### Metric flow 绘制

对于已经记录的结果，可以渲染 metric flow，包括：
- 按时间顺序的指标序列
- best-so-far 序列
- 每一步的表格
- 便于终端快速查看的 ASCII 图

使用方式：

```bash
python3 scripts/autoresearch_wrapper.py flow
python3 scripts/autoresearch_wrapper.py flow --run-id <run-id>
python3 scripts/autoresearch_wrapper.py flow --json
```

### Planning workspace

每次扫描还会重新生成：

```text
.autoresearch-wrapper/plans/
```

这个 planning workspace 会镜像仓库内各个部分的相对路径，并为每个部分创建一个目录，包含：
- `metadata.json`
- `dependencies.md`
- `notes.md`

这是用于规划和检查的派生工作区，不是事实来源。

### Dependency-aware 运行门禁

在运行开始之前，wrapper 要求以下信息齐备：
- 选中的部分
- 指标名称
- 指标命令
- 指标目标
- 执行模式
- 轮数或停止规则
- 足够明确的重要直接依赖

如果选中的部分存在未解析的重要依赖边界，`run` 会被阻止，直到重新扫描、缩小目标范围或完成澄清。

### 基于 Git worktree 的优化

默认使用 Git worktree 进行优化。

这意味着：
- 主工作区不会被直接拿来做实验
- 每个运行都有一个 seed worktree
- 新候选会分配到各自独立的 worktree 中
- candidate 分支和路径会被持久化，以便恢复和查看状态

### Karpathy 风格的运行程序

每次运行都会在 run 目录下生成一个 `program.md`。其中包括：
- 锁定后的指标与停止设置
- 选中部分的依赖邻域
- 指向状态与规划产物的引用
- 用于 baseline、candidate 分配、评估和记录的辅助命令

### 参考仓库支持

wrapper 可以把 Karpathy 上游的 `autoresearch` 仓库克隆到本地状态目录中，作为实现参考：

```bash
python3 scripts/autoresearch_wrapper.py reference
python3 scripts/autoresearch_wrapper.py reference --refresh
```

## 命令接口

这个 skill 暴露了七个主要命令。两个平台的命名略有不同：

| Codex | Claude Code | CLI 子命令 |
| --- | --- | --- |
| `/autoresearch-wrapper` | `/autoresearch-wrapper` | `scan` / `wrap` |
| `/autoresearch-wrapper:status` | `/autoresearch-wrapper-status` | `status` |
| `/autoresearch-wrapper:run` | `/autoresearch-wrapper-run` | `run` |
| `/autoresearch-wrapper:flow` | `/autoresearch-wrapper-flow` | `flow` |
| `/autoresearch-wrapper:create` | `/autoresearch-wrapper-create` | `create` |
| `/autoresearch-wrapper:delete` | `/autoresearch-wrapper-delete` | `delete` |
| `/autoresearch-wrapper:monitor` | `/autoresearch-wrapper-monitor` | `monitor` |

主命令还支持一种简写的 script-wrapper 形式：

```bash
python3 scripts/autoresearch_wrapper.py path/to/script.py
python3 scripts/autoresearch_wrapper.py wrap path/to/script.py
```

这会把脚本选为主要 part，推断一个指标 preset，并在普通 wrapper 状态中创建一个未完成的配置 stub。

底层辅助 CLI 为：

```bash
python3 scripts/autoresearch_wrapper.py
```

CLI 子命令：
- `scan`
- `wrap`
- `configure`
- `status`
- `run`
- `allocate`
- `evaluate`
- `record`
- `flow`
- `reference`
- `preset-metric`
- `resources`
- `monitor`
- `create`
- `delete`

## 典型工作流

### 1. 扫描仓库

```bash
python3 scripts/autoresearch_wrapper.py scan
```

这会发现各个 part、构建依赖图、更新 `state.json`、刷新 `STATUS.md`，并重新生成 `.autoresearch-wrapper/plans/`。

### 2. 配置选中的部分

```bash
python3 scripts/autoresearch_wrapper.py configure \
  --part path/to/module.py \
  --metric latency_ms \
  --metric-command "python -c \"print('METRIC=123.4')\"" \
  --metric-goal minimize \
  --mode sequential \
  --rounds 5
```

或者使用交互式提示：

```bash
python3 scripts/autoresearch_wrapper.py configure --part path/to/module.py --interactive
```

对于脚本入口，可以先使用 script-wrapper 简写进行脚手架配置：

```bash
python3 scripts/autoresearch_wrapper.py path/to/script.py
```

然后确认系统建议的、基于 preset 的指标命令：

```bash
python3 scripts/autoresearch_wrapper.py configure \
  --part path/to/script.py \
  --metric-preset runtime_seconds \
  --use-suggested-command
```

### 3. 查看状态

```bash
python3 scripts/autoresearch_wrapper.py status
python3 scripts/autoresearch_wrapper.py status --json
```

### 4. 启动或恢复一个运行

```bash
python3 scripts/autoresearch_wrapper.py run
```

### 5. 在运行过程中管理候选

```bash
python3 scripts/autoresearch_wrapper.py allocate --run-id <run-id>
python3 scripts/autoresearch_wrapper.py evaluate --run-id <run-id> --candidate seed
python3 scripts/autoresearch_wrapper.py record --run-id <run-id> --candidate seed --status auto --description "baseline"
```

### 6. 查看 metric flow

```bash
python3 scripts/autoresearch_wrapper.py flow
python3 scripts/autoresearch_wrapper.py flow --run-id <run-id>
```

### 7. 使用基于 preset 的脚本指标

可用的 preset 辅助项：
- `runtime_seconds`
- `latency_ms`
- `throughput`
- `memory_mb`

你可以直接运行某个 preset：

```bash
python3 scripts/autoresearch_wrapper.py preset-metric --preset runtime_seconds --script path/to/script.py
```

也可以让 `wrap` 先生成建议命令，再通过 `configure --use-suggested-command` 进行确认。

## 生成的目录结构

```text
.autoresearch-wrapper/
  state.json
  STATUS.md
  plans/
    <repo-relative-part-path>/
      metadata.json
      dependencies.md
      notes.md
  runs/
    <run-id>/
      program.md
      results.tsv
      logs/
  reference/
    autoresearch-upstream/
```

## 依赖图说明

当前图结构刻意保持简单：
- 只关注直接依赖
- 使用尽力而为的提取方式
- 优先记录仓库内部边
- 当未解析的 import/include 会影响本地优化边界时，会将其记录下来

当前依赖提取在多种语言上采用启发式方法；在本地 import/include 结构清晰的语言中效果最好。

## Script Wrapper 说明

新的 script-wrapper 流程刻意设计成一个快捷入口，而不是独立模式：
- 它仍然使用常规扫描结果
- 它仍然持久化常规的 part 配置和选择状态
- 它仍然遵守 dependency-aware 的运行阻塞逻辑
- 一旦指标命令被确认，它仍然使用相同的基于 worktree 的运行流程

## 测试

仓库中包含的单元测试覆盖：
- 扫描分类
- 依赖图提取
- planning workspace 生成
- configure 持久化
- 基于 worktree 的运行流程
- dependency-aware 运行阻塞
- schema 迁移（v1→v2）
- 系统资源检测
- 早退机制
- 狂野模式默认值
- create 和 delete 运行类型
- wizard 系统（非交互模式）

运行方式：

```bash
python3 -m unittest -q
```

## 关键文件

- `SKILL.md`
  - Codex 的 skill 行为和命令映射
- `.claude/skills/`
  - Claude Code 的 skill 定义（每个命令一个目录）
- `scripts/autoresearch_wrapper.py`
  - CLI 入口
- `autoresearch_wrapper/core.py`
  - 扫描、依赖图、状态、worktree 和运行逻辑
- `templates/autoresearch_program_template.md`
  - 每次运行自动生成的说明模板
- `references/karpathy-autoresearch.md`
  - 上游参考说明
