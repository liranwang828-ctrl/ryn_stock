# DAILY 每日交易工作流契约

状态：高阶审核未通过，待按审核记录修订
审核记录：`investing-os/handoff/reviews/2026-06-30-daily-contract-review.md`
基于审计：DAILY-AUDIT-0 至 DAILY-AUDIT-4（2026-06-30）
来源 commit：`c1024c3` 至 `fb61fc6`

本契约定义 DAILY-0 至 DAILY-4 的合法顺序、进入/完成条件、系统动作、用户交互、固定产物和失败恢复。它是代码实现的唯一需求依据。

---

## 0. 全局规则

### 0.1 合法顺序

```
DAILY-0 晨间准备
  → DAILY-1 盘前决策（若活动类型为 trading 或 observation）
  → DAILY-2 开盘观察（若存在已批准计划）
  → DAILY-3 盘中管理（若存在已批准计划）
  → DAILY-4 盘后复盘（若当日为交易日且进入过 DAILY-1）
```

observation 模式：DAILY-0 → DAILY-1（仅到市场环境证据包）→ 结束。不进入 DAILY-2/3。

research / review / maintenance 模式：DAILY-0 后直接旁路到对应工作流，不进入 DAILY-1/2/3/4。

### 0.2 脑-肌边界硬约束

以下边界在全部 DAILY 步骤中生效，不得在任何实现中违反：

1. **`stock_team` 不得下单** — 协调器和 `stock_team` 的任何组件不得创建、修改或发送交易指令到 IBKR。`stock_team` 只读取 IBKR 事实。
2. **IBKR 是持仓和交易事实的唯一正式来源** — 账户数值、持仓列表、成交记录必须以 IBKR 返回数据为准。yfinance/Polygon 只能是行情价格来源，不能替代 IBKR 的账户事实。
3. **权限变更必须经用户确认** — 任何 risk_mode、allowed_actions、forbidden_actions 的变更必须通过 investing-os 呈现并由用户显式批准。

### 0.3 真实与模拟数据的区分

- 所有产物必须声明 `data_source` 字段，取值为 `ibkr_live` / `polygon_live` / `yfinance_delayed` / `cached` / `simulated`。
- 模拟数据产物必须在文件名或 front matter 中包含 `[SIMULATED]` 标记。
- 使用模拟数据时，Dashboard 和 CLI 必须在可见位置显示 "模拟数据" 警告。
- Schema 中 `data_source` 为必填字段。

### 0.4 证据等级约定

本契约沿用审计报告的证据等级体系：

- `code-only`：代码中存在，未在其他文档中描述
- `documented`：文档或契约中有定义，代码未实现或未验证
- `test-covered`：存在并通过了相关测试
- `runtime-unverified`：代码存在但未在真实或模拟流程中运行验证
- `conflict`：文档、代码或测试之间互相矛盾
- `missing`：在审计范围内未找到所需能力

---

## 1. DAILY-0 晨间准备

### 目的

恢复上下文，确认今天是否进入交易、观察或其他活动。处理前日未完成状态。

### 进入条件

- 无正在进行的交易会话（状态为 `IDLE` 或 `DAY_ARCHIVED` 或不存在会话文件）
- 系统数据源可达（IBKR 或确认降级路径）

### 系统自动准备

| 项目 | 当前实现 | 证据等级 |
|------|---------|----------|
| 交易日与时间窗口判断 | `market_calendar.py` 存在，未与 init-day 集成 | code-only |
| IBKR 账户/持仓/近期成交事实 | `ibkr_monitor.py` 有完整同步函数，测试通过（11/11） | test-covered |
| 前一日未完成状态检查 | Architecture spec Section 7 完整定义，代码零实现 | documented |
| 数据源健康与缺失项 | 无统一健康检查入口 | missing |

### 必须显示给用户

1. 当前账户摘要：现金、净清算值、未实现盈亏、当日盈亏
2. 当前持仓列表：代码、数量、成本、现价、盈亏%
3. 前一日复盘状态：已完成 / 欠账（含欠账类型和日期）
4. 今日可用活动类型：trading / observation / research / review / maintenance

### 必须由用户确认

