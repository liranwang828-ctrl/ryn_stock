# 2026-07-13 AMAT / TSM 入场与 MU / COHR 处理研究

> 状态：observation / decision-support。stock_team 使用 yfinance 只读数据，最近有效收盘为 2026-07-10 ET；账户实际仓位、成本和工具类型未确认，因此不构成正式交易许可或个性化订单。

## 结论摘要

| 标的 | 当前权限 | 核心结论 |
|---|---|---|
| TSM | `event_wait` | 四者中第一建仓候选，但 CPI/PPI 与 7 月 16 日财报前不抢跑；优先等待财报后确认 |
| AMAT | `pullback_or_reclaim_wait` | 基本面强但波动极高；用 TSM 财报验证 capex Reality，等待回踩稳定或重新站稳 MA20 |
| MU | `hold_no_add`（若为普通股且已持有） | Reality 强、Price 在高波动消化；不补仓修复，先等价格重新确认 |
| COHR | `risk_review / no_add` | 公司事实尚未证伪，但价格显著弱于行业；反弹不能自动当成 thesis 修复 |

## stock_team 价格证据

数据源：yfinance adjusted daily history；截至 2026-07-10 ET，仅用于观察。

| 标的 | Close | MA20 | MA50 | ATR14 | ATR% | 近期结构 |
|---|---:|---:|---:|---:|---:|---|
| AMAT | 602.50 | 608.72 | 507.99 | 54.12 | 8.98% | 20D +21.2%，近期低点 527.63，高波动回撤 |
| TSM | 434.11 | 441.11 | 423.37 | 21.29 | 4.90% | 位于 MA20 下、MA50 上，近期支撑 419–428 |
| MU | 979.30 | 1053.44 | 898.92 | 98.19 | 10.03% | 低于 MA20、高于 MA50，近期低点 891.66 |
| COHR | 324.50 | 370.35 | 368.40 | 34.48 | 10.63% | 同时低于 MA20/MA50，近期低点 304.07 |

环境证据：QQQ 仍在 MA20/MA50 上方，但 SMH/SOXX 已在 MA20 下；10Y proxy 约 4.57，高于其 MA20/MA50。成长指数尚未破坏，但半导体与利率环境没有给出低风险同步确认。

## Investing-OS 认知拆解

### Reality

- TSM：先进制程、AI/HPC、2nm、毛利率和 capex 是本周最重要的产业事实验证器；
- AMAT：AI 对先进逻辑、DRAM/HBM、先进封装设备需求的二阶价值捕获仍强；
- MU：HBM4 已高量出货、Q3 结果和 Q4 指引强，memory Reality 尚未被价格回撤证伪；
- COHR：datacenter/communications 需求、收入和毛利改善仍成立，但产能扩张能否持续转成利润仍需验证。

### Consensus

四只股票的共同 Consensus 已经包含较强 AI capex 预期，因此“基本面好”本身不够。TSM 财报的关键不是 beat，而是实际值、指引与市场已计价程度之间的差；AMAT、MU、COHR 都会受到该解释的交叉影响。

### Price

- TSM 价格结构相对最好，波动也最低；
- AMAT 20 日涨幅大但从高点剧烈回撤，说明预期与获利兑现同时存在；
- MU 的 Reality 很强，但 Price 未重新站回 MA20；
- COHR 明显弱于行业，Price 正在表达兑现/执行疑虑，不能用长期主题覆盖。

## TSM：入场计划候选

### 事件约束

7 月 14 日 CPI、7 月 15 日 PPI、7 月 16 日 TSM Q2 财报形成连续事件窗口。正式建议是不在财报前建立完整仓位。

### 路径一：回踩型候选

- 观察区间：419–428；
- 条件：财报事实未破坏 thesis，利率不继续上冲，价格在该区间停止扩大跌幅并重新收回 428 附近；
- 含义：用近期低点与 MA50 附近获得较好风险收益，而不是见到区间即自动买入；
- 失效观察：约 409 下方仍无法快速收回，则暂停建仓并重审财报解释。

### 路径二：确认型候选

- 确认区间：重新站稳 441–452；
- 条件：财报后至少经过第一轮价格发现，TSM 相对 SMH/SOXX 保持强势，且不是高开低走；
- 含义：价格稍高，但 Reality、Consensus 与 Price 的一致性更好。

