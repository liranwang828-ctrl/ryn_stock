# Skill 格式标准化：trading-day（编排层）— Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 trading-day skill 的输出契约，包括 `daily_plan_{date}.json`（早晨一次生成）和 `session_state_{date}.json`（全天脚本更新）的完整 schema，以及用户上线时的恢复视图逻辑

---

## 背景

trading-day 是整个系统的**编排层**，管理 7 个节点的全天工作流。现有 `session_manager.py` 已实现节点推进和告警队列，但缺乏：
1. 统一的日计划文件（每次用户上线不知道今天的整体作战计划）
2. 结构化的"用户离线期间发生了什么"记录
3. 明确的 GTC 状态追踪

**设计原则**：支持"间歇上线"而非"全程盯盘"。用户唯一必须在线的窗口是 08:00-10:30（约 2.5 小时），其余时间系统自动运行，🔴 事件才需要介入。

---

## 架构决策

| 决策 | 结论 |
|---|---|
| LLM 使用 | 后台**零 LLM 调用**；仅用户主动上线时 Claude 读状态文件生成恢复摘要 |
| 后台运行 | 纯 Python 脚本（`session_manager.py` + `daily_plan_writer.py`）|
| 文件结构 | `daily_plan_{date}.json`（Node 0 生成，一次）+ `session_state_{date}.json`（全天更新）|
| postmarket | 16:00 自动触发（已在 postmarket spec 定义），用户不必在线 |

---

## 用户在线窗口

```
08:00-09:00   Node 0：晨间准备（必须在线，约 30 分钟）
09:00-09:25   Node 1：盘前分析（必须在线）
09:30-10:00   Node 2：开盘观察 + post_open_adj 校准（必须在线）
10:00-10:30   Node 3→4：执行窗口，挂 GTC 单（必须在线）
10:30-16:00   Node 4→5：自动（poll.py + GTC 管理，用户可离线）
16:00+        Node 5→6：postmarket 自动，用户不必在线
```

---

## daily_plan_{date}.json（Node 0 由脚本生成）

路径：`daily_plan_{date}.json`（已有文件，本 spec 定义正式 schema）

```json
{
  "date":          "YYYY-MM-DD",
  "generated_at":  "ISO-timestamp",

  "market_context": {
    "env":            "顺风 | 中性 | 逆风",
    "vix_level":      float | null,
    "macro_events":   ["string"],         // 来自 premarket_summary.market_context
    "tomorrow_risk":  ["string"]          // 来自昨日 postmarket_summary per-day
  },

  "symbols_today": ["string"],           // 今日涉及标的（持仓 + 关注列表）

  "per_symbol": {
    "SYM": {
      "premarket_summary_path": "findings/premarket_summary_{date}_{sym}.json",
      "action_now":  "enter | watch | hold | reduce | exit | pass",
      "key_levels": {
        "entry_base":   float | null,
        "hard_stop":    float | null,
        "flex_add":     float | null,
        "flex_reduce":  float | null,
        "target":       float | null
      },
      "entry_go_status":        "pending | go | abort | expired | null",
      "pending_suggestions":    int,        // 来自昨日 postmarket confirmed=null 的建议数
      "memo_valid":             true|false  // strategic_memo valid_until 未过期
    }
  },

  "schedule": [
    {
      "node":    int,
      "name":    "string",
      "window":  "HH:MM-HH:MM",
      "status":  "done | active | pending | auto",
      "summary": "string ≤60字 | null"   // Node 0-3：advance_node() 调用时由模板填入；Node 4-6（自动节点）：由 session_state_updater 在对应时间自动填入模板摘要
    }
  ],

  "gtc_required": ["string"],    // 按 positions.json gtc_stop_placed=false 自动生成警示
  "pending_suggestions_total": int  // 所有标的 pending_suggestions 之和
}
```

**`action_now` 来源**（纯规则推导，exit 优先于 entry）：
```
优先级从高到低，第一条命中即停止：
1. exit.decision = "exit"       → "exit"
2. exit.decision = "reduce"     → "reduce"
3. entry.decision = "enter"     → "enter"
4. entry.decision = "watch"     → "watch"
5. thesis=intact AND is_held    → "hold"
6. 其他                         → "pass"
```
注：exit 字段仅在持仓时存在（is_held=true），无仓时跳过规则 1-2 和 5。

---

## session_state_{date}.json（扩展现有 schema）

在现有 `node / active_symbols / alert_queue` 基础上新增字段：

```json
{
  "node":            int,                  // 已有
  "node_name":       "string",             // 已有
  "active_symbols":  ["string"],           // 已有
  "alert_queue":     [ ... ],              // 已有，不变

  "last_online_at":  "HH:MM | null",       // 用户上次在线时间（用户上线时写入）
  "last_offline_at": "HH:MM | null",       // 用户上次离线时间

  "missed_alerts":   [                     // 用户离线期间发生的 🔴🟡 事件
    {
      "time":    "HH:MM",
      "level":   "red | yellow",
      "sym":     "string",
      "event":   "string",                 // llm_trigger 枚举值
      "detail":  "string ≤60字"
    }
  ],

  "next_action": {                         // 用户回来时第一件事（规则推导）
    "priority":    "immediate | normal",
    "instruction": "string ≤60字"
  },

  "gtc_status": {
    "placed":  ["string"],                 // gtc_stop_placed=true 的标的
    "missing": ["string"]                  // 应挂未挂（positions 中 gtc_stop_placed=false）
    // 注：_excluded 标的（BABA/PONY 等，来自 positions.json._excluded）不纳入 gtc_status 计算
  },

  "handoff_note": "string ≤80字"           // 用户离线时的状态摘要（脚本模板生成）
}
```

