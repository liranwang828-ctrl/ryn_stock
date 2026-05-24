# 股票分析 Skill 框架 — Design Spec

**Date**: 2026-05-20
**Status**: Draft
**Scope**: 7个分析 skill 的架构设计，统一调用链 + 固定模板 + CLAUDE.md 路由

---

## 问题陈述

现有系统有 48 个 Python 脚本，能力完整，但调用完全依赖我的临时判断：
- 每次"全面分析 NVDA"的输出内容和格式都不一样
- 我不会自动想到调用 report_agent.py、strategy_agent.py 等存在但未集成的脚本
- translator.py 有意图路由但在对话中不生效（被动脚本）

**解决方案**：7 个 skill 文件，分别定义调用链和固定模板，CLAUDE.md 路由触发。

---

## 架构原则

**脚本负责计算，Skill 负责编排和格式化**

```
用户说 "全面分析 NVDA"
    ↓
CLAUDE.md 触发表 → invoke stock-deep-research skill
    ↓
Skill 按序调用脚本 → 各脚本写 JSON 文件
    ↓
Skill 读 JSON 文件 → 按固定模板格式化输出
    ↓
确定性输出：每次格式相同，内容随数据变化
```

**确定性保证**：模板固定，数据来自 JSON 文件，skill 不做自由合成，只做 JSON → 模板的填充。

---

## translator.py 边界

**保留**，但职责缩小为**交易记录类文本**：
- "买了 MRVU 20股" → entry_guard
- "卖了 BABA" → 更新持仓
- "止损了" → 记录

**不再**负责分析类工作流调度（由 skills 接管）。

---

## CLAUDE.md 路由表（更新）

```markdown
## 脚本触发规则（自然语言 → Skill/命令）

| 用户说 | 触发 |
|--------|------|
| 全面分析/调研/深度看 X | invoke stock-deep-research skill |
| 今天 X / 盘前 X / X 今日 | invoke stock-premarket skill |
| X 现在如何 / X 盘中 / 状态 X | invoke stock-intraday skill |
| 收盘 / 盘后 / 复盘 / harvest | invoke stock-postmarket skill |
| 回测 / 信号扫描 / 阈值 | invoke stock-backtest skill |
| 新建仓位 / 加 X / 建仓 X | invoke position-builder skill |
| 组合健康 / 持仓检查 / 风险 | invoke portfolio-health skill |
```

---

## Skill 1: stock-deep-research

**触发词**：全面分析 X / 调研 X / 深度看 X / 研究 X

**调用链**（按序执行）：

```
Step 1: python3.12 agents/quick_fundamentals.py {SYM}
        → console output（直接展示）

Step 2: python3.12 agents/cio.py {SYM} --phases 013
        → discussion_board.jsonl（6 Agent 发言）
        → persona_stances.jsonl（大师立场，Phase 1.5 产出）
        → findings/strategy_result.json（Phase 3 strategy_agent 产出）
        （Phase 0: 数据拉取 + 验证；Phase 1: 6 Agent 并行 + Phase 1.5 大师立场；Phase 3: 综合评分）

Step 3: python3.12 agents/premarket_exit_sheet.py {SYM}
        → findings/exit_decision_{date}.json
        （仅当 SYM 在 positions.json 中）

Step 4: python3.12 agents/premarket_decision.py {SYM}
        → findings/entry_decision_{date}.json

Step 5: python3.12 agents/report_agent.py {SYM}
        → 读 strategy_result.json + board → 叙述性摘要
```

**输出模板**（固定章节，按序）：

```
═══════════════════════════════════════════════
【{SYM} 全面分析报告】{date}
═══════════════════════════════════════════════

【基本面】                  ← quick_fundamentals 输出
  价格/市值/PE/PEG/营收增速/盈利增速/FCF/分析师目标

【Agent 综合评估】          ← strategy_result.json → agent_signals[agentName]
  TechAgent:      {signal} {conf}% — {key_point}
  FundAgent:      {signal} {conf}% — {key_point}
  MacroAgent:     {signal} {conf}% — {key_point}
  RiskAgent:      {signal} {conf}% — {key_point}
  SentimentAgent: {signal} {conf}%
  板块：{sector_info.signal}（{sector_info.confidence}%）  ← sector_info 字段，非 agent_signals

【宏观 / Regime】           ← MacroAgent + macro.json
  yield_curve / DXY / VIX / macro_score / Regime

【大师综合立场】            ← persona_stances.jsonl（stances[masterName]）
  {master}: {signal}({conf}%) — {core_argument}
  （6-7 大师列表）
  统一置信度: {strategy_result.confidence}/100 → {strategy_result.signal}

【持仓出场评估】            ← exit_decision_{date}.json → positions[SYM]
  {decision} | 硬止损: ${hard_stop}（{stop_source}）
  软触发: {soft_triggers}

【入场决策】                ← entry_decision_{date}.json → decisions[SYM]
  {decision} | 硬否决: {hard_vetoes} | 软否决: {soft_vetoes}

【叙述摘要】                ← report_agent 输出
  {narrative_text}
═══════════════════════════════════════════════
```

