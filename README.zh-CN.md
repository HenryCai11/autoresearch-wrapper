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

[安装](#安装) · [使用](#使用) · [命令](#命令) · [详细文档](./DETAILS.md) · [English](./README.md)

</div>

---

## 安装

<details open>
<summary><b>Claude Code</b></summary>

```bash
git clone https://github.com/HenryCai11/autoresearch-wrapper.git
```

Claude Code 会自动从 `.claude/skills/` 发现 skill。如果仓库在项目外，用符号链接：

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

安装后重启 Codex。

</details>

<details>
<summary><b>仅 CLI</b></summary>

无需安装，直接运行：

```bash
python3 scripts/autoresearch_wrapper.py scan
```

</details>

## 使用

### 1. 扫描

```bash
python3 scripts/autoresearch_wrapper.py scan
```

或通过 skill：`/autoresearch-wrapper scan this repo`

### 2. 配置

```bash
python3 scripts/autoresearch_wrapper.py configure \
  --part src/api.py \
  --metric latency_ms \
  --metric-command "python bench.py" \
  --metric-goal minimize \
  --mode sequential \
  --rounds 5
```

或使用交互式 wizard：`--interactive`

### 3. 运行

```bash
python3 scripts/autoresearch_wrapper.py run
```

Wrapper 会创建 seed worktree，生成 `program.md`，启动优化循环。

### 4. 监控

```bash
python3 scripts/autoresearch_wrapper.py flow          # 指标历史 + ASCII 图
python3 scripts/autoresearch_wrapper.py monitor        # 实时进度轮询
python3 scripts/autoresearch_wrapper.py status         # 完整状态摘要
```

## 命令

| Codex | Claude Code | CLI | 说明 |
| --- | --- | --- | --- |
| `/autoresearch-wrapper` | `/autoresearch-wrapper` | `scan` / `wrap` | 扫描仓库或包装脚本 |
| `:status` | `-status` | `status` | 查看状态和就绪情况 |
| `:run` | `-run` | `run` | 启动或恢复运行 |
| `:flow` | `-flow` | `flow` | 指标历史和图表 |
| `:create` | `-create` | `create` | 多候选功能添加 |
| `:delete` | `-delete` | `delete` | 删除后参数优化 |
| `:monitor` | `-monitor` | `monitor` | 实时进度轮询 |

其他 CLI 子命令：`configure`、`allocate`、`evaluate`、`record`、`resources`、`preset-metric`、`reference`

## 测试

```bash
python3 -m unittest -q
```

## 文档

| 文档 | 内容 |
| --- | --- |
| [DETAILS.md](./DETAILS.md) | 功能细节、依赖图说明、生成目录结构、典型工作流 |
| [CORE_FEATURES.md](./CORE_FEATURES.md) | 功能清单 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 开发工作流、分支布局、验证 |
| [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) | 上游归属声明 |
