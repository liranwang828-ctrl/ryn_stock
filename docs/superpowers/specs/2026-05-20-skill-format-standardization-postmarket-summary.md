# Skill 格式标准化：stock-postmarket 与 postmarket_summary — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 stock-postmarket skill 的输出契约，即 `postmarket_summary_{date}_{sym}.json`（每股）和 `postmarket_summary_{date}.json`（每日汇总）的完整 schema、生成时机、建议确认机制、源文件写回规范

---

## 背景

stock-postmarket skill 当前有两条主线：
1. `harvest_agent.py`：记录结果、验证大师准确率、处理 observation_log
2. `postmarket_review.py`：LLM 复盘讨论（手动触发）

两者输出互相独立，无统一格式，无法被 dashboard 或次日 premarket 系统性读取。

**目标**：建立结构化的 `postmarket_summary`，作为：
- 当日复盘的结构化输出（B 级）
- 次日盘前建议的来源（12 类建议 → 用户确认 → 写回源文件）
- dashboard 盘后复盘 Tab 的数据源

---

## 架构决策

| 决策 | 结论 |
|---|---|
| 文件粒度 | per-stock（`postmarket_summary_{date}_{sym}.json`）+ per-day 汇总（`postmarket_summary_{date}.json`）|
| 生成时机 | 16:00 ET 自动：harvest_agent.py + Claude API 生成草稿；用户说"复盘"时可继续深度讨论 |
| 学习反馈 | 半自动：postmarket 生成建议 → 用户确认 → `suggestion_applier.py` 写回源文件 |
| 确认时机 | 次日盘前 premarket skill 运行时提示"N 条待确认建议"，逐条处理 |
| 与 premarket 的关系 | **不直接读 postmarket_summary**；confirmed 建议写回 positions.json 等源文件，premarket 有机地读到 |

---

## per-stock schema：`postmarket_summary_{date}_{sym}.json`

```json
{
  "date":           "YYYY-MM-DD",
  "sym":            "string",
  "generated_at":   "ISO-timestamp",
  "execution":      { ... },
  "performance":    { ... },
  "signal_accuracy": { ... },
  "snapshot_thesis_status": "intact | weakening | broken | null",  // 收盘时 thesis_status 快照（供 portfolio_weekly thesis_changes 使用）
  "learning_notes": "string",     // A 级，LLM 生成，≤300字
  "next_day": {
    "suggestions":  [ ... ],      // 12 类建议列表
    "summary_note": "string"      // A 级，整体建议摘要，≤100字
  }
}
```

---

### execution（B 级）

```json
"execution": {
  "plan_entry_triggered":  true|false|null,  // 读 premarket_summary.post_open_adj.entry_go（bool）；null = post_open_adj 未写
  "actual_entry":          float | null,      // 实际入场价（来自 translator.py 记录）
  "plan_exit_triggered":   true|false|null,  // 止损/目标今日是否触发；读 intraday_snapshot 末条 plan_vs_now.thesis_signal == "breach"
  "actual_exit":           float | null,
  "followed_plan":         "yes | partial | no | na",
  "deviation_note":        "string ≤60字"    // A 级，偏差原因
}
```

---

### performance（B 级）

```json
"performance": {
  "open_price":      float,
  "close_price":     float,
  "day_ret_pct":     float,
  "vs_target_pct":   float,        // (close - target) / target × 100
  "vs_stop_pct":     float,        // (close - hard_stop) / close × 100
  "days_held":       int,          // 今日为持仓第几天
  "thesis_days":     int           // 论点建立至今天数（for 时间止损评估）
}
```

---

### signal_accuracy（B 级，全部规则推导）

