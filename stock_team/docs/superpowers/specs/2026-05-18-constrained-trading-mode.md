# 简化交易框架（Constrained Mode）— Design Spec

**Date**: 2026-05-18  
**Status**: Approved  
**Background**: 全天高强度盯盘不可持续，需要设计一个"约束交易模式"，将交易活动限制在开盘后第一小时，之后由预设 GTC 单接管。

---

## 核心原则

1. **不删除任何现有组件**——所有指标、大师评分、轮询功能保留，第一小时内继续使用
2. **加约束层，不换系统**——原有 active 模式保留作为可选项
3. **前一小时仍然主动参与**——不是甩手掌柜，而是聚焦、高效的参与
4. **盘前分析质量提升**——从2分钟快照式变为深度一次性分析

---

## 工作流设计

### 阶段一：深度盘前分析（09:00–09:25 ET）

比现在更深入，不再是方向判断，而是产出具体的执行计划。

**输入**：
- `quick_fundamentals.py` — 标的基本面数据
- `macro_agent.py` + `market_regime.json` — 宏观环境
- `premarket_checklist.py` — 持仓论点状态
- overnight narrative — 昨夜盘后信号

**产出（新增）**：
- 今日2只关注标的的**条件订单表**
- 每只标的的**取消条件**（可观测，开盘即知）
- 今日**热手/冷手状态**（基于近5-10笔交易质量，非今日计数）
- 大师的**深度评分**（完整论点分析，非2分钟快照）

### 阶段二：开盘观察期（09:30–10:00 ET，前30分钟）

**定位**：观察 + 校准，不轻易入场

**轮询**：2分钟继续运行，关注：
- 开盘方式是否符合盘前预判（高开高走 vs 高开低走）
- 宏观拐点（`check_macro_pivot()` 继续运行）
- 大盘环境确认（sector 是否配合）

**允许的操作**：
- 入场价校准：±1×ATR/2（不是随意调整）
- 止损收紧（只能收紧，不能放宽）
- 仓位调整：基于 Flex 信号强度（±50%）

**不允许**：入场新仓位（这30分钟是观察期）

### 阶段三：执行窗口（10:00–10:30 ET，后30分钟）

**定位**：执行期，满足条件则入场并挂 GTC 单

**决策**（二元，不复杂）：
```
满足条件 → 执行入场 + 挂 GTC 止损 + 挂 GTC 目标价 + 走人
不满足条件 → 取消今日计划，不交易
```

**仍然监控**：宏观拐点（随时可能取消计划）

### 阶段四：走人（10:30 ET 之后）

- 轮询停止（或降频至30分钟/次纯监控）
- GTC 单自动管理止损和止盈
- 用户不再主动干预
- 16:30 ET `harvest_agent` 自动运行

---

## 条件订单表格式（新模块输出）

```
【今日条件订单表】{date}

标的: LITE $883（当前盘前价）
────────────────────────────────
入场条件（前30分钟观察期核查）:
  ✓ 开盘在 $860-905 区间（偏差±ATR=$89）
  ✓ QQQ 开盘不跌超 -1%
  ✓ LITE 不破今日盘前低点 $857

入场参数（后30分钟执行）:
  入场价: $870 限价
  仓位: 1股（可调至 0.5-2股，基于 Flex 信号）
  止损: $855 GTC（只能收紧）
  目标: $920 GTC（只能上调）

取消条件（任一满足则取消）:
  × QQQ 开跌 > -1.5%
  × LITE 跳空低开破 $855
  × 10:00 前宏观拐点出现且方向看空

Flex 加仓级别（后续触发，非今日）:
  Framework B: LITE $857 + 缩量守住 + MACD 正 → +1股
```

---

## 需要改造的组件

### 1. 新建 `premarket_order_sheet.py`

**功能**：整合盘前数据，生成条件订单表
**输入**：`quick_fundamentals`、`macro.json`、`positions.json`、`premarket_analysis`
**输出**：标准化条件订单表（文本 + JSON）

**关键函数**：
```python
def generate_order_sheet(symbols, date_str=None) -> dict:
    """
    为每只关注标的生成条件订单表。
    返回 {sym: {entry_conditions, params, cancel_conditions, flex_levels}}
    """
```

ATR 基础的入场区间计算：
```python
entry_range = (target_entry - 0.5 * atr14, target_entry + 0.5 * atr14)
```

