# DAILY-AUDIT-4 盘后复盘事实审计

## 审计元数据

- Base commit: c1024c3b67a213eea0419cccd486eef84907e673
- Branch: codex/repository-cleanup-20260630
- Allowed scope respected: yes

## 收尾链

| 顺序 | 业务动作 | 用户是否必须交互 | 输入 | 输出 | 当前入口 | 证据等级 |
|---:|---|---|---|---|---|---|
| 1 | 获取成交、持仓和市场事实 | 否 | IBKR fills/orders/positions, market data (Polygon/yfinance) | trade evidence JSON (via `export_trade_evidence.py`) | `python -m stock_team.cli trade-evidence --symbol --date --fills --output` | code-only |
| 2 | 生成交易复盘证据包 | 否 | premarket summary + intraday snapshot + positions.json + day return % | per-stock postmarket summary JSON (execution, performance, signal_accuracy, suggestions) | `stock_team/data_ingest/postmarket_summary.py` → `build_per_stock_summary()` / `write_per_stock_summary()` | test-covered |
| 3 | 区分判断、执行、仓位和情绪 | 是 | 交易复盘证据包 + 市场环境 + 用户访谈 | 分类后的偏差记录 (判断/执行/仓位/情绪/数据) | 文档定义在 `post-market-trade-review.md` Step 3-4；无 `stock_team` 自动化代码；由 `investing-os` 与用户对话完成 | documented |
| 4 | 用户确认当日结论 | 是 | 上一步的分类输出 | 用户确认的当日结论 (噪声 vs 候选经验) | 文档定义在 `PROJECT-CHARTER.zh.md` 第 216 段；无代码入口 | documented |
| 5 | 生成经验候选 | 是 (用户决定哪些进入 LEARNING) | 当日结论 + `generate_suggestions()` 输出 | lesson candidates (类型: lesson_record, thesis_status, correlation_warning 等) | `stock_team/data_ingest/postmarket_data_collector.py` → `generate_suggestions()` | test-covered |
| 6 | 归档当日并支持次日恢复 | 否 (系统操作) | 当日所有产物 | 归档文件 + 状态转换 `MARKET_CLOSED → DAY_ARCHIVED` | `transitions.py` 定义 `("MARKET_CLOSED", "archive_day"): "DAY_ARCHIVED"`；无实际归档写入代码；`dashboard_server.py` 提供 `DAY_ARCHIVED → init-day` 跨日恢复入口 | runtime-unverified |

## 无交易日与未完成复盘

| 场景 | 文档定义 | 代码行为 | 测试证据 | 缺口 |
|---|---|---|---|---|
| 无交易日正常关闭 | `PROJECT-CHARTER.zh.md` DAILY-0: 用户确认今天的活动类型 | `transitions.py` 中 `INTRADAY_ACTIVE → close_market → MARKET_CLOSED` 只定义了标准路径；无「无交易日」专用状态 | 无专项测试 | 无交易日场景没有独立状态或跳过逻辑；当前只能走标准 `MARKET_CLOSED → archive_day` 路径 |
| 快速复盘 | 架构规格 `2026-06-13-unified-investing-operating-system-architecture.zh.md` 第 233 行: 至少检查持仓异常、风险偏离和待处理警告；状态变为 `QUICK_REVIEWED` | `dashboard_server.py` 第 535 行: `if decision.get("choice") in {"freeze", "quick_review", "full_review"}` — 识别用户选择并返回 `init-day`；`transitions.py` 没有 `QUICK_REVIEWED` 状态 | 无专项测试 | UI 层可识别选择，但状态机 (`transitions.py`) 没有 `QUICK_REVIEWED` 状态；复盘内容的最小检查逻辑未实现 |
| 冻结收尾 | 同上规格第 239 行: 昨日状态变为 `CLOSED_UNREVIEWED`，创建带日期的欠账任务 | `dashboard_server.py` 同上，识别 `freeze` 选择后返回 `init-day`；`transitions.py` 没有 `CLOSED_UNREVIEWED` 状态 | 无专项测试 | 欠账任务创建逻辑未实现；`CLOSED_UNREVIEWED` 状态不在 `models.py` 的 `TRADING_STATES` 中 |
| 完整复盘 | 同上规格第 231 行: 先完成完整复盘再开始今天；标准 DAILY-4 路径 | `transitions.py` 仅定义了 `MARKET_CLOSED → archive_day` 单一路径；无完整复盘状态跟踪 | `test_postmarket_summary.py` 11 个测试覆盖了单个标的复盘数据生成，但未测试端到端闭环 | 从 review 开始到 `DAY_ARCHIVED` 的完整串联未验证 |

