# Skill 格式标准化：stock-premarket 与 premarket_summary — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 stock-premarket skill 的输出契约，即 `premarket_summary_{date}_{sym}.json` 的完整 schema、生成机制、两档策略层、开盘校准接口

---

## 背景

stock-premarket skill 当前产出 6 个独立文件：
1. `findings/today_focus.json` — watchlist 评分
2. `premarket_analysis_{date}.json` — gap/场景/新闻/催化剂
3. `findings/order_sheet_{date}.json` — 入场条件/价位
4. `findings/entry_decision_{date}.json` — 入场决策
5. `findings/exit_decision_{date}.json` — 出场评估
6. `daily_checklist_{date}.json` — thesis 状态/今日行动

这 6 个文件格式独立，stock-intraday 和 trading-day skill 需要分别读取，无法可靠互相引用。

**目标**：新建 `premarket_summary_{date}_{sym}.json`，作为下游 skill 的统一输入契约。

---

## 架构决策

| 决策 | 结论 |
|---|---|
| 文件粒度 | 每股一文件：`premarket_summary_{date}_{sym}.json` |
| A 级输出 | 终端打印，不存文件，每股 4-5 行 |
| 生成者 | 新建 `agents/premarket_summary.py`，作为 stock-premarket skill 最后一步 |
| 数据来源 | 读取上述 6 个文件 + `strategic_memo_{sym}.json`（若存在）|

---

## 完整 Schema

### 顶层结构（10 个 key）

```json
{
  "date": "YYYY-MM-DD",
  "sym": "string",
  "generated_at": "ISO-timestamp",
  "market_context": { ... },
  "stock_snapshot": { ... },
  "entry": { ... },
  "exit": null,              // 不持仓时为 null
  "thesis": null,            // 不持仓时为 null
  "strategic_context": { ... },
  "post_open_adj": null      // 开盘前为 null，9:30-10:00 后填入
}
```

---

### market_context

```json
"market_context": {
  "spy_pre_chg": float,            // premarket_analysis.macro.spy_pre
  "nq_futures": float,             // premarket_analysis.macro.nq_futures
  "env": "顺风 | 中性 | 逆风",      // premarket_analysis.macro.env，strip emoji 后写入
  "vix_level": float,              // premarket.py 已计算，补写入 macro 输出
  "macro_events_today": ["string"] // 优先读 config/macro_events_tomorrow.json（由昨日 postmarket 写入）；不存在时手动维护；无则 []
}
```

**注**：代码实际写入 env 含 emoji（`"顺风✅"`, `"逆风❌"`），`premarket_summary.py` 写入前 strip。

---

### stock_snapshot

```json
"stock_snapshot": {
  "gap_pct": float,
  "pred_scene": "A|B|C|D|E|F|G|H | null",
  "news_type": "earnings_beat|strategic_invest|analyst_upgrade|product_catalyst|announcement|sector_driven|negative|macro|neutral|sector_leader",
  "catalyst_strength": 0|1|2|3,
  "pre_vol_ratio": float,           // 盘前量比，scene 预测的依据
  "overnight_note": "string ≤80字",
  "sector_ref": "string",           // 如 "SOXX"
  "sector_gap_pct": float,          // 板块盘前涨跌幅
  "rs_vs_sector": float,            // 股票1月涨幅 − 板块ETF同期涨幅
  "sector_note": "string ≤60字",    // 板块热点/阻力说明（A 级，来自 regime_note）
  "risk_flag": true|false,          // 关键词匹配：今日新闻是否命中 strategic_memo.main_risks
  "risk_note": "string ≤60字"       // 命中的风险关键词（risk_flag=false 时为 ""）
}
```

**`risk_flag` 计算规则**：从 `strategic_memo.support_and_risk.main_risks` 提取关键词，与 `premarket_analysis.stocks[sym].all_headlines` 做字符串匹配。任意命中 → true。无 strategic_memo 时 → false。

---

### entry

```json
"entry": {
  "decision": "enter | watch | pass",
  "hard_vetoes": ["string"],
  "soft_vetoes": ["string"],
  "entry_base": float | null,
  "stop_loss": float | null,
  "target_price": float | null,
  "rr_ratio": float | null,
  "sizing": "×1.5 | ×1.0 | ×0.5",
  "entry_conditions": ["string"],
  "cancel_conditions": ["string"]
}
```

**`decision` 翻译映射**（`premarket_decision.py` 输出中文，summary 写入英文枚举）：

| 代码输出 | schema 值 |
|---|---|
| `"可入场"` | `"enter"` |
| `"观察"` | `"watch"` |
| `"不入场"` | `"pass"` |

**`sizing` 规则**（规则驱动，先执行 Rules 1-3，再以 Rule 4 封顶）：

```
Rule 1: binary_risk_flag=true OR unified_confidence ≤ 2  → ×0.5
Rule 2: unified_confidence = 3-4                         → ×1.0
Rule 3: unified_confidence = 5 AND binary_risk_flag=false → ×1.5
Rule 4（封顶）: strategic_context.source = "premarket_inferred" → cap 为 ×1.0
```

