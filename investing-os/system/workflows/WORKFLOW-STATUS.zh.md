# 工作流实现状态台账

更新日期：2026-07-01
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
| `DAILY` 每日交易 | `implemented` | 2026-07-01 | DAILY-CONTRACT v4 终版 approved；C1–C14 全部实现 (12 tasks, 164 tests)；E2E 路径可运行 |
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

DAILY 契约：[`DAILY-CONTRACT.zh.md`](DAILY-CONTRACT.zh.md)（v4 终版 approved — 11 项高阶决策 + Q1–Q3 全部批准选项 A）

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
| `DAILY-0 晨间准备` | `implemented` | SESSION_TYPES 常量完整；init-day→DAY_INITIALIZED→STAGE0 正向链完好；IBKR 同步函数测试通过 (11/11)；会话持久化+乐观锁 test-covered；`--session-type` 已实施 (C1)；runtime 路径已修正为绝对路径 (C14) | 跨日恢复路由器仍待实现；非交易模式状态转换定义仍待添加；缓存不可替代 IBKR 正式事实（R2） | 实施跨日恢复路由器；集成 IBKR 事实确认闸门；添加非交易模式路径 |
| `DAILY-1 盘前决策` | `implemented` | 状态机与盘前 CLI 测试通过 (16/16)；as-of 校验、时区和盘前窗口 test-covered；adapters 已映射现有盘前 intent；`record_plan_approval` 跃迁经高阶复核正常；confirm 产物校验已实施 (C7)；焦点池回退闸门已修复 (C8)；canonical runtime 路径已统一 (C14) | 端到端握手链集成测试仍待完成 | 实施 E2E 握手链集成；对接 IBKR 正式事实源 |
| `DAILY-2 开盘观察` | `implemented` | intraday_snapshot.py 库函数完整且 test-covered (21/21)；transitions.py 硬阻止未批准计划时的 start_intraday；循环刷新不改写 Stage 0/1 锚点 test-covered；OBSERVATION_ACTIVE 独立状态已创建 (C5)；intraday-snapshot adapter 已添加 (C11)；时间窗口软提示已实施 (7.9) | 时间窗口行为待运行时验证 | runtime 验收观测模式端到端 |
| `DAILY-3 盘中管理` | `implemented` | 条件计算函数全覆盖 test-covered (30/30)；handle_intraday_snapshot 单次快照可用；dashboard_server price sync test-covered；post_open_adj 已移除 (C9)；盘中例外确认流程已实施 (C10)；Dashboard runtime manifest 已统一 (C12) | IBKR streaming 路径在代码中不存在；单次刷新和循环模式仍是两个独立系统 | 统一盘中事实动作；对接 runtime manifest 完整链路 |
| `DAILY-4 盘后复盘` | `implemented` | per-stock summary 和复盘事实包 test-covered (11/11)；MARKET_CLOSED→archive_day→DAY_ARCHIVED 三条复盘路径完整 (C3, C4)；archive_day 最小归档逻辑已实施 (C6)；脑-肌边界已修正 — stock_team 只输出事实 (C13) | Step 3-6 零代码实现；三种复盘交互仍待实施 | 实施复盘交互对话流；investing-os 侧经验生成 |

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
- ~~14 项候选修正（C1–C14）~~ → 已全部实现（2026-07-01），12 个实现 task + 1 个路径修正，164 tests passed；
- 11 项高阶决策 + 3 项用户决策全部定案，见契约 v4 第 7 节；
- 初版 H4（`record_plan_approval` 跃迁 bug）经高阶复核不成立，已从当前契约和当前待实施清单移除；历史审计报告和审核记录保留纠正谱系；
- 下一阶段：跨日恢复路由器、非交易模式路径、复盘交互对话流、IBKR streaming 对接、E2E 握手链集成测试。

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
