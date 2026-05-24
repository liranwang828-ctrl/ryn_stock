# Memo 更新内容 → 盘前报告 → 盘中策略 数据流设计

**记录时间**: 2026-05-20

---

## 一、strategic_memo 新增/更新字段汇总

### 本轮新增字段
| 字段 | 内容 | 是否已生效 |
|---|---|---|
| `support_and_risk.derived_falsification[]` | 从 key_risks/bear_case/财务指标自动推导的证伪条件列表 | ✅ memo 内 |
| `support_and_risk.core_supporting_facts[]` | 从 moat/growth_drivers/FCF/ROE 丰富的支撑论据 | ✅ memo 内 |
| `position_context.add_strategy` | T2加仓条件（论点类型/触发价/分批逻辑）| ✅ memo 内 |
| `position_context.reduce_strategy` | 减仓策略（目标价/Flex减仓价/硬止损/时间止损）| ✅ memo 内 |
| `position_context.position_snapshot` | 成本/持仓量/浮盈/GTC状态/持仓天数 | ✅ memo 内 |
| `agent_analysis.{tech/fund/macro/risk/sentiment/sector}` | 六维度完整分析文本 | ✅ memo 内 |
| `debate_highlights` | 辩论轮次/关键分歧/综合结论 | ✅ memo 内 |
| `scenarios.{bull/base/bear}` | 三情景价格目标和触发条件 | ✅ memo 内 |
| `outlook.exit_logic` | 基于分析师目标+证伪条件的出场逻辑（已改为客观锚点）| ✅ memo 内 |
| `fundamentals_snapshot` | 扩充至 18 字段：毛利/运营利润/ROE/n_analysts/rec_key/sector 等 | ✅ memo 内 |

---

## 二、哪些字段可以直接作用于 premarket_summary

### premarket_summary.strategic_context（Full 模式已读 memo，但字段不完整）

**当前已读**：strategic_stance / unified_confidence / thesis_lifecycle / key_condition /
next_catalyst / main_tensions / macro_fit / technical_stage / binary_risk_flag / alignment_check

**待补充读取**（memo 有但 premarket_summary 没传递）：

| memo 字段 | 应写入 premarket_summary 字段 | 用途 |
|---|---|---|
| `derived_falsification[]` | `strategic_context.falsification_conditions` | 盘前让用户看到当天的证伪条件监控点 |
| `scenarios.base.price_target` | `entry.target_price` 覆盖（当前用 order_sheet 的，可能是旧值）| 更客观的目标价（基于分析师，非成本） |
| `scenarios.bear.price_target` | `exit.hard_stop` fallback（当 t1_stop_snapshot 为 None 时）| 自动填充合理止损 |
| `position_context.reduce_strategy.target_price` | `exit.target_price` 覆盖 | 基于分析师目标的减仓价 |
| `position_context.add_strategy.t2_price_floor` | `exit.flex_add_level` 补充（当 order_sheet 没有时）| T2 加仓触发价 |
| `agent_analysis.risk.key_points` | `stock_snapshot.risk_note` 丰富 | 当日风险提示更具体 |
| `unified_confidence` | `entry.sizing`（已用，但来源简单）| sizing 规则更精准 |

### premarket_summary.entry（当前从 entry_decision 读）

**待补充**：
- `strategic_context.falsification_conditions` → 盘前清单用于当日论点保护检查
- `position_context.add_strategy.sizing_note` → 加仓说明

### premarket_summary.exit（当前从 exit_decision + order_sheet 读）

**待补充**：
- `scenarios.bear.price_target` → 自动提供 hard_stop 候选（无 GTC 时）
- `scenarios.base.price_target` → 目标价（更客观）
- `derived_falsification[0..1]` → today_falsification（今日要监控的证伪条件）

---

## 三、premarket → 盘中策略（intraday_snapshot）数据流

### 已有的传递（✅ 已实现）
- `premarket_summary.exit.hard_stop` → `plan_vs_now.dist_to_stop_pct`
- `premarket_summary.exit.target_price` → `plan_vs_now.dist_to_target_pct`
- `premarket_summary.exit.flex_add_level` → `plan_vs_now.dist_to_flex_add_pct`
- `premarket_summary.thesis.today_falsification` → `plan_vs_now.thesis_signal` 规则

### 待实现的传递（❌ 有数据但未串联）

| premarket 字段（源自 memo）| 盘中用途 | 触发机制 |
|---|---|---|
| `strategic_context.falsification_conditions[]` | 盘中监控：当某条件接近触发时，自动升级为 ⚠️ 告警 | 在 `compute_thesis_signal()` 里加一条规则：key_risk 关键词出现在新闻 → warning |
| `scenarios.bear.price_target` | 熊市情景价格作为次级止损线（soft_stop 补充）| 写入 `plan_vs_now.dist_to_bear_scenario_pct` |
| `position_context.reduce_strategy.target_price` | 目标价改为客观值 → dist_to_target 更准确 | 覆盖 `plan_vs_now.dist_to_target_pct` |
| `agent_analysis.risk.key_points` | 盘中新闻触碰 key_risks 关键词 → `risk_flag=True` | 在 `intraday_snapshot.write_snapshot_entry` 里加关键词匹配 |
| `derived_falsification[]` | 每轮 poll 检查证伪条件是否逼近 → `thesis_signal=warning` | 新增 `check_falsification_proximity()` 函数 |

---

## 四、实施优先级

### P0（直接影响盘中决策质量）
1. **`scenarios.bear.price_target` → `exit.hard_stop` fallback**：当 positions.json 没有 t1_stop_snapshot 时，用熊市情景价格作为止损（NVDA: $184×0.87=$160 或分析师保守目标$140附近）
2. **`scenarios.base.price_target` → `exit.target_price` 覆盖**：目标价用分析师目标$275 而非成本价推算

### P1（丰富盘中监控）
3. **`derived_falsification[]` → 盘中关键词监控**：每条证伪条件转为关键词，新闻触碰时提升 thesis_signal 级别
4. **持仓策略改为技术位**：T2条件基于 MA50/近期低点，不用 cost×0.92

### P2（报告质量提升）
5. **premarket_summary Full 模式补读 derived_falsification**：让盘前报告展示当日需监控的证伪条件
6. **支撑论据替换**：把 [Tech] key_points 换成 company_profile.competitive_moat

---

## 五、下次恢复时说
"继续研究报告和数据流优化，从 scenarios.bear → hard_stop fallback 开始"