1. **活动类型选择**（当前代码硬编码为 `trading`，需改为交互式）
2. **前日欠账处理**（若存在未完成复盘）：
   - 选项 A：快速复盘 — 检查持仓异常、风险偏离和待处理警告 → 状态标记 `QUICK_REVIEWED`
   - 选项 B：冻结收尾 — 创建带日期的欠账任务，前日状态标记 `CLOSED_UNREVIEWED`
   - 选项 C：完整复盘 — 先完成 DAILY-4 再开始今天
3. **持仓和观察对象确认** — 哪些持仓需要进入盘前判断

### stock_team 输入与输出

**输入：** 日期、活动类型、IBKR 连接状态
**输出：**
- 会话状态 JSON（`{runtime_dir}/sessions/{session_id}.json`）
- 账户快照（来自 IBKR 同步）
- 持仓快照（来自 IBKR 同步）
- 前日复盘状态报告

### investing-os 输入与输出

**输入：** stock_team 输出的所有事实
**输出：**
- 翻译后的活动类型确认
- 前日欠账处理决定
- 当日关注列表

### 完成条件

- 会话状态为 `DAY_INITIALIZED`
- 活动类型已确认
- 前日欠账已处理或确认跳过
- 持仓和观察对象已确认

### 允许跳过或降级路径

- 若 IBKR 不可达：使用最近一次缓存的 positions.json，显式标记 `data_source: cached` 和缓存时间
- 若无前日会话：跳过欠账处理，直接进入活动类型选择
- research / review / maintenance 模式：跳过持仓确认，直接旁路到对应工作流

### 失败与恢复

- IBKR 连接失败：降级到缓存 + 用户确认，标记数据源
- 会话文件冲突：`SessionStore` 已有乐观锁保护，冲突时报告并让用户选择覆盖或恢复
- 跨日恢复：若检测到前日会话未关闭（非 `DAY_ARCHIVED`、非 `IDLE`），必须在 Step 2 中让用户选择处理方式

### 固定产物

| 产物 | 路径 | 状态 |
|------|------|------|
| 会话状态 JSON | `{runtime_dir}/sessions/{session_id}.json` | test-covered |
| 账户快照 | 由 IBKR monitor 写入 | test-covered |
| 持仓快照 | `config/positions.json` | test-covered |

### 对应旧入口

- Node 0（stock_team/docs/SYSTEM_FLOWCHART.md）
- `coordinator_cli.py init-day`
- `main.py` 交互式 CLI

---

## 2. DAILY-1 盘前决策

### 目的

从市场事实走到用户批准的当日交易计划。内部包含一条 6 步握手链，其中市场环境证据包和焦点标的证据包构成两个核心依赖。

### 进入条件

- 状态为 `DAY_INITIALIZED`
- 活动类型为 `trading` 或 `observation`
- as-of 时间在盘前窗口内（04:00–09:29:59 ET）

### 握手链

```
Step 1: investing-os 定义市场范围和事实请求
  → stock_team 生成 Pre-Market Snapshot + 市场环境证据包
Step 2: investing-os 呈现市场环境证据包给用户
Step 3: 用户与 investing-os 解释环境、讨论权限和优先级
  → 用户确认焦点池
Step 4: stock_team 仅为焦点池生成焦点标的证据包
Step 5: investing-os 形成权限、风险、允许和禁止事项
  → 生成交易计划 + 盘中指导
Step 6: 用户批准具体计划版本
  → 状态跃迁至 PLAN_APPROVED
```

### 系统自动准备

| 项目 | 当前实现 | 证据等级 |
|------|---------|----------|
| as-of 与时区校验 | `cli.py _validate_stage0_as_of()` 强制 <09:30 ET 和时区一致性 | test-covered |
| 数据降级链（Polygon → yfinance → stale cache） | `_history_context()` 实现三级降级，每级向 missing/warnings 追加 | code-only |
| Pre-Market Snapshot 生成 | `cli.py premarket-snapshot` 命令 | code-only |
| 市场环境证据包生成 | `cli.py market-context` 命令 | test-covered |

### 必须显示给用户