### 禁止

- 财报前因“怕踏空”抢跑；
- 财报首个跳空直接追入；
- 只因回到 419–428 就忽略财报或利率变化。

## AMAT：入场计划候选

AMAT Q2 官方结果为 record revenue 79.1 亿美元，公司预计 2026 年 semiconductor equipment business 增长超过 30%，但当前价格波动约为日均 9%，不能用窄止损或单点买入处理。

### 路径一：回踩稳定型

- 观察区间：550–580；
- 条件：CPI/PPI 与 TSM 财报没有破坏客户 capex Reality，AMAT 在区间内形成收缩波动并恢复相对 SMH 强度；
- 风险复核线：近期低点约 528；若有效跌破且不能收回，不把更低价格自动解释为更高胜率。

### 路径二：重新确认型

- 确认条件：重新站稳约 609 的 MA20，并突破/消化 629–630 附近近期阻力；
- 条件：量价不是单日新闻跳空，且 TSM 财报支持先进制程/封装 capex；
- 含义：牺牲部分价格，换取趋势重新确认。

### 禁止

- 在 630 上方的事件跳空中追价；
- 把 20 日上涨后的大幅回撤只解释成便宜；
- 同时新建 TSM、AMAT、MU 等多个同源风险的完整仓位。

## MU：处理建议

### 若持有 MU 普通股

- 当前：`hold_no_add`；
- 不加仓原因：ATR 约 10%，仍低于 MA20 1053，价格尚未证明消化结束；
- 正向确认：先稳定在 950–1000 上方，再观察能否重新站回约 1050；
- 风险复核：若有效跌破 891–900 且不能收回，应重新审视仓位大小与 Price 所表达的周期/预期风险，而不是立即补仓；
- TSM 财报用于验证 AI/HPC 与 capex，但不能代替 memory 自身供需证据。

### 若持有 MUU 或其他杠杆工具

必须与 MU thesis 分开处理。事件窗口、10% 左右标的日波动与杠杆路径叠加，不适合用长期 HBM thesis 为短期工具风险辩护；在未核对工具和仓位前不授予持有/加仓权限。

## COHR：处理建议

- 当前：`risk_review / no_add`；
- 304 附近是近期风险观察线；有效跌破后不能快速收回，优先降低脆弱性或重审，而不是摊低成本；
- 330–340 只是第一层修复；反弹到该区域不代表趋势恢复；
- 只有重新站稳 368–370（MA20/MA50）并恢复对 SMH/SOXX 的相对强度，才允许讨论从风险处理升级为持有确认；
- 若反弹至 340–370 但量价和行业相对强度没有改善，应把它视为风险处理窗口，而非新的加仓理由。

## 组合约束

TSM、AMAT、MU、COHR 并非四个独立押注，均暴露于 AI capex、半导体周期和成长估值。执行顺序建议：

1. 先等 CPI/PPI；
2. 用 TSM 财报更新产业 Reality；
3. TSM 与 AMAT 最多先选择一个作为首个新建候选；
4. MU 若已持有，计入同一风险桶，不再无视相关性叠加；
5. COHR 先解决风险状态，不能与新建仓讨论混在一起。

## 本周对话触发点

- CPI/PPI 后：记录数据、2Y/10Y、美元、QQQ/SMH 解释；第一跳不行动；
- TSM 财报后：逐项填写 revenue、gross margin、operating margin、capex、AI/HPC、2nm 与海外 fab；
- 随后才把 TSM/AMAT 标记为 `entry_candidate`、`continue_wait` 或 `thesis_review`；
- MU/COHR 在账户事实未确认前只给条件式处理，不产生订单。

## 官方来源

- TSMC Q2 2026 earnings/guidance：https://investor.tsmc.com/english/quarterly-results/2026/q2
- Applied Materials Q2 2026：https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-second-quarter-2026-results
- Micron Q3 2026：https://investors.micron.com/node/50671
- Coherent Q3 FY2026：https://www.coherent.com/news/press-releases/third-quarter-fiscal-year-2026-results
- BLS July 2026 schedule：https://www.bls.gov/schedule/2026/07_sched.htm

