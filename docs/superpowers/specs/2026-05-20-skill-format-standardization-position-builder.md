# Skill 格式标准化：position-builder — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 position-builder skill 的输出契约，包括三种触发模式（规划/快速/补全）、positions.json 完整字段 schema、position_entry 审计文件结构

---

## 背景

当前 `positions.json` 是手动维护的持仓数据库，缺乏正式 schema：
- `falsification_conditions` 在多数持仓中为空
- 建仓时无系统性引导，事后止损决策容易情绪化
- `t2_conditions` 格式因持仓而异
- 快速入场时没有机制确保关键字段被填写

**目标**：定义 `positions.json` 的正式 schema（整个系统的数据基础），并设计 position-builder skill 的三种引导模式，在情绪最平静的建仓时刻结构化地填好所有字段。

---

## 架构决策

| 决策 | 结论 |
|---|---|
| 触发场景 | 规划模式（建仓前）+ 快速模式（盘中，translator 触发）+ 补全模式（盘后 _pending 持仓）|
| 有 strategic_memo | 快路径：系统预填 thesis/macro_sensitivity，用户只需确认证伪条件和止损 |
| 无 strategic_memo | 深度引导：逐步追问 position_type → thesis → falsification → stop |
| 输出 | position_entry_{date}_{sym}.json（审计）+ positions.json 更新 + 触发 premarket_summary 重算 |
| _pending 机制 | 快速模式下标记未填字段，postmarket 检测后提示补全 |

---

## positions.json 正式 schema

### 顶层结构

```json
{
  "positions": {
    "SYM": { ... }
  },
  "_excluded": ["BABA", "PONY"]   // 跟踪仓位：持仓数据完整存在于 positions，但不纳入 portfolio_risk_agent 风险计算
}
```

**`_excluded` 语义**：sym 同时出现在 `positions` 和 `_excluded` 是合法状态（BABA 就是这种情况）。`_excluded` 表示"用户自愿持有、不参与系统风险管理"，position-builder 仍然为这类持仓维护完整 schema（包括 falsification_conditions），区别仅在于 portfolio_risk_agent 跳过计算。

### 每股字段（完整 schema）

```json
{
  // ── 身份层（建仓时写，稳定不变）────────────────────────────
  "cost":       float,              // 加权平均成本价
  "shares":     int,                // 总持仓量
  "date":       "YYYY-MM-DD",       // 最近一次仓位调整日期
  "note":       "string",           // 人类可读备注（如"MRVL 2x杠杆ETF"）

  // ── T1/T2/T3 分批结构 ────────────────────────────────────
  "tranche":    "T1 | long_term | flex",
  "t1_cost":    float,
  "t1_shares":  int,
  "t1_date":    "YYYY-MM-DD",
  "t2_cost":    float | null,
  "t2_shares":  int,               // 默认 0，不为 null（区别于 t2_cost 可为 null）
  "t2_conditions": {
    "note":                   "string",
    "underlying_price_floor": float | null,
    "etf_price_floor":        float | null,
    "vol_ratio_min":          float | null
  },
  "t3_cost":    float | null,
  "t3_shares":  int,               // 默认 0

  // ── 决策框架层（建仓时引导填写，影响整个持有期）────────────
  "position_type":   "thesis | catalyst | trend | flex",
  "thesis":          "string ≤50字",
  "thesis_status":   "intact | weakening | broken",
  "thesis_updated":  "YYYY-MM-DD",
  "falsification_conditions": ["string"],   // ≥1条，具体可观测
  "falsification_updated":    "YYYY-MM-DD",
  "catalyst_type":        "earnings | policy | product | order | regulatory | null",
  "catalyst_deadline":    "YYYY-MM-DD | null",
  "catalyst_persistence": "one_time | structural | null",

  // ── 运行状态层（每日由 postmarket/poll 更新）──────────────
  "daily_action":      "A | B | C",
  "action_updated":    "YYYY-MM-DD",
  "t1_stop_snapshot":  float | null,    // 硬止损价快照（用于 premarket_exit_sheet）
  "stop_note":         "string",        // 止损说明（如"GTC已挂 $76，2026-05-19"）
  "gtc_stop_placed":   true|false,
  "gtc_stop_date":     "YYYY-MM-DD | null",

  // ── 宏观映射层（有 strategic_memo 时自动填，否则引导填写）──
  "macro_type":  "string",              // 如"趋势型+AI基础设施"
  "macro_sensitivity": {
    "rate_up":       "正 | 负 | 中",
    "inflation":     "正 | 负 | 中",
    "recession":     "正 | 负 | 中",
    "dollar_strong": "正 | 负 | 中",
    "credit_tight":  "正 | 负 | 中"
  },

  // ── 仓位规模层 ────────────────────────────────────────────
  "target_pct": float,              // 目标仓位占总资产%
  "min_pct":    float,
  "max_pct":    float,

  // ── 内部标记（position_builder 维护，供 postmarket 检测）──
  "_pending":        true|false,    // 快速模式下有字段待补全
  "_pending_fields": ["string"]     // 具体哪些字段名待补全
}
```

---

## position_entry_{date}_{sym}.json（审计记录）

路径：`findings/position_entry_{date}_{sym}.json`

每次调用 position-builder（三种模式都写）：