1. 市场环境证据包：QQQ/SPY/IWM/VIXY 行情、板块热度、universe 相关性、催化剂、缺失数据
2. 焦点池建议：基于持仓和观察列表的默认焦点符号
3. 每个焦点标的的证据包：因子计算、规则碰撞、缺失/警告/禁止检查
4. 交易计划草案：risk_mode、各符号允许/禁止动作、作废条件、盘中检查项
5. 盘中指导：Green/Yellow/Red/No-Trade 状态及对应行为边界

### 必须由用户确认

1. **焦点池确认**（`record_focus_confirmation`）— 确认、添加或排除标的
2. **计划版本批准**（`record_plan_approval`）— 批准 risk_mode、allowed_actions、forbidden_actions、invalidation conditions

### stock_team 输入与输出

**输入：**
- universe JSON（含 source_inputs.positions / prior_review / cognition_state / permission_state_before_open / forbidden_actions）
- decision sheet JSON（焦点池确认后的符号列表、risk_mode、允许/禁止动作）
- 日期和 as-of 时间戳

**输出：**
- Pre-Market Snapshot JSON
- 市场环境证据包 Markdown（6 节：market context、sector heat、universe quality、universe relevance map、catalysts、missing data）
- 焦点标的证据包 Markdown（7 节：input summary、market context echo、brain decision echo、factor calculations、formula outputs、rule collisions、missing/warnings/forbidden check）

### investing-os 输入与输出

**输入：** stock_team 输出的市场环境证据包和焦点标的证据包
**输出：**
- Stage 0 讨论笔记（`trading-YYYY-MM-DD-stage0-discussion-notes.md`）
- Stage 1 决策单（`trading-YYYY-MM-DD-stage1-decision-sheet.json`）
- 交易计划（`trading-YYYY-MM-DD-trading-plan.json`）
- 盘中指导（`trading-YYYY-MM-DD-intraday-guidance.json`）

### 完成条件

- 状态为 `PLAN_APPROVED`
- 焦点池已确认（`user_confirmed: true`）
- 交易计划和盘中指导已生成且用户已批准
- 所有证据包的数据源已声明

### 允许跳过或降级路径

- observation 模式：仅执行 Step 1-3（市场环境证据包 + 焦点池确认），不进入 Step 4-6，不生成交易计划
- 数据降级：若 Polygon 不可达 → yfinance；若全部行情源不可达 → 标记 `missing` 并阻止进入 DAILY-2
- 焦点池为空：若用户确认无关注标的，DAILY-1 以 observation 模式完成

### 失败与恢复

- `record_focus_confirmation` 和 `record_plan_approval` 当前为 pass-through intent（仅记录路径，不校验内容）。需实现内容校验。
- `record_plan_approval` 在 `SUCCESS_TRANSITIONS` 中缺少映射（H4），导致状态不自动跃迁。需修复。
- Stage 1 在 decision sheet 不存在时回退到 watchlist 全量（`handle_premarket()` L1159），存在绕过焦点池确认的风险。需增加闸门。

### 固定产物

| 产物 | 当前路径 | 状态 |
|------|---------|------|
| Pre-Market Snapshot | `--out` 参数指定 | code-only |
| 市场环境证据包 | `investing-os/system/data/packets/pre-market-context-packet.md` | test-covered |
| Stage 0 讨论笔记 | `system/runtime/inputs/trading-YYYY-MM-DD-stage0-discussion-notes.md` | code-only |
| Stage 1 决策单 | `system/runtime/inputs/trading-YYYY-MM-DD-stage1-decision-sheet.json` | code-only |
| 焦点标的证据包 | `--out` 参数指定 | test-covered |
| 交易计划 | `system/runtime/inputs/trading-YYYY-MM-DD-trading-plan.json` | code-only |
| 盘中指导 | `system/runtime/inputs/trading-YYYY-MM-DD-intraday-guidance.json` | code-only |

### 已知冲突

1. **路径不一致** — 代理文档引用 `system/runtime/packets/` 和 `system/runtime/inputs/`，协议文档和代码使用 `investing-os/system/data/packets/` 和 `stock_team/findings/`。**决定：以代码实际路径为准，文档需统一。**
2. **`record_plan_approval` 不自动跃迁** — `transitions.py` L44-50 的 `complete_transition` 对 `record_plan_approval` 落在 default 分支返回原状态。**决定：这是一个 bug，需在 `SUCCESS_TRANSITIONS` 中添加映射。**
3. **IBKR 优先级未实现** — 协议文档声明 IBKR 为第二数据源优先级，但盘前路径中未见 IBKR 调用。**决定：IBKR 仅用于账户/持仓事实；行情数据沿用 Polygon → yfinance 降级链。协议文档需修正。**

