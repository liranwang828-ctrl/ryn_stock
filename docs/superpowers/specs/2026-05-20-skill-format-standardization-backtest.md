# Skill 格式标准化：stock-backtest — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 定义 stock-backtest skill 的输出契约，即 `backtest_result_{date}.json`（每次运行）和 `backtest_log.jsonl`（历史追加）的完整 schema、三种触发模式、自动阈值更新规则

---

## 背景

`backtest_engine.py` 已实现信号阈值扫描（`scan`）和框架模拟（`simulate`），输出两个格式松散的 JSON 文件。问题：
1. 阈值更新缺乏判断依据的记录（improvement_pp 未存档）
2. 历次运行结果无法对比（无追加日志）
3. dashboard 无法展示胜率趋势

**目标**：建立结构化的 backtest 输出，支持冷启动、月度全量、周度增量三种模式，自动更新显著改善的阈值，并通过 `backtest_log.jsonl` 支持 dashboard 趋势展示。

---

## 架构决策

| 决策 | 结论 |
|---|---|
| 目的 | C：参数优化（scan）+ 策略验证（simulate），两者联动 |
| 触发频率 | 冷启动（一次性）+ 月度全量 + 周度增量 + 按需 |
| 冷启动数据 | yfinance 历史 10 年日线 OHLCV |
| 阈值更新 | A：自动更新（improvement_pp > 5pp AND 样本量充足） |
| 文件结构 | `backtest_result_{date}.json`（每次）+ `backtest_log.jsonl`（历史追加）|

---

## backtest_result_{date}.json

### 顶层结构

```json
{
  "meta":             { ... },
  "scan_results":     { ... },
  "simulate_results": { ... },
  "threshold_update": { ... },
  "llm_summary":      "string ≤200字"
}
```

---

### meta

```json
{
  "date":          "YYYY-MM-DD",
  "run_type":      "bootstrap | full | incremental",
  "symbols":       ["string"],
  "data_years":    int,              // bootstrap=10, full=2, incremental=N/A
  "data_from":     "YYYY-MM-DD",
  "data_to":       "YYYY-MM-DD",
  "sample_source": "yfinance_historical | observation_outcomes | mixed",
  "generated_at":  "ISO-timestamp"
}
```

---

### scan_results（B 级，仅 full / bootstrap 运行时存在；incremental 时为 null）

每个信号独立扫描最优阈值：

```json
{
  "ma20_dev_max": {
    "optimal":               float,   // 最优阈值候选值
    "current":               float,   // config/decision_thresholds.json 当前值
    "win_rate_at_optimal":   float,   // 使用最优阈值时的历史胜率
    "win_rate_at_current":   float,   // 使用当前阈值时的历史胜率
    "improvement_pp":        float,   // win_rate_at_optimal - win_rate_at_current（百分点）
    "sample_size":           int      // 满足该阈值条件的历史样本数
  },
  "rs5_min":      { ... },            // 同结构
  "vol_ratio_max": { ... }            // 同结构
}
```

**扫描范围限制**（来自现有 backtest_engine.py）：
- 仅覆盖可从历史 OHLCV 重建的信号：`ma20_dev / rs5 / vol_ratio`
- 不覆盖：`watchlist_score / analyst_target / rr_ratio / thesis_status`（需实时数据）

---

### simulate_results（B 级）

使用当次扫描的最优参数（或 incremental 时的当前参数）模拟入场框架：

```json
{
  "n_entries":         int,
  "win_rate":          float,
  "mean_ret_pct":      float,
  "median_ret_pct":    float,
  "max_drawdown_pct":  float,        // 单次最大亏损（不含持仓周期）
  "sharpe_proxy":      float,        // mean_ret / std_ret，非年化，仅作相对参考
  "hold_days":         int,          // 模拟使用的持有天数（默认 5）
  "vs_baseline": {
    "baseline_win_rate":       float,  // 无信号筛选时同期同标的的实际胜率：取同一历史数据集全部交易日（无任何 soft_veto 过滤），计算 fwd_5d > 0 的比例，非理论值 0.5
    "baseline_mean_ret":       float,  // 同上，取 fwd_5d 的平均值
    "win_rate_improvement_pp": float   // win_rate - baseline_win_rate（百分点）
  },
  "params_used": {
    "ma20_dev_max": float,
    "rs5_min":      float,
    "vol_ratio_max": float
  }
}
```

---

### threshold_update（B 级）

```json
{
  "triggered":       true|false,
  "reason":          "string ≤60字",      // 未触发时说明原因
  "updates_applied": [
    {
      "param":          "ma20_dev_max | rs5_min | vol_ratio_max",
      "old_value":      float,
      "new_value":      float,
      "improvement_pp": float,
      "sample_size":    int
    }
  ],
  "applied_at":  "ISO-timestamp | null"   // null = triggered=false
}
```

**`win_rate_at_current` 获取方式**：`_scan_signal` 扫描所有候选阈值并返回各阈值对应胜率列表，从中按 `current` 值查找对应胜率。若当前值不在候选列表中，取最近邻候选值的胜率作为近似。

