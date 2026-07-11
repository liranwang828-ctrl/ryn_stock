# DAILY 现有资产与复用链映射

日期：2026-07-11  
依据：`2026-07-11-conversation-driven-daily-workflow-design.zh.md`  
范围：只映射已锁定的 DAILY、runtime、packet、template、Dashboard 和 focused tests；未重新扫描整个仓库。

## 1. 结论

现有系统不是缺少一条 DAILY 链，而是已经存在三条尚未统一的链：

1. `investing-os` canonical workflow / template / cognition 链；
2. `stock_team` coordinator / CLI / artifact ledger 执行链；
3. operating console、legacy daily dashboard、intraday/evidence dashboard、growth dashboard 多个展示面。

可直接复用的核心能力包括：Stage 0 正式盘前数据、脑侧前置条件检查、焦点确认、Stage 1 证据、计划与盘中指导校验、盘中快照、例外确认、三种复盘模式、归档与跨日恢复、认知 lineage/promotion Dashboard。

第一缺口不是再造功能，而是缺少一个以 canonical 文件为依据的统一 `daily-status manifest`。当前 operating console 仍以 coordinator state 和按钮动作为中心，并且部分“就绪”只检查文件存在，未统一检查内容与用户确认。

## 2. DAILY-0 晨间准备

### 已有能力

| 能力 | 现有实现 | 证据 |
|---|---|---|
| 会话类型与日期 | `new_trading_session()` | `stock_team/orchestration/models.py` 支持 trading、observation、research、review、maintenance |
| 跨日恢复 | coordinator CLI recovery matrix | `test_coordinator_cli.py` 覆盖 freeze、quick_review、full review gate、损坏/多旧会话路径 |
| 持仓输入 | Dashboard Stage 0 universe builder | `dashboard_server.py::_build_stage0_universe_document()` 读取当前 positions 并写入 `source_inputs.positions` |
| 前日认知输入 | 最新 journal + promotion queue | `_build_stage0_universe_document()` 与 `_build_current_task_payload()` 已引用 journal、portfolio snapshot、promotion queue |
| 降级边界 | canonical contract | `DAILY-CONTRACT.zh.md` 规定 IBKR 是正式账户事实源，缓存仅 `stale_unverified` |

### 现有 canonical 等价物

不应立即新增独立 `daily-start.json`。现有 session JSON 已保存 `session_type`、`market_date`、state、allowed actions、artifacts；当日 `pre-market-universe` 已保存 positions、prior review、cognition、permission 和 forbidden actions。首轮检查器可联合读取这两者，推导 DAILY-0 是否完成。

### 已证实缺口

- session 与 universe 尚未形成统一 DAILY-0 manifest；
- IBKR 正式账户事实是否已验证，没有统一字段投影到 operating console 的 `entry_state`；
- operating console 的 `Init Day` 按钮与“当前对话为主控制器”的新设计冲突。

## 3. DAILY-1 盘前决策

### 3.1 Stage 0 市场环境

现成执行链：

```text
dashboard_server._build_stage0_universe_document
-> ExistingCliAdapter(start_stage0 或 start_stage0_from_snapshot)
-> stock_team.cli premarket-snapshot
-> stock_team.cli market-context
-> runtime/packets/{session_id}-stage0-market-context.md
```

`market-context` 已具备：

- `--as-of` 强制检查；
- 正式盘前时段验证；
- Polygon paid premarket bars/snapshot；
- snapshot adapter；
- `_brain_precondition_state_quality()` 检查五项脑侧前置；
- 缺失正式数据时显式 missing/warning，不能伪装昨日收盘。

`start_stage0_from_snapshot` 已存在并只生成 market-context，适合“对话/外部流程已经准备正式 snapshot”的复用路径。

### 3.2 环境讨论与焦点池确认

现成 canonical 文件与交互骨架：

- `runtime/inputs/{session_id}-stage0-discussion-notes.md`
- `runtime/inputs/{session_id}-stage1-decision-sheet.json`
- `investing-os/agents/pre-market-planning-agent.md`
- `dashboard_server._build_current_task_payload()` 的 `stage0_discussion` task

`record_focus_confirmation` 已验证：decision sheet 必须存在、JSON 可读、包含 `focus_symbols`，且 `user_confirmed == true`。这正是“对话确认后由文件推进”的现成基础。

现有 `bootstrap_current_task_outputs()` 会创建空白草稿，但 operating console 通过按钮触发；新设计下应由当前对话写入，Dashboard 只展示检查结果。

### 3.3 Stage 1 证据

现成执行链：

