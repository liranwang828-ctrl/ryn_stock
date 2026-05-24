# 出场决策模块 — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 与入场决策对称的持仓出场评估模块，盘前为每只持仓生成三态出场建议和今日止损价位

---

## Goal

入场框架（premarket_decision.py）已完整，但持仓侧缺少对等模块。每天盘前，持仓股应和关注股一样经过系统性评估：今天是否应该出场/减仓/继续持有？止损在哪里？本模块解决这个缺口。

---

## Architecture

```
新建文件：
  agents/premarket_exit_sheet.py
    evaluate_exit(sym, pos_cfg, macro) -> dict          # 单只持仓出场评估（内部获取实时价）
    generate_exit_sheet(pos_syms) -> dict               # 批量生成
    write_exit_decision(decisions, findings_dir) -> None # 写 JSON
    fmt_exit_sheet(decisions) -> str                    # 格式化输出

运行时生成：
  findings/exit_decision_{date}.json

集成位置：
  session_manager.py node 0 Step 3.7（持仓健康之后，焦点选股之前）
  premarket_decision.py main() 末尾（入场/出场并列调用）
```

**与入场模块的对称关系：**

| 维度 | 入场（premarket_decision）| 出场（premarket_exit_sheet）|
|---|---|---|
| 输入标的 | 焦点股（today_focus.json）| 当前持仓（positions.json）|
| 三态 | 可入场 / 观察 / 不入场 | 应出场 / 考虑减仓 / 继续持有 |
| 输出文件 | findings/entry_decision_{date}.json | findings/exit_decision_{date}.json |
| CLI | `python3.12 agents/premarket_decision.py LITE` | `python3.12 agents/premarket_exit_sheet.py` |

---

## 止损价位计算（两层）

### 硬止损（hard_stop）— 触发立即出场

优先级顺序：

1. `positions.json` 的 `t1_stop_snapshot`（非 None 且非 0 即认定为手工设置，最可靠）→ `stop_source: "manual_gtc"`
2. `positions.json` 的 `node1`（论点支撑位，手工填写，非 None 且非 0）→ `stop_source: "node1"`
3. yfinance 计算：`lo5 - ATR14 × 0.3`（标注 ⚠️ 需确认）→ `stop_source: "auto_atr"`

判定逻辑：`t1_stop_snapshot not in (None, 0)` → manual_gtc；否则 `node1 not in (None, 0)` → node1；否则 → auto_atr。

### 软止损（soft_stop）— 触发考虑减仓

= 持仓成本（`t1_cost` 或 `cost`），价格跌破成本 = 浮亏。

### 辅助指标

- `hard_dist_pct`：`(cur - hard_stop) / cur × 100`，负数表示已跌破
- `rr_remaining`：`(target - cur) / (cur - hard_stop)`，需 target 在 positions.json 中可估

---

## 三态出场判断

### 应出场（硬触发，任一满足）

| 触发条件 | 数据来源 | 自动判断 |
|---|---|---|
| 价格 < hard_stop | yfinance 现价 | ✅ 自动 |
| thesis_status = "broken" | positions.json | ✅ 自动 |
| 时间证伪条件已过期（今天或更早）| falsification_conditions 文本解析 | ✅ 自动 |
| 所有基本面证伪条件已触发 | falsification_conditions | ⚠️ 需人工确认（系统只展示，不自动判定）|

### 考虑减仓（软触发，≥1 满足）

| 触发条件 | 数据来源 |
|---|---|
| thesis_status = "weakening" | positions.json |
| 价格在 soft_stop 和 hard_stop 之间（浮亏区）| yfinance |
| hard_dist_pct < 3%（距硬止损不足 3%）| 计算 |
| rr_remaining < 1.0（剩余盈亏比已不划算）| 计算 |
| 时间证伪条件将在 ≤3 天内到期 | falsification_conditions 文本解析 |

### 继续持有

以上所有触发条件均不满足。

### 证伪条件的处理方式

`falsification_conditions` 列表中的条件分两类：
- **可自动检测**：含日期字符串的时间条件（如"截止 2026-06-02"）→ 自动解析并判断是否到期
- **需人工确认**：基本面事件（如"大客户减单"、"财报 miss"）→ 系统展示为 `⚠️ 请确认是否已触发`，不自动判断为已触发

---

## 输出格式

### 控制台输出

```
【今日持仓出场评估】2026-05-20

MRVU  ⚠️ 考虑减仓
  硬止损 $76.00（GTC 已挂）  现价 $88.42  距硬线 +14.0%
  软止损（成本）$102.50  现价 < 成本，浮亏 -13.7%（浮亏区）
  触发：价格在软硬止损之间（浮亏区）+ 时间证伪条件 2 天内到期
  ⚠️ 请确认证伪条件：路径/时间成本（截止 2026-05-22，还有 2 天→≤3天软触发）

LITE  ❌ 应出场
  硬止损 $855.00（GTC 已挂）  现价 $848.20  距硬线 -0.8%（已在止损下方）
  触发：价格 < 硬止损

BABA  ✅ 继续持有
  硬止损 $130.41（⚠️ ATR估算，建议设 GTC）  现价 $141.00  距硬线 +8.1%
  软止损（成本）$141.00  现价 = 成本，处于盈亏平衡线
```

