# Skill 格式标准化：stock-intraday 与 intraday_snapshot — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 stock-intraday skill 的输出契约，即 `intraday_snapshot_{date}_{sym}.jsonl` 的完整 schema、生成机制、事件触发规则、dashboard 字段映射

---

## 背景

stock-intraday skill 在用户盘中询问"X 现在如何"时触发，当前无结构化输出，仅凭 poll_state + 实时价格做 ad-hoc 分析。问题：
1. 无历史可查：无法复盘"10:15 时为什么建议等待"
2. 与盘前计划割裂：不知当前价格相对 premarket_summary 节点在哪
3. LLM 每次重新读取所有文件，效率低

**目标**：建立 `intraday_snapshot_{date}_{sym}.jsonl`，作为盘前计划与实时状态的交汇点，支持事件驱动的自动分析和 dashboard 展示。

---

## 架构决策

| 决策 | 结论 |
|---|---|
| 文件格式 | `intraday_snapshot_{date}_{sym}.jsonl`（JSONL，每轮追加一条） |
| 写入频率 | poll.py 每轮（约每 2 分钟），全天约 200 条 |
| 开始时间 | 9:30 ET（随 poll.py 启动） |
| LLM 触发 | 事件分级驱动，非定时，非全量 |
| poll_state 合并 | 每轮同步写入关键字段到 `poll_state_{date}.json`（均为新增 key，不覆盖已有字段）|
| dashboard 数据源 | JSONL 负责"每股详情"+"事件日志"；premarket_summary 负责"节点历程" |
| 用户按需调用 | 读最新条目 + premarket_summary → LLM 生成叙述 + action_now |

---

## 每条 JSONL 记录结构

每 2 分钟 poll.py 追加一条，包含以下 6 个顶层字段：

```json
{
  "ts":            "HH:MM:SS",
  "meta":          { ... },
  "price_now":     { ... },
  "plan_vs_now":   { ... },
  "node_snapshot": { ... },   // post_open_adj 的节点快照副本，用于节点历程 Tab
  "action_now":    null       // 仅 LLM 触发时非 null
}
```

---

### meta

```json
"meta": {
  "date":                  "YYYY-MM-DD",
  "sym":                   "string",
  "session_min":           int,                   // 开盘后第几分钟
  "llm_triggered":         true|false,
  "llm_trigger":           "hard_stop_breach | entry_go | vix_spike | gate_flip | consensus_shift | thesis_breach | manual | null",
  "cooldown_until":        "HH:MM:SS | null",    // 持久化冷却结束时间（同步写入 poll_state）
  "post_open_calibrated":  true|false             // premarket_summary.post_open_adj 是否已写入
}
```

**`llm_trigger` 与 `thesis_signal` 关系说明**：
- `meta.llm_trigger = "thesis_breach"` 表示触发原因
- `plan_vs_now.thesis_signal = "breach"` 表示当时的论点状态
- 两者联动但语义不同，触发事件名含 `_breach` 后缀以示区分

---

### price_now（B 级，poll.py 每轮填写）

```json
"price_now": {
  "price":             float,
  "chg_pct":           float,
  "vwap_dist_pct":     float,
  "rs_vs_spy":         float,
  "rs_vs_sector":      float,
  "rsi14_5m":          float,
  "vol_ratio":         float,
  "gate_status":       "通过 | 未通过",
  "gate_pass":         ["string"],
  "gate_block":        ["string"],
  "master_avg":        float | null,
  "master_consensus":  "buy | neutral | no_buy | null"
}
```

---

### plan_vs_now（B 级，规则推导，完全确定性）

**读取优先级**：所有价格节点优先读 `post_open_adj` 的 `*_adj` 值（若非 null），否则回退到 `premarket_summary` 原始值。具体：
- `entry_base` → `post_open_adj.entry_base_adj` ?? `entry.entry_base`
- `hard_stop` → `post_open_adj.hard_stop_adj` ?? `exit.hard_stop`
- `target` → `post_open_adj.target_adj` ?? `exit.target_price` ?? `entry.target_price`
- `flex_add` → `post_open_adj.flex_add_adj` ?? `exit.flex_add_level`
- `flex_reduce` → `post_open_adj.flex_reduce_adj` ?? `exit.flex_reduce_level`

```json
"plan_vs_now": {
  "dist_to_entry_pct":       float | null,
  "dist_to_stop_pct":        float | null,
  "dist_to_target_pct":      float | null,
  "dist_to_flex_add_pct":    float | null,
  "dist_to_flex_reduce_pct": float | null,
  "entry_conditions_met":    int,
  "entry_conditions_total":  int,
  "scene_match":             true|false|null,
  "thesis_signal":           "intact | warning | breach",
  "entry_go_status":         "pending | go | abort | expired"
}
```

