# DAILY Workflow Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不重写现有业务逻辑的前提下，查清 `DAILY-0` 至 `DAILY-4` 的现有能力、用户交互、固定产物和断点，形成经用户批准的 DAILY 契约，再据此安排实现。

**Architecture:** 第一批工作是五个互不修改共享文件的窄范围审计任务，每个任务只写一份独立报告。高阶模型随后综合报告、现有架构与用户决定，生成唯一 DAILY 契约和下一批实现任务。任何代码改动必须晚于契约批准。

**Tech Stack:** Markdown contracts, JSON Schema, Python 3, pytest, existing `stock_team` coordinator and CLI.

---

## 0. 执行规则

### 0.1 当前只执行第一批

本计划的第一批是 Task 1–5。它们可以分发给低阶模型并行完成。

Task 6 必须由高阶模型执行，并等待五份报告齐备。Task 7 之后的代码实施必须等待用户批准 Task 6 的 DAILY 契约。

### 0.2 低阶模型共同限制

低阶模型可以：

- 读取任务列出的文件；
- 运行任务列出的只读命令和测试；
- 创建自己任务唯一的一份审计报告；
- 提交该报告的独立 commit。

低阶模型不得：

- 修改 Python、JavaScript、HTML、schema、现有工作流或状态台账；
- 重新命名旧代码中的 Stage/Node/state/action；
- 决定 DAILY 步骤、用户确认点或状态转换；
- 使用真实账户、真实交易或未脱敏运行文件；
- 扫描整个仓库；
- 顺手修复发现的问题；
- 修改 `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`。

### 0.3 报告证据等级

每条能力只能标记为：

- `code-only`：只看到实现；
- `documented`：只看到说明或契约；
- `test-covered`：存在并实际运行了相关测试；
- `runtime-unverified`：没有执行真实或模拟流程；
- `conflict`：文档、代码或测试互相矛盾；
- `missing`：任务范围内没有找到所需能力。

不得使用“完成”“已支持”“可用”，除非任务中的运行命令直接证明该结论。

## 第一批：低阶模型可并行任务

### Task 1: DAILY-0 晨间准备事实审计

**负责人级别：** 低阶模型
**任务编号：** `DAILY-AUDIT-0`

**允许读取：**

- `investing-os/PROJECT-CHARTER.zh.md`
- `investing-os/system/workflows/trading-day.md`
- `investing-os/docs/superpowers/specs/2026-06-13-unified-investing-operating-system-architecture.zh.md`
- `stock_team/docs/SYSTEM_FLOWCHART.md`
- `stock_team/coordinator_cli.py`
- `stock_team/orchestration/models.py`
- `stock_team/orchestration/store.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/core/ibkr_monitor.py`
- `stock_team/tests/unit/orchestration/test_coordinator_cli.py`
- `stock_team/tests/unit/orchestration/test_models.py`
- `stock_team/tests/unit/orchestration/test_store.py`
- `stock_team/tests/unit/core/test_ibkr_monitor.py`

**允许创建：**

- `investing-os/handoff/daily-audit/DAILY-AUDIT-0.md`

**禁止修改：** 除上述报告外的所有文件。

- [ ] **Step 1: 记录版本和范围**

Run:

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
```

Expected: 记录分支、完整 SHA；工作区应为空。若不为空，停止并报告，不清理文件。

- [ ] **Step 2: 运行限定测试**

Run:

```powershell
python -m pytest stock_team/tests/unit/orchestration/test_coordinator_cli.py stock_team/tests/unit/orchestration/test_models.py stock_team/tests/unit/orchestration/test_store.py stock_team/tests/unit/core/test_ibkr_monitor.py -q
```

Expected: 报告实际通过/失败数量；失败时保留完整失败测试名，不修代码。

- [ ] **Step 3: 创建审计报告**

Create `investing-os/handoff/daily-audit/DAILY-AUDIT-0.md` with exactly these sections:

```markdown
# DAILY-AUDIT-0 晨间准备事实审计

## 审计元数据

- Base commit:
- Branch:
- Allowed scope respected: yes/no

## 预期用户交互

