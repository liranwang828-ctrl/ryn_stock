# 2026-07-13 DAILY-0 准备草稿

> 状态：非交易日预备草稿，等待下一交易日由用户确认。不得据此授予交易权限。

## 建议活动模式

`observation`

原因：当前没有经本会话验证的 IBKR 账户事实；yfinance observation Stage 0 已可用，但只能提供只读市场环境。

## 账户与持仓事实状态

`stale_unverified`

已读取来源：`stock_team/config/positions.json`

- positions/account sync source：`ibkr_live_api`；
- positions/cash updated：2026-06-16；
- local record date：2026-06-16 18:53:03；
- 文件内 cash：8984.19；
- 文件内 net liquidation：46463.2；
- 缓存持仓数量：10；
- 部分单标的 `broker_snapshot_at` 停在 2026-05-26 或 2026-05-27；
- 因时间过期，以上数值只能作为核对线索，不能作为 2026-07-13 正式账户事实。

缓存符号：

- core/已有 thesis：NVDA、MSFT、GOOGL；
- tactical 或需要复核：VST、MUU、INTC、AXTX、SNXX、NBIS、AAOX；
- 多个 tactical 标的为 `needs_review` 或 `needs_classification`。

## 认知与组合输入

读取来源：

- `investing-os/cognition/self-model.md`；
- `investing-os/cognition/bias-map.md`；
- `investing-os/cognition/mistake-patterns.md`；
- `investing-os/decision/portfolio-thesis.md`；
- `investing-os/decision/risk-budget.md`；
- 最近 durable review：2026-06-08 market rebound cognition review、2026-06-05 major drawdown review。

当前仍应生效的主要约束：

- 信号不能代替 thesis；
- 禁止无计划短线入场；
- 禁止因亏损或部分恢复进行 repair/re-risk；
- 杠杆产品必须单独检查路径风险、持有期和最大损失；
- 低信念交易不得占用高信念注意力；
- 若账户事实未验证，只能观察和研究。

## 已知状态不一致

1. `portfolio-thesis.md` 状态日期为 2026-06-05，早于持仓缓存；
2. thesis 中列出的 COHR、ORCL 当前不在缓存持仓；
3. 缓存新增 MUU、AXTX、NBIS、AAOX 等标的，但 durable portfolio thesis 尚未给出完整角色；
4. SNXX 在 cognition/risk 文件中仍是 blocked pending review，但缓存仍显示持仓；
5. VST、MUU、INTC 等存在 needs_review/needs_classification，不能直接进入交易计划。

这些不一致应作为下一交易日 DAILY-0 的核对清单，不在本草稿中自行修正。

## 建议分析范围

第一层：市场环境代理

- QQQ、SPY、IWM、VIXY；

第二层：账户核对队列

- NVDA、MSFT、GOOGL；
- VST、MUU、INTC、AXTX、SNXX、NBIS、AAOX；

上述第二层不是已确认 focus pool，只是账户事实与角色核对范围。

## 建议禁止动作

- 任何真实下单或新风险；
- 将缓存持仓视为当前 IBKR 事实；
- loss-repair re-entry；
- 未写 thesis、invalidation、max loss 和 attention budget 的短线动作；
- 未复核角色的 tactical 标的加仓；
- 将 yfinance daily history 当作正式盘前报价；
- 在用户确认前生成正式 trading plan。

## 下一交易日确认清单

用户只需确认或修正：

1. 是否继续使用 observation 模式；
2. 当前真实持仓和现金是否与缓存一致；
3. 哪些缓存标的已清仓、新增或数量变化；
4. 是否同意上述分析范围和禁止动作；
5. 确认后才创建 2026-07-13 ET session 并运行 observation Stage 0。