## 测试结果

- Command: `python -m pytest stock_team/tests/unit/sop/test_postmarket_summary.py -q`
- Result: pass 11, fail 0
- Failures: none

## 只陈述事实的结论

- 已有：
  - `transitions.py` 定义了从 `MARKET_CLOSED` 到 `DAY_ARCHIVED` 的状态转换路径
  - `models.py` 定义了 `REVIEW_REQUIRED` 和 `DAY_ARCHIVED` 状态，以及 `archive_day` action intent
  - `dashboard_server.py` 识别 `freeze`、`quick_review`、`full_review` 三种用户选择并路由到 `init-day`
  - `stock_team` 侧有 `build_per_stock_summary` / `write_per_stock_summary` (test-covered, 11/11 pass)
  - `generate_suggestions` 可为每个标的生成 lesson_record / thesis_status 等建议类型 (test-covered)
  - `post-market-trade-review.md` 定义了完整的 8 步复盘流程和 completion rule checklist
  - `journal-to-principle-promotion.md` and `packet-absorption.md` 定义了经验吸收的目标文件和决策路径

- 缺失：
  - 步骤 3 (区分判断/执行/仓位/情绪) 没有代码实现 — 纯属 human + investing-os 对话任务，文档定义完成但无可执行入口
  - 步骤 4 (用户确认当日结论) 没有代码实现 — 存在于文档描述中，但没有任何 CLI 命令、API 端点或状态转换与之对应
  - 步骤 6 (归档当日) 的 `archive_day` 在 `transitions.py` 中仅定义了状态名称转换，没有实际的归档写入逻辑 (文件写入、产物清单生成、索引更新)
  - `QUICK_REVIEWED` 和 `CLOSED_UNREVIEWED` 状态不在 `TRADING_STATES` 集合中 (架构规格定义了这些状态但 `models.py` 未注册)
  - `transitions.py` 没有 `REVIEW_REQUIRED` 状态的处理 — 该状态在 `models.py` 定义但不在任何 `BEGIN_TRANSITIONS` 或 `SUCCESS_TRANSITIONS` 中
  - 跨日恢复的 `init-day` 动作不在 `ACTION_INTENTS` 集合中
  - 未完成复盘的欠账任务 (backlog item) 没有代码创建逻辑
  - 从 `REVIEW_REQUIRED` 或 `MARKET_CLOSED` 到 `DAY_ARCHIVED` 没有经过步骤 3-5 的强制门控

- 冲突：
  - `models.py` 定义了 `REVIEW_REQUIRED` 状态但 `transitions.py` 不识别它 — architecture spec 描述了一个从 `INTRADAY_ACTIVE` 不能直接进入新交易日的中间状态，但代码中该状态不存在于任何 TRANSITIONS 字典
  - 架构规格定义了三种复盘场景 (快速/冻结/完整) 和对应状态 (`QUICK_REVIEWED`、`CLOSED_UNREVIEWED`、`REVIEW_PENDING`)，但 `models.py` 的 `TRADING_STATES` 只包含 `REVIEW_REQUIRED` 和 `DAY_ARCHIVED`，三个规格状态均未注册
  - `dashboard_server.py` 的 `_postmarket_action()` 将 `freeze`/`quick_review`/`full_review` 都映射到 `init-day`，但 architecture spec 要求不同选择产生不同状态 (`QUICK_REVIEWED` vs `CLOSED_UNREVIEWED` vs 继续完整复盘)

- 需要高阶模型决定：
  - `archive_day` 的实际实现范围：是否只需要状态转换 (当前)，还是需要写入归档文件、更新产物清单、刷新 dashboard 索引 (文档描述)
  - 是否将 `QUICK_REVIEWED`、`CLOSED_UNREVIEWED`、`REVIEW_PENDING` 加入 `TRADING_STATES` 并接入 `transitions.py`
  - 步骤 3 (区分判断/执行/仓位/情绪) 是保持纯 human + investing-os 对话，还是需要一个结构化输入表单或 CLI 命令
  - 步骤 4 (用户确认当日结论) 的交互形式：CLI 确认、dashboard 按钮、还是对话响应解析
  - 非交易日场景是否需要一个新的 session_type (当前 `SESSION_TYPES` 只有 trading/observation/research/review/maintenance，但无 "non-trading-day" 或 "skip-day")
