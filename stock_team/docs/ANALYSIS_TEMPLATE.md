# 个股分析输出模板

> 基于我们系统自有字段设计，融合 positions.json / evaluate_thesis_health / check_flex_signals / macro_sensitivity

---

## 使用前必读

**每次分析前运行**：
```bash
python3.12 agents/quick_fundamentals.py {SYM}
python3.12 agents/macro_agent.py {SYM}  # 更新 findings/macro.json
```

**数据缺口处理**：
- 能拿到：用数字
- 拿不到：标 `数据不可用`，尝试 WebSearch 补充
- 禁止估算 / 编造任何财务数字

---

## 输出模板

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【{SYM} 分析报告】{date}
  现价 ${cur} ({chg:+.2f}%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【数据完备度】
  ✅ 价格/技术（yfinance 实时）
  ✅ 估值/基本面（quick_fundamentals.py: PE/FCF/分析师目标/增速）
  ✅/❌ 宏观（findings/macro.json）
  ⚠️/❌ 分部营收（WebSearch，需标注信息时效）
  ❌ 期权流向（未获取，分析不覆盖此维度）

━━━ 宏观适配层 ━━━

macro_type: {成长型/避险型/周期型}
宏观定调: {偏多/中性/偏空} ({score}/10)
当前活跃逆风: {rate_up↓ / credit_tight↓ / ...}
对该持仓影响: ✅友好 / ⚠️部分承压 / 🔴多维逆风

━━━ 基本面层（Tier 1 数据）━━━

估值:
  PE(fwd)={pe_fwd:.1f}x  PEG={peg:.2f}
  分析师目标: ${target}（{高于/低于}现价 {dev:+.1f}%）| 评级: {rec_str}（{n_ana}人）
  ⚠️注：目标价为分析师均值，存在更新滞后

成长:
  营收(TTM): ${rev}B | 增速: {rev_growth:+.1f}% YoY
  盈利增速: {earn_growth:+.1f}% YoY | FCF: ${fcf}B

持仓结构:
  内部人: {insider_pct:.1f}% | 机构: {inst_pct:.1f}%
  内部人近期净: {买入/卖出/中性}（近20条）| 空头: {short_pct:.1f}%

Tier3缺口（WebSearch补充 / 标注N/A）:
  分部营收占比: {AI_pct}% / N/A
  主要客户集中度: {description} / N/A

━━━ 论点状态层（持仓独有）━━━

position_type: {thesis/catalyst/flex/trend}
thesis: {thesis_text}
thesis_status: {intact ✅ / weakening ⚠️ / broken ❌}

节点位置:
  node1（支撑）: ${n1} ({n1_dist:+.1f}%)
  node2（怀疑线）: ${n2} ({n2_dist:+.1f}%)
  node3（突破确认）: ${n3} ({n3_dist:+.1f}%)
  当前区间: {A突破确认 / B论点区间 / C_warn论点警告 / C_confirm论点承压}

止损线:
  软线（成本）: ${soft_stop} ({soft_dist:+.1f}%)
  硬线（结构）: ${hard_stop} ({hard_dist:+.1f}%)

下跌性质（如有触发）: {论点收尾 / 个股事件 / 大盘拖累 / 板块联动}

━━━ 技术信号层 ━━━

RS vs SPY: {rs:+.2f}% | 量比: {vol_ratio:.2f}x | candle_drop_5m: {drop:.1f}%
Stage 2: {✅ MA200向上，价格在MA200之上} | 距MA200: {dist_ma200:+.1f}%
今日窗口: {开盘5分钟 / 开盘窗口 / 午盘低量 / 尾盘方向 / 正常盘中}
极端速度: {无 / 🚨Level1 / 🚨🚨Level2 / ⚠️流动性真空}

Flex信号（4维: RSI14/VWAP偏离/量比/MACD）:
  减仓信号: {n}/4 → {触发减仓 / 观察中 / 无信号}
  加仓信号: {n}/4 → {触发加仓 / 观察中 / 无信号}

━━━ 大师评分层 ━━━

今日判断状态: 🟢热手 / 正常 / 🔴冷手（{reason}）

Minervini（技术）:  {m}/10 — {m_reason}
Marks（风险/RR）:   {k}/10 — {k_reason}
Druckenmiller（宏观/sizing）: {d}/10 — {d_reason}
综合: {avg}/10 → {buy/hold/no_buy/not_sell/sell}

━━━ 操作建议 ━━━

当前 Flex 行动: {加仓N股 / 减仓N股 / 观望}
触发条件:
  加仓: 价格>${trigger_add} + 量比>{vol_trigger}x + RS>+{rs_trigger}%
  减仓: 价格<${trigger_reduce} + 量比放大 / Flex减仓信号4/4
止损执行: 硬线 ${hard_stop} 跌破+量能放大 → 立即执行

下一个关键观察时间: {具体时间段或价格点}
```

---

## 字段来源说明

| 字段 | 来源 | 获取命令 |
|------|------|---------|
| 宏观层字段 | findings/macro.json | `macro_agent.py {sym}` |
| 基本面 Tier1 | yfinance .info | `quick_fundamentals.py {sym}` |
| 论点/节点/止损 | positions.json | 直接读取 |
| evaluate_thesis_health | poll.py 函数 | 调用函数 |
| 技术信号 | snap() | poll.py snap() |
| Flex信号 | check_flex_signals() | poll.py 函数 |
| 大师评分 | quick_persona_score() | poll.py 函数 |
| 热手/冷手 | poll_state.json | load_poll_state() |
| 下跌性质 | classify_pullback() | poll.py 函数 |

---

## 数据缺口降级规则

| 缺口 | 降级方式 |
|------|---------|
| macro.json 不存在 | 标"宏观数据不可用"，跳过宏观适配层 |
| 非持仓标的（无 positions.json 记录）| 跳过论点状态层 |
| yfinance 某字段返回 None | 显示"N/A"，不估算 |
| Tier3数据未获取 | 标"需补充"，不影响其他层 |
