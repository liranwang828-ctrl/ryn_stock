# Stage0 真实试跑阻断低阶任务包

日期：2026-07-03  
前置纲领：[`2026-07-03-stage0-real-run-blockers-charter.zh.md`](./2026-07-03-stage0-real-run-blockers-charter.zh.md)

## 总原则

- 只处理真实试跑阻断
- 不扩大到 DAILY 其他阶段
- 每个任务独立 commit
- 每轮交付必须给出真实命令结果，而不只是测试结果

---

## R1 — 补齐 `38a4dc9` 等价修补到当前分支

目标：

- 让当前工作分支真实包含 `new_trading_session().allowed_actions` 的修补

允许读取：

- `stock_team/orchestration/models.py`
- `stock_team/tests/unit/orchestration/test_models.py`
- `stock_team/coordinator_cli.py`

允许修改：

- `stock_team/orchestration/models.py`
- `stock_team/tests/unit/orchestration/test_models.py`

禁止修改：

- `stock_team/server/dashboard_server.py`
- `stock_team/orchestration/adapters.py`
- `stock_team/cli.py`

必须证明：

- 当前分支代码中 `new_trading_session()` 的 `allowed_actions` 同时包含
  - `start_stage0`
  - `start_stage0_from_snapshot`

验收命令：

- `python -m pytest stock_team/tests/unit/orchestration/test_models.py -q`

额外真实检查：

- 用隔离 runtime 跑一次：
  - `python -m stock_team.coordinator_cli init-day --date 2026-07-03 --session-type trading --runtime-dir <isolated sessions dir>`
- 并展示生成 session JSON 中的 `allowed_actions`

---

## R2 — 修复 `market-context` 真实 `--as-of` 集成阻断

目标：

- 修复 `start_stage0_from_snapshot` 真实命令链里 `market-context` 无法正确吃进 `--as-of` 的问题

允许读取：

- `stock_team/orchestration/adapters.py`
- `stock_team/cli.py`
- `stock_team/tests/unit/orchestration/test_adapters.py`
- `stock_team/tests/unit/core/test_cli.py`

允许修改：

- `stock_team/orchestration/adapters.py`
- `stock_team/cli.py`
- `stock_team/tests/unit/orchestration/test_adapters.py`
- `stock_team/tests/unit/core/test_cli.py`

禁止修改：

- `stock_team/server/dashboard_server.py`
- `stock_team/tests/integration/test_daily_e2e.py`
- DAILY-4 / archive / review 相关文件

必须证明：

- 不是只修 FakeAdapter 单测
- 必须给出真实命令执行证据：
  - `python -m stock_team.cli market-context ...`
  - 在 formal snapshot 场景下不再报 `--as-of is required`

验收命令：

- `python -m pytest stock_team/tests/unit/orchestration/test_adapters.py -q`
- `python -m pytest stock_team/tests/unit/core/test_cli.py -q`

额外真实检查：

- 在隔离 runtime 下直接运行一条 `python -m stock_team.cli market-context ...`
- 展示返回码与产物文件存在性

---

## R3 — 真实隔离试跑闭环验证

目标：

- 在当前分支上重新完成一次真实隔离试跑
- 证明 `start_stage0_from_snapshot` 可以从 `DAY_INITIALIZED` 推进到 `STAGE0_READY`

允许读取：

- `stock_team/coordinator_cli.py`
- `stock_team/server/dashboard_server.py`
- `stock_team/orchestration/*`
- `stock_team/tests/unit/orchestration/test_coordinator.py`
- `stock_team/tests/integration/test_daily_e2e.py`

允许修改：

- 仅当 R1/R2 真实修补需要时，允许最小测试补充

禁止修改：

- 不允许再扩大业务逻辑范围

必须证明：

1. `init-day` 后 session `allowed_actions` 包含 `start_stage0_from_snapshot`
2. `_default_stage0_action()` 在 formal-ready 时返回 `start_stage0_from_snapshot`
3. `python -m stock_team.coordinator_cli run --action <stage0-from-snapshot action json>` 之后
   - session 进入 `STAGE0_READY`
   - 产出 Stage 0 packet
4. 原 `start_stage0` 路径未破坏

验收命令：

- `python -m pytest stock_team/tests/unit/orchestration/test_coordinator.py -q`
- `python -m pytest stock_team/tests/integration/test_daily_e2e.py -q`

额外真实检查：

- 必须附一段隔离 runtime 真实试跑记录摘要

---

## 推荐分发顺序

1. R1
2. R2
3. R3

R3 不应在 R1/R2 未过前启动。
