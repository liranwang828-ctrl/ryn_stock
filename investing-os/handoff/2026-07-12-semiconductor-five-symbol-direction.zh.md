# 2026-07-12 AMAT / TSM / MU / COHR / NBIS 方向研究

> observation-only；账户事实和实际持仓未核对。本文件定义研究状态与证据门槛，不定义仓位或订单。

## 决策摘要

| Symbol | 当前状态 | 结论 |
|---|---|---|
| TSM | `event_wait / build_candidate` | 高质量候选，等待 7 月 16 日 Q2 财报后验证，不在财报前追建 |
| AMAT | `pullback_wait / build_candidate` | 基本面强，但近月涨幅和波动较大，等待 CPI、TSM 财报和价格稳定 |
| MU | `thesis_intact / hold_no_add` | AI memory 事实强，但价格处于高波动消化期；若已持有普通股，暂不补仓 |
| COHR | `risk_review / no_add` | datacenter 基本面仍强，但相对价格结构破坏；禁止 repair averaging down |
| NBIS | `observation_only` | 高增长、高资本需求、高融资/稀释风险；暂不升级为建仓候选 |

## 价格结构（yfinance，截至 2026-07-10）

| Symbol | Close | 5D | 20D | vs MA20 | vs MA50 | 20D avg range |
|---|---:|---:|---:|---:|---:|---:|
| AMAT | 602.50 | -0.09% | +21.22% | -1.02% | +18.57% | 6.37% |
| TSM | 434.11 | -0.01% | +6.20% | -1.59% | +2.40% | 3.79% |
| MU | 979.30 | +0.38% | +9.80% | -7.05% | +8.93% | 7.32% |
| COHR | 324.50 | -2.66% | -8.53% | -12.38% | -11.92% | 9.20% |
| NBIS | 219.65 | +1.87% | +3.76% | -10.45% | -0.83% | 10.89% |

这些价格仅用于结构观察，不是下单价。

## TSM：第一优先候选，但等财报

TSMC 将于 7 月 16 日发布 Q2 结果。公司此前给出的 Q2 指引：

- revenue：390–402 亿美元；
- gross margin：65.5%–67.5%；
- operating margin：56.5%–58.5%。

来源：https://investor.tsmc.com/english/quarterly-results/2026/q2

候选成立条件：

1. 实际收入与毛利率至少接近指引；
2. AI/HPC 与先进制程需求继续支撑；
3. 海外 fab、2nm ramp 和能源/材料成本没有显著恶化利润率；
4. 财报后不是高开低走式预期兑现；
5. CPI/PPI 后长端利率没有进一步压制成长估值。

处理：财报前保持 `event_wait`。若事实与价格共同确认，再讨论分批建仓；如果财报很好但股价持续走弱，先尊重价格中的预期差，不急着解释为便宜。

## AMAT：基本面强，但不追扩张后的估值

Applied Materials Q2 2026：

- record revenue 79.1 亿美元，同比增长 11%；
- non-GAAP gross margin 50.0%；
- non-GAAP EPS 2.86 美元，同比增长 20%；
- 公司预计 2026 年 semiconductor equipment business 增长超过 30%；
- Q3 revenue 指引 89.5 亿美元 ± 5 亿美元。

来源：https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-second-quarter-2026-results

候选逻辑：

- AI 对先进制程、先进封装、DRAM/HBM 设备形成二阶价值捕获；
- AMAT 比单一芯片设计公司更接近全行业资本开支基础设施；
- TSMC/Micron 的 capex 与设备需求可交叉验证。

阻断：

- 20 日涨幅约 21%，但已从 20 日高点明显回落；
- 20 日平均日内区间约 6.4%，并非低波动核心建仓环境；
- 当前估值和预期扩张后，不适合因一日强势追入。

处理：列入 `build_candidate`，但等待 TSM 财报验证客户 capex，并等待价格在 MA20 附近稳定或形成新的低风险结构。

## MU：普通股 thesis 较强，执行上暂不加仓

Micron Q3 FY2026 官方结果显示 record revenue，且 HBM4 已进入量产出货，HBM4E 开发推进。公司给出更强 Q4 指引，表明 AI memory 需求仍强。

来源：https://investors.micron.com/node/50671

但价格状态显示：

