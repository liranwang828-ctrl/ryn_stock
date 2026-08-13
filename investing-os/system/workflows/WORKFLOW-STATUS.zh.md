# 工作流实现状态台账

更新日期：2026-08-13
状态口径来源：[`../../PROJECT-CHARTER.zh.md`](../../PROJECT-CHARTER.zh.md)
实现计划：[`../../../docs/superpowers/plans/2026-07-01-daily-contract-implementation.md`](../../../docs/superpowers/plans/2026-07-01-daily-contract-implementation.md)

## 使用规则

- 这是实现追溯台账，不是愿望清单。
- 文档存在不等于功能可运行，测试存在不等于完整工作流已验证。
- 未做针对性审计时使用 `unknown`，不得凭文件名推断完成度。
- 每次工作流验收或相关任务合入后，更新状态、证据、缺口、下一动作和 commit。

## 总览

| 工作流 | 当前状态 | 最近核验 | 当前判断 |
|---|---|---:|---|
| `DAILY` 每日交易 | `partial` | 2026-07-16（历史证据）；2026-08-13（恢复盘点） | 已有跨日恢复、归档、观察模式、daily-status manifest、只读 Operating Console 和盘前/观察修复；8 月尚未重新跑通最小 DAILY |
| `RESEARCH` 投资研究 | `partial` | 2026-07-16（历史测试）；2026-08-13（恢复盘点） | Research Database 模板、三大 Alpha Questions、Dashboard summary 和公司阅读报告已有原型；Evidence 自动生产未闭环 |
| `REVIEW` 周期复盘 | `documented` | 2026-07-03（DAILY-4 历史测试）；2026-08-13（恢复盘点） | DAILY-4 结构化 review 与归档资产存在；统一周期复盘和真实交互闭环未核验 |
| `LEARNING` 经验进化 | `documented` | 2026-07-22（候选记录）；2026-08-13（恢复盘点） | 候选原则、journal promotion、approval 和 Growth Dashboard 资产存在；完整批准/拒绝运行闭环未复验 |
| `VALIDATION` 策略验证 | `partial` | 2026-07-19（关键价格历史产物）；2026-08-13（恢复盘点） | 回测、关键价格和可靠性检查资产存在；与 Hypothesis 更新和用户批准的闭环未核验 |
| `SYSTEM` 系统维护 | `partial` | 2026-07-16（runtime 历史实现）；2026-08-13（恢复盘点） | 多项 schema、runtime、状态机和文件标签机制存在；尚无统一健康检查入口 |

## DAILY 每日交易

当前行动计划：[`../../../docs/superpowers/plans/2026-06-30-daily-workflow-foundation.md`](../../../docs/superpowers/plans/2026-06-30-daily-workflow-foundation.md)

当前审核记录：[`../../handoff/reviews/2026-06-30-daily-contract-review.md`](../../handoff/reviews/2026-06-30-daily-contract-review.md)

v2 审核记录：[`../../handoff/reviews/2026-06-30-daily-contract-v2-review.md`](../../handoff/reviews/2026-06-30-daily-contract-v2-review.md)

v3 审核记录：[`../../handoff/reviews/2026-07-01-daily-contract-v3-review.md`](../../handoff/reviews/2026-07-01-daily-contract-v3-review.md)

DAILY 契约：[`DAILY-CONTRACT.zh.md`](DAILY-CONTRACT.zh.md)（v4 已获用户批准）

用户批准记录：[`../../handoff/decisions/2026-07-01-daily-q1-q3-approval.md`](../../handoff/decisions/2026-07-01-daily-q1-q3-approval.md)

候选实现审核：[`../../handoff/reviews/2026-07-01-daily-implementation-review.md`](../../handoff/reviews/2026-07-01-daily-implementation-review.md)
高阶修复纲领：[`../../handoff/2026-07-01-daily-h1-h3-repair-charter.zh.md`](../../handoff/2026-07-01-daily-h1-h3-repair-charter.zh.md)
低阶任务包：[`../../handoff/2026-07-01-daily-l1-l3-task-packets.zh.md`](../../handoff/2026-07-01-daily-l1-l3-task-packets.zh.md)
H4 高阶契约：[`../../handoff/2026-07-01-daily-h4-review-contract.zh.md`](../../handoff/2026-07-01-daily-h4-review-contract.zh.md)
H4 低阶任务包：[`../../handoff/2026-07-01-daily-h4-task-packets.zh.md`](../../handoff/2026-07-01-daily-h4-task-packets.zh.md)

