# Skill 格式标准化：portfolio-health — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 portfolio-health skill 的输出契约，即 `portfolio_snapshot_{date}.json`（每日）和 `portfolio_weekly_{year}W{week}.json`（每周）的完整 schema、触发机制、警告规则、再平衡建议结构

---

## 背景

`portfolio_risk_agent.py` 已能计算总敞口、杠杆比率、VaR、板块集中度、相关性矩阵，但输出为非结构化文本，无法被 dashboard 或其他 skill 读取。

**目标**：建立结构化的组合健康输出，支持每日自动快照、每周深度周报、按需查询，并通过再平衡建议闭环到 positions.json 更新。

---

## 架构决策

| 决策 | 结论 |
|---|---|
| 触发来源 | A 按需 + B 每周一盘前 + C 每日收盘后（postmarket 流程内）|
| 文件结构 | `portfolio_snapshot_{date}.json`（轻量日快照）+ `portfolio_weekly_{year}W{week}.json`（深度周报）|
| 建议机制 | 同 postmarket：semi-auto，confirmed → suggestion_applier.py 写回源文件 |
| dashboard | 总览 Tab（警告/板块/相关性）+ 周报 Tab（绩效/建议）|

---

## portfolio_snapshot_{date}.json

### 顶层结构

```json
{
  "date":                 "YYYY-MM-DD",
  "generated_at":         "ISO-timestamp",
  "trigger":              "daily_auto | on_demand | weekly_sub",
  "positions_detail":     [ ... ],
  "totals":               { ... },
  "sector":               { ... },
  "correlation":          { ... },
  "strategic_alignment":  { ... },
  "warnings":             [ ... ]
}
```

---

### positions_detail[]（B 级，每股一条）

```json
{
  "sym":                "string",
  "underlying":         "string",        // 杠杆 ETF 对应底层标的
  "leverage":           int,             // 杠杆倍数，非杠杆为 1
  "shares":             int,
  "cost":               float,
  "cur_price":          float,
  "market_value":       float,           // cur_price × shares
  "net_exposure":       float,           // market_value × leverage
  "unrealized_pnl_pct": float,           // (cur_price - cost) / cost × 100
  "beta":               float,
  "var_5pct_loss":      float,           // net_exposure × beta × 0.05
  "dist_to_stop_pct":   float | null,    // (cur_price - hard_stop) / cur_price × 100
  "dist_to_target_pct": float | null,    // (target - cur_price) / cur_price × 100
  "thesis_status":      "intact | weakening | broken | null",
  "days_held":          int
}
```

数据来源：
- `cost / shares`：`positions.json`
- `cur_price / beta`：yfinance（`portfolio_risk_agent._fetch_current_price / _fetch_beta`）
- `hard_stop`：优先读 `findings/exit_decision_{today}.json.positions[sym].hard_stop`；不存在时 null
- `target`：优先读 `findings/order_sheet_{today}.json.symbols[sym].target_price`；不存在时 null
- `thesis_status`：`positions.json.positions[sym].thesis_status`
- `days_held`：今日日期 − `positions.json.positions[sym].date`（positions.json 的日期字段名为 `date`）

**跨 spec 依赖说明**：本 spec 假设以下文件在实施时已按对应 spec 生成。过渡期（文件不存在时）相关字段置 null：
- `exit_decision_{date}.json`：由 premarket_exit_sheet.py 生成（已有）
- `postmarket_summary_{date}_{sym}.json`：由 stock-postmarket spec 定义（待实施）

---

### totals（B 级）

```json
{
  "total_value":              float,   // Σ market_value
  "total_exposure":           float,   // Σ net_exposure
  "leverage_ratio":           float,   // total_exposure / total_value
  "var_5pct_loss":            float,   // Σ var_5pct_loss
  "var_5pct_pct":             float,   // var_5pct_loss / total_value × 100
  "total_unrealized_pnl_pct": float    // 持仓加权：Σ(unrealized_pnl_pct × market_value) / total_value
}
```

---

### sector（B 级）

```json
{
  "concentration":   {"Tech": 68.2, "Healthcare": 12.1},  // 按 net_exposure 加权
  "top_sector":      "string",
  "top_sector_pct":  float,
  "hhi":             float    // Herfindahl 集中度指数：Σ(pct/100)²；越高越集中；>0.25 为高度集中
}
```

---

### correlation（B 级）