**距离字段计算公式**（分母统一为当前 price）：
```
dist_to_entry_pct      = (price - entry_base) / price × 100   // 负值 = 未到入场价
dist_to_stop_pct       = (price - hard_stop)  / price × 100   // 越小越危险
dist_to_target_pct     = (target - price)     / price × 100   // 距目标还有多远
dist_to_flex_add_pct   = (price - flex_add)   / price × 100   // 负值 = 低于加仓价
dist_to_flex_reduce_pct= (flex_reduce - price)/ price × 100   // 负值 = 超过减仓价
```

注：所有分母统一用当前 `price`，表示"距当前价的百分比"，便于横向比较。

**`thesis_signal` 推导规则**（纯规则，不依赖 LLM）：
```
优先级从高到低，第一条命中即停止：

1. price ≤ hard_stop（有效止损线）                → breach
2. thesis.status == "broken"                      → breach
3. thesis.status == "weakening"
   AND dist_to_stop_pct < 3%（接近硬止损）         → breach
4. thesis.status == "weakening"                   → warning
5. dist_to_stop_pct < 3%（接近硬止损）             → warning
6. today_falsification 列表非空
   AND dist_to_stop_pct < 5%                      → warning
7. 其他                                           → intact
```

注：规则 3、5 用 `dist_to_stop_pct`（基于 hard_stop 计算）替代 soft_stop，避免引入额外字段依赖。soft_stop 作为展示字段存在于 exit_decision.json，不参与 thesis_signal 推导。

**`entry_go_status` 推导规则**（优先级从高到低，第一条命中即停止）：
```
1. session_min ≥ 60（10:30 后）                    → expired（窗口关闭，优先于其他）
2. post_open_calibrated = false                    → pending
3. post_open_adj.entry_go = true                   → go
4. post_open_adj.entry_go = false                  → abort
5. 其他                                            → pending
```

注：规则 1 优先于规则 4，避免"entry_go=false AND session_min≥60"时 abort/expired 歧义——超过 10:30 统一显示 expired，无论之前的 abort 原因。

---

### node_snapshot（每条 JSONL 记录的节点快照，供节点历程 Tab 使用）

```json
"node_snapshot": {
  "entry_base":  float | null,   // 当前生效的入场价（优先 adj）
  "hard_stop":   float | null,
  "target":      float | null,
  "flex_add":    float | null,
  "flex_reduce": float | null
}
```

每条 JSONL 都包含 `node_snapshot`，dashboard 节点历程 Tab 通过比较相邻条目的节点值来检测变化（diffing），无需 `source` 字段——当任意节点值与上一条不同时，dashboard 高亮该条目为"节点调整"。

---

### action_now（LLM 触发时非 null，其他轮次为 null）

```json
"action_now": {
  "conclusion":       "enter | add | hold | reduce | exit | wait | abort",
  "entry_action":     "enter | wait | abort",
  "position_action":  "add | hold | reduce | exit | none",
  "urgency":          "immediate | today | no_rush",
  "note":             "string ≤80字"
}
```

**`conclusion` 枚举语义**：
- `enter`：无仓位，现在入场
- `add`：有仓位，Flex 加仓
- `hold`：有仓位，维持不动
- `reduce`：有仓位，Flex 减仓
- `exit`：有仓位，全部退出
- `wait`：无仓位，条件未满足继续等
- `abort`：无仓位，放弃今日入场计划（`entry_action=abort` 时 `conclusion` 同为 `abort`）

---

## 事件触发规则

### 三级分类

| 级别 | 事件 key | 触发条件 | 策略 |
|---|---|---|---|
| 🔴 即时 | `hard_stop_breach` | price ≤ hard_stop | 立即，无冷却 |
| 🔴 即时 | `entry_go` | 10:00 首轮且 entry_go=true | 立即，无冷却 |
| 🔴 即时 | `vix_spike` | VIX 单轮涨 > 10% 或 SPY 5分钟跌 > -1% | 立即，无冷却 |
| 🟡 冷却 | `gate_flip` | gate_status 翻转 | per-sym 10 分钟冷却 |
| 🟡 冷却 | `consensus_shift` | master_consensus 代码变化 | per-sym 10 分钟冷却 |
| 🟡 冷却 | `thesis_breach` | thesis_signal 变为 breach | per-sym 10 分钟冷却 |
| ⚪ 不自动 | — | 价格触及 flex/entry 节点 | 只打印终端提示，不写 JSONL 事件 |
| ⚪ 不自动 | — | RS 微变、场景偏离 | 只更新 B 级字段 |

⚪ 级别终端提示格式：
```
⚡ NVDA 触及 flex_add $198.6（当前 $199.1）
```

### 冷却机制（完整规范）

- **per-sym 独立**：每只股票独立冷却计时器，互不影响
- **🔴 即时事件不受冷却限制**，可随时穿透冷却期触发
- **计时起点**：从 LLM 触发写入 JSONL 的时刻开始计 10 分钟
- **持久化**：`cooldown_until` 写入 `meta`，同时同步写入 `poll_state_{date}.json` 的 `symbols[sym].cooldown_until`（poll.py 重启后读此字段恢复冷却状态，防止重启后立即重复触发）
- **冷却期内**：仍追加 B 级 JSONL 条目（`llm_triggered=false`），不触发 LLM
- **冷却重置**：冷却时间到期后自动重置，无需手动操作

