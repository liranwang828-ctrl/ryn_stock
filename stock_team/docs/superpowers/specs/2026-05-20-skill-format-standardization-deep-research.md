# Skill 格式标准化：stock-deep-research 与 strategic_memo — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 stock-deep-research skill 的输出契约，以及 strategic_memo 的结构、字段和可复现合成机制

---

## 背景与核心问题

现有 8 个分析 skill 的输出格式独立设计，缺乏统一契约。具体问题：

1. **各说各的**：19 个分析字段没有合成机制，堆在一起无法产生统一判断
2. **不可复现**：如果让 LLM 自由生成综合判断，同样的数据可能产生不同结论
3. **无法集成**：stock-premarket 无法可靠地以 stock-deep-research 的分析为输入，因为格式不稳定

**核心约束**：同样的输入数据必须始终产生同样的结构化输出。LLM 不自由生成判断文字，而是从预定义的枚举集合中选择。

---

## 总体框架：A+B 混合，按 skill 特异化

| 格式类型 | 适用场景 | 实现方式 |
|---|---|---|
| **B 级（字段级固定）** | JSON 输出文件、集成关键字段 | 固定 schema，有限枚举值 |
| **A 级（章节级固定）** | 人类可读报告、叙述性内容 | 固定章节名，内容灵活 |
| **永不使用 C 级** | 纯代码生成叙述 | 失去 LLM 分析判断价值 |

每个 skill 自己决定哪些字段是 B，哪些是 A。本 spec 定义 stock-deep-research。

---

## stock-deep-research 的两类输出

```
stock-deep-research 产出：

战略层（相对稳定，跨天可复用）
  → strategic_memo_{sym}.json         ← 本 spec 重点定义
  → 有效期：由 valid_until 字段控制

战术层（每日刷新，依赖当日价格）
  → findings/entry_decision_{date}.json   ← premarket_decision.py 产出
  → findings/exit_decision_{date}.json    ← premarket_exit_sheet.py 产出
  → 有效期：仅当日有效，次日必须重算
```

---

## strategic_memo 字段定义

### 基础层（最稳定，背景知识）

| 字段 | 类型 | 格式 | 更新频率 |
|------|------|------|---------|
| `company_intro` | A | 文本，≤200字 | 季度或重大事件后 |
| `sector_intro` | A | 文本，≤150字 | 季度 |
| `fundamentals_snapshot` | B | 见下方 schema | 每次财报后 |

```json
"fundamentals_snapshot": {
  "pe_ttm": float,
  "pe_fwd": float,
  "peg": float,
  "revenue_growth_pct": float,
  "fcf_B": float,
  "analyst_target": float,
  "analyst_upside_pct": float,
  "last_updated": "YYYY-MM-DD"
}
```

---

### 支撑与风险层（建立在事实上的分析）

| 字段 | 类型 | 格式 |
|------|------|------|
| `core_supporting_facts` | A+B | 列表，每条≤80字，2-3条 |
| `main_risks` | A+B | 列表，含竞争替代子项，每条≤80字 |
| `tail_risk` | B | 见下方 schema |
| `macro_fit` | B | 见下方 schema |
| `liquidity_env` | B | 枚举 + 文本 |
| `technical_stage` | B | 枚举 |
| `sector_relative_strength` | B | 枚举 + 数字 |
| `next_catalyst` | B | 见下方 schema |

```json
"tail_risk": {
  "max_loss_scenario": "string ≤100字",       // A 级，人类可读，不参与编程集成
  "structural_fragility": "string ≤100字",    // A 级，人类可读，不参与编程集成
  "estimated_max_loss_pct": float              // B 级，参与规则4判断
}

"macro_fit": {
  "active_headwinds": ["rate_up", "dollar_strong"],  // 枚举集合
  "active_tailwinds": [],
  "headwind_count": int,
  "assessment": "favorable | neutral | challenging"  // 枚举
}

"liquidity_env": {
  "fed_direction": "tightening | neutral | easing",  // 枚举
  "credit_spread_trend": "widening | stable | narrowing",  // 枚举
  "institutional_flow": "inflow | neutral | outflow",  // 枚举
  "note": "string ≤80字"
}

"technical_stage": {
  "stage": "1" | "2" | "3" | "4",  // 字符串枚举，四个独立值（非组合）
  "note": "string ≤60字"
  // 规则匹配示例：stage == "3" OR stage == "4" → 触发规则1
}

"sector_relative_strength": {
  "trend": "outperforming | inline | underperforming",  // 枚举
  "period_days": int,
  "note": "string ≤60字"
}

"next_catalyst": {
  "event": "string",
  "date": "YYYY-MM-DD | unknown",
  "importance": "high | medium | low"  // 枚举
}
```

