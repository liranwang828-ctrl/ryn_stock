# 工作流实现状态台账

更新日期：2026-06-30
状态口径来源：[`../../PROJECT-CHARTER.zh.md`](../../PROJECT-CHARTER.zh.md)

## 使用规则

- 这是实现追溯台账，不是愿望清单。
- 文档存在不等于功能可运行，测试存在不等于完整工作流已验证。
- 未做针对性审计时使用 `unknown`，不得凭文件名推断完成度。
- 每次工作流验收或相关任务合入后，更新状态、证据、缺口、下一动作和 commit。

## 总览

| 工作流 | 当前状态 | 最近核验 | 当前判断 |
|---|---|---:|---|
| `DAILY` 每日交易 | `partial` | 2026-06-30 | 协调器、部分证据命令和界面已有实现；完整 DAILY-0 至 DAILY-4 尚未按统一名称和用户交互验收 |
| `RESEARCH` 投资研究 | `documented` | 2026-06-30 | 公司、行业等流程与 Packet 文档存在；当前端到端运行状态未核验 |
| `REVIEW` 周期复盘 | `documented` | 2026-06-30 | 周末、交易和论点复盘资料存在；统一周期复盘入口未核验 |
| `LEARNING` 经验进化 | `documented` | 2026-06-30 | Packet absorption、journal promotion 和 approval 流程存在；运行闭环未核验 |
| `VALIDATION` 策略验证 | `partial` | 2026-06-30 | 回测命令与契约存在，部分测试曾通过；与认知审核和候选队列的闭环未核验 |
| `SYSTEM` 系统维护 | `partial` | 2026-06-30 | 多项检查、schema 和 runtime 机制存在；尚无统一维护工作流验收 |

## DAILY 每日交易

当前行动计划：[`../../../docs/superpowers/plans/2026-06-30-daily-workflow-foundation.md`](../../../docs/superpowers/plans/2026-06-30-daily-workflow-foundation.md)

| 步骤 | 状态 | 已知证据 | 已知缺口 | 下一验收动作 |
|---|---|---|---|---|
| `DAILY-0 晨间准备` | `partial` | 会话初始化、IBKR 获取和跨日恢复设计存在 | 用户活动选择、前日处理和账户事实是否在同一入口闭环，未验证 | 从干净模拟会话启动，记录所有输入、确认点和产物 |
| `DAILY-1 盘前决策` | `partial` | 市场环境与焦点标的证据命令、讨论和计划 Agent 已有实现或设计 | 从事实请求到用户批准计划的完整握手未验证 | 运行市场环境包 → 用户确认焦点池 → 焦点证据包 → 计划批准 |
| `DAILY-2 开盘观察` | `unknown` | 旧 Node 2 和现行 intraday 设计存在 | 当前入口、产物、用户动作及与批准计划的关系未审计 | 仅审计相关入口和契约，形成最小验收场景 |
| `DAILY-3 盘中管理` | `partial` | intraday snapshot/dashboard 和旧盘中监控能力存在 | 是否严格只更新事实、是否保持计划锚点、用户如何处理例外，未验证 | 用非交易模拟运行一次单次刷新并核对状态不越权 |
| `DAILY-4 盘后复盘` | `documented` | trade evidence、post-market 和 lesson workflow 文档存在 | 真实交易事实、用户意义判断、候选经验和日终归档未串联验证 | 使用无交易或模拟交易日完成收尾并验证次日可恢复 |

### DAILY 当前共同阻塞

- 统一名称尚未进入现有协调器和界面；
- 用户交互点没有一份经过运行验证的操作清单；
- 旧 Node 体系、Evidence Stage 0/1 和新协调器状态需要建立映射；
- 完整的非交易模拟记录尚未生成；
- 当前只记录已知状态，不据此修改业务逻辑。

## RESEARCH 投资研究

| 子工作流 | 状态 | 证据 | 下一动作 |
|---|---|---|---|
| `RESEARCH-COMPANY` | `documented` | company research 与 dossier lifecycle 文档 | DAILY 稳定后再验证一次问题 → 证据 → 用户判断 → dossier 候选 |
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
| 2026-06-30 | 建立统一工作流台账；以 `DAILY` 为第一实施重点 | 以本行首次进入 Git 的提交为准 |
