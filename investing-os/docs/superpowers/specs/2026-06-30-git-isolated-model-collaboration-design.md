# Git 隔离的高低阶模型协作设计

日期：2026-06-30

## 1. 目标

建立一套以 Git 为强制审计边界的模型协作方式：

- 高阶模型负责架构、任务分发、审核和合入。
- 低阶模型负责边界明确的实现。
- 低阶模型不得直接修改主工作区或主分支。
- 每项实现都有任务单、独立分支、独立 worktree、commit、push 和审核记录。
- 任何越界改动都能在合入前被发现并拒收。

Git 提供隔离、审计和恢复能力，不等同于操作系统权限控制。执行低阶模型时，仍必须把其工作目录限定到指定 worktree，且不得向它提供主工作区路径作为可写目标。

## 2. 仓库现实

- Git 根目录是 `C:\Users\rriww\Documents\STOCK`。
- `investing-os` 和 `stock_team` 共用同一个 Git 仓库。
- 主工作区当前存在尚未提交的开发改动。
- 已存在 `.worktrees/`，并且该目录已被 `.gitignore` 忽略。
- 已存在 `codex/phase1-coordinator-foundation` worktree。
- 当前仓库没有配置 Git remote，因此现阶段可以 commit，但不能声称已经 push 或上传。

启动该协作机制前，高阶模型必须先审计现有未提交改动，并将可保留改动按意图拆成独立 commit。不得让低阶模型整理、提交或清理这些历史改动。

## 3. 方案选择

### 方案 A：同一工作区切换分支

优点是操作少。缺点是未提交文件会跨分支存在，低阶模型也能碰到用户和高阶模型正在编辑的文件。当前脏工作区下不可接受。

### 方案 B：每任务独立 branch 和 worktree

这是采用方案。每个低阶任务从一个明确的基准 commit 创建独立分支和 worktree。低阶模型只在该目录实现、验证和提交，高阶模型通过 Git diff 审核后决定是否合入。

### 方案 C：低阶模型只输出 patch 文本

隔离最强，但实现、测试和修正成本高，无法充分利用低阶模型处理完整小任务。保留为高度敏感任务的例外方式。

## 4. 权限模型

### 4.1 高阶模型

高阶模型独占以下操作：

- 定义系统架构、任务优先级和跨项目契约。
- 选择任务基准 commit。
- 创建任务单。
- 创建或授权创建任务分支和 worktree。
- 审核完整 diff、文件范围、测试和日志。
- 判断接受、返工或丢弃。
- 将审核通过的 commit 合入集成分支或主分支。
- 修改交易状态机、权限、风险、真实账户数据契约和核心 schema。

### 4.2 低阶模型

低阶模型只能：

- 读取任务单列出的文件和必要依赖。
- 在分配的 worktree 中修改允许文件。
- 运行任务单列出的验证命令。
- 在任务分支提交自己的改动。
- push 自己的任务分支。
- 更新任务执行日志。

低阶模型不得：

- 在 `C:\Users\rriww\Documents\STOCK` 主工作区执行写操作。
- checkout、merge、rebase、reset、clean 或删除分支/worktree。
- 修改任务单未授权的文件。
- 合入主分支。
- 提交运行日志、密钥、账户状态或未授权的生成文件。
- 自行扩大任务范围。

## 5. 任务生命周期

每个任务使用唯一编号，例如 `COLLAB-001`。

```text
draft
-> ready
-> dispatched
-> implemented
-> review_failed | review_passed
-> merged
-> pushed
-> closed
```

状态含义：

- `draft`：高阶模型正在定义任务。
- `ready`：输入、允许文件、验收命令和完成定义齐全。
- `dispatched`：独立 worktree 已建立，低阶模型开始工作。
- `implemented`：低阶模型已 commit，并提交执行日志。
- `review_failed`：发现越界、契约错误或验证失败，必须返工。
- `review_passed`：高阶模型完成 diff 和验证审核。
- `merged`：审核通过的 commit 已由高阶模型合入。
- `pushed`：对应分支和合入结果已上传远端。
- `closed`：审核记录完整，临时 worktree 已安全移除。

没有 remote 时，任务最多只能进入 `merged_local`，不得使用 `pushed` 或 `closed`。

## 6. Git 结构

### 6.1 分支

- 受保护主分支：当前为 `master`。
- 集成分支：复杂批次可使用 `codex/integration-<主题>`。
- 低阶任务分支：`codex/task-<任务编号小写>`。

示例：

```text
codex/task-collab-001
```

### 6.2 Worktree

低阶任务 worktree 放在：

```text
C:\Users\rriww\Documents\STOCK\.worktrees\<任务编号小写>
```

创建前必须确认：

1. 主仓库 Git 状态已记录。
2. `.worktrees/` 仍被忽略。
3. 任务基准 commit 已存在。
4. 同名分支和 worktree 不存在。

### 6.3 Commit

- 每个任务至少一个、通常一个实现 commit。
- 不同意图必须拆分 commit。
- commit message 使用：

