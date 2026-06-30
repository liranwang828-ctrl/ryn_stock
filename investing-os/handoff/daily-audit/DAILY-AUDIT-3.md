# DAILY-AUDIT-3 盘中管理事实审计

## 审计元数据

- Base commit: c1024c3b67a213eea0419cccd486eef84907e673
- Branch: codex/repository-cleanup-20260630
- Allowed scope respected: yes

## 事实刷新与决策边界

| 能力 | 当前入口 | 数据来源 | 输出 | 是否可能改写盘前锚点 | 测试证据 |
|---|---|---|---|---|---|
| IBKR/持仓事实 | `cli.py handle_intraday_snapshot()` (yfinance fallback); `dashboard_server.py sync_price_refresh_state()` | `config/positions.json` (静态文件); `intraday.md` 文档记载的 IBKR streaming (`ibkr_monitor.py`) 未在本次审计的代码路径中验证 | `intraday_snapshot.json`; `portfolio_snapshot_current.json` | 否。`handle_intraday_snapshot()` 读取 premarket summary 的 stop/entry 作为参考但不可写。`sync_price_refresh_state()` 仅更新 `broker_last_price` 字段，不触碰锚点。 | `test_dashboard_refresh_prices.py`: `test_price_refresh_state_sync_updates_positions_snapshot_and_nodes` 验证价格同步但不验证锚点改写 |
| 价格与 VWAP | `cli.py handle_intraday_snapshot()` | yfinance (proxy VWAP = (H+L+C)/3); `intraday.md` 文档记载的 IBKR anchored VWAP 未在本次审计验证 | `intraday_snapshot.json`; CLI markdown 输出 | 否。VWAP 仅作为事实字段输出，不写回 premarket summary。 | 无直接 VWAP 测试。`test_intraday_snapshot.py` 测试距离公式但未测试 VWAP 计算精度。 |
| 条件状态 | `stock_team/data_ingest/intraday_snapshot.py` 中的 `compute_thesis_signal()` / `compute_entry_go_status()` / `detect_event()` | `premarket_summary_{date}_{sym}.json` 中的 thesis_status; `poll_state_{date}.json` 中的历史状态 | `poll_state_{date}.json` (更新后的 symbol 状态); `intraday_snapshot_{date}_{sym}.jsonl` | 是（间接）。`get_effective_nodes()` 优先使用 `post_open_adj` 值覆盖原始 premarket 节点（entry_base/hard_stop/target/flex_add/flex_reduce）。此机制允许盘后调整改写盘前锚点，但仅影响内存中的 effective nodes，不写回 premarket summary 文件。 | `test_intraday_snapshot.py`: `test_get_effective_nodes_prefers_adj` 验证 post_open_adj 优先；`test_thesis_signal_breach_on_stop` 等 5 个测试覆盖条件状态计算 |
| 风险与警告 | `cli.py handle_intraday_snapshot()` 生成 proximity alerts; `SYSTEM_FLOWCHART.md` 记载 `poll.py` 中的 VIX spike / leverage / thesis health 检查 | yfinance prices; premarket summary stop 价位; `positions.json` 杠杆持仓映射 | CLI markdown 输出的 Position Proximity Alerts 章节; `intraday_snapshot.json` 中的 alerts 数组 | 否。风险检查是只读评估，不修改锚点。 | `test_intraday_snapshot.py`: `test_detect_event_hard_stop_breach` / `test_detect_event_thesis_breach` 验证事件检测逻辑 |
| 用户例外确认 | `dashboard_server.py` coordinator state machine: `record_focus_confirmation` 标记 `user_confirmation: True` | coordinator session state; decision sheet | `trading-{date}.json` (session state); `{session_id}.json` (decision sheet) | 不适用。确认流程属于 investing-os 的决策域，不直接操作 premarket 锚点。 | `test_dashboard_refresh_prices.py`: `test_coordinator_summary_exposes_skill_guided_stage0_discussion` 验证确认任务结构，但该流程仅覆盖盘前阶段（STAGE0_READY），未发现盘中例外确认的测试覆盖 |

## 单次刷新与循环模式