| 交互 | 文档证据 | 代码入口 | 测试证据 | 证据等级 |
|---|---|---|---|---|
| 选择 trading / observation / research / review / maintenance | | | | |
| 处理前日未完成状态 | | | | |
| 确认账户、持仓、近期成交与暴露事实 | | | | |
| 确认今日持仓、观察对象和问题 | | | | |

## 当前入口与状态

| 项目 | 文件与符号 | 当前行为 | 缺口或冲突 |
|---|---|---|---|
| init-day | | | |
| session persistence | | | |
| IBKR provenance | | | |
| cross-day recovery | | | |

## 固定产物

| 产物 | 当前路径 | 生产者 | 是否有 schema | 是否有测试 |
|---|---|---|---|---|

## 测试结果

- Command:
- Result:
- Failures:

## 只陈述事实的结论

- 已有：
- 缺失：
- 冲突：
- 需要高阶模型决定：
```

- [ ] **Step 4: 验证报告没有越界结论**

Run:

```powershell
rg -n "建议修改|应该改成|我决定|已完成|完全支持" investing-os/handoff/daily-audit/DAILY-AUDIT-0.md
git diff --check
git status --short
```

Expected: `rg` 无匹配；Git 只显示 `DAILY-AUDIT-0.md`。

- [ ] **Step 5: 提交独立 commit**

```powershell
git add -- investing-os/handoff/daily-audit/DAILY-AUDIT-0.md
git commit -m "docs: audit DAILY-0 morning preparation"
git push -u origin HEAD
```

交付时报告分支、commit SHA 和 push 结果。

### Task 2: DAILY-1 盘前决策事实审计

**负责人级别：** 低阶模型
**任务编号：** `DAILY-AUDIT-1`

**允许读取：**

- `investing-os/PROJECT-CHARTER.zh.md`
- `investing-os/agents/pre-market-planning-agent.md`
- `investing-os/agents/stock-team-evidence-agent.md`
- `investing-os/agents/risk-boundary-plan-approval-agent.md`
- `investing-os/system/workflows/pre-market.md`
- `investing-os/system/workflows/brain-muscle-handshake-protocol.md`
- `stock_team/orchestration/adapters.py`
- `stock_team/orchestration/coordinator.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/cli.py`
- `stock_team/tests/unit/orchestration/test_adapters.py`
- `stock_team/tests/unit/orchestration/test_coordinator.py`
- `stock_team/tests/unit/orchestration/test_transitions.py`
- `stock_team/tests/unit/core/test_cli.py`

**允许创建：**

- `investing-os/handoff/daily-audit/DAILY-AUDIT-1.md`

**禁止修改：** 除上述报告外的所有文件。

- [ ] **Step 1: 记录版本并运行测试**

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
python -m pytest stock_team/tests/unit/orchestration/test_adapters.py stock_team/tests/unit/orchestration/test_coordinator.py stock_team/tests/unit/orchestration/test_transitions.py -q
python -m pytest -q stock_team/tests/unit/core/test_cli.py::test_cli_market_context_requires_brain_universe stock_team/tests/unit/core/test_cli.py::test_cli_market_context_rejects_post_open_as_of stock_team/tests/unit/core/test_cli.py::test_cli_premarket_generation
```

Expected: 记录实际结果；失败不修复。

- [ ] **Step 2: 创建审计报告**

Create `investing-os/handoff/daily-audit/DAILY-AUDIT-1.md`:

```markdown
# DAILY-AUDIT-1 盘前决策事实审计

## 审计元数据

- Base commit:
- Branch:
- Allowed scope respected: yes/no

## 握手链

| 顺序 | 统一名称 | 旧代码名称 | 用户是否必须交互 | 输入 | 输出 | 证据等级 |
|---:|---|---|---|---|---|---|
| 1 | 市场范围与事实请求 | | | | | |
| 2 | 市场环境证据包 | | | | | |
| 3 | 环境解释与焦点池确认 | | | | | |
| 4 | 焦点标的证据包 | | | | | |
| 5 | 权限与风险计划 | | | | | |
| 6 | 计划版本批准 | | | | | |

## 数据真实性检查

| 项目 | 实现位置 | 测试位置 | 当前证据 | 缺口 |
|---|---|---|---|---|
| as-of 与时区 | | | | |
| 盘前窗口 | | | | |
| provider/source | | | | |
| degraded/stale/missing | | | | |
| 焦点池限制 | | | | |

## 固定产物与 schema

| 产物 | 当前路径 | schema/模板 | 生产者 | 验证方式 |
|---|---|---|---|---|

## 状态与动作映射

| state/action | 业务含义 | 是否需要用户确认 | 测试证据 | 冲突 |
|---|---|---|---|---|

## 测试结果

- Command:
- Result:
- Failures:

## 只陈述事实的结论

- 已有：
- 缺失：
- 冲突：
- 需要高阶模型决定：
```

