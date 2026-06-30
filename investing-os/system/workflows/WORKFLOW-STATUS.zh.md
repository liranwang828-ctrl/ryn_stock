# 工作流实现状态台账

更新日期：2026-07-01
状态口径来源：[`../../PROJECT-CHARTER.zh.md`](../../PROJECT-CHARTER.zh.md)

## 使用规则

- 这是实现追溯台账，不是愿望清单。
- 文档存在不等于功能可运行，测试存在不等于完整工作流已验证。
- 未做针对性审计时使用 `unknown`，不得凭文件名推断完成度。
- 每次工作流验收或相关任务合入后，更新状态、证据、缺口、下一动作和 commit。

## 总览

| 工作流 | 当前状态 | 最近核验 | 当前判断 |
|---|---|---:|---|
| `DAILY` 每日交易 | `contracted` | 2026-07-01 | DAILY-CONTRACT v4 终版 approved；11 项高阶决策全部定案；可编写代码实施计划 |
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

| 步骤 | 状态 | 已知证据 | 已知缺口 | 下一验收动作 |
|---|---|---|---|---|
| `DAILY-0 晨间准备` | `partial` | SESSION_TYPES 常量完整；init-day→DAY_INITIALIZED→STAGE0 正向链完好；IBKR 同步函数测试通过 (11/11)；会话持久化+乐观锁 test-covered | 会话路由器无实现（仅 trading 可运行）；跨日恢复零实现；coordinator 工作流无用户确认闸门；非交易模式无状态转换定义；缓存不可替代 IBKR 正式事实（R2） | 实施：添加 --session-type 参数；按高阶方案实现跨日恢复；集成 IBKR 事实确认闸门；缓存路径仅作 stale_unverified 只读展示 |
| `DAILY-1 盘前决策` | `partial` | 状态机与盘前 CLI 相关审计测试通过 (16/16)；as-of 校验、时区和盘前窗口 test-covered；adapters 已映射现有盘前 intent；`record_plan_approval` 跃迁经高阶复核正常（审核 R1：初版 H4 不成立） | confirm intent 只记录路径、不校验内容；decision sheet 缺失时回退到 watchlist 全量可绕过焦点池确认；无端到端握手链集成测试；observation 模式在初版契约中被截断（R3 已修正） | 实施：按高阶方案实现 confirm 校验；修复焦点池回退闸门；统一 canonical runtime 路径 |
| `DAILY-2 开盘观察` | `partial` | intraday_snapshot.py 库函数完整且 test-covered (21/21)；transitions.py 硬阻止未批准计划时的 start_intraday；循环刷新不改写 Stage 0/1 锚点 test-covered；observation 只读路径已纳入契约（R3 修正） | 无独立状态；handle_intraday_snapshot 无时间窗口提示；adapters.py 不支持 intraday-snapshot intent | 实施：创建独立 OBSERVATION_ACTIVE 状态；按 Q3 实现时间窗口行为；添加 adapters 映射 |
| `DAILY-3 盘中管理` | `partial` | 条件计算函数全覆盖 test-covered (30/30)；handle_intraday_snapshot 单次快照可用；dashboard_server price sync test-covered；observation 只读路径已纳入契约（R3 修正） | IBKR streaming 路径在代码中不存在；post_open_adj 无文档无权限控制；盘中用户例外确认流程零实现；Dashboard 消费路径与 CLI 生产路径不一致；单次刷新和循环模式是两个独立系统 | 实施：按 Q1 处理 post_open_adj；统一为单一盘中事实动作；对接 runtime manifest；添加盘中例外确认流程 |
| `DAILY-4 盘后复盘` | `partial` | per-stock summary 和复盘事实包 test-covered (11/11)；transitions.py 定义了 MARKET_CLOSED→archive_day→DAY_ARCHIVED；收尾链 Step 1-2 代码可用 | Step 3-6 零代码实现；REVIEW_REQUIRED 不在 transitions.py 的 TRANSITIONS 字典中；QUICK_REVIEWED / CLOSED_UNREVIEWED 未注册；archive_day 无实际归档逻辑；三种复盘选择在 dashboard_server 中映射为同一动作；经验候选归属越过脑-肌边界（R5 已修正） | 实施：按 Q2 实现复盘交互；注册缺失状态；实现 archive_day 最小归档；创建三种复盘不同路径；将经验生成移至 investing-os |

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
- 11 项高阶决策 + 3 项用户决策全部定案，见契约 v4 第 7 节；
- 14 项候选修正（C1–C14）已分类，可据此编写代码实施任务；
- 下一阶段：编写独立实现任务单，按 TDD 执行，每个任务独立 commit。
- 初版 H4（`record_plan_approval` 跃迁 bug）经高阶复核不成立，已从当前契约和当前待实施清单移除；历史审计报告和审核记录保留纠正谱系；
- 批准前不得修改任何代码。

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
