![Autoresearch Wrapper Banner](./assets/banner.svg)

# Autoresearch Wrapper

`autoresearch-wrapper` 是一个 Codex skill，加上一组辅助 CLI，用于在任意仓库上运行一种 `autoresearch` 风格的优化工作流。

核心思路是：
- 扫描仓库中的优化候选部分
- 为每个部分构建 dependency-aware 视图
- 将每个部分分类为 `surely optimizable` 或 `probably optimizable`
- 为选中的部分收集指标与运行配置
- 在 Git worktree 中启动或恢复优化，而不是直接修改主工作区

它受 Karpathy 的 [`autoresearch`](https://github.com/karpathy/autoresearch) 启发，但额外增加了仓库扫描、依赖图构建、状态持久化、规划产物以及基于 worktree 的候选管理。

## 功能

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

这个 skill 暴露了三个主要命令：
- `/autoresearch-wrapper`
- `/autoresearch-wrapper:status`
- `/autoresearch-wrapper:run`

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
- `reference`
- `preset-metric`

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

### 6. 使用基于 preset 的脚本指标

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

运行方式：

```bash
python3 -m unittest -q
```

## 关键文件

- `SKILL.md`
  - Codex 的 skill 行为和命令映射
- `scripts/autoresearch_wrapper.py`
  - CLI 入口
- `autoresearch_wrapper/core.py`
  - 扫描、依赖图、状态、worktree 和运行逻辑
- `templates/autoresearch_program_template.md`
  - 每次运行自动生成的说明模板
- `references/karpathy-autoresearch.md`
  - 上游参考说明