### DAILY C1–C14 实施结果 (2026-07-01)

| 候选修正 | 分类 | 任务 | Commit | Tests |
|---|---|---|---|---|
| C1 会话路由器 | `missing_capability` | I-1 | `7843db3` | +5 |
| C2 跨日恢复路由器 | `missing_capability` | I-1 | `7843db3` | 同上 |
| C3 复盘状态注册 | `missing_capability` | I-8 | `1b50273` | +3 |
| C4 复盘状态实现 | `missing_capability` | I-8 | `1b50273` | +5 |
| C5 观察状态注册 | `design_decision` | I-6 | `a24b32e` | +5 |
| C6 最小归档逻辑 | `missing_capability` | I-8 | `1b50273` | +3 |
| C7 confirm 产物校验 | `missing_capability` | I-4 | `9da8388` | +7 |
| C8 焦点池闸门 | `verified_bug` | I-2 | `9ca82d6` | +2 |
| C9 移除 post_open_adj | `design_decision` | I-3 | `8233cc1` | +2 |
| C10 盘中例外确认 | `missing_capability` | I-9 | `bae2fe5` | +3 |
| C11 盘中快照适配器 | `design_decision` | I-7 | `4451f52` | +4 |
| C12 Dashboard manifest | `missing_capability` | I-11 | `3d209af` | +4 |
| C13 脑-肌边界修正 | `boundary_conflict` | I-10 | `2f4e283` | +3 |
| C14 规范运行时路径 | `design_decision` | I-5 | `9ca82d6` | +2 |
| E2E 集成测试 | `missing_capability` | I-12 | `efab796` | +11 |

**合计：164 tests passed, 0 failed**（12 个实现 commit + 1 个路径修正 commit）

### DAILY 步骤状态
|---|---|---|---|---|
| `DAILY-0 晨间准备` | `partial` | 跨日恢复状态矩阵、损坏/多旧会话阻断、归档日选择、exchange trading date 和 daily0 confirmation 均有历史实现与测试 | 2026 年 8 月尚未证明旧历史会话不会阻塞今天；IBKR 正式账户事实闸门未复验 | 在隔离 runtime 验证正确交易日期与跨日恢复 |
| `DAILY-1 盘前决策` | `partial` | timestamped premarket evidence、焦点池闸门、Stage1 管线、`start_stage0_from_snapshot`、cross-asset tape 和计划模板已有实现 | 正式 provider / IBKR 的当前盘前价格链未复验；完整用户握手链尚无 8 月运行证据 | 验证来源、时间戳、市场时段、焦点确认和 Dashboard 报告一致性 |
| `DAILY-2 开盘观察` | `partial` | `OBSERVATION_ACTIVE`、yfinance observation producer、market context、intraday snapshot 和交易日期修复已有历史测试 | 当前实时价格可靠性未复验；旧试跑曾发现非交易日仍可标为 verified | 验证交易日闸门、真实开盘价和 observation 合法动作 |
| `DAILY-3 盘中管理` | `partial` | 快照、VWAP、关键位、例外记录、manifest 和价格刷新资产存在 | 单次刷新、循环、IBKR 与页面展示仍可能是不同链；8 月未运行 | 先验证一次事实刷新贯穿同一 session 与 Dashboard，不扩展循环功能 |
| `DAILY-4 盘后复盘` | `partial` | full/quick/freeze review schema、review 文件、白名单归档、缺失文件阻断和 artifact ledger 均有历史实现与测试 | 尚未完成一次 8 月真实对话收尾；周期复盘与 Growth promotion bridge 未复验 | 用最小 DAILY 完成收尾、归档并验证次日恢复 |