注：`hard_dist_pct = (cur - hard_stop) / cur × 100`，正数表示价格高于止损，负数表示已跌破。

### JSON 输出（`findings/exit_decision_{date}.json`）

```json
{
  "date": "2026-05-20",
  "positions": {
    "MRVU": {
      "decision":              "考虑减仓",
      "hard_stop":             76.0,
      "soft_stop":             102.5,
      "stop_source":           "manual_gtc",
      "cur":                   88.42,
      "hard_dist_pct":         14.0,
      "hard_triggers":         [],
      "soft_triggers":         ["price_in_loss_zone", "time_condition_expiring_2d"],
      "falsification_check":   ["路径/时间成本（截止 2026-05-22，还有 2 天）"],
      "rr_remaining":          null,
      "reason":                "浮亏区 + 时间证伪条件 2 天内到期（≤3天软触发）"
    },
    "LITE": {
      "decision":              "应出场",
      "hard_stop":             855.0,
      "soft_stop":             870.0,
      "stop_source":           "manual_gtc",
      "cur":                   848.2,
      "hard_dist_pct":         -0.8,
      "hard_triggers":         ["price < hard_stop"],
      "soft_triggers":         [],
      "falsification_check":   [],
      "rr_remaining":          null,
      "reason":                "价格已低于硬止损"
    },
    "BABA": {
      "decision":              "继续持有",
      "hard_stop":             130.41,
      "soft_stop":             141.0,
      "stop_source":           "auto_atr",
      "cur":                   141.0,
      "hard_dist_pct":         8.1,
      "hard_triggers":         [],
      "soft_triggers":         [],
      "falsification_check":   [],
      "rr_remaining":          null,
      "reason":                "无触发条件"
    }
  }
}
```

---

## Node 0 集成

在 `session_manager.py` 的 Step 3（持仓健康）之后，新增 **Step 3.7**：

```python
# Step 3.7: 持仓出场评估
lines.append("\n【Step 3.7】持仓出场评估")
try:
    from agents.premarket_exit_sheet import generate_exit_sheet, fmt_exit_sheet
    _exit_decisions = generate_exit_sheet(pos_syms)
    lines.append(fmt_exit_sheet(_exit_decisions))
    # 写 exit_decision_{date}.json
    from agents.premarket_exit_sheet import write_exit_decision
    write_exit_decision(_exit_decisions)
except Exception as _e:
    lines.append(f"  出场评估失败: {_e}")
```

---

## 关键函数签名

```python
def evaluate_exit(sym: str, pos_cfg: dict, macro: dict) -> dict:
    """
    对单只持仓进行出场评估。在函数内部通过 yfinance 获取实时价格和技术数据
    （ATR14、lo5），调用方不需要传入 tech 参数。
    返回 {decision, hard_stop, soft_stop, stop_source, cur,
           hard_dist_pct, hard_triggers, soft_triggers,
           falsification_check, rr_remaining, reason}
    """

def generate_exit_sheet(pos_syms: list) -> dict:
    """
    批量评估持仓列表，返回 {sym: evaluate_exit() 结果}。
    从 positions.json 读取持仓配置，从 yfinance 获取实时价格。
    """

def write_exit_decision(decisions: dict, findings_dir: str = None) -> None:
    """
    写入 findings/exit_decision_{date}.json。
    """

def fmt_exit_sheet(decisions: dict) -> str:
    """
    格式化为人类可读输出，含 ❌/⚠️/✅ 标记。
    """
```

---

## CLI 用法

```bash
# 评估所有当前持仓
python3.12 agents/premarket_exit_sheet.py

# 评估指定持仓
python3.12 agents/premarket_exit_sheet.py MRVU BABA
```

---

## Validation

1. `evaluate_exit("LITE", pos_cfg_with_stop=855, ...)` 对现价 $848（< $855 硬止损）→ 输出 `decision="应出场"`，`hard_triggers=["price < hard_stop"]`，`hard_dist_pct < 0`
2. `generate_exit_sheet(["BABA"])` 对无止损数据的持仓 → `stop_source="auto_atr"`，输出含 ⚠️ 提示
3. 含时间截止日期的 falsification_condition（如"截止 2026-05-01"的过期条件）→ 自动识别为已触发
4. 未来日期（"截止 2026-05-22"，还有 2 天）→ ≤3天，作为软触发；若日期改为 13 天后 → >3天，不触发
5. `findings/exit_decision_{date}.json` 写入后包含 positions 字段和每只持仓的完整结果
6. Node 0 运行后在 Step 3.7 显示出场评估

---

## Out of Scope

- 自动执行出场操作（保持人工确认）
- 基本面证伪条件的自动判断（需要实时新闻/财务数据，目前不可用）
- 期权/对冲出场策略