---

### exit（持仓时非 null）

```json
"exit": {
  "decision": "hold | reduce | exit",
  "hard_stop": float,
  "stop_source": "manual_gtc | node1 | auto_atr",
  "hard_dist_pct": float,
  "hard_triggers": ["string"],
  "soft_triggers": ["string"],
  "target_price": float | null,
  "current_rr_ratio": float | null,   // exit_decision.rr_remaining（改名映射）
  "flex_add_level": float | null,
  "flex_reduce_level": float | null
}
```

**`decision` 翻译映射**（`premarket_exit_sheet.py` 输出中文，summary 写入英文枚举）：

| 代码输出 | schema 值 |
|---|---|
| `"继续持有"` | `"hold"` |
| `"考虑减仓"` | `"reduce"` |
| `"应出场"` | `"exit"` |

**`stop_source` 枚举说明**（直接沿用 premarket_exit_sheet.py 的实际值）：
- `"manual_gtc"` — t1_stop_snapshot 已设，GTC 单挂好
- `"node1"` — 以 node1 价位作止损基准
- `"auto_atr"` — ATR 估算，建议设 GTC

---

### thesis（持仓时非 null）

```json
"thesis": {
  "status": "intact | weakening | broken",
  "daily_action": "A | B | C",
  "position_type": "thesis | catalyst | trend | flex",
  "today_falsification": ["string"]   // exit_decision.falsification_check（已有字段）
}
```

**`daily_action` 含义**：A = 主动操作日 / B = 被动守护日 / C = 评估日

---

### strategic_context

两档模式，由 `source` 字段区分。

```json
"strategic_context": {
  "source": "strategic_memo | premarket_inferred"
}
```

#### Full 模式（source = "strategic_memo"）

字段来自 `strategic_memo_{sym}.json`，含显式路径映射：

```json
"strategic_context": {
  "source": "strategic_memo",
  "memo_date": "YYYY-MM-DD",              // ← strategic_memo.analysis_date
  "memo_valid_until": "string",           // ← strategic_memo.outlook.valid_until
  "strategic_stance": "strong_hold | hold | hold_reduced | reduce | exit_ready | avoid",
                                          // ← strategic_memo.synthesis.strategic_stance
  "unified_confidence": 1|2|3|4|5,       // ← strategic_memo.judgment.unified_confidence
  "thesis_lifecycle": "early | mid | late",
                                          // ← strategic_memo.judgment.thesis_lifecycle_stage.stage（flatten）
  "key_condition": "string ≤50字",        // ← strategic_memo.synthesis.key_condition
  "next_catalyst": {
    "event": "string",                    // ← strategic_memo.support_and_risk.next_catalyst.event
    "date": "YYYY-MM-DD | unknown",       // ← strategic_memo.support_and_risk.next_catalyst.date
    "importance": "high | medium | low",  // ← strategic_memo.support_and_risk.next_catalyst.importance
    "days_away": int | null               // 由 premarket_summary.py 计算：today − next_catalyst.date；date="unknown" 时 null
  },
  "main_tensions": ["enum"],             // ← strategic_memo.synthesis.main_tensions
  "macro_fit": "favorable | neutral | challenging",
                                          // ← strategic_memo.support_and_risk.macro_fit.assessment（取 .assessment 子字段）
  "technical_stage": "1|2|3|4",          // ← strategic_memo.support_and_risk.technical_stage.stage（取 .stage 子字段）
  "binary_risk_flag": true|false,         // 规则推导：days_away ≤ 2 AND importance="high"
  "alignment_check": {                    // 由 premarket_summary.py 实时计算，不来自 strategic_memo
    "strategic_vs_tactical": "consistent | tension | contradiction",
    "note": "string ≤60字"
  }
}
```

**`alignment_check` 推导规则**（Full 和 Lite 模式相同）：
```
strategic_stance ∈ {strong_hold, hold} AND entry.decision = "enter" → consistent
strategic_stance ∈ {hold_reduced, reduce} AND entry.decision = "enter" → tension
strategic_stance ∈ {exit_ready, avoid} AND entry.decision ∈ {enter, watch} → contradiction
strategic_stance ∈ {exit_ready, avoid} AND exit.decision = "hold" → contradiction
其他组合 → consistent
```

#### Lite 模式（source = "premarket_inferred"）

无 strategic_memo 时，盘前数据就地推导：

| 字段 | 推导来源 | 精度 |
|---|---|---|
| `strategic_stance` | thesis.status 映射：intact→hold / weakening→hold_reduced / broken→**exit_ready** | 粗 |
| `unified_confidence` | premarket confidence 字段："高"→4 / "中"→3 / "低"→2 | 粗 |
| `thesis_lifecycle` | null | 无 |
| `key_condition` | premarket_analysis.stocks[sym].reasoning | 可用 |
| `next_catalyst.event` | news_type | 粗 |
| `next_catalyst.date` | "unknown" | — |
| `next_catalyst.days_away` | null | — |
| `next_catalyst.importance` | catalyst_strength：0→low / 1-2→medium / 3→high | 粗 |
| `main_tensions` | [] | 空 |
| `macro_fit` | env 映射：顺风→favorable / 中性→neutral / 逆风→challenging | 可用 |
| `technical_stage` | month_context 推导（见下表） | 粗 |
| `binary_risk_flag` | catalyst_strength ≥ 2 → true（保守近似：Full 模式用时间距离，Lite 无日期信息故改用强度替代，有意偏保守）| 粗 |
| `alignment_check` | 同 Full 模式规则，使用 Lite 推导的 strategic_stance | 可用 |
| `memo_date / memo_valid_until` | null | — |