---

### 判断层（在充分了解数据后形成的综合判断）

| 字段 | 类型 | 格式 |
|------|------|------|
| `thesis_quality_score` | B | 1-10 整数 + 一句话说明 |
| `thesis_lifecycle_stage` | B | 枚举 |
| `falsifiability_quality` | B | 枚举 |
| `best_vehicle` | B | 枚举 + 说明 |
| `master_votes` | B | 见下方 schema（投票，非自由叙述）|
| `unified_confidence` | B | 1-5 整数 |

```json
"thesis_lifecycle_stage": {
  "stage": "early | mid | late",  // 枚举
  "note": "string ≤60字"
}

"falsifiability_quality": {
  "rating": "clear | adequate | vague",  // 枚举
  "note": "string ≤60字"
}

"best_vehicle": {
  "is_best_vehicle": true | false,  // 布尔，B 级
  "alternatives": ["SYM1", "SYM2"],  // 列表，来自 CIO SectorAgent 对同板块标的的分析，非用户输入
  "reason": "string ≤80字"  // A 级，人类可读
}
```

**大师投票（可复现的核心设计）：**

每位大师回答 3 个结构化问题，从枚举集合中选择，不生成自由文字：

```json
"master_votes": {
  "minervini": {
    "supports_holding": "strong_yes | yes | neutral | no",
    "primary_concern_type": "technical | macro | fundamental | liquidity",
    "position_direction": "add | hold | reduce | exit",
    "core_argument": "string ≤60字"  // 唯一允许的自由文本，限60字
  },
  "druckenmiller": { ... },
  "marks": { ... },
  "lynch": { ... },
  "soros": { ... },
  "livermore": { ... },
  "taleb": { ... },
  "_summary": {
    "bullish_count": int,
    "neutral_count": int,
    "bearish_count": int,
    "dominant_concern": "technical | macro | fundamental | liquidity | none"
    // 规则：统计 primary_concern_type 各类别票数，取最多者；
    // 若平票（两类或以上票数相同）→ "none"
  }
}
```

---

### 合成层（矛盾显式化 + 综合结论）

**矛盾类型（枚举，从中选 ≥0 个）：**

```json
"main_tensions": [
  // 从以下枚举集合中选择（可多选）:
  // "strong_fundamentals_macro_headwind"
  // "intact_thesis_late_lifecycle"
  // "bullish_masters_poor_technical"
  // "good_quality_poor_liquidity"
  // "thesis_intact_weak_falsifiability"
  // "none"
]
```

**矛盾解决规则（规则驱动，不由 LLM 自由判断）：**

规则按优先级排序，**第一条命中即停止**，不叠加后续规则：

```
规则1: technical_stage.stage == "3" OR technical_stage.stage == "4"
       → resolution_logic = "technical_wins"
       → strategic_stance = "reduce" 或 "exit_ready"（视 unified_confidence 决定，≥3 → reduce，<3 → exit_ready）

规则2: macro_fit.headwind_count >= 3
       → resolution_logic = "macro_wins"
       → strategic_stance = "hold_reduced"

规则3: thesis_lifecycle_stage.stage == "late"
       → resolution_logic = "lifecycle_wins"
       → strategic_stance = "reduce"

规则4: tail_risk.estimated_max_loss_pct > 30
       → resolution_logic = "inconclusive"
       → strategic_stance 降一档（strong_hold→hold，hold→hold_reduced，hold_reduced→reduce）

规则5（默认）: 以上均不触发
       → resolution_logic = "fundamentals_wins"
       → strategic_stance 由 thesis_quality_score 决定：
           ≥8 → "strong_hold"
           6-7 → "hold"
           4-5 → "hold_reduced"
           ≤3 → "reduce"
```

**`synthesis` schema（B 级固定）：**

```json
"synthesis": {
  "main_tensions": ["enum"],  // 从枚举集合多选，顺序按枚举定义顺序排列，用 "; " 连接展示
  "resolution_logic": "fundamentals_wins | macro_wins | technical_wins | lifecycle_wins | inconclusive",
  "strategic_stance": "strong_hold | hold | hold_reduced | reduce | exit_ready | avoid",
  "confidence": 1 | 2 | 3 | 4 | 5,
  "key_condition": "string ≤50字（A 级，人类可读，不参与编程集成）"
}
```