| 模式 | 当前实现 | 状态所有者 | 停止方式 | 缺口 |
|---|---|---|---|---|
| 单次刷新 (intraday snapshot) | `cli.py handle_intraday_snapshot()` 的 `--refresh` 标志：运行 `refresh_prices.py --once` 后采集 yfinance 快照并输出 markdown/JSON。无循环逻辑。 | 调用者（CLI 进程本身） | 进程退出即停止 | 不写入 `intraday_snapshot.json`（此文件路径在 `intraday.md` schema 中定义但 cli.py 不写入）；输出是独立 markdown 文件而非统一 JSON。 |
| 循环模式 (poll loop) | `SYSTEM_FLOWCHART.md` 记载 `/loop 2m` 命令持续运行 `poll.py`；`dashboard_server.py` `/api/run?task=poll` 启动后台子进程。`intraday-dashboard.html` 以 5 秒间隔 `fetch()` `intraday_snapshot.json`。 | `/loop 2m` 由 session_manager 管理；`/api/run?task=poll` 由 `ACTIVE_TASKS` 字典跟踪；dashboard 前端自主轮询不管理状态 | `/api/stop` 杀死子进程；`/loop` 的终止机制未在本次审计文件中发现 | (a) `intraday-dashboard.html` 的前端轮询（5s）与后端 snapshot 生产之间不存在驱动关系——前端假设 JSON 文件已由外部进程写入；(b) `cli.py` 的 `handle_intraday_snapshot()` 不实现循环模式，与 `intraday.md` 描述的 `ibkr_monitor.py` 持续 streaming 模式是两条独立路径；(c) 循环模式的停止方式在 dashboard API 中有 `/api/stop` 端点（代码存在，未完整审阅其实现），但 `/loop 2m` 的停止机制不在本次审计范围。 |

## 测试结果

- Command: `python -m pytest stock_team/tests/unit/sop/test_intraday_snapshot.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q`
- Result: pass 30, fail 0
- Failures: none

## 只陈述事实的结论

- 已有：
  - `intraday_snapshot.py` 提供 `compute_thesis_signal` / `compute_entry_go_status` / `detect_event` / `get_effective_nodes` 等条件计算函数，均已测试覆盖（evidence: test-covered）。
  - `cli.py handle_intraday_snapshot()` 提供单次盘中快照 CLI，输出 markdown 格式的 proximity alerts 和 VWAP 偏差（evidence: code-only）。
  - `dashboard_server.py sync_price_refresh_state()` 将手动刷新价格同步到 positions.json / portfolio_snapshot_current.json / dashboard_cache.json / current_nodes.json（evidence: test-covered）。
  - `intraday-dashboard.html` 是静态 HTML 模板，通过前端 JS `fetch()` 轮询 `intraday_snapshot.json`（evidence: code-only）。该 HTML 本身没有服务端集成——只是一个期望 JSON 文件已存在于磁盘上的消费者。
  - `intraday-guidance-protocol.md` 定义了 Green/Yellow/Red/No-Trade 状态机及 investing-os / stock_team 的决策边界（evidence: documented）。

- 缺失：
  - `intraday.md` 文档记载的 `ibkr_monitor.py` 持续 streaming 路径在本次审计的 Python 代码中未被验证——`handle_intraday_snapshot()` 仅使用 yfinance fallback（evidence: conflict between documented and code-verified）。
  - `cli.py handle_intraday_snapshot()` 的输出路径与 `intraday.md` schema 定义的 `intraday_snapshot.json` 路径不一致：cli.py 写入 `--out` 指定的任意路径，不写入 `investing-os/system/data/packets/intraday_snapshot.json`（evidence: code-only）。
  - 盘中用户例外确认的代码实现仅存在于盘前 coordinator（STAGE0_READY -> FOCUS_CONFIRMED），未发现盘中阶段（INTRADAY_ACTIVE）的例外确认或权限变更流程（evidence: missing）。
  - `get_effective_nodes()` 的 `post_open_adj` 机制存在但无文档说明其何时、由谁、以何依据填充——代码中存在但 workflow 文档未提及（evidence: code-only, undocumented）。

- 冲突：
  - `intraday.md` 描述 `ibkr_monitor.py` 作为 Primary streaming source，但 `cli.py` 和 `dashboard_server.py` 的实际价格来源均为 yfinance 和本地 JSON 文件。IBKR 路径在本次审计的代码中未被发现（evidence: conflict）。
  - `intraday-dashboard.html` 的 `SNAPSHOT_URL = '../system/data/packets/intraday_snapshot.json'` 假设相对于 HTML 文件位置的路径，但从 `dashboard_server.py` 的路由看，该 HTML 是通过 `handle_static_dashboard_page()` 直接 serve 的，不会经过 investing-os 路径解析。在生产环境中此相对路径可能解析失败（evidence: code-only, runtime-unverified）。

- 需要高阶模型决定：
  - `post_open_adj` 机制是否应继续存在——它允许盘中改写 premarket 锚点，但无文档、无触发规则、无权限控制（evidence: code-only, undocumented）。
  - `ibkr_monitor.py` 路径是继续推进还是正式降级为 yfinance-only——当前文档声称 IBKR 是 primary source，但代码实现是 yfinance fallback（evidence: conflict）。
  - `intraday-dashboard.html` 的前端轮询（5s）是否需要一个后端驱动的 snapshot 生产者——当前 HTML 是纯消费者，依赖外部进程预先写入 JSON，无契约保证 JSON 新鲜度（evidence: code-only, runtime-unverified）。
