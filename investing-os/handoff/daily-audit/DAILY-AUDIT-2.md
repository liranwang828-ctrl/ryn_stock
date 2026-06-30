# DAILY-AUDIT-2 开盘观察事实审计

## 审计元数据

- Base commit: c1024c3b67a213eea0419cccd486eef84907e673
- Branch: codex/repository-cleanup-20260630
- Allowed scope respected: yes

## 预期边界

| 问题 | 文档答案 | 代码行为 | 测试证据 | 证据等级 |
|---|---|---|---|---|
| 开盘观察何时开始和结束 | DAILY-2 定义为 9:30-10:00 ET (PROJECT-CHARTER.zh.md L201-205; SYSTEM_FLOWCHART.md L230-238) | transitions.py 无独立的 DAILY-2 状态，PLAN_APPROVED 直接跳转到 INTRADAY_ACTIVE 通过 start_intraday intent；cli.py handle_intraday_snapshot 无时间窗口门控 | test_cli_intraday_snapshot_generation 仅验 smoke：产物可生成，不验时间窗口 | documented, code-only (时间窗口未在代码中 enforce) |
| 无批准计划时允许做什么 | "没有已批准计划时，只能观察" (PROJECT-CHARTER.zh.md L204)；DAILY-3 "任何计划外扩张都必须回到用户确认" (L209) | transitions.py L5-12: begin_transition 要求 PLAN_APPROVED 状态才能执行 start_intraday，否则 raise TransitionError；allowed_actions 中 PLAN_APPROVED 的合法动作为 start_intraday，不包含任何观察模式的 fallback | test_cli_intraday_dashboard_generation 始终依赖 guidance.json（即有已批准计划），无测试覆盖无计划场景 | documented, test-covered (状态机阻止未批准时的 start_intraday) |
| 哪些事实可以刷新 | "系统只更新事实、条件状态和数据健康" (PROJECT-CHARTER.zh.md L203)；intraday.md 定义 snapshot JSON 包含 price/VWAP/volume/account/alerts | cli.py handle_intraday_snapshot (L1700-1841) 可刷新：价格、VWAP 偏差、volume ratio、到止损距离、cooldown 状态 | test_intraday_snapshot.py 覆盖 compute_dist_fields、compute_thesis_signal、compute_entry_go_status、detect_event | documented, test-covered |
| 哪些盘前锚点禁止改写 | intraday-guidance-protocol.md L287-292: stock_team 不得显示 buy/sell/hold、permission approved、should enter/exit、direct execution controls；L248: "Only investing-os can interpret those facts into permission state" | cli.py test_cli_intraday_dashboard_loop_refreshes_runtime_only (L1562-1623) 验证：更新循环不重写 Stage 0/1 锚点文件；handle_intraday_snapshot 产物带 forbidden_sections_absent 标记 | test_cli_intraday_dashboard_loop_refreshes_runtime_only 验证 stage0/stage1 文件内容在循环后不变 | documented, test-covered |
| 哪些情况必须回到用户 | 涉及意义、权限、计划批准、例外处理和教训吸收 (PROJECT-CHARTER.zh.md L72)；Red 状态禁止新风险 (intraday-guidance-protocol.md L204-218)；No-Trade 状态禁止所有新风险 (L229-239)；计划外扩张必须用户确认 (PROJECT-CHARTER.zh.md L209) | transitions.py CONFIRMATION_ACTIONS = {"record_focus_confirmation", "record_plan_approval"} 要求用户确认；权限状态变更仅由 investing-os 解释 (brain-muscle 边界) | 无测试直接覆盖 Red/No-Trade 状态下的拒绝行为 | documented, code-only (状态机有确认闸门，但 Red/No-Trade 的运行时 enforce 无测试) |

## 当前入口、产物和动作

