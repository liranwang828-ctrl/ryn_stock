# 回测 / 因子可信度摘要层设计

> 日期：2026-06-01
> 范围：把已有因子 IC、周度 OOS、参数稳定性和盘中随机搜索结果整理成可被 Decision State Hub、LLM 主控和 dashboard 消费的可信度证据
> 状态：已确认方向，待实施计划

## 中文摘要

本阶段不重写回测引擎，不重新调参，也不改变交易规则。目标是先新增一个 **证据可信度摘要层**，把现有结果翻译成清晰、保守、可复用的证据标签。

它读取现有文件：

- `findings/factor_ic_report.json`
- `findings/weekly_oos_validation_results.json`
- `config/best_weekly_params.json`
- 可选：`findings/random_search_v2_summary.json`

输出新文件：

- `findings/evidence_credibility_report.json`

这个报告会回答四个问题：

1. 哪些因子已经相对可靠，哪些只是探索性信号？
2. 回测表现是 time-OOS、style-OOS、full lifecycle 都支持，还是只在部分场景支持？
3. 当前最优参数是否稳定，还是可能只是局部最优？
4. 哪些证据必须提醒 LLM 和 dashboard 不能过度解释？

## 为什么先做摘要层

现在系统已经有因子 IC 和回测结果，但它们还不是“决策可用证据”：

- `factor_ic_report.json` 是统计结果，但没有统一的 `robust / usable / exploratory / insufficient` 标签。
- 情绪因子样本只有 2 周，数值看起来显眼，但应该被明确标为样本不足。
- `weekly_oos_validation_results.json` 里 time-OOS 是正 alpha，但 style-OOS alpha 为负，不能只展示总体收益。
- `best_weekly_params.json` 有 neighborhood sortino，但没有直接转成参数稳定性标签。
- `random_search_v2_summary.json` 说明盘中精确点位层还不是强 alpha 来源，这应进入可信度提醒，而不是被忽略。

所以第一阶段应先做“只读解释层”，把已有证据变成结构化可信度。

## 非目标

本阶段不做：

- 不改 `agents/backtest_*`
- 不改 `scripts/weekly_*`
- 不重跑完整回测
- 不改交易规则
- 不自动写回参数
- 不把 exploratory 因子提升成强信号
- 不做 dashboard UI

如果实施中发现回测引擎、因子计算或交易规则问题，只记录 TODO，不顺手改核心逻辑。

## 输出契约

`evidence_credibility_report.json` 建议结构：

```json
{
  "date": "2026-06-01",
  "generated_at": "2026-06-01T10:00:00+08:00",
  "factor_credibility": {
    "overall_verdict": "usable",
    "factors": {
      "5. Volatility (20d)": {
        "tier": "robust",
        "mean_ic": 0.0553,
        "ir": 0.2088,
        "t_stat": 2.18,
        "positive_weeks_pct": 61.5,
        "weeks_count": 109,
        "sample_label": "sufficient",
        "notes": ["当前最强因子，但仍应作为排序证据而非独立交易结论"]
      },
      "6. Sentiment Catalyst": {
        "tier": "insufficient",
        "weeks_count": 2,
        "sample_label": "too_small",
        "notes": ["样本只有 2 周，禁止作为强证据"]
      }
    }
  },
  "backtest_credibility": {
    "overall_verdict": "caution",
    "time_oos": {"alpha": 15.94, "mdd": -5.78, "verdict": "supportive"},
    "style_oos": {"alpha": -23.64, "mdd": -18.19, "verdict": "caution"},
    "full_lifecycle": {"return": 129.87, "mdd": -26.95, "verdict": "supportive"},
    "parameter_stability": {
      "tier": "usable",
      "best_sortino": 0.8522,
      "neighborhood_avg_sortino": 0.8508,
      "notes": ["邻域表现接近最优，初步说明参数不是孤点"]
    },
    "notes": ["style-OOS alpha 为负，LLM 和 dashboard 必须显式提示"]
  },
  "intraday_precision_credibility": {
    "tier": "exploratory",
    "best_pf": 1.2819,
    "best_return": 1.7871,
    "benchmark_return": 21.2192,
    "notes": ["盘中随机搜索 PF 略高于 1，但收益显著低于 QQQ，不能作为强 alpha 层"]
  },
  "decision_state_overrides": {
    "factor_quality": "usable",
    "backtest_verdict": "caution",
    "required_warnings": [
      "Sentiment Catalyst 样本不足",
      "Style-OOS alpha 为负",
      "盘中精确点位层仍属探索性"
    ]
  }
}
```

## 分级规则

### 因子分级