```json
{
  "matrix":           {},        // {SYM: {SYM: float}}，基于底层标的 60 日日线
  "top_pair":         ["SYM1", "SYM2"],
  "top_pair_value":   float,
  "high_corr_count":  int        // 相关性 > 0.8 的持仓对数
}
```

---

### strategic_alignment（B 级）

```json
{
  "memo_expiry_alerts": [
    {
      "sym":         "string",
      "valid_until": "YYYY-MM-DD | next_earnings | null",
      "days_left":   int | null
    }
  ],
  "stance_misalign": [
    {
      "sym":               "string",
      "strategic_stance":  "reduce | exit_ready | avoid",
      "current_situation": "still_holding | adding",
      "note":              "string ≤50字"
    }
  ]
}
```

数据来源：`strategic_memo_{sym}.json`（若不存在则跳过该股）

**`stance_misalign` 触发规则**：
```
strategic_stance ∈ {reduce, exit_ready, avoid}
AND thesis_status ∈ {intact, weakening}（仍持有）
→ 标记为不一致
```

---

### warnings[]（B 级，规则驱动）

```json
[{"level": "high | medium | low", "code": "string", "msg": "string ≤60字"}]
```

**触发规则**（优先级从高到低）：

| 条件 | level | code | msg |
|---|---|---|---|
| `leverage_ratio > 2.5` | high | `leverage_excess` | 总杠杆 {ratio}x 超过 2.5x 安全线 |
| `top_sector_pct > 70` | high | `sector_concentrated` | {sector} 板块占比 {pct}%，集中度过高 |
| 任一 `dist_to_stop_pct < 3` | high | `approaching_stop` | {sym} 距硬止损仅 {dist}%，需关注 |
| `top_pair_value > 0.85` | medium | `high_correlation` | {SYM1}/{SYM2} 相关性 {corr}，实际敞口被低估 |
| 任一 `memo days_left < 7` | medium | `memo_expiring` | {sym} strategic_memo 还剩 {n} 天有效期 |
| 任一 `stance_misalign` | medium | `stance_mismatch` | {sym} 战略建议 {stance} 但仍持有 |
| `leverage_ratio > 2.0` | low | `leverage_warning` | 总杠杆 {ratio}x，建议关注 |
| `hhi > 0.25` | low | `hhi_high` | HHI={hhi:.2f}，组合集中度偏高 |

---

## portfolio_weekly_{year}W{week}.json

在 `portfolio_snapshot` 所有字段基础上追加以下字段（`trigger` 固定为 `"weekly"`）：

### week_performance[]

```json
{
  "sym":          "string",
  "week_open":    float,
  "week_close":   float,
  "week_ret_pct": float,
  "vs_target":    "above | at | below",   // at = 距目标 ±2% 以内
  "vs_stop":      "safe | warning | breached",  // warning = dist_to_stop < 5%
  "plan_followed": "yes | partial | no | na"
}
```

---

### thesis_changes[]

```json
{
  "sym":   "string",
  "from":  "intact | weakening | broken",
  "to":    "intact | weakening | broken",
  "date":  "YYYY-MM-DD"
}
```

数据来源：读取本周各日 `postmarket_summary_{date}_{sym}.json` 的 `snapshot_thesis_status` 字段（各日收盘时的 thesis_status 快照），对比相邻日发现变化。

**跨 spec 依赖**：需要在 stock-postmarket spec 的 per-stock schema 中追加 `snapshot_thesis_status: "intact | weakening | broken"` 字段（收盘时 positions.json 的快照值）。文件不存在时 `thesis_changes` 置 `[]`。

---

### signal_accuracy_week（B 级）

```json
{
  "master_accuracy":  {"Minervini": 0.6, "Druckenmiller": 0.4},   // 本周命中率
  "scene_accuracy":   {"B": 0.7, "D": 0.3},                       // 本周各场景胜率
  "gate_accuracy":    float,                                        // 门控通过 → 实际正向
  "sample_size":      int                                           // 本周有效信号条数
}
```

数据来源：读取本周各日 `postmarket_summary_{date}_{sym}.json`（stock-postmarket spec 定义的文件）的 `signal_accuracy` 字段聚合。文件不存在时该字段整体置 null，不阻断周报生成。

---

### exposure_trend（B 级）

```json
{
  "leverage_ratio_prev": float,
  "leverage_ratio_curr": float,
  "total_exposure_prev": float,
  "total_exposure_curr": float,
  "exposure_chg_pct":    float    // (curr - prev) / prev × 100
}
```

