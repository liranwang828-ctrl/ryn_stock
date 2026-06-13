# 交易决策规则显性化 + 历史回测引擎 — Design Spec

**Date**: 2026-05-19
**Status**: Draft
**Scope**: 两个子系统：盘前分层否决决策框架 + 历史信号回测引擎

---

## Goal

解决两个核心问题：

1. **唯一性**：当前盘前入场决策是定性的（大师分析→人工判断），需要显性化为可量化、可执行的分层否决规则
2. **可靠性**：用历史数据扫描各信号最优阈值，用实盘数据验证催化剂层，逐步建立对系统的数据支撑信心

---

## Architecture

```
config/decision_thresholds.json          ← 阈值配置（回测可更新，决策框架读取）
agents/premarket_decision.py             ← 子系统1：分层否决逻辑
agents/backtest_engine.py                ← 子系统2：参数扫描 + 规则回测
findings/signal_thresholds_optimized.json   ← 回测输出：各信号最优阈值
findings/backtest_results_{date}.json       ← 回测输出：详细记录
```

闭环关系：`backtest_engine` 输出最优阈值 → 写入 `decision_thresholds.json` → `premarket_decision` 读取执行 → 实盘记录积累 → 季度重新回测

实施顺序：**子系统1先行**（用默认阈值立即可用）→ 子系统2验证并优化阈值

---

## 子系统1：盘前分层否决决策框架

### 输入

| 来源 | 字段 |
|------|------|
| `premarket_order_sheet` | rr_ratio, overnight_note, entry_range |
| `premarket_watchlist_score` | score（总分） |
| `findings/macro.json` | macro_score, macro_tone |
| `config/market_regime.json` | regime, overnight_signal |
| `config/positions.json` | thesis_status, macro_sensitivity, macro_type |
| yfinance 盘前 | QQQ 盘前涨跌幅 |

### 硬否决（任一触发 → 今日不入场）

按优先级排序，最高优先级先判断：

| 优先级 | 条件 | 默认阈值 | 数据来源 |
|--------|------|---------|---------|
| 1 | `thesis_status` = weakening / broken | — | positions.json |
| 2 | RR < 阈值 | 2.0x | order_sheet.rr_ratio |
| 3 | QQQ 盘前跌幅 > 阈值 | -1.5% | yfinance |
| 4 | `macro_score` < 阈值 | 4 | macro.json |
| 5 | `watchlist_score` < 阈值 | 50 | watchlist_score |
| 6 | overnight_note 含"区间失效" | — | order_sheet.overnight_note（系统生成固定字符串，非人工填写，`_get_overnight_data()` 产生） |

### 软否决（≥2个触发 → 观察，不入场）

| 条件 | 默认阈值 | 数据来源 |
|------|---------|---------|
| MA20乖离 > 阈值（追高） | +5% | yfinance 日线 |
| RS5日超额 < 阈值 | 0% | yfinance 日线 |
| 活跃宏观逆风项数 ≥ 阈值 | 2项 | positions.macro_sensitivity + macro.json |
| 大师置信度全部为"低" | — | 大师 brief |
| Regime 错位（热点板块与标的板块不匹配） | — | market_regime.json |
| Stage 2 结构不足（RS5日≤0 且 MA20不向上倾斜，两个条件同时成立才触发） | — | yfinance 日线 |

### 输出三态

```
可入场：0个硬否决 + ≤1个软否决
观察：  0个硬否决 + 2-3个软否决 → 开盘观察窗口内30分钟后必须给出是/否
不入场：≥1个硬否决
```

### 量比条件（移至观察窗口09:30-10:00）

盘前无当日量比数据，该条件在开盘观察期处理：
- 开盘量比 > 1.5x 且价格方向不利 → 触发取消，不执行入场

### 阈值配置文件格式

```json
{
  "_comment": "premarket_decision.py 读取，backtest_engine.py 更新",
  "_updated": "2026-05-19",
  "hard_vetoes": {
    "rr_min": 2.0,
    "qqq_premarket_min": -0.015,
    "macro_score_min": 4,
    "watchlist_score_min": 50
  },
  "soft_vetoes": {
    "ma20_dev_max": 0.05,
    "rs5_min": 0.0,
    "max_headwinds": 2
  },
  "macro_type_overrides": {
    "防御型": {"macro_score_min": 3},
    "大宗商品型": {"macro_score_min": 3}
  }
}
```

`macro_type_overrides` 可覆盖特定类别的阈值。默认统一阈值，回测验证后决定是否启用分组覆盖。

### 关键函数