### 对应旧入口

- Node 1（SYSTEM_FLOWCHART.md）
- Evidence Stage 0/1
- `cli.py market-context` + `cli.py premarket`
- `transitions.py` 中的 `start_stage0`、`record_focus_confirmation`、`start_stage1`、`record_plan_approval`

---

## 3. DAILY-2 开盘观察

### 目的

观察真实开盘如何验证或否定盘前假设。只更新事实，不做决策。

### 进入条件

- 状态为 `PLAN_APPROVED`
- 当前时间在 9:30–10:00 ET 之间
- 存在已批准的盘中指导

### 系统自动准备

| 项目 | 当前实现 | 证据等级 |
|------|---------|----------|
| 盘中快照生成 | `cli.py handle_intraday_snapshot()` 用 yfinance 获取价格/VWAP | code-only |
| 条件状态计算 | `intraday_snapshot.py` compute_thesis_signal / compute_entry_go_status / detect_event | test-covered |
| 距离计算 | `intraday_snapshot.py` compute_dist_fields | test-covered |

### 必须显示给用户

1. 焦点标的实时价格、VWAP 偏差、成交量比率
2. 距止损/入场位的距离
3. 论点信号状态（intact / warning / breached）
4. 入场条件状态（go / caution / no_go）
5. 盘中指导的当前权限状态（Green/Yellow/Red/No-Trade）
6. 数据源状态和新鲜度

### 必须由用户确认

开盘观察阶段不要求用户确认。用户决定是否：
- 维持观察
- 启用已批准条件（若盘中指导允许）
- 保持不行动

**若用户需要任何计划外行动，必须回到 DAILY-1 的 Step 5-6 重新批准。**

### stock_team 输入与输出

**输入：** 焦点符号列表、premarket summary（止损/入场参考）、盘中指导
**输出：** runtime_monitor_packet（价格、VWAP 偏差、volume ratio、止损距离、cooldown 状态）

### investing-os 输入与输出

**输入：** runtime_monitor_packet
**输出：** 对用户的观察摘要

### 完成条件

- 开盘观察窗口结束（10:00 ET）或用户主动进入 DAILY-3
- 状态跃迁至 `INTRADAY_ACTIVE`

### 允许跳过或降级路径

- 若用户选择 observation 模式：DAILY-2 不可用（进入条件不满足）
- 若无已批准计划：DAILY-2 不可用，状态机硬阻止（`TRANSITION_ERROR`）

### 失败与恢复

- 行情数据不可达：标记 missing，显示最后可用数据和时间戳
- 焦点标的数据缺失：在 monitor packet 中标记，不阻塞其他标的

### 固定产物

| 产物 | 当前路径 | 状态 |
|------|---------|------|
| runtime_monitor_packet | `--out` 参数指定（CLI） | code-only |

### 已知冲突

1. **无独立状态** — DAILY-2 在 `transitions.py` 中被隐式合并进 `PLAN_APPROVED → INTRADAY_ACTIVE` 过渡。**决定：当前保持隐式过渡，不创建独立状态。DAILY-2 的业务语义由时间窗口和用户行为定义，不由状态机额外状态定义。**
2. **无时间窗口 enforce** — `handle_intraday_snapshot()` 不检查 9:30-10:00 窗口。**决定：需添加时间窗口闸门。**
3. **adapters.py 不支持 intraday-snapshot** — 仅支持 intraday-dashboard。**决定：需添加适配器映射。**

### 对应旧入口

- Node 2（SYSTEM_FLOWCHART.md）
- `cli.py intraday-snapshot` + `cli.py intraday-dashboard`
- `transitions.py` 的 `start_intraday` intent

---

## 4. DAILY-3 盘中管理

### 目的

按已批准计划管理注意力、风险和已有持仓。只刷新事实，不制造新观点。任何计划外扩张必须回到用户确认。

### 进入条件