```text
<type>(<scope>): <任务结果> [<任务编号>]
```

示例：

```text
feat(coordinator): validate task artifact paths [COLLAB-001]
```

## 7. 任务单契约

任务单由高阶模型创建，至少包含：

```yaml
task_id: COLLAB-001
status: ready
base_commit: <完整 SHA>
branch: codex/task-collab-001
worktree: C:\Users\rriww\Documents\STOCK\.worktrees\collab-001
goal: 一句话可验证目标
read_paths:
  - 明确路径
write_allowlist:
  - 明确路径
write_denylist:
  - 明确路径
contracts:
  - 输入和输出约束
verification:
  - 可直接执行的命令
definition_of_done:
  - 可观察结果
```

`write_allowlist` 是硬边界。低阶模型即使认为其他文件也需要修改，也只能在执行日志中提出请求，不能先改后报。

## 8. 低阶模型交付契约

低阶模型交付时必须提供：

- 任务编号。
- 基准 commit。
- 实现 commit SHA。
- 修改文件列表。
- 验证命令及原始结果摘要。
- 未解决问题。
- 建议审核重点。
- push 的分支和结果。

工作树必须为 clean。若存在未提交文件，任务状态保持 `implemented_incomplete`，不能进入审核。

## 9. 高阶模型审核门

审核按以下顺序进行：

1. 确认任务分支的 merge base 等于任务单中的基准 commit，或差异已被明确解释。
2. 使用 `git diff --name-only <base>...<worker>` 检查所有修改都在白名单内。
3. 使用 `git diff --check <base>...<worker>` 检查基础格式错误。
4. 阅读完整 diff，不只接受低阶模型摘要。
5. 在隔离 worktree 中重新运行验收命令。
6. 检查没有密钥、账户状态、运行日志和无关生成文件。
7. 检查实现没有改变任务单未授权的交易语义或系统边界。
8. 形成 `accepted`、`changes_requested` 或 `rejected` 审核结论。

任意一步失败都不得合入。

## 10. 合入策略

小型单 commit 任务优先由高阶模型 cherry-pick 到集成分支，以便只接收明确审核过的提交。

多 commit 且提交历史本身有价值的任务，可以 `merge --no-ff`，但必须先审核整个提交范围。

低阶模型永远不执行合入。发生冲突时，由高阶模型判断：

- 在高阶模型工作区解决。
- 退回低阶任务分支，基于新的基准重新实现。
- 放弃任务分支。

## 11. Push 规则

配置 remote 后：

1. 低阶模型完成实现后 push 任务分支。
2. 高阶模型从远端引用重新确认 commit SHA。
3. 审核通过并合入后，高阶模型 push 集成分支或主分支。
4. 执行日志同时记录任务分支 push 和合入分支 push。

没有 remote 时：

- 可以创建本地 branch、worktree 和 commit。
- 日志必须写 `push_status: blocked_no_remote`。
- 不得把本地 commit 描述为“已上传 Git”。

## 12. 失败与恢复

- 越界文件：拒收，低阶模型在原任务分支修正；不得由高阶模型静默删除后合入。
- 测试失败：保持 `review_failed`，记录失败命令和输出。
- 基准过期：高阶模型决定重建任务分支或重新分发，低阶模型不得自行 rebase。
- worktree 变脏：保留现场并记录，不执行 `git clean` 或强制 reset。
- 低阶模型误改主工作区：立即停止该模型，记录主工作区 diff；由高阶模型识别并恢复，不能让低阶模型自行清理。
- remote 不可用：保留本地 commit 和日志，状态不得越过 `merged_local`。

## 13. 所需协作产物

实施阶段需要增加：

- Git 隔离协作协议。
- 低阶模型任务单模板。
- 低阶模型执行日志模板。
- 高阶模型审核记录模板。
- 只读审核脚本，用于检查基准、白名单、工作树和 commit。
- 协作入口说明，规定新模型的读取顺序。

审核脚本只报告问题，不自动 reset、clean、checkout、merge 或删除文件。

## 14. 验收场景

机制至少通过以下模拟：

1. 合法任务只修改白名单文件，审核通过。
2. 低阶模型多改一个未授权文件，审核明确失败。
3. 任务 worktree 留有未提交文件，审核明确失败。
4. commit 包含日志或敏感路径，审核明确失败。
5. 验收命令失败，任务不能合入。
6. 没有 remote 时，任务不能标记为 pushed 或 closed。
7. 主工作区已有脏改动时，低阶任务仍从明确的 clean commit 建立，不读取或提交主工作区的未提交内容。

## 15. 首次启用顺序

1. 高阶模型审计当前主工作区和已有 coordinator worktree。
2. 将历史改动按功能拆分并验证，形成可信基准 commit。
3. 配置 Git remote。
4. 创建协议、模板和只读审核脚本。
5. 用一个纯文档任务验证完整低阶协作流程。
6. 通过后再分发代码实现任务。

