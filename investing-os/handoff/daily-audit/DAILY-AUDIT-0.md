# DAILY-AUDIT-0 晨间准备事实审计

## 审计元数据

- Base commit: c1024c3b67a213eea0419cccd486eef84907e673
- Branch: codex/repository-cleanup-20260630
- Allowed scope respected: yes

## 预期用户交互

| 交互 | 文档证据 | 代码入口 | 测试证据 | 证据等级 |
|---|---|---|---|---|
| 选择 trading / observation / research / review / maintenance | PROJECT-CHARTER.zh.md 4.1 定义六种工作流类型；Architecture spec 4.2 定义 Session Router 五种活动类型；Architecture spec 5.2 列出非交易会话类型 | models.py L6 定义 SESSION_TYPES 常量；models.py L155-171 new_trading_session() 硬编码 session_type="trading"；coordinator_cli.py init-day 无 mode 参数 | test_models.py 覆盖 session_type 校验 | documented（概念完整），code-only（类型常量存在），但 Router 未实现：CLI 无模式选择参数，只有 trading 可运行 |
| 处理前日未完成状态 | Architecture spec Section 7 描述跨日恢复三种选项（快速复盘/冻结欠账/完整复盘），提及 REVIEW_PENDING、QUICK_REVIEWED、CLOSED_UNREVIEWED 状态 | coordinator_cli.py init-day 硬编码 expected_state="IDLE"，假定无前日会话；store.py create() 遇已存在 session 抛 SessionConflictError；transitions.py 无跨日恢复转换、无上述三种状态 | 无 | documented（规格完整），missing（代码零实现） |
| 确认账户、持仓、近期成交与暴露事实 | PROJECT-CHARTER DAILY-0 系统准备："IBKR 可用的账户、持仓、近期成交和暴露事实" | ibkr_monitor.py update_positions_file() 从 IBKR 同步账户/持仓到 positions.json；run_monitor_loop() 提供实时账户数值；transitions.py 无确认闸门 | test_ibkr_monitor.py（11 passed）覆盖 monitor 函数 | test-covered（IBKR 同步函数），missing（工作流确认闸门） |
| 确认今日持仓、观察对象和问题 | PROJECT-CHARTER DAILY-0 用户交互："确认需要进入盘前判断的持仓、观察对象和问题" | ibkr_monitor.py parse_watchlist_symbols() 读取 current-watchlist.md；get_positions_symbols() 读取 positions.json；coordinator 流程无确认动作 | 无 | documented（章程），missing（coordinator 无此步骤） |

## 当前入口与状态

| 项目 | 文件与符号 | 当前行为 | 缺口或冲突 |
|---|---|---|---|
| init-day | coordinator_cli.py main() `init-day --date`；models.py new_trading_session() | 创建 IDLE→DAY_INITIALIZED 的交易会话，allowed_actions=["start_stage0"]，session_type 硬编码为 "trading" | 无 mode 参数；expected_state 硬编码为 "IDLE"，忽略前日未完成会话；无交易日验证 |
| session persistence | store.py SessionStore.create/load/save | 原子写入（tmp+suffix→os.replace）、文件锁（O_CREAT\|O_EXCL）、乐观锁（state_version 比对）；会话文件位于 {runtime_dir}/{session_id}.json | 无跨日查询能力；无会话列表功能；无多会话操作 |
| IBKR provenance | ibkr_monitor.py _cleanup_legacy_position_metadata()、update_positions_file() | 剥离遗留 metadata 键（broker_snapshot、cash_note、positions_update_note、market_trade_date、broker_price_source）；设置 account_sync_source/positions_source/trade_history_source 为 ibkr_live_api/ibkr_tws_api_reqExecutions | 未与 coordinator 集成；作为独立进程运行；coordinator 无触发 IBKR 同步的动作 |
| cross-day recovery | 无 | 不可用 | Architecture spec Section 7 完整描述了三种恢复选项和 REVIEW_PENDING/QUICK_REVIEWED/CLOSED_UNREVIEWED 状态，但代码中不存在对应实现：transitions.py 无这些状态、coordinator_cli.py 无跨日检查逻辑、store.py 无前日会话查询能力 |