---

## Skill 2: stock-premarket

**触发词**：今天 X / 盘前 X / X 今日分析 / 盘前看 X

**调用链**：

```
Step 1: python3.12 agents/premarket_watchlist_score.py {SYM} --no-interactive --output findings/today_focus.json
        → findings/today_focus.json（6维评分，默认只打印到控制台，必须显式传 --output）

Step 2: python3.12 agents/premarket.py {SYM}
        → premarket_analysis_{date}.json（场景/Gap/入场区间）

Step 3: python3.12 agents/premarket_order_sheet.py {SYM}
        → findings/order_sheet_{date}.json
        → daily_plan_{date}.json（poll 兼容格式）

Step 4: python3.12 agents/premarket_decision.py {SYM}
        → findings/entry_decision_{date}.json

Step 5: python3.12 agents/premarket_exit_sheet.py {SYM}
        → findings/exit_decision_{date}.json（如持仓）

Step 6: python3.12 agents/premarket_checklist.py {SYM}
        → daily_checklist_{date}.json（论点 + 取消条件）
```

**输出模板**（一页纸）：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【{SYM} 盘前摘要】{date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
评分: {score}分 | 场景: {pred_scene} | Gap: {gap_pct}%

【入场决策】  {entry_decision_icon} {entry_decision}    ← entry_decision_{date}.json → decisions[SYM].decision
  {entry_reason}

【出场评估】  {exit_decision_icon} {exit_decision}（如持仓）  ← exit_decision_{date}.json → positions[SYM].decision
  硬止损: ${hard_stop}（{stop_source}）  距硬线: {hard_dist}%

【条件订单表】
  入场区间: ${entry_low} – ${entry_high}
  止损 GTC: ${stop_loss}  目标: ${target}  RR={rr}x

【论点状态】  {thesis_status_icon} {thesis_status}
  {thesis}

【取消条件】
  × {cancel_condition_1}
  × {cancel_condition_2}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Skill 3: stock-intraday

**触发词**：X 现在如何 / X 盘中状态 / 还按原计划吗 / X 怎么样了

**调用链**（只读 JSON，不跑脚本）：

```
读取（poll 已在运行，不重复调用）:
  learning/observation_log.jsonl 最新 10 条   → 当前信号快照
  findings/entry_decision_{date}.json         → 盘前原计划
  findings/exit_decision_{date}.json          → 出场状态
  quick_debate_{SYM}.json（若存在）           → 最近辩论结论
  learning/poll_state_{date}.json             → 最新 poll 状态

判断逻辑:
  比较当前价格 vs 入场区间 / 取消条件是否触发
  输出 "仍按原计划" / "取消条件触发" / "需要重新评估"
```

**输出模板**（状态卡）：

```
【{SYM} 盘中状态】{time} ET
  现价: ${cur}  vs 盘前计划入场区间: ${entry_low}–${entry_high}
  RS: {rs}%  MACD: {macd}  Vol: {vol_ratio}x

【原计划状态】  {plan_status_icon} {plan_status}
  入场决策: {entry_decision} | 出场评估: {exit_decision}

【取消条件核查】
  {cancel_check_1}  ← ✅ 未触发 / ❌ 已触发
  {cancel_check_2}

【建议】  {recommendation}
```

---

## Skill 4: stock-postmarket

**触发词**：收盘 / 盘后 / 复盘 / harvest / 今天结果

**调用链**：

```
Step 1: python3.12 agents/harvest_agent.py
        → learning/daily_harvest.jsonl（今日结果记录）
        → learning/observation_outcomes.jsonl（信号验证）
        → learning/master_accuracy.json（大师评分更新）

Step 2: session_manager.run_node(6)
        → postmarket_review.py（大盘三段式 + 大师复盘视角）

读取:
  daily_harvest.jsonl     → 今日盈亏
  entry_decision_{date}.json → 盘前计划
  exit_decision_{date}.json  → 出场评估结果
```

**输出模板**：

```
【今日盘后复盘】{date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【执行对比】
  盘前计划: {entry_decision} → 实际: {actual_action}
  偏差: {deviation_note}

【今日盈亏】
  {sym}: {pnl}% ({outcome_label})

【信号验证】
  入场门通过正确率: {pass_correct}/{pass_total}
  门控禁止正确率:   {block_correct}/{block_total}

【大市复盘】    ← postmarket_review 输出
  {market_3tier_summary}

【教训记录】
  {lesson_1}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Skill 5: stock-backtest

**触发词**：回测 / 信号扫描 / 阈值优化 / backtest

**调用链**：

```
Step 1: python3.12 agents/backtest_engine.py scan {SYMS}
        → findings/signal_thresholds_optimized.json

Step 2: python3.12 agents/backtest_engine.py simulate {SYMS}
        → findings/backtest_results_{date}.json

Step 3: python3.12 agents/backtest_engine.py update
        → 若胜率 ≥ 55%，更新 config/decision_thresholds.json
```

**输出模板**：

```
【策略回测报告】{date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【信号最优阈值】（历史 2年，{n}个标的）
  MA20乖离上限: {ma20_optimal}（胜率{ma20_wr}%）
  RS5超额下限:  {rs5_optimal}（胜率{rs5_wr}%）
  量比上限:     {vol_optimal}（胜率{vol_wr}%）

【框架模拟结果】
  入场次数: {n_entries}  胜率: {win_rate}%  均收益: {mean_ret}%
  注：仅使用技术信号，不含催化剂/消息面

【阈值更新】
  {update_status}  ← "已更新" 或 "未达到55%基线，不更新"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Skill 6: position-builder

**触发词**：新建仓位 X / 加 X / 建仓 X / 我要买 X

**调用链 + 交互流程**：

```
Step 1: python3.12 agents/quick_fundamentals.py {SYM}
        → 展示基本面快照（供论点参考）

Step 2: 交互引导（固定问题序列）:
  Q1: "这只股票的核心论点是什么？（一句话）"
  Q2: "催化剂类型：earnings / order / policy / capital ?"
  Q3: "macro_type（成长型/防御型/大宗商品型）?"
  Q4: "证伪条件：什么情况下你会认错出场？（至少1条时间条件）"

Step 3: python3.12 agents/premarket_order_sheet.py {SYM}
        → 生成初始止损估算（ATR-based）

Step 4: 写入 positions.json（新持仓条目）
        → 包含 thesis / falsification_conditions / t1_stop / macro_type
```

---

## Skill 7: portfolio-health

**触发词**：组合健康 / 持仓检查 / 整体风险 / 周报

**调用链**：

```
Step 1: python3.12 agents/portfolio_risk_agent.py
        → VaR 5% / 集中度 / 相关性 / 杠杆率

Step 2: python3.12 agents/premarket_exit_sheet.py
        （对 ALL 持仓批量运行）
        → findings/exit_decision_{date}.json（全仓出场评估）
```

**输出模板**：

```
【组合健康报告】{date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【风险指标】
  总敞口: ${total} | 杠杆率: {leverage}x
  VaR(5%): 大盘跌5% → 预估亏损 ${var_loss}（-{var_pct}%）
  最高相关对: {top_corr_pair}（{corr}）
  板块集中度: {top_sector} {sector_pct}%

【持仓出场评估汇总】
  {SYM1}: {exit_decision} — {exit_reason}
  {SYM2}: {exit_decision} — {exit_reason}
  ...

【需要行动的持仓】
  ❌ 应出场: {sym_list}
  ⚠️ 考虑减仓: {sym_list}
  ✅ 继续持有: {sym_list}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 实施顺序

```
优先级（按使用频率）:
P1（每日）: stock-premarket → stock-intraday → stock-postmarket
P2（按需）: stock-deep-research → portfolio-health
P3（周期）: stock-backtest → position-builder

依赖关系:
stock-intraday 依赖 stock-premarket 已产出 entry_decision/exit_decision
portfolio-health 依赖 premarket_exit_sheet（已实现）
stock-postmarket 依赖 harvest_agent（已实现）
```

---

## Validation

1. **stock-premarket**：对持仓股 NVDA 运行，输出含"入场决策 ⚠️ 观察"+ 止损价 + 论点状态，格式每次相同
2. **stock-intraday**：不重跑脚本，读现有 JSON，10秒内输出状态卡
3. **stock-deep-research**：完整运行约5分钟，输出含 6 Agent 信号 + 7 大师立场 + 入场/出场决策，章节顺序固定
4. **stock-postmarket**：收盘后运行，输出含"计划 vs 实际"对比
5. **CLAUDE.md 路由**：说"全面分析 NVDA"自动触发 stock-deep-research，不需要我"想"该跑什么
6. **position-builder**：新建仓位后 positions.json 自动包含 falsification_conditions 字段

---

## Out of Scope

- 期权分析（数据不可用）
- 实时新闻推送（需外部 API）
- 自动执行交易（保持人工确认）
- community_agent.py 集成（机构股无社群信号价值，保留为可选调用）