- 状态为 `INTRADAY_ACTIVE`
- 存在已批准的盘中指导和交易计划
- 当前时间在市场交易时段内（09:30–16:00 ET）

### 系统自动准备

| 项目 | 当前实现 | 证据等级 |
|------|---------|----------|
| 单次盘中快照 | `cli.py handle_intraday_snapshot()` | code-only |
| Dashboard 生成 | `cli.py handle_intraday_dashboard()` | code-only |
| 条件状态刷新 | `intraday_snapshot.py` 全套函数 | test-covered (30/30) |
| 价格同步到 positions | `dashboard_server.py sync_price_refresh_state()` | test-covered |

### 必须显示给用户

1. 焦点标的实时状态（价格、VWAP、距离、论点、入场条件）
2. 账户暴露和风险摘要
3. 当前权限状态（Green/Yellow/Red/No-Trade）及允许/禁止动作
4. 触发警告的事件（止损逼近、论点破裂、异常成交量等）
5. 计划锚点对照（当前状态 vs 盘前设定的 entry_base、hard_stop、target）

### 必须由用户确认

1. **任何计划外行动** — 包括但不限于：交易未在计划中的标的、超出计划允许的风险、改变 risk_mode
2. **权限状态变更请求** — 从 Green→Yellow 或 Yellow→Red 等
3. **例外处理** — 任何偏离盘中指导的操作

### stock_team 输入与输出

**输入：** 焦点符号列表、premarket summary、盘中指导、IBKR 流式数据（若可用）
**输出：**
- 盘中快照（单次刷新）
- 条件状态更新（poll_state JSON）
- Dashboard 数据（JSON manifest + Markdown + HTML）

### investing-os 输入与输出

**输入：** 盘中快照和条件状态
**输出：** 对用户的盘中摘要、警告、权限状态更新建议

### 完成条件

- 市场收盘（16:00 ET）或用户主动关闭
- 状态跃迁至 `MARKET_CLOSED`

### 允许跳过或降级路径

- 单次刷新模式（当前唯一实现）：用户手动触发快照
- 循环模式（设计存在，未统一实现）：`poll.py` + `/loop 2m` 或 `dashboard_server.py /api/run?task=poll`
- IBKR 流式数据不可达：降级到 yfinance 定时轮询

### 失败与恢复

- 行情数据源全部不可达：标记 missing，保留最后快照时间和数据
- 盘中指导文件丢失：回退到硬编码路径搜索，若全部缺失则标记并阻止盘中动作

### 固定产物

| 产物 | 当前路径 | 状态 |
|------|---------|------|
| 盘中快照 JSON | `--out` 参数指定（不与 `intraday.md` schema 路径一致） | code-only |
| 盘中快照 Markdown | `--out` 参数指定 | code-only |
| Dashboard JSON manifest | `--out` 参数指定 | code-only |
| Dashboard HTML | `investing-os/dashboards/intraday-dashboard.html`（静态模板，前端轮询 JSON） | code-only |

### 已知冲突

1. **IBKR streaming 路径缺失** — `intraday.md` 文档声明 IBKR 为 primary streaming source，但代码中 `handle_intraday_snapshot()` 仅使用 yfinance。**决定：文档需修正。IBKR 用于账户/持仓事实，行情价格走 Polygon → yfinance 链。**
2. **`post_open_adj` 无文档无权限** — `get_effective_nodes()` 优先使用 `post_open_adj` 覆盖盘前锚点（entry_base/hard_stop/target），但无文档说明谁、何时、以何依据填充该字段。**决定：`post_open_adj` 只能由 investing-os 在用户确认后写入。需添加写入权限校验和审计日志。**
3. **Dashboard 前端无后端生产者** — 静态 HTML 以 5 秒间隔 fetch `intraday_snapshot.json`，但无后端保证该文件存在或新鲜。**决定：`dashboard_server.py` 需在启动时确保 JSON 文件存在，并提供新鲜度时间戳。**

### 对应旧入口

- Node 3（SYSTEM_FLOWCHART.md）
- `poll.py`（旧实时监控）
- `cli.py intraday-snapshot` + `cli.py intraday-dashboard`
- `dashboard_server.py` `/api/run?task=poll`

---