### DAILY 审计证据汇总 (2026-06-30)

| 审计报告 | Commit | Tests |
|---------|--------|-------|
| DAILY-AUDIT-0 晨间准备 | `643df03` | 11 passed |
| DAILY-AUDIT-1 盘前决策 | `fb61fc6` | 16 passed |
| DAILY-AUDIT-2 开盘观察 | `fdf9241` | 21 passed |
| DAILY-AUDIT-3 盘中管理 | `26a070e` | 30 passed |
| DAILY-AUDIT-4 盘后复盘 | `b31b3fe` | 11 passed |
| **合计** | — | **89 passed, 0 failed** |

### DAILY 当前共同阻塞

- ~~DAILY-CONTRACT 待批准~~ → 已批准（2026-07-01）；
- C1–C14 存在候选实现，但高阶审核发现未接线和语义缺口，不能声明全部完成；
- Q1–Q3 已于 2026-07-01 获得用户明确批准，全部选择 A；此前 commit `e0d4338` 的批准记录缺少来源，现以独立用户批准记录为准；
- 初版 H4（`record_plan_approval` 跃迁 bug）经高阶复核不成立，已从当前契约和当前待实施清单移除；历史审计报告和审核记录保留纠正谱系；
- 下一阶段：L1/L2/L3 已通过高阶复核后，按 `2026-07-01-daily-h4-review-contract.zh.md` 固化 DAILY-4 契约，再按 `2026-07-01-daily-h4-task-packets.zh.md` 依次实施 H4-L1/H4-L2/H4-L3；完成前不得升级为 `implemented`。

### 最小入口接线批次（2026-07-08）

相关设计：

- [`../../docs/superpowers/specs/2026-07-08-minimal-usable-entry-and-stage0-design.zh.md`](../../docs/superpowers/specs/2026-07-08-minimal-usable-entry-and-stage0-design.zh.md)

相关计划：

- [`../../docs/superpowers/plans/2026-07-08-minimal-usable-entry-and-stage0-plan.zh.md`](../../docs/superpowers/plans/2026-07-08-minimal-usable-entry-and-stage0-plan.zh.md)

相关台账：

- [`../../handoff/2026-07-08-entry-source-map.zh.md`](../../handoff/2026-07-08-entry-source-map.zh.md)
- [`../../handoff/2026-07-08-entry-file-tag-ledger.zh.md`](../../handoff/2026-07-08-entry-file-tag-ledger.zh.md)

当前结果：

- `operating-console.html` 已恢复为第一批最小入口壳；
- 入口可见 5 个核心字段：`Today Mode`、`Current Step`、`Readiness`、`Missing Items`、`Next Action`；
- 入口保留了 `Growth / Principles / Review` 的轻量回链，不牺牲 `investing-os` 成长性；
- `dashboard_server.py` 已提供最薄的 `entry_state` 聚合 helper 与 summary 暴露；
- blocker 缺口已优先通过 active blocker → `entry_state.missing_items` → UI 这条链展示；
- 文件标签体系已建立，用于后续筛选“主链文件 / 过渡桥文件 / 参考文件”。

验证结果：

- `python -m pytest stock_team/tests/unit -k "coordinator_summary_payload_exposes_blocker_missing_items" -v` → 通过
- `python -m pytest stock_team/tests/unit -k "entry_state or dashboard or coordinator" -q` → 77 通过，1 旧失败
- `python -m pytest stock_team/tests/unit/orchestration/ -q` → 121 通过
- 旧失败仍是 `test_dashboard_reads_from_runtime_manifest` 的 freshness 断言，属于先前已知问题，与本批最小入口接线无关

下一动作：

- 在不扩大范围的前提下，决定是否让 `operating-console` 直接读取统一的 `entry_state` payload，而不是继续兼容局部 fallback；
- 把 Stage0 brain precondition 的 canonical 回写结果继续接到真正可运行的入口与写回链；
- 继续利用文件标签体系，为后续筛掉无用文件、保留主链文件做准备。