**`next_action` 规则推导**（优先级从高到低，第一条命中即停止）：
```
1. missed_alerts 有 level=red                → immediate: "有 🔴 紧急事件待处理，先看 missed_alerts"
2. gtc_status.missing 非空                  → immediate: "{sym} GTC 止损单未挂，请立即处理"
3. 当前时间在 10:00-10:30 且 entry_go 已触发 → immediate: "{sym} entry_go 已触发，确认是否入场"
4. pending_suggestions_total > 0            → normal: "有 {N} 条昨日建议待确认"
5. 其他                                     → normal: "当前节点 {name}，按计划继续"
```

**`handoff_note` 模板**（用户说"我要离开"或 10:30 后自动生成）：
```
"{N}只持仓在监控中，GTC单{已全部挂好|{sym}未挂}，下次上线建议查看{missed_alerts}"
```

---

## 生成流程

```
Node 0（08:00，用户上线）：
  → daily_plan_writer.py 读取所有 premarket_summary + positions.json
  → 生成 daily_plan_{date}.json（纯脚本，0 LLM）
  → 初始化 session_state（node=0，清空 missed_alerts）

Node 1-3（盘前/开盘/执行）：
  → session_manager.advance_node() 更新 node + schedule.status
  → 用户完成节点后写入 schedule.summary

全天自动（10:30-16:00）：
  → poll.py 每轮：检测 🔴🟡 事件 → 写入 session_state.alert_queue（已有行为不变）
  → session_state_updater（daily_plan_writer.py 的后台函数）每轮 poll 后：
      读取 alert_queue 中 time > last_online_at 的条目 → 写入 missed_alerts
      alert_queue 保留全量（不删除），missed_alerts 是过滤视图
  → 用户上线时：missed_alerts 展示后自动清空（重置为 []），last_online_at 更新为当前时间
  → 每小时：检查 gtc_status（读 positions.json）→ 更新 session_state.gtc_status
  → 10:30：生成 handoff_note，node=4（自动模式）

16:00（postmarket 自动）：
  → harvest_agent.py + postmarket_data_collector.py 自动跑
  → session_state.node=5，schedule 最后两项 status="auto"

用户上线（任意时间，说"开始今天"）：
  → session_manager.get_status() 读 session_state + daily_plan
  → Claude 读两个文件，生成叙述性恢复摘要（唯一 LLM 调用，按需）
  → 更新 last_online_at
```

---

## 用户恢复摘要格式（Claude 生成，A 级）

```
当前：10:47 ET / 节点3（盘中主动期）
离线 35 分钟（09:30-10:47）

【需要立即处理】
🔴 NVDA 10:00 entry_go 已触发（entry_base $218，止损 $215.6）
   → 确认是否已入场？

【供参考】
⚡ NBIL 10:23 触及 flex_add $62.3（未触发分析）

组合状态：GTC 全部已挂 ✅ | 待确认建议 2 条
→ 说"NVDA 已买" 或 "NVDA 跳过" 继续
```

---

## dashboard 字段映射

| 字段 | Tab |
|---|---|
| `daily_plan.per_symbol[*].action_now` | 总览（今日行动列）|
| `daily_plan.schedule` | 总览（节点进度条）|
| `session_state.missed_alerts` | 总览（离线期间事件，红色高亮）|
| `session_state.next_action` | 总览顶部（下一步提示横幅）|
| `session_state.gtc_status.missing` | 总览（⚠️ GTC 未挂警示）|
| `daily_plan.pending_suggestions_total` | 总览（角标）|

---

## 与其他 skill 的集成关系

```
trading-day 读取：
  premarket_summary_{date}_{sym}.json   → per_symbol.action_now / key_levels
  session_state_{date}.json            → 持续更新
  positions.json                       → gtc_status
  postmarket_summary_{date}.json       → pending_suggestions / tomorrow_risk

trading-day 写出：
  daily_plan_{date}.json               → dashboard 总览 + 用户作战计划
  session_state_{date}.json            → 全天状态（所有 skill 的事件汇总点）

poll.py 写入 session_state.alert_queue（已有，不变）
→ session_state_updater 每轮 poll 后过滤 time > last_online_at 的条目写入 missed_alerts
→ alert_queue 保留全量（审计），missed_alerts 是用户离线期间的未读视图，上线后清空
```

---

## Out of Scope

- `daily_plan_writer.py` 的具体实现逻辑（属于实施计划）
- `daily_dashboard.html` 完整实现（独立 spec）
- Constrained Mode 的完整实施（参见 TODO.md P1 条目）
- 用户恢复摘要的 prompt 设计（属于 prompt engineering）