## 5. DAILY-4 盘后复盘

### 目的

重建事实，评价判断与执行，区分噪声与经验，归档当日并支持次日恢复。

### 进入条件

- 状态为 `MARKET_CLOSED`
- 当日进入过 DAILY-1（即使未交易）

### 系统自动准备

| 项目 | 当前实现 | 证据等级 |
|------|---------|----------|
| 交易复盘证据包生成 | `postmarket_summary.py` build_per_stock_summary / write_per_stock_summary | test-covered (11/11) |
| 经验候选生成 | `postmarket_data_collector.py` generate_suggestions() | test-covered |
| 状态跃迁 | `transitions.py` `MARKET_CLOSED → archive_day → DAY_ARCHIVED` | code-only |

### 收尾链

```
Step 1: stock_team 获取成交、持仓和市场事实 → 交易复盘证据包
Step 2: investing-os 呈现复盘证据给用户
Step 3: 用户与 investing-os 区分判断/执行/仓位/情绪/数据因素
Step 4: 用户确认当日结论（噪声 vs 候选经验）
Step 5: stock_team 生成经验候选（lesson_record / thesis_status 等）
Step 6: 用户决定哪些进入 LEARNING → 归档当日产物 → 状态跃迁至 DAY_ARCHIVED
```

### 必须显示给用户

1. 当日成交记录（来自 IBKR）
2. 每个标的的执行质量对比（进场/离场 vs 计划）
3. 信号准确性复盘（盘前论点 vs 实际走势）
4. 偏差分类（判断偏差 / 执行偏差 / 仓位偏差 / 情绪偏差 / 数据问题）
5. 经验候选建议（含建议类型：lesson_record / thesis_status / correlation_warning 等）
6. 当日 P&L 和风险使用情况

### 必须由用户确认

1. **偏差分类** — 确认或调整 investing-os 的分类
2. **当日结论** — 哪些是噪声（仅当天有效），哪些进入 LEARNING 候选
3. **归档确认** — 确认所有产物已生成，允许状态跃迁至 `DAY_ARCHIVED`

### stock_team 输入与输出

**输入：** 当日 premarket summary、intraday snapshots、positions.json、IBKR 成交记录
**输出：**
- per-stock postmarket summary JSON（执行、绩效、信号准确性、建议）
- 经验候选建议

### investing-os 输入与输出

**输入：** stock_team 输出的复盘证据包和经验候选
**输出：**
- 分类后的偏差记录
- 用户确认的当日结论
- LEARNING 候选清单

### 完成条件

- 状态为 `DAY_ARCHIVED`
- 当日所有产物已归档
- 用户已确认当日结论和经验候选
- 欠账任务已创建（若选择冻结收尾）
- 次日恢复所需的最小状态已持久化

### 允许跳过或降级路径

- **无交易日正常关闭** — 若当日未进入 DAILY-1，DAILY-4 简化为状态检查 → 直接 `DAY_ARCHIVED`
- **快速复盘**（quick_review）— 最少检查：持仓异常、风险偏离、待处理警告 → 状态 `QUICK_REVIEWED` → `DAY_ARCHIVED`
- **冻结收尾**（freeze）— 创建欠账任务，当日状态 `CLOSED_UNREVIEWED` → `DAY_ARCHIVED`
- **完整复盘**（full_review）— 执行完整 6 步收尾链

### 失败与恢复

- IBKR 成交数据不可达：使用日末缓存，标记数据源和缓存时间
- 复盘中断：会话状态保留在 `MARKET_CLOSED` 或 `REVIEW_REQUIRED`，次日 DAILY-0 检测到未完成状态时提示用户

### 固定产物

| 产物 | 当前路径 | 状态 |
|------|---------|------|
| per-stock postmarket summary | 由 `postmarket_summary.py` 写入 | test-covered |
| 交易复盘证据包 | 由 `export_trade_evidence.py` 写入 | code-only |
| 经验候选 | 由 `generate_suggestions()` 输出 | test-covered |
| 归档产物清单 | 未实现 | missing |

### 已知冲突