- [ ] **Step 3: 验证并提交**

```powershell
rg -n "建议修改|应该改成|我决定|已完成|完全支持" investing-os/handoff/daily-audit/DAILY-AUDIT-1.md
git diff --check
git status --short
git add -- investing-os/handoff/daily-audit/DAILY-AUDIT-1.md
git commit -m "docs: audit DAILY-1 premarket decision"
git push -u origin HEAD
```

Expected: `rg` 无匹配；提交只包含该报告。

### Task 3: DAILY-2 开盘观察事实审计

**负责人级别：** 低阶模型
**任务编号：** `DAILY-AUDIT-2`

**允许读取：**

- `investing-os/PROJECT-CHARTER.zh.md`
- `investing-os/system/workflows/intraday.md`
- `investing-os/system/workflows/intraday-guidance-protocol.md`
- `stock_team/docs/SYSTEM_FLOWCHART.md`
- `stock_team/cli.py`
- `stock_team/orchestration/adapters.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/tests/unit/core/test_cli.py`
- `stock_team/tests/unit/sop/test_intraday_snapshot.py`

**允许创建：**

- `investing-os/handoff/daily-audit/DAILY-AUDIT-2.md`

**禁止修改：** 除上述报告外的所有文件。

- [ ] **Step 1: 运行限定测试**

```powershell
git rev-parse HEAD
git status --short
python -m pytest stock_team/tests/unit/sop/test_intraday_snapshot.py -q
python -m pytest -q stock_team/tests/unit/core/test_cli.py::test_cli_intraday_snapshot_generation
```

- [ ] **Step 2: 创建审计报告**

Create `investing-os/handoff/daily-audit/DAILY-AUDIT-2.md`:

```markdown
# DAILY-AUDIT-2 开盘观察事实审计

## 审计元数据

- Base commit:
- Branch:
- Allowed scope respected: yes/no

## 预期边界

| 问题 | 文档答案 | 代码行为 | 测试证据 | 证据等级 |
|---|---|---|---|---|
| 开盘观察何时开始和结束 | | | | |
| 无批准计划时允许做什么 | | | | |
| 哪些事实可以刷新 | | | | |
| 哪些盘前锚点禁止改写 | | | | |
| 哪些情况必须回到用户 | | | | |

## 当前入口、产物和动作

| 项目 | 文件与符号 | 当前行为 | 缺口或冲突 |
|---|---|---|---|

## 测试结果

- Command:
- Result:
- Failures:

## 只陈述事实的结论

- 已有：
- 缺失：
- 冲突：
- 需要高阶模型决定：
```

- [ ] **Step 3: 验证并提交**

```powershell
rg -n "建议修改|应该改成|我决定|已完成|完全支持" investing-os/handoff/daily-audit/DAILY-AUDIT-2.md
git diff --check
git status --short
git add -- investing-os/handoff/daily-audit/DAILY-AUDIT-2.md
git commit -m "docs: audit DAILY-2 opening observation"
git push -u origin HEAD
```

### Task 4: DAILY-3 盘中管理事实审计

**负责人级别：** 低阶模型
**任务编号：** `DAILY-AUDIT-3`

**允许读取：**

- `investing-os/PROJECT-CHARTER.zh.md`
- `investing-os/system/workflows/intraday.md`
- `investing-os/system/workflows/intraday-guidance-protocol.md`
- `investing-os/dashboards/intraday-dashboard.html`
- `stock_team/docs/SYSTEM_FLOWCHART.md`
- `stock_team/cli.py`
- `stock_team/server/dashboard_server.py`
- `stock_team/tests/unit/sop/test_intraday_snapshot.py`
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`

**允许创建：**

- `investing-os/handoff/daily-audit/DAILY-AUDIT-3.md`

**禁止修改：** 除上述报告外的所有文件。

- [ ] **Step 1: 检查允许文件并运行测试**

```powershell
git rev-parse HEAD
git status --short
python -m pytest stock_team/tests/unit/sop/test_intraday_snapshot.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q
```

Expected: 记录实际通过/失败数量；失败时不修代码。

- [ ] **Step 2: 创建审计报告**

Create `investing-os/handoff/daily-audit/DAILY-AUDIT-3.md`:

```markdown
# DAILY-AUDIT-3 盘中管理事实审计

