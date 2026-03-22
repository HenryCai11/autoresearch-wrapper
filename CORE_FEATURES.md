# AutoResearch-Wrapper核心功能

## Planning Workspace & Dependency Graph & Git Worktree

1. ✅ 自动识别并管理各模块间的dependency
2. ✅ 每个模块的信息都会保存在一个结构化的目录里，包含可优化的方向、metric、实验记录等
3. ✅ 每个优化的方向都会用Git Worktree进行隔离

## Wrapper

1. ✅ wrap一个script
2. ✅ wrap某个模块
3. ✅ 自动根据选择的模块之间的关系进行autoresearch
4. ✅ /autoresearch-wrapper:create 添加新功能时也可以propose多个candidate，自动识别相关的依赖进行optimize，对比各candidate的"真实能力上限"
5. ✅ /autoresearch-wrapper:delete 删除某个功能的时候也可以用wrapper，然后search/optimize删除该功能/模块后的最优参数

## Side Features

1. ✅ 并发：根据系统情况以及资源需求自动识别，例如某些任务是需要GPU还是CPU还是网络服务，又比如GPU的话是local的还是cluster的，例如slurm
2. ✅ monitor：多久check一次进度，给用户选项且能让用户自行输入
3. ✅ 早退机制：当有中间metric的时候可以根据需求早退，像karpathy那样
4. ✅ 狂野模式：当搜索空间较大的时候可以根据output分析同步修改多个参数

## 设计哲学

1. ✅ 尽可能简单，方便二次开发
2. ✅ 每一个操作都要有plan mode一样的wizard，让用户能够选择且把握中间细节