注：`main_tensions` 是列表，展示时用 `"; "` 连接成字符串，顺序固定（按枚举定义顺序）以保证可复现。

---

### 展望层

```json
"exit_logic": {
  "target_reached": "string ≤80字（A 级，人类可读，不参与编程集成）",
  "proactive_exit_signal": "string ≤80字（A 级，人类可读，不参与编程集成）"
}

"valid_until": "YYYY-MM-DD | next_earnings | next_catalyst_event"  // 枚举或日期
```

---

## 完整 strategic_memo schema（层次结构）

```json
{
  "sym": "string",
  "analysis_date": "YYYY-MM-DD",
  "analyst": "CIO-phases013",

  "foundation": {
    "company_intro": "string",
    "sector_intro": "string",
    "fundamentals_snapshot": { ... }
  },

  "support_and_risk": {
    "core_supporting_facts": ["string", "string"],
    "main_risks": ["string", "string"],
    "tail_risk": { ... },
    "macro_fit": { ... },
    "liquidity_env": { ... },
    "technical_stage": { ... },
    "sector_relative_strength": { ... },
    "next_catalyst": { ... }
  },

  "judgment": {
    "thesis_quality_score": int,
    "thesis_quality_note": "string ≤60字",
    "thesis_lifecycle_stage": { ... },
    "falsifiability_quality": { ... },
    "best_vehicle": { ... },
    "master_votes": { ... },
    "unified_confidence": int
  },

  "synthesis": {
    "main_tensions": ["enum"],
    "resolution_logic": "enum",
    "strategic_stance": "enum",
    "confidence": int,
    "key_condition": "string ≤50字"
  },

  "outlook": {
    "exit_logic": { ... },
    "valid_until": "string"
  }
}
```

---

## 可复现性保证

**LLM 在 stock-deep-research skill 中的角色：**

| 任务 | LLM 行为 | 级别 | 输出约束 |
|------|---------|------|---------|
| 填写 company_intro / sector_intro | 自由生成 | A | 字数上限（人类可读，不集成）|
| 填写 tail_risk 描述文本 | 自由生成 | A | 字数上限（人类可读，不集成）|
| 填写 exit_logic 文本 | 自由生成 | A | 字数上限（人类可读，不集成）|
| 填写 key_condition | 自由生成 | A | ≤50字（人类可读，不集成）|
| 列举 main_risks / core_facts | 从数据提取 | A+B | 数量上限，每条字数上限 |
| 填写 master_votes | 从枚举中选择 | B | 固定选项集，每次相同选项集 |
| 识别 main_tensions | 从枚举中多选 | B | 固定枚举集 |
| 填写 tail_risk.estimated_max_loss_pct | 数值估算 | B | 浮点数，参与规则4 |
| 计算 resolution_logic | **规则驱动，LLM 不参与** | B | 第一匹配规则决定，完全确定 |
| 推导 strategic_stance | **规则驱动，LLM 不参与** | B | 由 resolution_logic + 附加条件决定 |
| 展示 main_tensions | 枚举列表按定义顺序排列 | B | "; " 连接，顺序固定 |

**可复现性来源**：
- B 级字段：枚举约束 + 规则驱动推导，完全确定性
- A 级字段：字数上限约束，允许表述差异，**不参与编程集成**，仅供人类阅读
- 集成层只读 B 级字段

---

## Validation

1. 对同一只股票用同样数据运行两次 → `synthesis.strategic_stance` 相同（规则驱动，无随机性）
2. `master_votes._summary.dominant_concern` 由投票结果自动计算，平票时固定输出 "none"
3. 规则遵守性验证：构造触发各规则的单元测试输入（如 stage="3"），验证 resolution_logic 和 strategic_stance 输出符合规则表；此项需要 mock 测试，不能仅从输出文件自动验证
4. `synthesis.main_tensions` 列表顺序固定（按枚举定义顺序）：同一组 tensions 多次运行后顺序相同
5. strategic_memo 可被 stock-premarket skill 读取，且 B 级字段路径稳定（A 级字段路径同样稳定，但内容可变）
6. `valid_until` 字段使 premarket skill 能判断 memo 是否过期，过期后触发重新生成提示

---

## Out of Scope

- stock-premarket 及其他 skill 的格式标准化（后续 brainstorm）
- strategic_memo 与盘前分析的集成层（premarket skill 读取 memo 的具体逻辑，依赖本 spec 完成后定义）
- 大师 `core_argument` 字段的内容质量保证（属于 prompt engineering，非本 spec 范围）
