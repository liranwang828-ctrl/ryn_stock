# Antigravity 当前任务

日期：2026-06-07

负责人：Antigravity
提出方：Codex / 用户
目标仓库：`D:\gemini\lianghua\stock_team`
模式：只在 `stock_team` 内部独立实现；不要修改 `investing-os`

## 工作边界

开始前先读：

- `C:\Users\rriww\Documents\investing-os\system\closed-loop-operating-architecture.md`
- `C:\Users\rriww\Documents\investing-os\system\workflows\brain-muscle-handshake-protocol.md`

所有面向用户的交易入口都从 `investing-os` 开始。

`stock_team` 是证据引擎。它可以产出：

- 事实证据包
- Polygon / IBKR / cache 数据
- 指标计算
- 条件 pass / fail
- 数据 freshness 与 missing-data notes
- 证据 dashboard 与 manifest

`stock_team` 不允许产出：

- 买入 / 卖出 / 持有建议
- 交易权限批准
- 最终 thesis 采纳
- 心理解释
- 原则更新
- 实盘执行控件
- 绕过 `investing-os` 的竞争性用户流程

## 数据源优先级

1. Polygon：价格、盘中 K 线、历史 aggregates、成交量、VWAP、新闻。
2. IBKR：券商持仓、订单、成交、账户暴露、已实现 / 未实现 P&L。
3. 本地缓存：必须带 source、generated timestamp、freshness metadata。
4. yfinance：只能作为 fallback 或 sandbox 便利数据源，不能作为生产默认主源。

每个 packet 必须披露数据源和 freshness。如果使用 fallback，必须在 `missing_data` 或 `warnings` 里说明原因。

## 当前执行顺序

### 0. Stage 0 盘前市场环境包 - 已完成 / 保持稳定

状态：

- `market-context` 命令已存在。
- `--universe` 已设为必填。
- Polygon cache 和事实型 catalyst feed 已接入。
- Codex 验证：`tests\unit\core\test_cli.py` 通过，结果为 `8 passed`。