1. **`REVIEW_REQUIRED` 状态游离** — 在 `models.py` 中定义但在 `transitions.py` 中不存在于任何 TRANSITIONS 字典。**决定：需添加到 `BEGIN_TRANSITIONS` 中，支持从 `REVIEW_REQUIRED` 进入复盘流程。**
2. **`QUICK_REVIEWED` 和 `CLOSED_UNREVIEWED` 未注册** — Architecture spec 定义了这些状态但 `models.py` 的 `TRADING_STATES` 不包含它们。**决定：需添加到 `TRADING_STATES` 并在 `transitions.py` 中支持。**
3. **`archive_day` 无实际归档逻辑** — 当前仅有状态名称转换，无文件归档、产物清单生成、索引更新。**决定：需实现最小归档逻辑（文件汇总 + 产物清单 JSON）。**
4. **三种复盘选择被映射为同一个动作** — `dashboard_server.py` 将 freeze/quick_review/full_review 都映射到 `init-day`，未区分状态。**决定：需在状态机中创建不同的状态转换路径。**

### 对应旧入口

- Node 6（SYSTEM_FLOWCHART.md）
- `transitions.py` 的 `close_market` 和 `archive_day` intent
- `postmarket_summary.py` + `export_trade_evidence.py`

---

## 6. 状态机修正清单

以下是从五份审计报告中提取的、必须在代码实施前修正的状态机问题：

| 序号 | 问题 | 所在文件 | 严重程度 | 修正方向 |
|------|------|---------|---------|---------|
| H1 | `init-day` 无活动类型参数，硬编码 `session_type="trading"` | `coordinator_cli.py`、`models.py` | P1 | 添加 `--session-type` 参数，支持全部 SESSION_TYPES |
| H2 | 跨日恢复零实现 | `transitions.py`、`coordinator_cli.py`、`store.py` | P0 | 实现 Architecture spec Section 7 的三种恢复选项 |
| H3 | `REVIEW_REQUIRED` 不在任何 TRANSITIONS 字典中 | `transitions.py` | P1 | 添加到 BEGIN_TRANSITIONS |
| H4 | `record_plan_approval` 成功时不自动跃迁 | `transitions.py` L44-50 | P1 | 在 SUCCESS_TRANSITIONS 中添加映射 |
| H5 | `QUICK_REVIEWED`、`CLOSED_UNREVIEWED` 未注册 | `models.py` | P1 | 添加到 TRADING_STATES |
| H6 | DAILY-2 无独立状态 | `transitions.py` | P2 | 当前保持隐式过渡，由时间窗口 enforce |
| H7 | `archive_day` 无实际归档写入 | `transitions.py`、缺失归档模块 | P1 | 实现最小归档逻辑 |
| H8 | `record_focus_confirmation` 和 `record_plan_approval` 不校验产物内容 | `adapters.py` L141-144 | P1 | 添加产物存在性和必填字段校验 |

---

## 7. 未解决的高阶决策

以下问题需用户与高阶模型决定，不得由低阶模型在实现时自行判断：

1. **跨日恢复实现优先级** — 三种选项（快速复盘/冻结欠账/完整复盘）的实现顺序。
2. **非交易模式入口** — observation/research/review/maintenance 是否需要独立 CLI 入口，还是仅通过 Dashboard 触发。
3. **账户/持仓确认闸门位置** — 放在 `DAY_INITIALIZED → start_stage0` 之前还是作为独立的 `confirm_account` 动作。
4. **IBKR monitor 集成方式** — coordinator 触发同步 vs monitor 独立运行 + coordinator 读取产物。
5. **confirm 类 intent 的产物生成** — 由 CLI 命令自动化还是保持 investing-os 手动写入模式。
6. **焦点池最大数量** — 是否需要显式约束。
7. **`post_open_adj` 机制的去留** — 保留并加权限控制，还是移除。
8. **步骤 3（区分判断/执行/仓位/情绪）的交互形式** — 纯对话还是结构化表单/CLI。

---

## 8. 契约生效条件

本契约在以下条件全部满足后生效：

1. 用户逐段批准 DAILY-0 至 DAILY-4 的交互和完成条件
2. 用户对第 7 节的高阶决策给出明确指示
3. 状态机修正清单（第 6 节）的修正方向获用户确认
4. `WORKFLOW-STATUS.zh.md` 已更新
5. 本文件作为独立 commit 提交