```json
"signal_accuracy": {
  "pred_scene_correct":          true|false|null,   // pred_scene == actual_scene；null = actual_scene 未确认
  "actual_scene":                "A|B|C|D|E|F|G|H | null",
  "master_consensus_correct":    true|false|null,   // consensus=buy → day_ret_pct > 0；consensus=no_buy → day_ret_pct < 0
  "gate_correct":                true|false|null,   // gate 通过且 entry_go=true → day_ret_pct > 0
  "thesis_signal_correct":       true|false|null,   // thesis_signal=breach 当日是否确实大跌（day_ret_pct < -2%）
  "entry_go_outcome":            "profitable | break_even | loss | not_triggered | null"
}
```

**`actual_scene` 数据来源**：读 `premarket_summary.post_open_adj.scene_confirmed`（10:00 观察窗口确认的场景）。若 `scene_confirmed=null`（未确认），则 `actual_scene=null`，`pred_scene_correct=null`。不由 LLM 生成，保持 B 级。

**`total_day_ret_pct` 计算**：所有 signal_accuracy 字段均为纯规则推导，无需 LLM。

---

### next_day.suggestions[]

每条建议结构：

```json
{
  "type":           "enum（见下方12类）",
  "priority":       "high | medium | low",
  "description":    "string ≤80字",
  "proposed_value": {},                      // type 决定格式，见各类说明
  "confirmed":      null,                    // null=待确认 / true=接受 / false=拒绝
  "applied_at":     "ISO-timestamp | null",
  "applied_to": {                            // confirmed=true 后填写，用于追溯和回滚
    "file":         "positions.json | config/master_weights.json | ...",
    "field":        "positions.NVDA.node1",
    "old_value":    {},
    "new_value":    {}
  }
}
```

**12 类建议类型及 `proposed_value` 格式：**

| type | 触发条件 | proposed_value 格式 | 写回目标 |
|---|---|---|---|
| `thesis_status` | price 行为 / 新闻 影响论点 | `{"new_status": "weakening"}` | `positions.json.positions[sym].thesis_status` |
| `stop_move` | 价格上涨 + 利润足够锁定 | `{"new_stop": 219.0}` | `positions.json.positions[sym].node1` |
| `node_reset` | 今日高低点显著偏移盘前节点 | `{"flex_add": 198.0, "flex_reduce": 228.0}` | `positions.json.positions[sym].flex_override` |
| `trigger_deep_research` | 颠覆性新闻 / 持续亏损 | `{"reason": "string"}` | `config/rerun_queue.json`（追加） |
| `master_weight` | 某大师近5日准确率 < 45% | `{"master": "Druckenmiller", "delta": -0.1}` | `config/master_weights.json` |
| `scene_calibration` | pred_scene 近10日胜率 < 45% | `{"scene": "B", "sizing_adj": "-1_tier"}` | `config/scene_calibration.json` |
| `lesson_record` | 每日必有 | `{"lesson": "string ≤100字"}` | `trading_lessons.json`（追加） |
| `stage_alert` | 技术结构从 Stage 2 滑向 Stage 3/4 | `{"from": "2", "to": "3", "action": "reduce"}` | `positions.json.positions[sym].stage_override` |
| `correlation_warning` | 持仓间当日相关性 > 0.8 | `{"pair": ["NVDA", "NBIL"], "corr": 0.91}` | 展示型：`applied_to=null`；`confirmed=true` 表示"已知晓"，不写任何文件 |
| `thesis_confirmation` | 今日积极确认论点 | `{"signal": "string", "add_opportunity": true}` | 展示型：同上 |
| `time_stop_eval` | `thesis_days` 超过论点预期时间线 | `{"thesis_days": 22, "expected_days": 14}` | 展示型：同上 |
| `tomorrow_risk_calendar` | 明日有已知事件 | `{"events": ["NVDA earnings", "FOMC"]}` | `config/macro_events_tomorrow.json` |

---

## per-day schema：`postmarket_summary_{date}.json`