被 `investing-os` 调用时的正式输出路径：

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md
```

规则：

- `stock_team` 可以保存内部诊断副本。
- Stage 1 和主脑默认只读取这个正式路径，除非 simulation 显式覆盖。
- 不要回退已有字段：market context、sector/theme heat、universe input quality、universe relevance map、catalysts、missing data、forbidden sections absent。

Stage 0 的主脑输入 artifact：

- 模板：
  - `C:\Users\rriww\Documents\investing-os\templates\pre-market-universe.json`
- 验收 demo universe：
  - `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-pre-market-universe.MU-NVDA-COHR-INTC.demo.json`

必须使用的 Stage 0 验收命令：

```powershell
python -m stock_team.cli market-context --date 2026-06-06 --themes "semiconductors,ai_infrastructure,memory,cloud,optical" --universe "C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage0-pre-market-universe.MU-NVDA-COHR-INTC.demo.json" --out "C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md"
```

只剩维护要求：

- 保持 cache freshness metadata 可见。
- 保持 catalysts 为事实型证据。
- 如果改 Stage 0 内部逻辑，需要补 regression tests。

### 1. Stage 1 盘前计划证据包 - 当前最高优先级

目的：

当 `investing-os` 和用户确认当天 focus pool 后，`stock_team` 读取主脑拥有的盘前决策单，计算证据，检查主脑提供的规则，并写出计划证据包。

当前状态：

- 实现已经存在。
- Codex 验证：`tests\unit\core\test_cli.py` 通过，结果为 `9 passed`。
- 输出已经写到正式路径。
- 但 contract review 还没有通过。先修下面问题，再进入盘中 dashboard。
- 端到端路线还没有通过验收，因为 `investing-os` 里的 Stage 0 正式 packet 目前仍是空模板；Stage 1 必须用写入正式路径的真实 Stage 0 packet 测试，不能只用 simulation 或 `findings` 内部副本。

主脑输入：

- `pre_market_decision_sheet` JSON
- Stage 0 正式 packet：
  - `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`

Stage 1 demo 输入：

- `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.MU-NVDA.demo.json`

正式输出：

```text
C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.md
```

必须使用的 Stage 1 验收命令：

```powershell
python -m stock_team.cli premarket --date 2026-06-06 --decision-sheet "C:\Users\rriww\Documents\investing-os\system\simulations\inputs\stage1-pre-market-decision-sheet.MU-NVDA.demo.json" --out "C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.md"
```

如果 `stock_team` 目前仍要求 `--watchlist`，可以把 Stage 0 universe 文件作为 `--watchlist` 传入，但 Stage 1 的 focus pool 必须以 decision sheet 为准。

必须输出：

- YAML header，包含 `packet_type: plan_evidence_packet`
- `brain_input_artifact`
- `derived_from_stage0_packet`
- data sources 与 freshness
- missing data / warnings
- Stage 0 market context echo
- Brain Decision Echo
- Symbol Candidate Factor Calculations
- Requested Formula Outputs
- Rule Collision Results
- Machine-Readable Summary JSON block
- Forbidden Sections Absent

允许计算：

- 1D / 5D / 20D return
- 相对 benchmark / theme proxy 的 relative strength
- volume ratio
- ATR(14)
- MA20 / MA50 distance
- prior day high / low
- VWAP 或 anchored VWAP，前提是数据支持
- premarket gap，前提是可用
- 来自 IBKR 或 fallback positions 的相关杠杆暴露事实

字段命名要求：

- 用 `computed_reference_levels`，不要用 `recommended_entry`。
- 用 `risk_distance_facts`，不要用 `stop_loss`。
- 用 `formula_output_echo`，不要用 `support recommendation`。

规则碰撞边界：

- 只能把事实与 `investing-os` 提供的规则做碰撞。
- Yellow / Red 状态可以回显并检查，但 `stock_team` 不能改变权限状态。
- Stage 1 中的 `preauthorized_action_fast_check` 只检查规则定义是否完整、所需数据是否可用。盘中实时 pass/fail 属于 intraday dashboard。
- 如果 focus pool 包含 MU，且存在 MUU 暴露，只输出相关杠杆暴露事实，例如：
  - `linked_leveraged_exposure_detected: true`
  - `related_position: MUU`
  - `source: IBKR | cached_ibkr | positions_fixture`
  不允许判断用户动机是亏损修复。

禁止：

- buy / sell / hold
- can trade / should enter / should exit
- permission approved
- 发明 entry / stop / sizing
- 心理动机分类

必须测试：

- 决策单解析，含可选字段缺失
- Stage 0 正式路径读取
- YAML 与 JSON summary 格式合法
- MU + MUU 相关杠杆暴露 fixture
- Yellow / Red rule collision 只回显，不改变权限
- forbidden language scan

Codex review 要求返修：

0. 证明正式 Stage 0 -> Stage 1 路线，而不是只证明内部输出。
   - 运行 Stage 0，并输出到 `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`。
   - 确认这个正式文件包含真实 market context、data sources、catalyst facts、universe quality、forbidden sections absent。
   - 再运行 Stage 1，并通过 `derived_from_stage0_packet` 读取这个正式文件。
   - 回报两个命令和两个输出路径。
1. Stage 1 不允许把盘中条件标记为已满足。
   - 当前输出里有 `preauthorized_conditions_met`。
   - Stage 1 只能输出 `preauthorized_definition_complete`、`required_data_available` 或 `required_data_missing`。
   - 实时 trigger pass/fail 属于盘中 dashboard。
2. 不允许暗示心理动机。
   - 当前输出里的 `loss_repair_guard` 和 `risk_context_for_brain_review` 只有在表达为“相关暴露事实”时才可接受。
   - 改成 `linked_leveraged_exposure_detected`。
   - 输出 `related_position: MUU` 和数据源 freshness。
3. 使用 fallback / yfinance 时，不允许宣称生产级 verified。
   - 当前输出 `status: verified`，但 `data_sources` 是 `yfinance`，computed levels 里也是 `Source: fallback`。
   - 要么使用 Polygon / IBKR 生产数据源，要么把 status 降级为 `verified_fixture` / `fallback_data`。
   - `warnings` 必须解释为什么没有使用 Polygon / IBKR。
4. stale metadata 必须真实。
   - 如果模拟日期使用的是前一日 / 周末 / fallback bars，不要在没有 freshness 说明的情况下写 `Stale: false`。
5. forbidden-language scan 要区分“边界声明”和“推荐语句”。
   - 在 `Forbidden Sections Absent` 里列出禁止短语是可以的。
   - 只有这些短语以推荐、动作准备、权限批准的形式出现时，才应该 fail。
6. 正式验收 Stage 0 时要使用结构化 universe。
   - 当前 demo watchlist 只有 `default_symbols`。
   - 这可以作为宽松 smoke test，但正式 Stage 0 验收应使用带 `symbol`、`role`、`theme`、`research_status` 的 brain universe。
   - 缺失字段要审计出来，不能静默猜测。
7. Stage 1 demo 作为契约 fixture 前，需要清理动机语言。
   - 把 `MUU_repair_motive` 改成中性暴露规则，例如 `MUU_linked_leveraged_exposure`。
   - 把 `not_repair_trading` 改成可测量检查，例如 `no_linked_leveraged_exposure_exception`。

### 2. 盘中 Evidence Dashboard Producer - Stage 1 后执行

目的：

读取主脑生成的盘中指导 artifact，生成 `stock_team` evidence dashboard 和 latest manifest。

主脑 artifact 示例：

- `C:\Users\rriww\Documents\investing-os\templates\intraday-guidance-to-stock-team.json`
- `C:\Users\rriww\Documents\investing-os\system\simulations\inputs\intraday-guidance.NVDA-conditional.demo.json`

最新 manifest 固定路径：

```text
D:\gemini\lianghua\stock_team\reports\latest_evidence_dashboard.json
```

Dashboard 可以显示：

- packet readiness
- data source health
- runtime snapshot freshness
- symbol condition pass / fail / partial / stale / missing
- missing data
- latest packet links

Dashboard 禁止显示：

- buy / sell / hold
- permission approved
- can trade / should enter / should exit
- 实盘执行控件

### 3. 盘后交易证据包

目的：

在 `investing-os` 开始认知复盘前，`stock_team` 先产出事实型盘后交易证据包。

输入契约：

- `C:\Users\rriww\Documents\investing-os\templates\post-market-trade-evidence-request.json`

输出契约：

- `C:\Users\rriww\Documents\investing-os\system\data\packets\post-market-trade-evidence-packet.md`
- `C:\Users\rriww\Documents\investing-os\system\data\packets\contextual-trade-evidence-packet.md`

必须包含：

- IBKR orders、fills、positions、account P/L、commissions、exposure
- QQQ / SPY / IWM / VIX proxy 全天走势
- 交易标的和复盘标的全天走势
- 相关板块 / 主题 / peer proxy 全天走势
- VWAP、volume ratio、price-vs-VWAP state
- 前 30 分钟结构，拆成 0-5m、5-15m、15-30m
- 关键盘中节点
- fill-against-context table
- data quality 与 missing-data notes

禁止：

- 心理解释
- 最终交易判断
- 原则更新
- 买入 / 卖出 / 持有建议

### 4. 事件重建与周期性战术总结

目的：

为错过机会、假阳性、规则触发但未交易、周/月度战术复盘提供证据。

输入 / 输出契约：

- `C:\Users\rriww\Documents\investing-os\templates\event-reconstruction-request.json`
- `C:\Users\rriww\Documents\investing-os\system\data\packets\event-reconstruction-packet.md`
- `C:\Users\rriww\Documents\investing-os\templates\tactic-event-summary-request.json`
- `C:\Users\rriww\Documents\investing-os\system\data\packets\tactic-event-summary-packet.md`

必须保持 evidence-only：

- 不输出最终 lesson
- 不做策略采纳决定
- 不做心理解释
- 不更新原则
- 不给交易建议

### 5. 研究证据包

目的：

为公司研究 / 行业研究提供事实证据，而不是结论。

公司 packet 契约：

- `C:\Users\rriww\Documents\investing-os\system\data\packets\company-research-packet.md`

行业 packet 契约：

- `C:\Users\rriww\Documents\investing-os\system\data\packets\industry-research-packet.md`

建议先做两个例子：

- COHR peer evidence：COHR、LITE、AAOI、SOXX、QQQ
- ORCL company evidence：ORCL、MSFT、AMZN、GOOGL、IGV、QQQ

### 6. Packet Producer Map 与 CLI Contract 文档

目的：

让人一眼知道哪个 `stock_team` 命令生产哪个 packet。

在 `stock_team` 内创建或更新：

- `docs/CLI_CONTRACT.md`
- `docs/PACKET_PRODUCER_MAP.md`

每个 producer map 条目必须包含：

- command
- input artifact
- output artifact
- data sources
- tests
- known gaps
- forbidden behavior check

## 回报格式

Antigravity 回报时请使用：

```yaml
implemented_commands:
  - command:
    status:
    smoke_test:
    example_output:
    canonical_output_path:
known_gaps:
  - gap:
    reason:
    proposed_next_step:
forbidden_behavior_check:
  buy_sell_hold_recommendations_present: false
  permission_approval_present: false
  psychological_interpretation_present: false
  live_execution_controls_present: false
  direct_user_entrypoints_created: false
```

## 已清理 / 当前不活跃

已从当前 active queue 移除：

- 旧的宽泛 CLI checklist，它混合了已完成项和未来项。
- 把 `scratch` 或 `findings` 当作 Stage 0 正式输出路径的旧描述。
- runtime consumer implementation request。
- 直接 polling / live workflow，除非 `investing-os` 明确授权盘中契约。
- SNXX / COHR / ORCL 作为顶层 current task 的重复例子；现在它们分别归入盘后证据包或研究证据包示例。

归档参考：

- `C:\Users\rriww\Documents\investing-os\handoff\inventory\antigravity-completed-and-cleared-2026-06-06.md`