## 审计元数据

- Base commit:
- Branch:
- Allowed scope respected: yes/no

## 事实刷新与决策边界

| 能力 | 当前入口 | 数据来源 | 输出 | 是否可能改写盘前锚点 | 测试证据 |
|---|---|---|---|---|---|
| IBKR/持仓事实 | | | | | |
| 价格与 VWAP | | | | | |
| 条件状态 | | | | | |
| 风险与警告 | | | | | |
| 用户例外确认 | | | | | |

## 单次刷新与循环模式

| 模式 | 当前实现 | 状态所有者 | 停止方式 | 缺口 |
|---|---|---|---|---|

## 测试结果

- Command:
- Result:
- Failures:

## 只陈述事实的结论

- 已有：
- 缺失：
- 冲突：
- 需要高阶模型决定：
```

- [ ] **Step 3: 验证并提交**

```powershell
rg -n "建议修改|应该改成|我决定|已完成|完全支持" investing-os/handoff/daily-audit/DAILY-AUDIT-3.md
git diff --check
git status --short
git add -- investing-os/handoff/daily-audit/DAILY-AUDIT-3.md
git commit -m "docs: audit DAILY-3 intraday management"
git push -u origin HEAD
```

### Task 5: DAILY-4 盘后复盘事实审计

**负责人级别：** 低阶模型
**任务编号：** `DAILY-AUDIT-4`

**允许读取：**

- `investing-os/PROJECT-CHARTER.zh.md`
- `investing-os/system/workflows/post-market.md`
- `investing-os/system/workflows/post-market-trade-review.md`
- `investing-os/system/workflows/journal-to-principle-promotion.md`
- `investing-os/system/workflows/packet-absorption.md`
- `stock_team/cli.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/tests/unit/sop/test_postmarket_summary.py`
- `stock_team/tests/unit/core/test_cli.py`

**允许创建：**

- `investing-os/handoff/daily-audit/DAILY-AUDIT-4.md`

**禁止修改：** 除上述报告外的所有文件。

- [ ] **Step 1: 运行限定测试**

```powershell
git rev-parse HEAD
git status --short
python -m pytest stock_team/tests/unit/sop/test_postmarket_summary.py -q
```

- [ ] **Step 2: 创建审计报告**

Create `investing-os/handoff/daily-audit/DAILY-AUDIT-4.md`:

```markdown
# DAILY-AUDIT-4 盘后复盘事实审计

## 审计元数据

- Base commit:
- Branch:
- Allowed scope respected: yes/no

## 收尾链

| 顺序 | 业务动作 | 用户是否必须交互 | 输入 | 输出 | 当前入口 | 证据等级 |
|---:|---|---|---|---|---|---|
| 1 | 获取成交、持仓和市场事实 | | | | | |
| 2 | 生成交易复盘证据包 | | | | | |
| 3 | 区分判断、执行、仓位和情绪 | | | | | |
| 4 | 用户确认当日结论 | | | | | |
| 5 | 生成经验候选 | | | | | |
| 6 | 归档当日并支持次日恢复 | | | | | |

## 无交易日与未完成复盘

| 场景 | 文档定义 | 代码行为 | 测试证据 | 缺口 |
|---|---|---|---|---|
| 无交易日正常关闭 | | | | |
| 快速复盘 | | | | |
| 冻结收尾 | | | | |
| 完整复盘 | | | | |

## 测试结果

- Command:
- Result:
- Failures:

## 只陈述事实的结论