## 固定产物

| 产物 | 当前路径 | 生产者 | 是否有 schema | 是否有测试 |
|---|---|---|---|---|
| 会话状态 JSON | {runtime_dir}/sessions/{session_id}.json（默认 investing-os/system/runtime/sessions/） | store.py SessionStore | 有：models.py validate_session() 校验 session_id、session_type、state、state_version、artifacts、data_quality、pending_confirmations、allowed_actions、processed_actions、updated_at 等必填字段及格式 | 有（test_store.py） |
| 盘中快照 JSON | investing-os/system/data/packets/intraday_snapshot.json | ibkr_monitor.py write_snapshot_packets() | 无正式 schema；内联 dict 结构含 timestamp、source、account（cash/net_liquidation/unrealized_pnl/day_pnl）、positions、alerts | 有（test_ibkr_monitor.py） |
| 盘中快照 MD | investing-os/system/data/packets/intraday_snapshot.md | ibkr_monitor.py write_snapshot_packets() | 无正式 schema | 有（test_ibkr_monitor.py，同函数） |
| IB 事件日志 | investing-os/system/data/packets/ib_event_log.json | ibkr_monitor.py log_ib_event() | 无正式 schema；列表结构，每条含 timestamp、event 及动态 detail 字段 | 有（test_ibkr_monitor.py） |
| positions.json（IBKR 同步更新） | config/positions.json | ibkr_monitor.py update_positions_file()（也由 entry_guard.py 写入） | 无正式 schema；约定结构含 cash、net_liquidation、positions 等 | 有（test_ibkr_monitor.py） |

## 测试结果

- Command: `python -m pytest stock_team/tests/unit/orchestration/test_coordinator_cli.py stock_team/tests/unit/orchestration/test_models.py stock_team/tests/unit/orchestration/test_store.py stock_team/tests/unit/core/test_ibkr_monitor.py -q`
- Result: pass 11, fail 0
- Failures: none

## 只陈述事实的结论

- 已有：SESSION_TYPES 常量定义（models.py，六种会话类型已声明）；交易会话的 init-day→DAY_INITIALIZED→STAGE0_RUNNING→STAGE0_READY 正向转换链（transitions.py，七步 BEGIN_TRANSITIONS + 两步 SUCCESS_TRANSITIONS）；会话持久化与乐观锁（store.py，原子写入 + 文件锁 + state_version 比对）；IBKR 实时账户/持仓同步与盘中监控（ibkr_monitor.py，含在线流模式与离线 yfinance 降级）；会话状态 schema 校验（models.py validate_session + validate_action）
- 缺失：会话路由器（无 CLI 参数或 UI 支持 observation/research/review/maintenance 模式选择）；跨日恢复逻辑（transitions.py 无 REVIEW_PENDING/QUICK_REVIEWED/CLOSED_UNREVIEWED 状态，coordinator_cli.py 无前日会话检查，store.py 无跨日查询）；coordinator 流程中的账户/持仓/观察对象确认闸门；非交易会话类型的状态转换定义
- 冲突：PROJECT-CHARTER DAILY-0 描述"确认今天的活动类型"为用户交互，但 coordinator_cli.py init-day 无活动类型参数且硬编码 session_type="trading"；Architecture spec 4.2 描述 Session Router 在创建状态前识别活动类型，但代码中无 Router 实现
- 需要高阶模型决定：跨日恢复的三个选项（快速复盘/冻结欠账/完整复盘）的实现优先级；非交易会话模式（observation/research/review/maintenance）是否需要独立 CLI 入口还是仅通过 Dashboard 触发；账户/持仓确认闸门应放在 DAY_INITIALIZED→start_stage0 之前还是作为独立的 confirm_account 动作；IBKR monitor 与 coordinator 的集成方式（coordinator 触发同步 vs monitor 独立运行 + coordinator 读取产物）