### Stage0 brain precondition canonical 回写批次（2026-07-09）

相关设计：

- [`../../docs/superpowers/specs/2026-07-08-stage0-brain-preconditions-canonical-writeback-design.zh.md`](../../docs/superpowers/specs/2026-07-08-stage0-brain-preconditions-canonical-writeback-design.zh.md)

相关计划：

- [`../../docs/superpowers/plans/2026-07-09-stage0-brain-preconditions-writeback-plan.zh.md`](../../docs/superpowers/plans/2026-07-09-stage0-brain-preconditions-writeback-plan.zh.md)

当前结果：

- `investing-os/templates/pre-market-universe.json` 已锁定 Stage0 正式 continuation 所需的 5 个脑侧前置字段语义；
- `investing-os/system/workflows/pre-market.md` 已明确：Stage0 不是纯 market-data 动作，缺少这些输入时不得视为正式 ready；
- `investing-os/system/data/packets/pre-market-context-packet.md` 已明确 ownership boundary：`stock_team` 只能消费这些前置输入做事实映射，不能改写最终 cognition / permission / forbidden-action judgment；
- 三处已形成分工：template 管结构，workflow 管进入条件与阻断语义，packet contract 管 brain–muscle 边界。

验证结果：

- `rg -n "positions|prior_review|cognition_state|permission_state_before_open|forbidden_actions" investing-os/templates/pre-market-universe.json investing-os/system/workflows/pre-market.md investing-os/system/data/packets/pre-market-context-packet.md` → 三处字段一致
- `rg -n "brain-owned precondition|must not overwrite|formally ready|not a pure market-data action" investing-os/system/workflows/pre-market.md investing-os/system/data/packets/pre-market-context-packet.md investing-os/templates/pre-market-universe.json` → 语义与边界一致

下一动作：

- 继续把这 5 个脑侧前置字段真正接到可运行入口，而不只是停留在文档层；
- 优先做最小可用闭环：进入入口时能判断“只是看见数据”还是“正式 Stage0 ready”；
- 后续再决定哪些 `stock_team` 过渡文件可以合并回 `investing-os` 主链，哪些应标记为 retire-later。

### 对话驱动 DAILY 现有资产映射（2026-07-11）

设计与执行依据：

- `investing-os/docs/superpowers/specs/2026-07-11-conversation-driven-daily-workflow-design.zh.md`
- `investing-os/docs/superpowers/plans/2026-07-11-daily-existing-assets-mapping-plan.zh.md`
- `investing-os/handoff/2026-07-11-daily-existing-assets-map.zh.md`
- `investing-os/handoff/2026-07-11-daily-existing-file-ledger.zh.md`

当前结论：

- DAILY-0/1 的 session、正式盘前 snapshot、Stage 0、对话笔记、焦点确认、Stage 1、计划与盘中指导文件均已有可复用链；
- DAILY-2/3 的盘中 snapshot、evidence dashboard、权限投影和例外确认已有实现，缺口集中在“用户主动观察 + 对话引用 + pending_review”的结构化事件文件；
- DAILY-4 的 full/quick/freeze schema、归档门和跨日恢复已有实现，缺口集中在对话聚类复盘与 growth dashboard promotion queue 的桥接；
- `operating-console.html` 作为每日交易 Dashboard 复用，但应改为只读统一 manifest，不再承担 Init/Confirm/Start 等流程推进；
- `growth-dashboard-draft.html` 及其 traceability 数据生成链作为独立认知 Dashboard 原样复用；
- 当前最小新增能力是 `daily-status manifest` builder，而不是新建 DAILY 文件体系或新 Dashboard。

下一实施批次：

1. 定义 daily-status manifest 精确 schema，并映射到现有 runtime 文件；
2. 测试先行实现只读 manifest builder；
3. operating console 改为只渲染 manifest 和下一句对话建议；
4. 用离线 fixture 隔离跑 DAILY-0/1，再安排真实盘前时点试跑；
5. DAILY-0/1 稳定后再设计 intraday conversation event schema。

### DAILY status manifest 第一实施批次（2026-07-11）