- 已有：
- 缺失：
- 冲突：
- 需要高阶模型决定：
```

- [ ] **Step 3: 验证并提交**

```powershell
rg -n "建议修改|应该改成|我决定|已完成|完全支持" investing-os/handoff/daily-audit/DAILY-AUDIT-4.md
git diff --check
git status --short
git add -- investing-os/handoff/daily-audit/DAILY-AUDIT-4.md
git commit -m "docs: audit DAILY-4 postmarket review"
git push -u origin HEAD
```

## 第二批：高阶模型整合

### Task 6: 形成唯一 DAILY 契约

**负责人级别：** 高阶模型 + 用户
**前置条件：** Task 1–5 的五份报告已经由高阶模型逐份审核。

**Files:**

- Create: `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- Modify: `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`
- Read: `investing-os/handoff/daily-audit/DAILY-AUDIT-0.md`
- Read: `investing-os/handoff/daily-audit/DAILY-AUDIT-1.md`
- Read: `investing-os/handoff/daily-audit/DAILY-AUDIT-2.md`
- Read: `investing-os/handoff/daily-audit/DAILY-AUDIT-3.md`
- Read: `investing-os/handoff/daily-audit/DAILY-AUDIT-4.md`

- [ ] **Step 1: 审核五份报告**

逐份检查：

- 是否越过允许读取范围；
- 是否把文档存在误写为运行可用；
- 是否附实际测试输出；
- 是否区分用户交互、系统事实和高阶决策；
- 是否发现旧 Node、Evidence Stage 与 coordinator state 的冲突。

- [ ] **Step 2: 编写 DAILY 契约**

`DAILY-CONTRACT.zh.md` 必须逐步定义：

```markdown
## DAILY-N 名称

### 目的
### 进入条件
### 系统自动准备
### 必须显示给用户
### 必须由用户确认
### stock_team 输入与输出
### investing-os 输入与输出
### 完成条件
### 允许跳过或降级路径
### 失败与恢复
### 固定产物
### 对应旧入口
```

契约还必须包含：

- DAILY-0 至 DAILY-4 的合法顺序；
- 市场环境证据包与焦点标的证据包在 DAILY-1 内的依赖；
- observation/no-trade 合法路径；
- 前日未复盘的三个用户选择；
- 真实与模拟数据的视觉和 schema 区分；
- IBKR 对持仓和交易事实的唯一正式来源地位；
- 不允许协调器或 `stock_team` 下单。

- [ ] **Step 3: 用户逐段批准交互和完成条件**

没有用户批准，不得修改 coordinator states、actions 或 schema。

- [ ] **Step 4: 更新状态台账**

只根据五份报告和用户批准契约更新状态，不得把 `defined` 或 `documented` 升格为 `runnable`。

- [ ] **Step 5: 验证并提交**

```powershell
rg -n "TBD|TODO|待定|稍后补充" investing-os/system/workflows/DAILY-CONTRACT.zh.md
git diff --check
git add -- investing-os/system/workflows/DAILY-CONTRACT.zh.md investing-os/system/workflows/WORKFLOW-STATUS.zh.md
git commit -m "docs: define canonical DAILY workflow contract"
git push
```

Expected: 无占位符；用户交互、系统动作和证据产物均有明确归属。

## 第三批：契约批准后的实现方向

以下不是当前可直接派发的任务。Task 6 完成后，高阶模型根据真实缺口分别写独立任务单：

1. `DAILY-0` 活动选择、IBKR 事实确认和跨日恢复；
2. `DAILY-1` 统一名称投影、两个证据包验证和用户确认产物；
3. `DAILY-2` 独立开盘观察状态与只读事实刷新；
4. `DAILY-3` 盘中单次刷新、循环生命周期和计划锚点保护；
5. `DAILY-4` 无交易收尾、交易复盘、经验候选与归档；
6. 非交易模拟 fixture 和 DAILY-0 至 DAILY-4 端到端测试；
7. Operating Console 的当前步骤、缺失项、用户确认和恢复动作。

每个实现任务都必须使用 TDD，拥有独立 commit，并在局部测试后运行 DAILY 端到端回归。

## 分发建议

Task 1–5 彼此独立，可分别交给五个低阶模型或按资源分批执行。每个模型使用独立分支或 worktree，并从包含本计划的同一基线 commit 开始。

若并发资源有限，推荐顺序：

1. Task 1 与 Task 5：先查开始、结束和跨日恢复；
2. Task 2：查最复杂的用户决策握手；
3. Task 3 与 Task 4：查开盘与盘中边界。

高阶模型不应在报告回来前开始修代码。