数据来源：读取上周 `portfolio_weekly_{year}W{prev_week}.json` 的 `totals`。**首周 fallback**：上周文件不存在时，`leverage_ratio_prev / total_exposure_prev` 置 null，`exposure_chg_pct` 置 null，不阻断周报生成。

---

### rebalancing_suggestions[]

同 postmarket 建议结构，`type` 枚举限定为组合层操作：

```json
{
  "type":           "reduce_leverage | diversify_sector | reduce_position | trigger_deep_research | memo_refresh",
  "priority":       "high | medium | low",
  "description":    "string ≤80字",
  "proposed_value": {},
  "confirmed":      null,
  "applied_at":     "ISO-timestamp | null",
  "applied_to": {
    "file":      "positions.json | config/rerun_queue.json | null",
    "field":     "string | null",
    "old_value": {},
    "new_value": {}
  }
}
```

**`proposed_value` 各类型格式**：

| type | proposed_value 结构 |
|---|---|
| `reduce_leverage` | `{"target_ratio": float, "note": "string"}` |
| `diversify_sector` | `{"overweight_sector": "string", "overweight_pct": float}` |
| `reduce_position` | `{"sym": "string", "reduce_pct": int}` |
| `trigger_deep_research` | `{"sym": "string", "reason": "string ≤60字"}` |
| `memo_refresh` | `{"sym": "string", "days_left": int}` |

**建议自动生成规则**（规则驱动，非 LLM）：

| 触发条件 | type | priority |
|---|---|---|
| `leverage_ratio > 2.5` | `reduce_leverage` | high |
| `top_sector_pct > 70%` | `diversify_sector` | high |
| 任一 `dist_to_stop_pct < 3%` | `reduce_position` | high |
| `top_pair_value > 0.85` | `reduce_position`（相关性最高的一方）| medium |
| 任一 `memo days_left < 7` | `memo_refresh` | medium |
| 任一 `stance_misalign` | `reduce_position` | medium |
| `leverage_ratio > 2.0` | `reduce_leverage` | low |

---

### llm_summary（A 级）

```json
"llm_summary": "string ≤400字"   // Claude API 生成，读取本文件 B 级字段后输出叙述性周报
```

---

## 生成流程

```
每日 16:00（postmarket 流程末尾）：
  → portfolio_risk_agent.compute_portfolio_risk()
  → 补充 dist_to_stop/target、thesis_status、days_held
  → 检查 strategic_alignment（读 strategic_memo）
  → 生成 warnings（规则驱动）
  → 写出 portfolio_snapshot_{date}.json（trigger="daily_auto"）

每周一 9:00（premarket 之前）：
  → 读取 portfolio_snapshot_{today}.json 作为基础
  → 聚合本周各日 postmarket_summary → signal_accuracy_week / thesis_changes
  → 读取上周 portfolio_weekly → exposure_trend
  → 规则生成 rebalancing_suggestions
  → Claude API 生成 llm_summary
  → 写出 portfolio_weekly_{year}W{week}.json

用户按需触发（"组合健康"）：
  → 读取最新 portfolio_snapshot（若当日无则实时计算）
  → 若时间为周一：一并读取 portfolio_weekly
  → LLM 叙述最新快照 + 补充按需洞察（不写新文件，dashboard 刷新）
```

---

## dashboard 字段映射

| 字段 | Tab |
|---|---|
| `totals` + `warnings` | 总览（组合健康区，high 警告显示角标）|
| `sector.concentration` | 总览（板块饼图）|
| `correlation.top_pair / high_corr_count` | 总览（相关性警示）|
| `positions_detail`（pnl / dist_to_stop）| 每股详情（持仓层）|
| `strategic_alignment` | 总览（战略对齐区）|
| `week_performance` | 周报 Tab |
| `signal_accuracy_week` | 周报 Tab（学习数据）|
| `rebalancing_suggestions[]`（confirmed=null）| 周报 Tab（待确认建议）|
| `llm_summary` | 周报 Tab（全文展示）|

---

## Out of Scope

- `portfolio_risk_agent.py` 的具体改造逻辑（属于实施计划）
- `suggestion_applier.py` 对 `reduce_position` 类型的具体操作逻辑（需用户确认减仓哪部分）
- 其他 skill 的格式标准化（后续 brainstorm）
- `daily_dashboard.html` 完整实现（独立 spec）