实现提交范围：

- session schema 已增加 `daily0_confirmation`，记录活动模式、账户事实状态、分析范围和用户确认；
- 新增 `daily-status.schema.json` 与独立只读 `stock_team/orchestration/daily_status.py`；
- builder 已从现有 DAILY-0/1 runtime 文件推导五节点、DAILY-1A/B/C/D、artifact 状态、缺口提示与 `state_sync_needed`；
- dashboard server 已生成并暴露 `{session_id}-daily-status.json`，兼容 `entry_state` 由 manifest 投影；
- operating console 已移除主流程 Init/Confirm/Start 按钮，改为只读显示 manifest 与“在当前对话继续”提示；
- growth cognition dashboard 未修改；
- 离线 fixture 已从 DAILY-0 confirmation 推进到 DAILY-2 observation，未冒充真实盘前数据成功。

验证：

- `python -m pytest stock_team/tests/unit/orchestration stock_team/tests/integration/test_daily_e2e.py -q` → 143 passed；
- `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -k "not dashboard_reads_from_runtime_manifest" -q` → 22 passed, 1 deselected；
- 保留的旧失败：`test_dashboard_reads_from_runtime_manifest` 使用固定 2026-07-01 `archived_at`，当前返回 stale 而非测试期待的 fresh，与本批 manifest 实现无关。

当前边界：

- 已完成离线 DAILY-0/1 文件驱动闭环与 Dashboard 投影；
- 尚未完成真实 IBKR 账户确认写入、真实盘前 provider 数据试跑、盘中 conversation event runtime 和 DAILY-4→growth dashboard 桥接；
- 下一步应进行隔离启动检查，然后在真实盘前窗口运行数据获取，不应继续扩展 schema。

### yfinance 隔离试跑（2026-07-11）

- 记录：`investing-os/handoff/2026-07-11-yfinance-isolated-daily-trial.zh.md`；
- yfinance 直接获取 COHR 成功，现有 intraday snapshot 也生成了价格/VWAP/量比事实；
- 正式 Stage 0 正确拒绝无 explicit premarket snapshot 的 yfinance fallback；
- 旧 `premarket --refresh` 生成分析缓存后超时，并改写正式 config，暂不接入 DAILY；
- 新发现：周六 intraday snapshot 仍标记 `in_window=true/status=verified`，需在真实 DAILY-2/3 前增加交易日校验；
- 当前状态保持：fallback observation 可用，formal Stage 0 未完成。

### Operating Console 首屏精简（2026-07-12）

- 首屏已收缩为今日步骤、事实就绪、当前对话、今日关注四块；
- coordinator、artifact、skill task、snapshot form、旧 routes 与认知摘要已移入默认折叠的诊断详情；
- 页面继续只读 `daily_status`，未恢复流程按钮，growth cognition dashboard 未修改；
- focused source-contract tests 通过；
- 本地 HTTP `/` 与 `/api/coordinator-summary` 均返回 200，页面包含四块首屏和默认折叠 diagnostics；
- Playwright 实际截图确认首屏在一个视口内完成主要信息呈现；
- 当前“今日关注”仍可能来自旧会话 snapshot，本轮明确视为恢复数据问题，不代表今日焦点池已经确认。

### Operating Console 分页信息架构（2026-07-12）

- 新规格：`investing-os/docs/superpowers/specs/2026-07-12-operating-console-paged-information-architecture.zh.md`；
- 本实现取代同日“首屏四块 + 整体折叠”的布局：四块重复摘要、旧 coordinator hero、minimal entry、daily routes 和 cognitive summary 已退出；
- `operating-console.html` 现提供 `#today / #evidence / #review / #diagnostics` 四个互斥页面，并保留独立认知系统入口；
- 今日页只显示唯一主任务、DAILY 时间线、确认焦点/权限和最高提醒；
- 证据页显示 artifact readiness 与当前产物任务；
- 复盘页对尚未接线的 intraday events / cognition bridge 明确显示缺失；
- 诊断页承接 coordinator、state sync、路径和 fallback 链接，不参与流程推进；
- focused Dashboard tests：23 passed，1 个已知 fixed-date freshness test deselected；
- Playwright 验证 desktop/mobile，`#review` 与 `#diagnostics` 均只有一个 active page；唯一 console error 为 favicon.ico 404；
- 当前页面仍读取旧会话 `2026-06-15`，不应解释为今日 session 已恢复。