| 项目 | 文件与符号 | 当前行为 | 缺口或冲突 |
|---|---|---|---|
| CLI 入口：intraday-snapshot | cli.py handle_intraday_snapshot (L1700-1841) | 接受 --symbols、--out、--refresh；用 yfinance 抓当日价格和 VWAP；读取 premarket_summary 的止损/入场参考；计算距离和状态 | 无时间窗口 enforce（9:30-10:00 未在代码中检查）；无批准计划验证 |
| CLI 入口：intraday-dashboard | cli.py handle_intraday_dashboard (未在截断范围内完整可见) | 接受 --guidance（内含 stage0/stage1 锚点路径）；--loop 模式可定时刷新 | 函数体未完整展示在本次读取中 |
| 适配器入口 | orchestration/adapters.py L150-162 | intent="start_intraday" 映射到 CLI 命令 stock_team.cli intraday-dashboard --snapshot --out | 仅支持 intraday-dashboard，不支持 intraday-snapshot |
| 状态机 | orchestration/transitions.py | PLAN_APPROVED → start_intraday → INTRADAY_ACTIVE；INTRADAY_ACTIVE → close_market → MARKET_CLOSED | 无 DAILY-2 独立状态；开盘观察是 PLAN_APPROVED→INTRADAY_ACTIVE 过渡的隐式部分 |
| 产物：runtime_monitor_packet | cli.py handle_intraday_snapshot 输出 | 包类型 runtime_monitor_packet；含价格、VWAP 偏差、volume ratio、止损距离、cooldown、state 字段 | — |
| 产物：evidence_dashboard | cli.py handle_intraday_dashboard 输出 (test 可见) | JSON manifest + Markdown + HTML；normalize brain rule IDs；符号条件状态 | — |
| 库函数 | stock_team/data_ingest/intraday_snapshot.py | compute_dist_fields、compute_thesis_signal、compute_entry_go_status、detect_event、append_snapshot、update_poll_state、write_snapshot_entry | — |
| 盘中事实刷新 | cli.py handle_intraday_snapshot --refresh | 运行 refresh_prices.py --once | 数据源切换逻辑未审计（仅 yfinance 路径在当前 snapshot 代码中可见） |

## 测试结果

- Command: `python -m pytest stock_team/tests/unit/sop/test_intraday_snapshot.py -q`
- Result: 20 passed, 0 failed
- Failures: none

- Command: `python -m pytest -q stock_team/tests/unit/core/test_cli.py::test_cli_intraday_snapshot_generation`
- Result: 1 passed, 0 failed
- Failures: none

## 只陈述事实的结论

- 已有：
  - DAILY-2 的名称、目的和边界已在 PROJECT-CHARTER.zh.md 中正式定义
  - intraday_snapshot.py 库提供距离计算、论点信号、事件检测、快照读写等完整函数，均有单元测试覆盖 (20 passed)
  - transitions.py 状态机通过 TRANSITION_ERROR 硬阻止未批准计划时的 start_intraday 调用
  - test_cli_intraday_dashboard_loop_refreshes_runtime_only 验证了循环刷新不改写 Stage 0/1 锚点
  - cli.py 的 handle_intraday_snapshot 命令行入口可生成 runtime_monitor_packet
  - cli.py 的 handle_intraday_dashboard 命令行入口可生成 evidence_dashboard (JSON manifest + MD + HTML)
  - 盘前锚点（permission state、role、thesis、risk budget）在代码中被标记为 brain-owned，stock_team 不回写

- 缺失：
  - DAILY-2 在 transitions.py 状态机中没有独立状态，被隐式合并进 PLAN_APPROVED → INTRADAY_ACTIVE 的过渡
  - intraday-snapshot CLI 入口（handle_intraday_snapshot）缺少 9:30-10:00 时间窗口 enforce
  - intraday-snapshot CLI 入口缺少"无批准计划时拒服"的闸门
  - adapters.py 不支持 intraday-snapshot intent，仅支持 intraday-dashboard
  - Red / No-Trade 状态下的运行时禁止行为缺乏单元测试覆盖
  - 无测试覆盖"无批准计划时 start_intraday 被拒"的端到端路径

- 冲突：
  - transitions.py 将 DAILY-2 隐式化为状态过渡，而未像 DAILY-0/DAILY-1 那样有独立的运行状态（STAGE0_RUNNING / STAGE1_RUNNING），与 PROJECT-CHARTER.zh.md 将 DAILY-2 作为独立工作流步骤的命名不一致
  - adapters.py 的 start_intraday 适配器仅暴露 intraday-dashboard 命令，不暴露 intraday-snapshot 命令

- 需要高阶模型决定：
  - 是否需要为 DAILY-2 在状态机中增加独立状态（如 OBSERVATION_ACTIVE），还是当前 PLAN_APPROVED → INTRADAY_ACTIVE 的隐式过渡已足够
  - intraday-snapshot 和 intraday-dashboard 两个 CLI 入口是否应统一为一个入口或由适配器全部支持
  - 9:30-10:00 时间窗口的代码 enforce 是否需要实现，还是文档约定已足够