---

## post_open_adj 填写逻辑（完整规范）

`premarket_summary_{date}_{sym}.json` 的 `post_open_adj` 由 poll.py 填写：

```
9:30 开盘首轮：
  记录 actual_open
  
  if actual_open > entry_base × 1.02：
    entry_go = false，note = "开盘高开超 2%，不追"
    entry_base_adj = null（不调整，价格已超计划）
    
  elif actual_open < hard_stop：
    entry_go = false，note = "开盘即破止损位"
    
  elif hard_stop ≤ actual_open < entry_base：
    entry_go = pending，note = "低开，观察能否回升至入场区间"
    entry_base_adj = actual_open × 1.005（小幅上移入场价，避免追涨）
    
  else（entry_base ≤ actual_open ≤ entry_base × 1.02）：
    entry_go = pending，note = "开盘在入场区间，观察中"

  延迟开盘 fallback：
    若 9:35 前无价格数据 → actual_open = null，entry_go = pending
    not_open_flag = true（dashboard 显示"未正常开盘"）

10:00 首轮（session_min ≈ 30）：
  若 entry_conditions_met ≥ entry_conditions_total × 0.6：
    entry_go = true → 触发 🔴 entry_go 事件
  else：
    entry_go = false
  写入 post_open_adj.updated_at = "10:00"

10:30 后：
  entry_go_status = expired（入场窗口关闭，不再更新 entry_go）
```

---

## poll_state 合并字段（均为新增 key）

经确认，以下字段名在现有 poll_state schema 中不存在，安全追加：

```json
"symbols": {
  "NVDA": {
    // 现有字段（last_price, master_score, gate_status 等）保留不变
    // 以下均为新增 key：
    "plan_vs_now": {
      "entry_conditions_met":   int,
      "entry_conditions_total": int,
      "dist_to_stop_pct":       float,
      "dist_to_target_pct":     float,
      "thesis_signal":          "intact | warning | breach",
      "entry_go_status":        "pending | go | abort | expired"
    },
    "last_action_now":  "enter | add | hold | reduce | exit | wait | abort | null",
    "last_event":       "event_type | null",
    "last_event_at":    "HH:MM | null",
    "cooldown_until":   "HH:MM:SS | null"   // 冷却持久化，poll.py 重启后读取
  }
}
```

---

## dashboard 字段映射

| 字段 | dashboard Tab | 数据来源 |
|---|---|---|
| `price_now`（price/chg/gate） | 总览（当前状态列）| JSONL 最新条 |
| `action_now.conclusion` | 总览（action_now 列）| JSONL 最新 llm_triggered=true 条 |
| `meta.llm_trigger` + `action_now.note` | 事件日志（触发条目高亮）| JSONL 全量，过滤 llm_triggered=true |
| `plan_vs_now`（dist 系列）| 每股详情（计划 vs 现实）| JSONL 最新条 |
| `entry_go_status` | 每股详情（入场窗口状态）| JSONL 最新条 |
| `node_snapshot`（随时间变化）| 节点历程（时间轴）| JSONL 全量，source 变化时高亮 |
| `plan_vs_now.thesis_signal` | 总览（论点状态）+ 每股详情 | JSONL 最新条 |

**dashboard 读取 JSONL 过滤规则**：
- 总览 / 每股详情：只读最新 1 条（current state）
- 事件日志：读所有 `llm_triggered=true` 的条目
- 节点历程：读 `node_snapshot.source` 发生变化的条目 + 最近 3 条

---

## 用户按需调用（stock-intraday skill）

用户说"X 现在如何"时：
1. 读取 `intraday_snapshot_{date}_{sym}.jsonl` 最新一条
2. 读取 `premarket_summary_{date}_{sym}.json`（含 post_open_adj）
3. LLM 生成叙述性分析 + `action_now`（`llm_trigger = "manual"`）
4. 追加一条新 JSONL 记录
5. 打印 A 级报告

**A 级终端报告格式**：
```
NVDA 10:23 | $219.4 +1.8% | RS+2.1% | gate:通过(3/4)
盘前计划：入场$218 ✅ / 止损$215.6(1.7%) / 目标$227(3.5%)
flex_add $198.6(-9.5%) | flex_reduce $226(+3.0%) | entry_go:已触发
论点intact | 大师avg=6.2 consensus=neutral
→ action_now: hold（等待 10:30 后 flex 信号确认）urgency=no_rush
```

---

## Out of Scope

- stock-postmarket 及其他 skill 的格式标准化（后续 brainstorm）
- `daily_dashboard.html` 的完整实现（独立 spec，最后统一做）
- `action_now` 的 LLM prompt 设计（属于 prompt engineering）
- `entry_conditions_met` 的具体判断逻辑（依赖 premarket_decision.py 现有实现）