```json
{
  "date":          "YYYY-MM-DD",
  "sym":           "string",
  "session_at":    "ISO-timestamp",
  "mode":          "planning | quick | catch_up",
  "source":        "strategic_memo | premarket_inferred | manual",
  "fields_written":  ["cost", "shares", "thesis", "falsification_conditions"],
  "fields_pending":  ["t2_conditions", "macro_sensitivity"],
  "pending_count":   int,
  "positions_json_updated": true|false,
  "premarket_triggered":    true|false,
  "user_inputs": {
    "thesis":                   "string",
    "falsification_conditions": ["string"],
    "t1_stop_snapshot":          float | null,
    "gtc_stop_placed":           true|false|null
  },
  "auto_filled": {
    "macro_sensitivity": {},       // 从 strategic_memo 读取
    "position_type":     "string"  // 若 strategic_memo 有 thesis_lifecycle
  }
}
```

---

## 三种模式的引导流程

### 规划模式（无 strategic_memo）

触发：用户说"新建仓位 X / 建仓 X / 我要买 X"，`positions.json` 中无此股。

```
Q1: position_type？（选择题：论点型 / 催化剂型 / 趋势型 / Flex）
Q2: 用一句话说清楚为什么买？（thesis，≤50字）
Q3: 什么情况下你会承认这笔投资是错的？（falsification_conditions，≥1条，要求具体可观测）
Q4: 硬止损价是多少？GTC 单是否已挂好？
    position_type=催化剂时额外问：催化剂是什么？deadline 是哪天？
可选: T2 加仓条件？目标仓位比例（target_pct）？
→ 写入 positions.json，_pending=false
```

### 规划模式（有 strategic_memo，快路径）

```
系统预填（无需用户输入）：
  - thesis ← strategic_memo.synthesis.key_condition
  - macro_sensitivity ← strategic_memo.support_and_risk.macro_fit
  - position_type ← 从 thesis_lifecycle / strategic_stance 推导

系统展示 strategic_memo.support_and_risk.main_risks 供参考

Q1: 确认/修改 thesis（展示预填值，用户可直接回车确认）
Q2: 从 main_risks 中选择哪条作为证伪条件（可多选，可自行添加）
Q3: 硬止损价？GTC 已挂好了吗？
→ 写入 positions.json，_pending=false
```

### 快速模式（盘中，translator.py 触发）

触发：translator.py 检测到用户记录了一笔买入交易，自动调用。

```
系统自动获取：cost、shares、date（从 translator.py 的交易记录）
Q1: position_type？（选择题，目标 30 秒完成）
Q2: 一句话 thesis？（≤50字）
→ 写入 positions.json：
    _pending=true
    _pending_fields=["falsification_conditions", "t1_stop_snapshot",
                     "gtc_stop_placed", "t2_conditions", "macro_sensitivity"]
→ 收盘后 postmarket_data_collector.py（Step 1）扫描 positions.json 中所有 _pending=true 的持仓，写入 postmarket_summary_{date}.json；LLM 阶段提示"X 建仓记录有 N 个字段待补全，说'补全 X 建仓'触发补全模式"
```

### 补全模式（盘后 _pending 持仓）

触发：postmarket 检测到 `_pending=true` 的持仓，提示用户；用户确认后调用。

```
系统展示 _pending_fields 列表
逐一引导补填（同规划模式对应问题）
→ 全部补完后：_pending=false，_pending_fields=[]
→ 触发 premarket_summary 重算
```

---

## 字段填写优先级

| 优先级 | 字段 | 说明 |
|---|---|---|
| **必须立即填**（_pending 不接受为空）| `cost / shares / date / position_type / thesis` | 最基础的持仓记录 |
| **必须在入场当天填完** | `falsification_conditions / t1_stop_snapshot / gtc_stop_placed` | 影响止损决策的核心字段 |
| **建议尽快填**（可延迟至周内）| `t2_conditions / macro_sensitivity / target_pct` | 影响加仓和组合管理 |
| **可选**（有则更好）| `catalyst_deadline / catalyst_persistence / stop_note` | 补充上下文 |

---

## 与其他 skill 的依赖关系

| 下游 skill | 读取的 positions.json 字段 |
|---|---|
| premarket_exit_sheet.py | `t1_stop_snapshot`（→ hard_stop 计算）|
| premarket_order_sheet.py | `cost / shares / thesis / t2_conditions` |
| portfolio_risk_agent.py | `cost / shares` |
| poll.py | `thesis_status / position_type / daily_action` |
| postmarket_summary | `thesis_status`（→ snapshot_thesis_status）|
| portfolio_health | `date`（→ days_held）、`thesis_status` |
| premarket_summary | `thesis_status / daily_action / position_type` |

---

## dashboard 字段映射

| 字段 | Tab |
|---|---|
| `_pending=true` 持仓列表 + `_pending_count` | 总览（⚠️ 待补全角标）|
| `position_entry` 历史记录 | 每股详情（建仓决策历史）|
| `falsification_conditions` | 每股详情（证伪条件展示）|
| `gtc_stop_placed / t1_stop_snapshot` | 每股详情（止损状态）|

---

## Out of Scope

- **premarket_summary 重算的触发方式**：补全模式完成后，Claude 直接调用 `python3.12 agents/premarket_summary.py {SYM}`，而非事件触发机制。这是 Claude skill 层的操作，不需要额外实现。
- `translator.py` 如何检测买入交易并触发 quick 模式（属于实施计划）
- `positions.json` 中历史字段的迁移（现有数据补全策略）
- trading-day skill 格式标准化（下一个 brainstorm）
- `daily_dashboard.html` 完整实现（独立 spec）