- 20 日仍上涨约 9.8%；
- 当前低于 MA20 约 7%；
- 20 日平均日内区间约 7.3%；
- 说明基本面强与价格消化并存。

处理：

- 如果指的是 `MU` 普通股且已经持有：`hold_no_add`，等待价格重新稳定及 TSM/ASML 交叉验证；
- 如果尚未持有：暂不与 TSM/AMAT 同时新建多个高度相关仓位；
- 如果实际持有的是 `MUU`：必须单独按杠杆工具处理，不能用 MU 长期 thesis 为 MUU 的路径风险辩护。

## COHR：公司事实尚可，价格结构要求停止补仓

Coherent Q3 FY2026：

- revenue 18.1 亿美元，同比增长 21%；
- non-GAAP gross margin 39.6%；
- non-GAAP EPS 1.41 美元；
- 公司称 datacenter 与 communications demand 强，正在扩张产能。

来源：https://www.coherent.com/news/press-releases/third-quarter-fiscal-year-2026-results

但价格结构明显弱于半导体指数：

- 5 日 -2.66%，20 日 -8.53%；
- 低于 MA20/MA50 约 12%；
- 日内波动约 9.2%。

这意味着“AI optical thesis”与“当前股票执行质量”必须分开。

处理：

- 不补仓，不做成本修复；
- 若已有仓位，先核对仓位大小、原 thesis、失效条件和注意力成本；
- 只有在 COHR 对 SMH/SOXX 恢复相对强度、价格重新建立趋势且下一季产能扩张转为收入/利润时，才重新讨论加仓；
- 公司基本面好不能覆盖价格连续弱势这一事实。

## NBIS：观察 AI cloud 扩张质量，不观察股价故事

Nebius Q1 2026 显示 AI cloud 增长和 EBITDA 改善，但 Q1 capex 约 25 亿美元；公司同时讨论近期筹集数十亿美元级债务、ATM 和其他融资来源。

来源：

- https://nebius.com/newsroom/nebius-reports-first-quarter-2026-financial-results
- https://assets.nebius.com/assets/6aba98d1-946c-4891-a420-d2f0aa60da95/Nebius%20SHL_Q1%202026.pdf

观察清单：

1. 已投运 MW 与签约 MW，而非仅公布规划容量；
2. revenue/ARR 是否按期转化；
3. AI cloud EBITDA margin 是否能覆盖集团成本；
4. capex 与自由现金流缺口；
5. 债务成本、ATM 使用和潜在稀释；
6. 客户集中度与预付款质量；
7. GPU 供给、电力和数据中心上线进度；
8. 同类公司价格变化是否造成无关的 sympathy move。

处理：保持 `observation_only`。当前平均波动极高且低于 MA20，不能把高增长叙事直接转换为建仓。

## 相关性与组合约束

AMAT、TSM、MU、COHR、NBIS 都不同程度暴露于 AI capex。它们不是五个独立方向：

- TSM：先进制程制造；
- AMAT：设备/材料工程；
- MU：memory/HBM；
- COHR：optical interconnect；
- NBIS：AI cloud/operator。

同时建立多个仓位会形成同一 AI capex cycle 的隐性集中。因此优先级应是：

1. TSM 财报验证产业需求；
2. AMAT 作为设备二阶价值候选；
3. MU 若已持有则不再叠加；
4. COHR 先处理风险与趋势；
5. NBIS 只观察经营兑现。

## 下周动作顺序

### 周一至周二

- 不建仓；
- 等 CPI/PPI 和利率反应；
- 建立五标的相对强弱基线。

### 周三

- 阅读 ASML/设备链信息；
- 观察 AMAT 是否相对 SMH/SOXX 稳定；
- 不因行业财报跳空追价。

### 周四 TSM 财报后

- 按收入、毛利率、capex、AI/HPC、海外 fab 稀释逐项复核；
- 等第一轮价格反应稳定后，再决定 TSM 是否升级为 `build_approved_candidate`；
- 用 TSM 结果同步修正 AMAT、MU、COHR 的行业判断。

## 当前最终分类

- `TSM`: first-priority build candidate, event wait；
- `AMAT`: second-priority build candidate, pullback/confirmation wait；
- `MU`: thesis intact, hold/no add if owned；
- `COHR`: risk review, no averaging down；
- `NBIS`: observation only, financing and execution watch。