```text
confirmed stage1-decision-sheet.json
-> ExistingCliAdapter(start_stage1)
-> stock_team.cli premarket --context-packet --decision-sheet --out
-> runtime/packets/{session_id}-stage1-plan-evidence.md
```

`handle_premarket()` 已把 decision sheet 记录为 `brain_input_artifact`，并生成 Stage 1 evidence。`stock_team` 的职责是证据，不是买卖结论。

### 3.4 计划与盘中指导确认

现成文件：

- `runtime/inputs/{session_id}-trading-plan.json`
- `runtime/inputs/{session_id}-intraday-guidance.json`
- `investing-os/agents/risk-boundary-plan-approval-agent.md`
- `investing-os/templates/pre-market-decision-sheet.json`
- `investing-os/templates/intraday-guidance-to-stock-team.json`

`record_plan_approval` 已检查两个 JSON 存在且含 `risk_mode`、`allowed_actions`、`forbidden_actions`。canonical template 还定义了 manual confirm、pre-authorized action、exception rule、permission owner 和 stock_team Dashboard 禁用词。

### DAILY-1 关键缺口

- `_build_current_task_payload().unlock_ready` 主要以文件存在判断，未统一调用 adapter 的内容校验；
- operating console 仍有 `Confirm Discussion Outputs`、`Start Stage 1 Evidence` 等按钮，和“对话负责推进”冲突；
- `entry_state` 没有表达 waiting_data、waiting_user、ready_artifacts 与具体缺口；
- 现有 runtime filename 已覆盖设计所需产物，不应新增同义文件。

## 4. DAILY-2 开盘观察与 DAILY-3 盘中管理

### 已有事实与展示链

- `stock_team.cli intraday-snapshot`：生成事实快照和 proximity alerts；
- `stock_team.cli intraday-dashboard`：读取 snapshot、Stage 0/1 和 guidance，输出 HTML/Markdown 与 `latest_evidence_dashboard.json`；
- `investing-os/system/workflows/intraday.md`：定义 IBKR stream primary、stateless pull fallback 和 `intraday_snapshot.json/md` contract；
- `investing-os/dashboards/intraday-dashboard.html`：直接轮询 `intraday_snapshot.json`，展示账户、持仓和 alerts；
- `investing-os/dashboards/latest_evidence_dashboard.html`：展示 Stage 0/1 readiness、数据健康、标的条件和 observe-only 边界；
- `start_intraday` 与 `refresh_market_observation` adapter 已存在；
- `request_exception` 和 `record_observation_exception` 状态/记录能力已存在，confirmed exception 写入 session ledger。

### 已有认知投影

`intraday-guidance-protocol.md` 与 `intraday-guidance-to-stock-team.json` 已定义：

- permission owner 是 investing-os；
- stock_team 只判断 evidence condition；
- new risk requires user confirmation；
- Dashboard 不得使用 buy/sell/permission approved 等越权标签；
- 盘前计划投影到盘中 Green/Yellow/Red/No-Trade 状态。

### 已证实缺口

- 没有 canonical `intraday-events` 文件承接“用户主动观察 + 高阶模型回应 + 原对话引用 + pending_review”；
- session 的 `intraday_exceptions` 只适合已确认例外，不足以承接普通观察、疑问和心得；
- single snapshot、live monitor、evidence dashboard manifest 和 operating console 仍是多条展示链；
- operating console 尚未展示对话事件卡片。

结论：盘中事实与权限边界 `reuse-now`；对话事件 schema 是真正需要新增的最小能力。

## 5. DAILY-4 盘后复盘

### 已有能力

- `post-market-trade-review.md` 已定义 stock_team 事实包、brain review、用户访谈、报告、lesson extraction、secondary evidence、absorption/archive 全流程；
- `new_daily4_review()` 与 `validate_daily4_review()` 已定义 full/quick/freeze、IBKR fact status、judgments、candidate lessons、四项用户确认和 archive closure；
- coordinator 已为 freeze、quick_review、review_day 生成并登记 `{session_id}-daily4-review.json`；
- full review 归档会阻止缺文件、缺用户确认或 IBKR 未 verified；
- archiver 使用 artifact ledger 与 whitelist，支持 trading_date 分层；
- 跨日恢复测试覆盖 freeze、quick review 和 REVIEW_REQUIRED 限制。

### 已证实缺口

- full review skeleton 存在，但“盘中事件聚类 → 用户处理异常/高价值项 → 写回 candidate lessons”的对话编排尚未统一；
- daily4 review 与 growth Dashboard 的 lesson/promotion indexes 尚无自动桥接；
- `next-day-state.json` 没有必要立即新增：session terminal state、archive manifest 和未完成 review 已能支持恢复，先映射后再判断是否需要独立投影。