### Research Database V3 Alpha 实施批次（2026-07-16 至 2026-07-22）

当前结果：

- DAILY report 已要求挂接一至三个 Alpha Questions，避免每日分析彼此孤立；
- 新增 Question、Evidence、Hypothesis、Observation 和 Decision Card 模板，以及 tracked metrics 最小索引；
- coordinator summary 和 Operating Console 已能以安全默认值读取并展示 research database bundle；
- runtime bootstrap 能生成 research topic、cards 和 tracked metrics 占位产物；
- V3 Alpha 暂时只维护三个长期问题：AI 利润沉淀、Hyperscaler CapEx、Inference 第二轮硬件需求；
- AMAT、MU、NBIS、TSM、NOW、NVDA 已有阅读报告原型，包含关键价格或 Reliability 检查；
- 这些实现和测试均属于 7 月历史证据，2026 年 8 月尚未重新运行。

历史证据：

- `544e1b7`：Research Database daily templates；
- `b1ae7ab` / `7192fbd` / `36485f7`：coordinator payload 与 Operating Console summary；
- `c39c472` / `a69360d` / `fcee080`：runtime bootstrap、payload shape 和 MVP alignment；
- `d1418d6`：研究报告可靠性闸门；
- `421d974`：AI repair-day follow-through 认知候选。

当前边界：

- `RESEARCH` 从纯 `documented` 提升为 `partial` 原型状态；
- 现有能力主要解决结构、展示和人工沉淀，尚未持续自动生产高质量 Evidence；
- 下一步不是批量增加公司静态报告，而是在 DAILY 稳定后完成一个 Question 的 Evidence 端到端更新。

### 2026 年 8 月恢复基线（2026-08-13）

系统地图：

- [`../../SYSTEM-OVERVIEW-AND-STATUS.zh.md`](../../SYSTEM-OVERVIEW-AND-STATUS.zh.md)

恢复事实：

- 当前分支为 `codex/repository-cleanup-20260630`，远端 `origin` 已配置；
- 恢复开始前本地相对远端领先 55 个提交；连同 4 个恢复文档提交共 59 个提交已审计并推送，推送后 ahead/behind 为 `0/0`；
- 工作区存在用户未提交的认知方法论、索引和运行时观察文件，不属于本轮同步内容；
- 8 月已运行隔离 canonical DAILY observation 第一段；真实交易日期、盘前时间戳/来源、snapshot/context 产物和 Dashboard 同源回读已验证；
- 最小回归固定验证：真实交易日期、跨日恢复、盘前/实时价格、Dashboard 对同一 session 和 artifact ledger 的展示；
- 遇到首个阻塞后停止扩展，以根因调查和 TDD 修复，然后重跑同一回归。

最小回归与修复记录：

- [`../../handoff/2026-08-13-daily-minimal-regression.zh.md`](../../handoff/2026-08-13-daily-minimal-regression.zh.md)
- 首个阻塞：`daily0_confirmation` 有 schema 和读取方但无正式写入入口；
- 修复：新增 `coordinator_cli confirm-daily0`，只写确认事实，不推进 coordinator、不运行工具、不改变权限；
- TDD 与相关回归：首个阻塞批次 230 passed；
- 修复后 Dashboard 从 DAILY-0 前进到 DAILY-1A；当前明确缺口为 canonical `stage0_universe`。

Stage 0 universe 第二阻塞修复：