```python
def evaluate_entry(sym: str, order_sheet: dict, score: int,
                   macro: dict, regime: dict, pos_cfg: dict,
                   qqq_premarket_chg: float,
                   thresholds: dict) -> dict:
    """
    返回 {
      decision: "可入场" | "观察" | "不入场",
      hard_vetoes: [str],
      soft_vetoes: [str],
      reason: str
    }
    """

def load_thresholds() -> dict:
    """读取 config/decision_thresholds.json，不存在则返回默认值"""
```

---

## 子系统2：历史回测引擎

### 双轨验证架构

**轨道A：历史信号回测**（技术 + 宏观代理指标）

- 标的：`poll_config.json` watchlist 中的趋势型标的
- 时间范围：近2-3年日线（yfinance）
- 宏观代理数据：VIX / DXY / 10Y收益率历史序列（yfinance 可获取）
- **明确局限**：不含消息面/催化剂，结论仅适用于技术+宏观维度

**轨道C：前向实盘验证**（催化剂层）

- 数据来源：`learning/observation_outcomes.jsonl`
- 新增字段：`has_catalyst`（bool）— 在 `harvest_agent.py` 写入时补充，利用现有 `catalyst_strength` 字段（>0 即为 True）
- 目标：积累50+条有/无催化剂记录后，比较两组胜率差异
- 预计时间：3-6个月

**汇合点**：每季度综合复盘，对比A轨历史结论与C轨实盘数据

### 阶段一：信号级参数扫描

对每个可量化信号，在阈值范围内做参数扫描：

| 信号 | 扫描范围 | 步长 |
|------|---------|------|
| MA20乖离（软否决上限） | +1% ~ +10% | 1% |
| RS5日超额（软否决下限） | -3% ~ +2% | 0.5% |
| macro_score（硬否决下限） | 3 ~ 6 | 1 |
| watchlist_score（硬否决下限） | 35 ~ 65 | 5 |
| RR（硬否决下限） | 1.5x ~ 3.0x | 0.25x |

每个阈值组合测试：触发信号当日入场，N天后（1/3/5日）的胜率和均值收益

输出：`findings/signal_thresholds_optimized.json`
```json
{
  "ma20_dev_max": {"optimal": 0.04, "win_rate": 0.62, "scan_date": "2026-05-19"},
  "macro_score_min": {"optimal": 5, "win_rate": 0.58, ...},
  ...
}
```

### 阶段二：规则级回测

将阶段一得到的最优阈值代入分层否决框架，模拟完整入场规则：

- 入场：框架输出"可入场"的日期
- 止损：以 order_sheet 逻辑计算（lo5 - 0.3×ATR）
- 止盈：目标价或 N 日强制平仓
- 统计：命中率、平均RR、最大回撤

### 阈值更新规则

回测完成后，若新阈值相较当前配置改善超过**5个百分点胜率**，才写入 `config/decision_thresholds.json`，避免过拟合噪音调整。

### 关键函数

```python
def run_signal_scan(sym: str, years: int = 2) -> dict:
    """对单只标的运行所有信号的参数扫描，返回各信号最优阈值"""

def run_portfolio_scan(symbols: list, years: int = 2) -> dict:
    """对标的列表汇总扫描结果（统一阈值有更大样本量）"""

def simulate_decision_framework(symbols: list, thresholds: dict,
                                 years: int = 2) -> dict:
    """规则级回测：用给定阈值模拟分层否决框架的历史表现"""
```

---

## Validation

1. **子系统1（不入场）**：对 MRVU 输入昨日真实数据（thesis=intact, RR=0.6x），框架应输出"不入场"（RR<2.0x 触发硬否决2）
2. **子系统1（可入场）**：对一只 watchlist_score=75、RR=3.5x、macro_score=6、0个软否决的标的，框架应输出"可入场"
3. **子系统1（观察）**：对一只0个硬否决、但触发2个软否决（MA20乖离+6% + RS5日超额-1.5%）的标的，框架应输出"观察"，不输出"可入场"
4. **子系统1（边界）**：触发恰好1个软否决时，框架应输出"可入场"而非"观察"
5. **子系统1（配置）**：阈值从 `decision_thresholds.json` 读取，修改配置文件后框架行为变化，不需改代码
6. **子系统2**：`run_signal_scan("MRVL", years=2)` 能正常运行并输出各信号最优阈值 JSON
7. **子系统2**：`simulate_decision_framework(["MRVL","RKLB"], thresholds, years=2)` 能输出胜率和平均RR
8. **轨道C**：`harvest_agent.py` 写入 observation_outcomes 时包含 `has_catalyst` 字段（来源：现有 `catalyst_strength` 字段，实现前需确认该字段已在 observation_outcomes.jsonl 中实际存在并有效填充）

---

## Out of Scope

- 消息面/新闻数据自动拉取（需专用数据源，P2）
- 期权数据回测（数据不可用，Tier4）
- 个股单独调阈值（样本量不足，统一+macro_type分组已足够）
- 实盘自动执行（保持人工确认）
