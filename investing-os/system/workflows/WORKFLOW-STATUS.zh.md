# 工作流实现状态台账

更新日期：2026-07-09
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
| `DAILY` 每日交易 | `partial` | 2026-07-01 | Q1–Q3 已获用户明确批准，171 tests passed；候选实现仍有归档、完整复盘、observation 动作和公开入口 E2E 阻断 |
| `RESEARCH` 投资研究 | `documented` | 2026-06-30 | 公司、行业等流程与 Packet 文档存在；当前端到端运行状态未核验 |
| `REVIEW` 周期复盘 | `documented` | 2026-06-30 | 周末、交易和论点复盘资料存在；统一周期复盘入口未核验 |
| `LEARNING` 经验进化 | `documented` | 2026-06-30 | Packet absorption、journal promotion 和 approval 流程存在；运行闭环未核验 |
| `VALIDATION` 策略验证 | `partial` | 2026-06-30 | 回测命令与契约存在，部分测试曾通过；与认知审核和候选队列的闭环未核验 |
| `SYSTEM` 系统维护 | `partial` | 2026-06-30 | 多项检查、schema 和 runtime 机制存在；尚无统一维护工作流验收 |

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
| `DAILY-0 晨间准备` | `partial` | session type、session listing 和 freeze 候选路径有测试；IBKR monitor 单元测试通过 | full_review 提前创建新会话；quick/full/REVIEW_REQUIRED/多旧会话/损坏会话未完整覆盖；IBKR 正式事实闸门未接线 | 修复跨日恢复语义并从公开入口补测试 |
| `DAILY-1 盘前决策` | `partial` | confirm 校验、焦点池闸门和 canonical runtime 候选实现有测试 | 完整真实握手链和 IBKR 账户事实接线未验证 | 从公开入口完成 Stage 0 → 用户确认 → Stage 1 → 计划批准回归 |
| `DAILY-2 开盘观察` | `partial` | `OBSERVATION_ACTIVE`、快照 adapter 和软时间提示已有候选实现 | allowed_actions 暴露 coordinator 无法执行的 `intraday-snapshot`；运行时 observation 路径未验收 | 统一动作契约并运行 observation E2E |
| `DAILY-3 盘中管理` | `partial` | post_open_adj 移除、例外记录和 runtime manifest 候选实现有测试 | 单次刷新与循环仍是两套系统；IBKR 事实和 manifest 生产链未完整接线 | 统一盘中事实动作并验证完整 manifest 链 |
| `DAILY-4 盘后复盘` | `partial` | review 状态和 archiver helper 有测试；stock_team 候选输出已收窄为事实 | archive_day 未调用 archiver；Step 3–6 对话和结构化产物未实现；full_review 语义错误 | 接线白名单归档、完成复盘交互，并由公开入口 E2E 验收 |

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

- [`../../../docs/superpowers/specs/2026-07-08-minimal-usable-entry-and-stage0-design.zh.md`](../../../docs/superpowers/specs/2026-07-08-minimal-usable-entry-and-stage0-design.zh.md)

相关计划：

- [`../../../docs/superpowers/plans/2026-07-08-minimal-usable-entry-and-stage0-plan.zh.md`](../../../docs/superpowers/plans/2026-07-08-minimal-usable-entry-and-stage0-plan.zh.md)

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

- [`../../../docs/superpowers/specs/2026-07-08-stage0-brain-preconditions-canonical-writeback-design.zh.md`](../../../docs/superpowers/specs/2026-07-08-stage0-brain-preconditions-canonical-writeback-design.zh.md)

相关计划：

- [`../../../docs/superpowers/plans/2026-07-09-stage0-brain-preconditions-writeback-plan.zh.md`](../../../docs/superpowers/plans/2026-07-09-stage0-brain-preconditions-writeback-plan.zh.md)

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