建议第一版使用保守阈值：

- `robust`：样本周数 >= 52，t-stat >= 2，Mean IC 绝对值 >= 0.04，正向周比例 >= 58%。
- `usable`：样本周数 >= 52，Mean IC 绝对值 >= 0.02，IR 为正，正向周比例 >= 52%。
- `exploratory`：样本周数 >= 8，但统计显著性不足。
- `insufficient`：样本周数 < 8，或字段缺失严重。

注意：负 IC 不自动等于无效，可能代表反向因子，但第一版不主动把它转换成交易方向，只标注需要人工解释。

### 回测分级

- `supportive`：time-OOS alpha 为正，最大回撤可接受，且 full lifecycle 没有明显崩坏。
- `caution`：至少一个关键样本外维度明显弱，例如 style-OOS alpha 为负。
- `reject`：time-OOS 和 style-OOS 都失败，或回撤超过系统可接受范围。
- `unavailable`：缺少报告或解析失败。

第一版中 style-OOS 负 alpha 不直接否定整套策略，但必须把总 verdict 从 `supportive` 降到 `caution`。

### 参数稳定性

第一版只用已有 `optimized_metrics`：

- 如果 `neighborhood_avg_sortino` 接近 `sortino`，参数稳定性为 `usable`。
- 如果邻域均值显著低于最优，标为 `fragile`。
- 如果字段缺失，标为 `unknown`。

后续完整系统优化时再做真正的参数曲面、bootstrap 和 walk-forward。

## Decision State Hub 集成

实施后，`agents/decision_state_hub.py` 应优先读取：

- `findings/evidence_credibility_report.json`

如果该文件不存在，则继续使用当前兼容逻辑：

- `factor_ic_report.json`
- `weekly_oos_validation_results.json`

这样可以渐进迁移，不破坏已有流程。

## LLM 主控纪律影响

本阶段会为后续 LLM 主控提供更明确的硬约束：

- `insufficient` 因子不能被 LLM 叙事升级成强证据。
- `caution` 回测不能被描述成“全面验证通过”。
- `style-OOS alpha 为负` 必须进入 `required_human_check` 或 dashboard warning。
- `intraday_precision_credibility = exploratory` 时，盘中精确点位只能作为执行辅助，不能作为主 alpha 来源。

## Dashboard / 可视化 Agent 笔记

这阶段不做 UI，但输出字段要服务后续可视化：

- 因子层：显示哪些因子强、哪些样本不足。
- 回测层：把 time-OOS、style-OOS、full lifecycle 三块并列展示。
- 风险层：把 `required_warnings` 做成醒目的复核队列。
- 参数层：显示参数稳定性，而不是只显示最优参数。

dashboard 自优化 agent 后续应检查：

- 用户是否能一眼看出“强证据”和“探索性证据”的区别。
- style-OOS 负 alpha 是否被隐藏。
- 情绪因子样本不足是否被误读成强信号。
- 盘中精确点位是否被过度突出。

## 完整系统优化目标

用户明确要求：长期标准要达到完整研究系统级别，而不只是摘要已有报告。

因此将“完整回测 / 因子可信度重建”列为后续系统优化目标：

1. 重新定义训练样本、验证样本、time-OOS、style-OOS、symbol-OOS。
2. 对因子做滚动 IC、分市场状态 IC、分行业/风格 IC。
3. 做因子相关性、冗余度和组合贡献分析。
4. 对策略参数做参数曲面、邻域稳定性、walk-forward 和 bootstrap。
5. 对交易执行层做 slippage、latency、成交约束和不同波动环境压力测试。
6. 用 Monte Carlo / bootstrap 生成收益、回撤、胜率、PF 的置信区间。
7. 把所有证据写入统一研究档案，供 LLM 主控引用和盘后审计。

这个目标不放进当前第一阶段实施，以免范围爆炸；但它是完整系统最终要达到的标准。

## 成功标准

第一阶段完成时应满足：

1. 能生成 `findings/evidence_credibility_report.json`。
2. 报告中每个因子都有可信度标签和样本量提示。
3. 回测证据明确区分 time-OOS、style-OOS、full lifecycle。
4. 参数稳定性有初版标签。
5. Decision State Hub 能优先读取该报告。
6. 不修改回测引擎和交易规则。
7. 相关测试通过，repo hygiene 通过。

## 实施状态

第一版实现范围：新增 `scripts/evidence_credibility_report.py` 生成 `findings/evidence_credibility_report.json`，并让 `agents/decision_state_hub.py` 优先读取该报告。此阶段没有修改回测引擎、weekly 回测脚本、交易规则或 dashboard UI。
