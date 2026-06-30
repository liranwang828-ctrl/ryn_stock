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
| `DAILY` 每日交易 | `partial` | 2026-06-30 | DAILY-0 至 4 已完成事实审计（89 tests passed, 0 failed）；DAILY-CONTRACT 已编写待主脑批准；代码实施须在批准后方可开始 |
| `RESEARCH` 投资研究 | `documented` | 2026-06-30 | 公司、行业等流程与 Packet 文档存在；当前端到端运行状态未核验 |
| `REVIEW` 周期复盘 | `documented` | 2026-06-30 | 周末、交易和论点复盘资料存在；统一周期复盘入口未核验 |
| `LEARNING` 经验进化 | `documented` | 2026-06-30 | Packet absorption、journal promotion 和 approval 流程存在；运行闭环未核验 |
| `VALIDATION` 策略验证 | `partial` | 2026-06-30 | 回测命令与契约存在，部分测试曾通过；与认知审核和候选队列的闭环未核验 |
| `SYSTEM` 系统维护 | `partial` | 2026-06-30 | 多项检查、schema 和 runtime 机制存在；尚无统一维护工作流验收 |

## DAILY 每日交易

当前行动计划：[`../../../docs/superpowers/plans/2026-06-30-daily-workflow-foundation.md`](../../../docs/superpowers/plans/2026-06-30-daily-workflow-foundation.md)
DAILY 契约：[`DAILY-CONTRACT.zh.md`](DAILY-CONTRACT.zh.md)（待主脑批准）

| 步骤 | 状态 | 已知证据 | 已知缺口 | 下一验收动作 |
|---|---|---|---|---|
| `DAILY-0 晨间准备` | `partial` | SESSION_TYPES 常量完整；init-day→DAY_INITIALIZED→STAGE0 正向链完好；IBKR 同步函数测试通过 (11/11)；会话持久化+乐观锁 test-covered | 会话路由器无实现（仅 trading 可运行）；跨日恢复零实现；coordinator 工作流无用户确认闸门；非交易模式无状态转换定义 | 主脑批准契约后：添加 --session-type 参数；实现跨日恢复三种选项；集成 IBKR 事实确认闸门 |
| `DAILY-1 盘前决策` | `partial` | 状态机 7 状态+4 可执行 intent 定义完整 (16/16 tests passed)；as-of 校验+时区+盘前窗口 test-covered；数据降级链 Polygon→yfinance→stale cache 已实现；adapters 支持 5 intent→CLI 映射 | record_focus_confirmation 和 record_plan_approval 仅记录路径不校验内容；record_plan_approval 成功时不自动跃迁 (transitions.py L44-50 bug)；IBKR 声明的优先级在盘前路径中未调用；decision sheet 缺失时回退到 watchlist 全量可绕过焦点池确认；无端到端握手链集成测试 | 主脑批准契约后：修复 SUCCESS_TRANSITIONS 映射；为 confirm intent 添加产物校验；修复焦点池回退闸门；统一产物路径 |
| `DAILY-2 开盘观察` | `partial` | intraday_snapshot.py 库函数完整且 test-covered (21/21)；transitions.py 硬阻止未批准计划时的 start_intraday；python 循环刷新不改写 Stage 0/1 锚点 test-covered | 无独立状态（隐式合并在 PLAN_APPROVED→INTRADAY_ACTIVE 过渡中）；handle_intraday_snapshot 无时间窗口 enforce (9:30-10:00)；无批准计划拒绝闸门未在 CLI 中 enforce；adapters.py 不支持 intraday-snapshot intent | 主脑批准契约后：在 CLI 添加入口时间窗口闸门；在 adapters 添加 intraday-snapshot 映射 |
| `DAILY-3 盘中管理` | `partial` | 条件计算函数全覆盖 test-covered (30/30)；handle_intraday_snapshot 单次快照可用；dashboard_server price sync test-covered | IBKR streaming 路径在代码中不存在（文档声称 primary 但实际用 yfinance）；post_open_adj 无文档无权限控制可改写盘前锚点；盘中用户例外确认流程零实现；Dashboard HTML 是纯消费者无后端生产者；单次刷新和循环模式是两个独立系统 | 主脑批准契约后：决定 post_open_adj 去留；统一单次刷新+循环模式；添加盘中例外确认流程 |
| `DAILY-4 盘后复盘` | `partial` | per-stock summary 和 generate_suggestions test-covered (11/11)；transitions.py 定义了 MARKET_CLOSED→archive_day→DAY_ARCHIVED；收尾链 Step 1-2 代码可用 | Step 3-6 零代码实现（纯 investing-os+human 对话任务但无入口）；REVIEW_REQUIRED 在 models.py 中定义但不在 transitions.py 的 TRANSITIONS 字典中；QUICK_REVIEWED / CLOSED_UNREVIEWED 未在 TRADING_STATES 中注册；archive_day 无实际归档写入逻辑；三种复盘选择在 dashboard_server 中映射为同一动作 | 主脑批准契约后：注册缺失状态；实现 archive_day 最小归档逻辑；创建三种复盘选择的不同状态路径；确定 Step 3-4 交互形式 |

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

- DAILY-CONTRACT.zh.md 待主脑批准；
- 8 个高阶决策待定（见契约第 7 节）；
- 8 个状态机修正待批准（见契约第 6 节）；
- 批准前不得修改任何代码。

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
| 2026-06-30 | 建立统一工作流台账；以 `DAILY` 为第一实施重点 | — |
| 2026-06-30 | 完成 DAILY-0 至 DAILY-4 事实审计 (89 tests passed)；编写 DAILY-CONTRACT.zh.md 待主脑批准 | — |