- 设计：[`../../docs/superpowers/specs/2026-08-13-stage0-universe-canonical-entry-design.zh.md`](../../docs/superpowers/specs/2026-08-13-stage0-universe-canonical-entry-design.zh.md)
- 既有完整 builder 已从 Dashboard 提取到共享模块，Dashboard 只保留薄包装；
- 新增 `coordinator_cli prepare-stage0-universe`，在 session 同一 runtime 的 inputs 目录生成 canonical universe；
- 命令不改变 session state/version，不写确认，不运行行情 provider；
- 第二次全新隔离试跑按 init → prepare → confirm → observation Stage 0 完成；
- universe、snapshot、market context 均 present/valid/fresh；
- Dashboard 到 `DAILY-1B / waiting_user`，coordinator 为 `STAGE0_READY`，`state_sync.needed=false`；
- observation 权限保持 `no_trading_permission`；
- Stage 0 universe 批次完整相关回归：233 passed。

跨日 freeze runtime 复核：

- 真实构造昨日 `DAY_INITIALIZED` observation session；无 recovery 时今天入口正确阻塞；
- 首次 `--recovery freeze` 暴露 `freeze is not legal from DAY_INITIALIZED`；
- H1 矩阵明确允许盘前中断 freeze，根因是 transitions 漏注册该路径，历史测试亦未覆盖；
- 公开 CLI 测试先失败后，以单一 transition 修复；
- 修复后旧会话进入 `DAY_ARCHIVED` 并生成交易日期分层 archive manifest，今日 observation session 正常创建；
- 完整相关回归：234 passed；
- quick_review / full_review 尚未做本轮 runtime 场景，不标记为已实测。

正式 runtime 盘前启动补充：

- 09:17 ET 启动 Dashboard，市场时钟正确识别 8 月 13 日盘前；
- 7 月 15 日 `STAGE0_READY` 观察会话触发跨日阻断，证明正式入口没有静默跳过旧会话；
- TDD 补齐 `STAGE0_READY -> freeze -> CLOSED_UNREVIEWED` 后，235 passed；
- 旧会话完成 freeze + archive，今日 observation 会话创建并推进至 `STAGE0_READY / DAILY-1 / waiting_user`；
- Dashboard 回读 snapshot 为 present / valid / fresh；QQQ 与期货均带 8 月 13 日盘前时间戳和明确来源；
- 开盘后盘中实时价格验收仍待执行，DAILY 状态不升级为 stable。

真实性纠正：

- 今日页原有 7 月 13 日短报告链接为静态硬编码，不是当日 artifact；现已改为只读取当前 session 交易日期对应的 `readable_brief`；
- 助手技术试跑曾越权写入 `daily0_confirmation.user_confirmed=true`；现已通过 `invalidate-daily0` 撤销并保留审计历史；
- 当前正式状态恢复为 `DAILY-0 / waiting_user / daily0_confirmation_missing`；
- 当日讨论完成前，预采集 Stage 0 数据不等于晨间准备完成，也不生成或回退显示历史短报告。

下一动作：

1. 09:30 ET 后刷新并验证盘中实时价格、时间戳、来源和 Dashboard 展示；
2. 只修复该试跑遇到的下一个真实技术阻塞；
3. 后续补做 quick_review / full_review 跨日 runtime 场景；
4. DAILY 稳定后设计 Evidence 自动生产的下一最小切片。

## RESEARCH 投资研究

| 子工作流 | 状态 | 证据 | 下一动作 |
|---|---|---|---|
| `RESEARCH-COMPANY` | `documented` | company research 与 dossier lifecycle 文档 | DAILY 稳定后再验证 |
| `RESEARCH-INDUSTRY` | `documented` | industry research 与 dossier lifecycle 文档 | 同上 |
| `RESEARCH-THEME` | `unknown` | 尚未做针对性审计 | 保持登记，不提前实现 |
| `RESEARCH-MACRO` | `unknown` | 尚未做针对性审计 | 保持登记，不提前实现 |
| `RESEARCH-EVENT` | `unknown` | 历史事件资料存在，统一流程未核验 | 保持登记，不提前实现 |

## REVIEW 周期复盘