### 2. `poll_config.json` 加 `trading_mode` 字段

```json
{
  "trading_mode": "constrained",  // "constrained" | "active"
  "trading_window": {"start": "09:30", "end": "10:30"},
  "post_window_interval_min": 30  // 10:30后轮询间隔（分钟）
}
```

### 3. `poll.py` 加时间门控

在 `run_poll()` 内，检查当前时间：
- 09:30–10:30 ET + `trading_mode == "constrained"` → 正常运行所有信号
- 10:30 ET 之后 → 屏蔽入场信号（strategy_gate 不输出 buy），只输出持仓监控和止损警报

```python
in_trading_window = (9*60+30 <= et_h*60+et_m <= 10*60+30)
if not in_trading_window and trading_mode == "constrained":
    # 只运行持仓监控，不运行入场信号
```

### 4. `get_time_window()` 简化

**调用点审计**：函数在 `poll.py` 中只有一个调用点（约第1997行），调用方式为：
```python
_win_name, _win_hint = get_time_window(et_h, et_m)
if _win_name:  # 已处理 None 返回，向后兼容
    print(...)
```
因此修改返回值为 constrained 模式下的2窗口（窗口外返回 None），不会破坏任何下游代码。

从4个窗口改为2个：

```python
def get_time_window(et_h, et_m, trading_mode="constrained"):
    t = et_h * 60 + et_m
    if trading_mode == "constrained":
        if 9*60+30 <= t < 10*60:
            return ("开盘观察期", "观察开盘方式，参数校准，不入场")
        if 10*60 <= t < 10*60+30:
            return ("执行窗口", "满足条件则入场挂 GTC 单")
        return (None, None)  # 窗口外不显示
    # active 模式保留原有4窗口逻辑
```

### 5. `calc_trading_state()` 改为近N笔质量

**原逻辑**：当日矛盾计数 + 今日浮盈峰值
**新逻辑**：读取最近5-10笔交易记录，计算：
- 方向正确率（高分时对了几次）
- 执行质量（是否按计划执行，还是情绪化操作）
- 止损触发率（触发止损的比例）

**数据来源**：CHANGELOG.md 的交易记录或新建 `learning/trade_log.json`

### 6. `premarket_checklist.py` 加取消条件输出

在 `_format_held()` 和 `_format_watch()` 中，新增一段：

```
【取消条件】今日若以下任一发生则取消计划：
  × QQQ 开跌 > -1.5%
  × 标的跳空低开破今日盘前低点
  × 宏观拐点且方向看空
```

### 7. 盘前大师分析升级

`premarket_checklist.py` 在生成清单时，对2只关注标的各运行一次完整大师分析：
- 不是2分钟快照评分
- 是完整的"论点健康 + 宏观适配 + 技术位置 + 置信度/证伪"
- 输出写入 `findings/premarket_masters_{date}.json`

---

## 配置开关

`poll_config.json` 控制模式：

```json
{
  "trading_mode": "constrained",
  "trading_window": {"start_et": "09:30", "end_et": "10:30"},
  "post_window_poll_interval_min": 30,
  "pre_window_deep_analysis": true
}
```

**constrained 模式**（新增，默认推荐）：
- 盘前深度分析 + 条件订单表
- 第一小时完整监控
- 10:30后降频至30分钟/次

**active 模式**（保留原有）：
- 全天2分钟轮询
- 所有盘中信号正常运行
- 适合需要高频交易的日子

---

## 不改变的部分

- 所有技术指标（乖离率、缩量回踩、极端速度、Flex信号）— 在第一小时内继续使用
- 宏观拐点检测 — 第一小时继续运行
- evaluate_thesis_health() — 不变
- harvest_agent.py — 不变
- 大师角色扮演规则（CLAUDE.md）— 不变
- positions.json 结构 — 不变

---

## Validation

1. constrained 模式下，10:30 后 poll 不输出入场信号（只显示持仓监控）
2. `premarket_order_sheet.py` 对 LITE 输出包含入场条件/价格/止损/取消条件的完整表格
3. `get_time_window()` 在 constrained 模式只返回两个窗口，窗口外返回 None
4. `calc_trading_state()` 基于近5笔交易而不是今日计数
5. active 模式行为与现在完全一致（向后兼容）
