# 数据覆盖度审计

> 最后更新：2026-05-17 | 基于 MRVL 实测

---

## Tier 1 — yfinance 完全可用（直接 .info 字段）

这些字段**必须**从 yfinance 获取，不得估算或编造：

| 字段 | yfinance key | 备注 |
|------|-------------|------|
| 分析师目标价均值 | `targetMeanPrice` | ⚠️ 关键：常低于/高于现价，必须对比 |
| 分析师评级均值 | `recommendationMean` | 1=强买 2=买 3=持有 4=卖 5=强卖 |
| 分析师覆盖数 | `numberOfAnalystOpinions` | 评级可信度依据 |
| 远期PE | `forwardPE` | 比市盈率(TTM)更重要 |
| 远期EPS | `forwardEps` | 用于验证增速假设 |
| 自由现金流 | `freeCashflow` | 判断盈利质量 |
| 营收(TTM) | `totalRevenue` | |
| 毛利率 | `grossMargins` | |
| 净利率 | `profitMargins` | |
| ROE | `returnOnEquity` | |
| 负债率 | `debtToEquity` | |
| 现金 | `totalCash` | |
| 空头占比 | `shortPercentOfFloat` | <3%=低 3-10%=中 >10%=高 |
| 内部人持股比 | `heldPercentInsiders` | 下降是负面信号 |
| 机构持股比 | `heldPercentInstitutions` | |
| 贝塔 | `beta` | 判断下跌放大倍数 |
| 盈利增速(YoY) | `earningsGrowth` | |
| 营收增速(YoY) | `revenueGrowth` | |
| PEG | `pegRatio` | <1=便宜 >2=贵 |
| 52周高/低 | `fiftyTwoWeekHigh/Low` | |

**获取方式**：
```python
import yfinance as yf
info = yf.Ticker(sym).info
target = info.get('targetMeanPrice')  # 不要用 info['targetMeanPrice']（可能 KeyError）
```

---

## Tier 2 — yfinance 可计算（需处理财务报表）

| 数据 | 获取方式 | 可信度 |
|------|---------|-------|
| 季度营收 YoY 增速 | `quarterly_financials.loc['Total Revenue']` | 高 |
| 内部人交易记录 | `insider_transactions` | 高（有日期/数量）|
| 机构持仓前10 | `institutional_holders` | 中（季度延迟）|

---

## Tier 3 — 需要 WebSearch 补充

这些数据 yfinance 没有，用 WebSearch 获取，**必须标注信息时效**：

| 数据 | 搜索关键词 | 重要性 |
|------|-----------|-------|
| **分部营收占比** | `"{sym} segment revenue breakdown Q{n} {year}"` | ⭐⭐⭐ 最重要缺口 |
| 短线空头趋势 | `"{sym} short interest trend"` | ⭐⭐ |
| 期权 P/C 比率 | `"{sym} put call ratio options flow"` | ⭐⭐ |
| 最新财报 beat/miss | `"{sym} earnings surprise Q{n}"` | ⭐⭐ |
| 主要客户依赖度 | `"{sym} major customers revenue concentration"` | ⭐⭐⭐ |

---

## Tier 4 — 当前无法获取

| 数据 | 原因 | 影响 |
|------|------|------|
| 实时期权流向（dark pool）| 需付费数据源 | 分析依赖公开信息，标注局限 |
| 13F 实时机构仓位变化 | 季度延迟 45 天 | 用内部人交易作代理 |
| 分析师个别报告原文 | 付费墙 | 用 recommendationMean 聚合值代替 |

---

## 数据完备度标准输出格式

每次分析必须在开头声明：

```
【数据完备度】
✅ 价格/技术（yfinance 实时）
✅ 基本面（yfinance info: PE/FCF/分析师目标/增速）
✅ 宏观（findings/macro.json）
⚠️ 分部营收（WebSearch，时效可能有限）
❌ 期权流向（未获取，分析忽略此维度）
```

---

## 使用规则

1. Tier 1 数据**必须**通过代码获取，不得估算
2. Tier 3 数据获取后**必须**标注来源和日期
3. Tier 4 数据**不得**假设具体数值，只能说"未获取"
4. 分析师目标价必须和现价对比（高于/低于/偏差%），不能只列数字