| 子工作流 | 状态 | 证据 | 下一动作 |
|---|---|---|---|
| `REVIEW-WEEKLY` | `documented` | weekend-review workflow | DAILY 稳定后核验 |
| `REVIEW-MONTHLY` | `unknown` | 未针对性审计 | 保持登记 |
| `REVIEW-QUARTERLY` | `unknown` | 未针对性审计 | 保持登记 |
| `REVIEW-PORTFOLIO` | `unknown` | 有组合风险能力，复盘闭环未核验 | 保持登记 |
| `REVIEW-THESIS` | `documented` | thesis 与 dossier 资料存在 | 保持登记 |
| `REVIEW-TACTIC` | `documented` | tactic review/backtest 契约存在 | 保持登记 |

## LEARNING、VALIDATION、SYSTEM

这些工作流已经登记，但当前不展开实施。DAILY 中发现的需求可以引用它们，不得借此扩大当前任务范围。

## 变更记录

| 日期 | 变更 | Commit |
|---|---|---|
| 2026-06-30 | 建立统一工作流台账；以 `DAILY` 为第一实施重点 | — |
| 2026-06-30 | 完成 DAILY-0 至 DAILY-4 事实审计 (89 tests passed)；编写 DAILY-CONTRACT v1 | `93306e2` |
| 2026-06-30 | 高阶审核：v1 六项阻断 + 非阻断修订；编写审核记录 | `d0933dc` |
| 2026-06-30 | DAILY-CONTRACT v2 修订：修正 R1–R6、observation 只读路径、脑-肌边界、候选修正分类、7 项用户决策 | — |
| 2026-07-01 | DAILY-CONTRACT v3 修订：V2-1 至 V2-4；v3 高阶审核通过（待用户批准 Q1–Q3） | `d69a206` / `279c89b` |
| 2026-07-01 | DAILY-CONTRACT v4 终版 approved：11 项高阶收口 + Q1–Q3 全部批准选项 A | — |
| 2026-07-01 | C1–C14 全部实施完成：12 tasks + 164 tests passed；DAILY-0 至 DAILY-4 全部升至 `implemented` | `7843db3`–`efab796` |
| 2026-07-01 | 高阶复核纠正：v4 用户批准无有效来源；171 tests 通过但生产链存在阻断，DAILY 降回 `partial` | 以 `2026-07-01-daily-implementation-review.md` 首次进入 Git 的提交为准 |
| 2026-07-01 | 用户明确批准 DAILY Q1–Q3，全部选择 A；实现状态仍保持 `partial` | 以 `2026-07-01-daily-q1-q3-approval.md` 首次进入 Git 的提交为准 |
| 2026-07-01 | 固化 H1/H2/H3 高阶修复纲领；生成 L1/L2/L3 低阶任务包，作为下一轮唯一实施入口 | 待本次提交 |
| 2026-07-01 | 固化 DAILY-4 H4 高阶契约；生成 H4 低阶任务包，作为下一轮复盘实现入口 | 待本次提交 |
| 2026-07-03 | 完成跨日恢复、白名单归档、observation 公共动作和 DAILY-4 review/归档闸门的历史实现与测试 | `cd69e75`–`e36b770` |
| 2026-07-11 | 完成 daily-status manifest、只读 Operating Console 投影和 yfinance observation 隔离试跑 | 见本页对应实施批次 |
| 2026-07-16 | 建立 Research Database V3 Alpha 模板、runtime bootstrap、Dashboard summary 和三大问题主线 | `544e1b7`–`fcee080` |
| 2026-08-13 | 建立系统总览和恢复基线；保留 `DAILY=partial`，等待隔离最小回归 | 以本次状态基线提交为准 |
| 2026-08-13 | 完成隔离 DAILY 第一段；修复 DAILY-0 确认无正式写入入口；定位下一缺口 `stage0_universe` | 以 `confirm-daily0` 修复提交为准 |
| 2026-08-13 | 提取共享 universe builder，增加 canonical CLI 入口；隔离 DAILY 到 DAILY-1B | 以 `prepare-stage0-universe` 修复提交为准 |
| 2026-08-13 | 跨日 freeze runtime 复核；补齐 DAY_INITIALIZED freeze transition | 以跨日 freeze 修复提交为准 |