## 6. 两个 Dashboard 的实际角色

### 6.1 每日交易 Dashboard：复用 operating console，收窄职责

`investing-os/dashboards/operating-console.html` 已显示：

- coordinator summary、current phase、main action、next step、mode；
- `entry_state` 五字段；
- workflow steps、current skill task、输入输出与 readiness；
- Stage 0 snapshot form；
- 研究、复盘和认知入口。

其数据来自 `operating-console-data.js` 静态 view model 与 `dashboard_server.py` 的 coordinator APIs。它是最接近新 DAILY Dashboard 的现成页面，应 `reuse-now`。

冲突：页面含 Init Day、Save Snapshot、Create Starter Files、Confirm、Start Stage 1 等主动按钮；服务端 `_coordinator_summary_payload()` 仍从 state/snapshot 推导业务动作。首轮应让它读取统一 manifest，并把推进动作留给对话。

### 6.2 认知 Dashboard：原样复用 growth dashboard

`growth-dashboard-draft.html` 实际不是空白草稿。它已展示：

- cognition/decision/execution/evolution 结构图；
- lesson lineage inspector 与推荐落点；
- report archive；
- capability radar 与来源；
- current operating tasks；
- investing-os/stock_team 边界。

`growth-dashboard-data.js` 提供认知结构与静态说明；`generate-growth-dashboard-data.ps1` 从 reports、lessons、file-lineage、capability-history 四个 traceability JSON 生成 `growth-dashboard-indexes.js`。它符合用户认可的独立认知 Dashboard，应 `reuse-now`，不并入 operating console。

### 6.3 其他展示面

- `intraday-dashboard.html`：账户/持仓/alert 的直接 JSON monitor，适合作为每日 Dashboard 的盘中事实参考或子视图，`merge-later`；
- `latest_evidence_dashboard.html`：stock_team evidence surface，适合作为只读证据链接，`merge-later`；
- `dashboard_writer.py + daily_dashboard.html.j2`：成熟的 legacy daily context、cache fallback、focus readiness、symbol drilldown 与 learning state，价值高但职责巨大，先 `merge-later`，不可直接取代 investing-os 入口；
- `dashboard_experience_loop.py`：围绕盘前定向、readiness、symbol drilldown、返回全局的体验验收工具，适合后续验收，不属于 DAILY 业务判断。

## 7. first isolated pass：最小现成链

第一轮只跑 DAILY-0 与 DAILY-1，不新增同义业务产物：

```text
1. 当前对话确认/恢复 session
2. 使用现有 session JSON + pre-market-universe 作为 DAILY-0 事实
3. premarket-snapshot 生成正式快照
4. market-context 生成 Stage 0 packet
5. 当前对话写 stage0-discussion-notes + stage1-decision-sheet(user_confirmed=true)
6. 现有 validator 校验 focus confirmation
7. premarket 只对确认焦点生成 Stage 1 packet
8. 当前对话写 trading-plan + intraday-guidance
9. 现有 validator 校验 plan approval
10. 统一检查器生成 daily-status manifest
11. operating console 只读展示 manifest；growth dashboard 保持独立
```

最小新增项只有：

- 一个读取上述既有文件与 validator 结果的 `daily-status manifest` builder；
- operating console 对该 manifest 的只读接线；
- 后续 DAILY-2/3 所需的 intraday conversation event schema。

## 8. 高阶、用户与低阶模型分工

### 用户 + 高阶模型

- DAILY-0 模式与风险确认；
- Stage 0 解释与焦点池；
- Stage 1 后计划、权限与禁止动作；
- 盘中观察、首次建仓/加仓和计划外变更确认；
- 复盘分类、经验候选和晋升决定。

### 低阶模型可胜任

- 按明确 schema 写/补测试；
- 为现有文件路径建立 deterministic manifest collector；
- 把 operating console 的展示字段改为读取 manifest；
- 增加缺文件、坏 JSON、确认字段缺失、stale source 的测试；
- 做静态链接、路径和文件分类核对。

低阶模型不得决定 canonical schema 的投资语义、用户交互问题、权限升级、经验晋升或两个 Dashboard 的产品边界。

## 9. 下一实施批次

1. 高阶先定义 `daily-status manifest` 精确 schema 与现有文件映射；
2. 测试先行实现只读 manifest builder；
3. operating console 移除流程推进责任，只渲染 manifest 和下一句建议；
4. 用离线 fixture 隔离跑 DAILY-0/1；
5. 再用真实盘前时点获取数据试跑；
6. 稳定后设计 intraday conversation event schema。