```json
{
  "date":         "YYYY-MM-DD",
  "generated_at": "ISO-timestamp",
  "symbols":      ["NVDA", "NBIL"],
  "portfolio": {
    "total_day_ret_pct":     float,   // 持仓加权：Σ(shares_i × open_price_i × day_ret_pct_i) / Σ(shares_i × open_price_i)；权重来自 positions.json.positions[sym].shares
    "best_performer":        "SYM | null",
    "worst_performer":       "SYM | null",
    "correlation_matrix":    {},             // {SYM: {SYM: float}}
    "max_correlation_pair":  ["SYM1", "SYM2"],
    "max_correlation_value": float,
    "concentration_risk":    "high | medium | low"
  },
  "tomorrow_risk_calendar": ["string"],      // 汇总所有标的的明日风险
  "pending_suggestions_count": int,          // 待确认建议总数
  "llm_review":   "string"                   // A 级，Claude API 生成复盘要点，≤500字
}
```

---

## 生成流程

```
16:00 ET（poll.py 检测市场关闭后触发）：
  Step 1: harvest_agent.py 自动跑
    → 记录 daily_harvest.jsonl
    → 更新 master_accuracy.json
    → 处理 observation_outcomes.jsonl
    → record_scene_development()

  Step 2: postmarket_data_collector.py（新建）
    → 读取 intraday_snapshot_{date}_{sym}.jsonl 末条
    → 读取 premarket_summary_{date}_{sym}.json
    → 计算 execution / performance / signal_accuracy（纯规则）
    → 生成 12 类建议草稿（规则驱动，高 priority 的先列）

  Step 3: Claude API 调用
    → 读取 Step 2 的结构化数据
    → 生成 learning_notes（per-stock）
    → 生成 llm_review（per-day）
    → 写出 postmarket_summary_{date}_{sym}.json × N 股
    → 写出 postmarket_summary_{date}.json

用户说"复盘"时（可选）：
  → 读取现有 postmarket_summary 作为上下文
  → 继续深度讨论，可追加/修改建议

次日盘前（premarket skill 运行时）：
  → 读取所有 confirmed=null 的建议
  → 提示用户逐条确认
  → 用户确认后：suggestion_applier.py 写回对应源文件
```

---

## suggestion_applier.py 规范

- 每次确认一条建议后立即执行，不批量
- 执行前先备份原始值到 `applied_to.old_value`
- 执行后记录 `applied_at`
- 支持回滚：读取 `applied_to`，将 `old_value` 写回对应字段
- `correlation_warning / thesis_confirmation / time_stop_eval` 三类只展示不写文件，`applied_to` 为 null

---

## dashboard 字段映射

| 字段 | Tab | 数据来源 |
|---|---|---|
| `performance.day_ret_pct` | 总览（今日结果列）| per-stock |
| `next_day.suggestions[]`（confirmed=null）| 盘后复盘（待确认建议）| per-stock |
| `signal_accuracy` | 每股详情 | per-stock |
| `portfolio.correlation_matrix` | 盘后复盘（组合风险）| per-day |
| `tomorrow_risk_calendar` | 盘后复盘 + 次日总览顶部警示 | per-day |
| `llm_review` | 盘后复盘（全文展示）| per-day |
| `pending_suggestions_count` | 总览（角标提示）| per-day |

---

## 跨 Spec 依赖说明

**premarket_summary spec 需同步更新**：`market_context.macro_events_today` 的读取逻辑需补充——次日盘前优先读 `config/macro_events_tomorrow.json`（若存在且日期匹配），否则读手动维护的 `macro_events_today`。该文件由本 spec 的 `tomorrow_risk_calendar` 建议确认后写入。

---

## Out of Scope

- `suggestion_applier.py` 的完整回滚 UI（属于 dashboard 实现）
- `postmarket_data_collector.py` 的具体计算逻辑（属于实施计划）
- Claude API prompt 设计（属于 prompt engineering）
- 其他 skill 的格式标准化（后续 brainstorm）
- `daily_dashboard.html` 完整实现（独立 spec，最后统一做）