**自动更新触发规则**（全部满足才更新）：
```
improvement_pp > 5.0               // 改善幅度足够显著
AND sample_size ≥ 20               // 样本量充足（_MIN_SAMPLES）
AND win_rate_at_optimal > 0.55     // 最优阈值绝对胜率过线
→ 自动写入 config/decision_thresholds.json
→ 记录到 threshold_update.updates_applied
```

incremental 运行只做验证，不更新阈值。阈值更新仅在 full / bootstrap 运行后触发。

---

### 增量滑落触发全量重扫规则

```
连续 4 次 incremental 运行：
  win_rate < 0.55（当前阈值已无效）
→ 自动追加调度：下次 monthly full 提前为本周运行
→ backtest_log 追加一条 {run_type: "triggered_full", reason: "连续4周滑落"}
```

---

## backtest_log.jsonl（历次运行追加）

路径：`findings/backtest_log.jsonl`，每次运行结束后追加一条（`"a"` 模式，不覆盖）：

```json
{
  "date":                    "YYYY-MM-DD",
  "run_type":                "bootstrap | full | incremental | triggered_full",
  "win_rate":                float,
  "n_entries":               int,
  "mean_ret_pct":            float,
  "vs_baseline_pp":          float,
  "threshold_updated":       true|false,
  "consecutive_low_weeks":   int,        // 连续 win_rate < 0.55 的增量运行次数；full/bootstrap 运行后重置为 0
  "params_snapshot": {
    "ma20_dev_max": float,
    "rs5_min":      float,
    "vol_ratio_max": float
  }
}
```

**4 周滑落触发机制**：每次增量运行后，读取 `backtest_log.jsonl` 最近 N 条 incremental 记录，统计 `win_rate < 0.55` 的连续数量，写入 `consecutive_low_weeks`。当该值 ≥ 4 时，本次结果的 `run_type` 写为 `"triggered_full"`，并在下次调度时自动触发全量重扫。full/bootstrap 运行后将 `consecutive_low_weeks` 重置为 0。

---

## 三种触发模式对比

| 属性 | 冷启动（bootstrap）| 全量（full）| 增量（incremental）|
|---|---|---|---|
| 频率 | 一次性 | 月度 + 按需 | 周度 |
| 数据来源 | yfinance 历史 10 年 | yfinance 历史 2 年 | yfinance 近 4 周（仅 observation_outcomes 涉及的标的）|
| scan_results | ✅ | ✅ | null（不重扫）|
| simulate_results | ✅ | ✅ | ✅（用当前阈值验证）|
| threshold_update | ✅（若改善显著）| ✅（若改善显著）| ❌（不更新）|
| 触发全量重扫 | — | — | 连续 4 周滑落时触发 |

**增量数据来源说明**：`observation_outcomes.jsonl` 用于确定"本周哪些标的有实盘信号记录"（不直接计算 win_rate）。增量 simulate 仍从 yfinance 拉取这些标的近 4 周日线 OHLCV，计算 `fwd_5d`，与现有 `simulate_decision_framework` 逻辑一致，仅缩小标的范围和时间窗口。

---

## dashboard 字段映射

| 字段 | Tab |
|---|---|
| `backtest_log.jsonl` win_rate 时序 | 回测 Tab（胜率趋势折线图，按 run_type 分色）|
| `simulate_results.vs_baseline` | 总览（策略有效性：vs 随机基准的改善 pp）|
| `threshold_update.updates_applied` | 回测 Tab（参数变更历史时间轴）|
| `scan_results`（各信号 improvement_pp）| 回测 Tab（各信号扫描对比表）|
| `simulate_results.params_used` | 回测 Tab（当次使用参数）|

---

## 与现有输出文件的关系

现有 `backtest_engine.py` 写出：
- `findings/signal_thresholds_optimized.json`（scan 结果）
- `findings/backtest_results_{date}.json`（simulate 结果，注意是复数 `results`）

本 spec 定义新文件 `findings/backtest_result_{date}.json`（单数 `result`，合并 scan + simulate + update 三层）。实施时两套文件并存，旧文件保留向后兼容，新文件作为下游 dashboard 的唯一读取来源。

---

## TODO（实施后待执行）

> ⚠️ 以下两项回测**从未运行过**，当前 `decision_thresholds.json` 的阈值是手动默认值，未经历史验证。

1. **2 年全量回测（full）**：实施完成后首先执行，验证当前阈值是否合理，输出 `backtest_result_{date}.json`
2. **10 年冷启动（bootstrap）**：需新版 backtest_engine 支持 `--years 10` 和 `run_type=bootstrap` 参数，建立初始阈值基准

详见 `docs/TODO.md` 回测冷启动条目。

---

## Out of Scope

- `observation_outcomes.jsonl` 格式定义（由 harvest_agent.py 维护）
- backtest 对更多信号的扩展（catalyst_type / RR 等，待实盘数据积累后再设计）
- `daily_dashboard.html` 完整实现（独立 spec）
- position-builder / trading-day skill 格式标准化（后续 brainstorm）
