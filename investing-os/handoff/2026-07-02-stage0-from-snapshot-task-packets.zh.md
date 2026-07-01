# Stage0 From Snapshot 低阶任务包

日期：2026-07-02  
前置设计：[`2026-07-02-stage0-from-snapshot-design.zh.md`](./2026-07-02-stage0-from-snapshot-design.zh.md)  
适用范围：仅实现 `start_stage0_from_snapshot` 最小链路

## 总原则

- 不允许修改 `start_stage0` 既有语义
- 不允许扩大 snapshot 来源范围
- 只允许正式 `formal_provider_snapshot` 走新链路
- 每个任务独立 commit
- 每个任务完成后必须附测试结果与未解决风险

---

## L1 — Orchestration 最小接线

目标：

- 在 orchestration 层新增 `start_stage0_from_snapshot`
- 让它成为一个 canonical intent
- 让 adapter 对该 intent 只执行 `market-context --pre-market-snapshot ...`

允许读取：

- `stock_team/orchestration/models.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/orchestration/adapters.py`
- `stock_team/tests/unit/orchestration/test_adapters.py`
- `stock_team/tests/unit/orchestration/test_models.py`
- `stock_team/tests/unit/orchestration/test_transitions.py`

允许修改：

- `stock_team/orchestration/models.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/orchestration/adapters.py`
- `stock_team/tests/unit/orchestration/test_adapters.py`
- `stock_team/tests/unit/orchestration/test_models.py`
- `stock_team/tests/unit/orchestration/test_transitions.py`

禁止修改：

- `stock_team/server/dashboard_server.py`
- 任何 DAILY-4 / archive / recovery 相关文件
- `start_stage0` 现有测试断言

输入契约：

- 新 intent 名称固定为 `start_stage0_from_snapshot`
- 输入参数至少包含：
  - `date`
  - `as_of`
  - `universe`
  - `pre_market_snapshot`
  - `out`

输出契约：

- `models.py` 接受该 intent
- `transitions.py` 允许从 `DAY_INITIALIZED` 进入该动作
- `adapters.py` 对该 intent 只构造一个 `market-context` 命令

验收命令：

- `python -m pytest stock_team/tests/unit/orchestration/test_models.py -q`
- `python -m pytest stock_team/tests/unit/orchestration/test_transitions.py -q`
- `python -m pytest stock_team/tests/unit/orchestration/test_adapters.py -q`

完成定义：

- 现有 `start_stage0` 行为测试不变
- 新增测试证明 `start_stage0_from_snapshot` 不调用 `premarket-snapshot`

---

## L2 — Dashboard / Coordinator 动作选择接线

目标：

- 当 snapshot 被判定为 `formal_provider_snapshot` 且 `formal_ready == true` 时
- Dashboard / coordinator 默认产出 `start_stage0_from_snapshot`
- 否则保持 `start_stage0`

允许读取：

- `stock_team/server/dashboard_server.py`
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`
- `stock_team/orchestration/models.py`
- `stock_team/orchestration/transitions.py`

允许修改：

- `stock_team/server/dashboard_server.py`
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`

禁止修改：

- `stock_team/orchestration/adapters.py`
- `stock_team/cli.py`
- 任何 archive / review / intraday 文件

输入契约：

- 只能复用现有 `formal_provider_snapshot` / `formal_ready` 判定
- 不允许新发明第二套 formal 判断逻辑

输出契约：

- `_default_stage0_action()` 在 formal-ready 时返回 `start_stage0_from_snapshot`
- 否则仍返回 `start_stage0`
- 相关 summary / current_task / first_action 表现与状态一致

验收命令：

- `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q`

完成定义：

- 新增测试证明 formal-ready 时默认动作切换到 `start_stage0_from_snapshot`
- 非 formal-ready 时仍保持 `start_stage0`

---

## L3 — Coordinator 隔离验收与回归

目标：

- 用隔离 runtime 验证“已有正式 snapshot”路径
- 确认它能从 `DAY_INITIALIZED` 推进到 `STAGE0_READY`
- 并且不影响原 `start_stage0` 路径

允许读取：

- `stock_team/tests/unit/orchestration/test_coordinator.py`
- `stock_team/tests/integration/test_daily_e2e.py`
- `stock_team/server/dashboard_server.py`
- `stock_team/orchestration/*`

允许修改：

- `stock_team/tests/unit/orchestration/test_coordinator.py`
- `stock_team/tests/integration/test_daily_e2e.py`
- 如确有必要，可微调与新 intent 直接相关的 orchestration 文件

禁止修改：

- `stock_team/cli.py`
- 非 Stage 0 范围的业务逻辑

输入契约：

- 测试中使用正式 snapshot 文件夹路径
- 不依赖真实 paid provider 在线

输出契约：

- 至少一条 coordinator / integration 测试证明：
  - `start_stage0_from_snapshot` 成功推进到 `STAGE0_READY`
  - 产出 Stage 0 packet artifact

验收命令：

- `python -m pytest stock_team/tests/unit/orchestration/test_coordinator.py -q`
- `python -m pytest stock_team/tests/integration/test_daily_e2e.py -q`

完成定义：

- 新链路通过隔离测试
- 原有 Stage 0 测试未被破坏

---

## 高阶复核顺序

固定按以下顺序复核，不并审：

1. L1
2. L2
3. L3

每轮低阶交付必须包含：

- 本轮只审范围
- commit SHA
- 改动文件列表
- 新增/修改测试列表
- 验收命令与结果
- 未确认风险

推荐交付模板：

- 使用 [`LOW-TOKEN-REVIEW-TEMPLATE.zh.md`](./LOW-TOKEN-REVIEW-TEMPLATE.zh.md)

## 当前建议分发方式

- 低阶模型 1：L1
- 低阶模型 2：L2
- L3 等 L1/L2 都过后再发

原因：

- L1 与 L2 基本并行
- L3 依赖前两者完成后再做完整隔离验收