**`technical_stage` 推导表**（Lite 模式）：

| month_context 条件 | 推导值 | 说明 |
|---|---|---|
| above_ma20=true AND above_ma50=true | `"2"` | 上升趋势，最优 |
| above_ma20=true AND above_ma50=false | `"3"` | 可能顶部区域 |
| above_ma20=false | `"4"` | 下跌趋势 |
| Stage 1（底部建仓）| 无法从 month_context 判断，默认 `"4"` | 需 deep-research 才能识别 |

**下游读取规则**：
- `source = "strategic_memo"` → 可信，参与集成逻辑
- `source = "premarket_inferred"` → 粗估参考；`thesis_lifecycle / main_tensions / days_away` 不可用于集成；sizing 被 Rule 4 封顶为 ×1.0

---

### post_open_adj（开盘前为 null）

由 `poll.py` 或 `opening_calibrator.py` 于 9:30-10:00 观察窗口后填入：

```json
"post_open_adj": {
  "updated_at": "HH:MM",
  "actual_open": float,
  "scene_confirmed": "A|B|C|D|E|F|G|H | null",  // 实际确认的场景字母；null 仅表示尚未确认，确认后无论是否与预测一致均写字母
  "entry_base_adj": float | null,
  "stop_loss_adj": float | null,
  "target_adj": float | null,
  "rr_ratio_adj": float | null,     // entry_base_adj 改变时重算
  "flex_add_adj": float | null,
  "flex_reduce_adj": float | null,
  "hard_stop_adj": float | null,
  "entry_go": true|false|null,       // 观察窗口后最终放行信号
  "current_rr_adj": float | null,   // 基于实际开盘价的持仓盈亏比（exit 侧）
  "note": "string ≤80字"
}
```

**读取优先级**（对 intraday/trading-day 层）：
- `post_open_adj != null` → 使用 `*_adj` 字段，覆盖对应盘前原始值
- `post_open_adj == null` → 使用盘前原始值

---

## premarket_summary.py 职责

1. 读取 6 个现有输出文件
2. 若存在 `strategic_memo_{sym}.json` → Full 模式；否则 → Lite 模式
3. 合并写出 `premarket_summary_{date}_{sym}.json`（B 级，结构化）
4. 终端打印 A 级报告（每股 4-5 行，不存文件）
5. 初始化 `post_open_adj: null`

**A 级终端报告格式**（每股）：
```
NVDA | gap +4.2% | 场景B(VWAP回踩) | 板块SOXX+0.3% RS+5.2%
论点intact / B类守护 | 止损$215.64(2.3%) / 目标$227(3%) / RR=1.8
加仓$198.6 / 减仓$226 | binary_risk=false | alignment=consistent
strategic[memo]: hold(conf=4/late) | key: Blackwell出货节奏
risk_flag=true → 命中风险: "competition"
```

---

## 需要的代码变更（前置条件）

| 变更 | 文件 | 说明 |
|---|---|---|
| `vix_level` 写入 macro 输出 | `agents/premarket.py` | 已计算，补一行写入 `macro` dict |
| `flex_reduce_level` 计算 | `agents/premarket_order_sheet.py` | 新增字段，与 `flex_add_level` 对称 |
| 新建合并脚本 | `agents/premarket_summary.py` | 本 spec 主体 |
| stock-premarket skill 末尾调用 | skill 文件 | 现有步骤后追加一步 |

---

## 可复现性保证

| 字段类型 | LLM 行为 | 约束 |
|---|---|---|
| 所有 B 级枚举字段 | 从枚举集合中选择 | 固定选项集 |
| `risk_flag` | 关键词匹配，不由 LLM 判断 | 确定性 bool |
| `sizing` | 规则推导（Rules 1-4） | 完全确定 |
| `alignment_check` | 规则推导 | 完全确定 |
| `binary_risk_flag` | 规则推导 | 完全确定 |
| Lite 模式所有推导字段 | 规则映射 | 完全确定 |
| `sector_note / overnight_note / key_condition` | LLM 生成或直接拷贝 | A 级，字数上限，不参与集成 |

---

## Out of Scope

- stock-intraday 及其他 skill 的格式标准化（后续 brainstorm）
- strategic_context 集成层的具体集成逻辑（依赖本 spec 完成后定义）
- `flex_reduce_level` 的具体计算算法（属于 order_sheet spec 范围）
- 经济日历 API 接入（用户手动维护 `macro_events_today`）
