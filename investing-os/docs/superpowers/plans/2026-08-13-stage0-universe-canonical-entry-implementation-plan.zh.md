# Stage 0 Universe Canonical 入口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将既有 Stage 0 universe builder 从 Dashboard 私有实现提取为共享模块，并提供可由当前对话调用的 canonical CLI 入口，使隔离 DAILY observation 从 DAILY-1A 推进至 DAILY-1B。

**Architecture:** 新模块 `stock_team/orchestration/stage0_universe.py` 成为 universe 生成的唯一实现，显式接收 `base_dir`、`runtime_root`、交易日期和 session id。Dashboard 保留兼容包装函数并调用共享模块；coordinator CLI 根据 `--runtime-dir` 推导同一 runtime root，绝不回退到仓库默认 runtime。

**Tech Stack:** Python 3.10、argparse、pathlib、pytest、现有 SessionStore / Dashboard helper。

---

## 文件结构

- 新建 `stock_team/orchestration/stage0_universe.py`：共享 universe builder 与原子 JSON 写入。
- 修改 `stock_team/server/dashboard_server.py`：删除重复业务实现，保留薄包装调用共享 builder。
- 修改 `stock_team/coordinator_cli.py`：新增 `prepare-stage0-universe` 命令。
- 新建 `stock_team/tests/unit/orchestration/test_stage0_universe.py`：锁定 builder 结构与路径。
- 修改 `stock_team/tests/unit/orchestration/test_coordinator_cli.py`：锁定 CLI 状态不变与隔离 runtime。
- 修改 `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`：锁定 Dashboard 共用 builder 后行为不变。
- 修改 8 月试跑记录、CURRENT-CONTEXT 与工作流台账：记录真实验收结果。

### Task 1：共享 builder

**Files:**
- Create: `stock_team/orchestration/stage0_universe.py`
- Create: `stock_team/tests/unit/orchestration/test_stage0_universe.py`

- [ ] **Step 1: 写失败测试**

测试调用：

```python
build_stage0_universe_document(
    base_dir=stock_team_home,
    runtime_root=runtime_root,
    market_date="2026-08-13",
    session_id="observation-2026-08-13",
)
```

断言输出路径等于 `runtime_root / "inputs" / "observation-2026-08-13-stage0-universe.json"`，并包含 `source_inputs.positions`、`prior_review`、`cognition_state`、`permission_state_before_open`、`forbidden_actions`。

- [ ] **Step 2: 运行失败测试**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_stage0_universe.py -q`

Expected: FAIL，因为模块或函数尚不存在。

- [ ] **Step 3: 提取最小实现**

函数签名固定为：

```python
def build_stage0_universe_document(
    *,
    base_dir: str | Path,
    runtime_root: str | Path,
    market_date: str,
    session_id: str,
) -> tuple[Path, str]:
```

复制现有 `_build_stage0_universe_document()` 的业务内容，只把 inputs 目录改为显式 `runtime_root / "inputs"`，并使用临时文件加 `replace()` 原子写入。

- [ ] **Step 4: 运行测试**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_stage0_universe.py -q`

Expected: PASS。

### Task 2：CLI canonical 入口

**Files:**
- Modify: `stock_team/coordinator_cli.py`
- Modify: `stock_team/tests/unit/orchestration/test_coordinator_cli.py`

- [ ] **Step 1: 写失败测试**

先 `init-day --runtime-dir <runtime/sessions>`，再执行：

```text
prepare-stage0-universe --session-id observation-2026-08-13 --runtime-dir <runtime/sessions>
```

断言：

- 输出 JSON 的 `universe_path` 位于同一 `<runtime>/inputs`；
- 文件存在且 date/session 对应；
- session state、state_version 不变；
- session 没有新增 `daily0_confirmation`。

- [ ] **Step 2: 运行失败测试**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_coordinator_cli.py -k prepare_stage0_universe -q`

Expected: FAIL，命令不存在。

- [ ] **Step 3: 实现 CLI**

parser 新增 `prepare-stage0-universe` 的 `--session-id` 与 `--runtime-dir`。handler 加载 session，以 `Path(args.runtime_dir).resolve().parent` 作为 runtime root，调用共享 builder并输出：

```json
{
  "session_id": "observation-2026-08-13",
  "market_date": "2026-08-13",
  "universe_path": "...",
  "journal_path": ""
}
```

- [ ] **Step 4: 运行 CLI 测试**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_coordinator_cli.py -k "prepare_stage0_universe or confirm_daily0" -q`

Expected: PASS。

### Task 3：Dashboard 共用 builder

**Files:**
- Modify: `stock_team/server/dashboard_server.py`
- Modify: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`

- [ ] **Step 1: 写失败测试**

在现有 `_default_stage0_action()` 测试中断言生成 universe 位于传入 `INVESTING_OS_HOME/system/runtime/inputs`，且包含共享 builder 的 canonical `artifact_type` 与五类脑侧字段。

- [ ] **Step 2: 运行测试并记录当前行为**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k default_stage0_action -q`

若现有断言通过，则新增源代码契约断言：Dashboard 的包装函数必须调用 `build_stage0_universe_document`，以便该测试在提取前失败。

- [ ] **Step 3: 替换 Dashboard 私有实现**

保留 `_build_stage0_universe_document(base_dir, market_date, session_id)` 兼容签名，内部只计算 runtime root 并调用共享 builder；删除原函数中的重复构造逻辑。

- [ ] **Step 4: 运行 Dashboard 测试**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q`

Expected: PASS。

### Task 4：隔离链路验收与状态落盘

**Files:**
- Modify: `investing-os/handoff/2026-08-13-daily-minimal-regression.zh.md`
- Modify: `investing-os/handoff/CURRENT-CONTEXT.zh.md`
- Modify: `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`

- [ ] **Step 1: 运行完整相关回归**

Run:

```text
python -m pytest stock_team/tests/unit/orchestration stock_team/tests/integration/test_daily_e2e.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q
```

Expected: 0 failures。

- [ ] **Step 2: 在新的隔离 canonical runtime 重跑**

顺序执行 `init-day`、`prepare-stage0-universe`、`confirm-daily0`、`start_stage0_observation`，随后生成 coordinator summary。

验收：

- universe、snapshot、market context 都是 present/valid/fresh；
- daily-status 为 `DAILY-1B / waiting_user`；
- permission 仍为 `no_trading_permission`；
- session 与所有产物属于同一交易日期和 runtime。

- [ ] **Step 3: 更新三份状态文档**

写入命令、测试数量、运行结果和下一个真实阻塞；不得把 `DAILY=partial` 提升为 stable，除非跨日恢复与盘中实时价格也完成同一轮 runtime 验证。

- [ ] **Step 4: 差异与链接检查**

Run:

```text
git diff --check -- <本轮文件>
```

并确认三份 Markdown 的相对链接存在。

- [ ] **Step 5: 独立提交并推送**

只 stage 本计划列出的文件，提交信息：

```text
fix: add canonical Stage 0 universe preparation
```

推送 `codex/repository-cleanup-20260630`，确认远端 ahead/behind 为 `0/0`。
