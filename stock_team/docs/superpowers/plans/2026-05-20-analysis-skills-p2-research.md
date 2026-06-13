# 分析 Skills P2（按需四个）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建四个按需 Claude skill 文件（stock-deep-research / stock-backtest / position-builder / portfolio-health），完善分析框架的研究和管理层。

**Architecture:** 同 P1，skill 文件在 `~/.claude/skills/`，调用现有 Python 脚本，读 JSON 填固定模板。stock-deep-research 需要跑 CIO（约5分钟）；stock-backtest 调用 backtest_engine；position-builder 是唯一有交互环节的 skill；portfolio-health 批量调用出场评估。

**Tech Stack:** Claude skill 文件（YAML frontmatter + Markdown），Python 3.12

---

## File Map

| 状态 | 路径 | 职责 |
|------|------|------|
| 新建 | `~/.claude/skills/stock-deep-research.md` | 全面调研报告（CIO + 大师辩论）|
| 新建 | `~/.claude/skills/stock-backtest.md` | 策略回测 + 阈值优化 |
| 新建 | `~/.claude/skills/position-builder.md` | 新建仓位交互引导 |
| 新建 | `~/.claude/skills/portfolio-health.md` | 组合健康全仓检查 |
| 修改 | `~/stock_team/CLAUDE.md` | 追加 P2 skill 触发词 |

---

## Task 1: stock-deep-research skill

**Files:**
- Create: `~/.claude/skills/stock-deep-research.md`

- [ ] **Step 1: 创建 skill 文件**

```bash
cat > ~/.claude/skills/stock-deep-research.md << 'SKILLEOF'
---
name: stock-deep-research
description: 全面深度股票调研。用户说"全面分析X"、"调研X"、"深度看X"、"研究X"时触发。运行CIO全量分析（约5分钟），包含6个专业Agent + 7大师立场 + 叙述性报告，输出固定章节格式的完整分析报告。
user-invocable: true
---

# Stock Deep Research Skill

## When to Invoke

Trigger when user says:
- "全面分析 [股票]" / "调研 [股票]" / "深度看 [股票]"
- "研究 [股票]" / "全面看一下 [股票]"
- "深度分析 [股票]"

Extract the stock symbol. Warn user this takes ~5 minutes (CIO phases 013).

## Instructions

Execute these commands IN ORDER for symbol {SYM}:

**Step 1: 基本面数据（快速）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/quick_fundamentals.py {SYM}
```
Show output immediately while waiting for Step 2.

**Step 2: CIO 全量分析（Phase 0+1+3，约5分钟）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/cio.py {SYM} --phases 013
```
Produces:
- `discussion_board.jsonl` → 6 Agent domain findings
- `persona_stances.jsonl` → 7 master stances (Phase 1.5)
- `findings/strategy_result.json` → unified signal (Phase 3)

**Step 3: 出场评估（如持仓）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_exit_sheet.py {SYM}
```
Writes: `findings/exit_decision_{date}.json`

**Step 4: 入场决策**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_decision.py {SYM}
```
Writes: `findings/entry_decision_{date}.json`

**Step 5: 叙述性摘要**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/report_agent.py {SYM}
```
Reads strategy_result + board → prints narrative summary.

## Reading JSON Files

```python
import json, os
from datetime import datetime
date = datetime.now().strftime("%Y-%m-%d")
base = "/home/lirawang/stock_team"

# Strategy result (Phase 3 output)
strategy = json.load(open(f"{base}/findings/strategy_result.json"))
# Fields: signal, confidence, score, agent_signals{agentName:{signal,confidence,key_points[]}},
#         sector_info{signal,confidence}, veto_agents

# 6 Agent findings from board
board_entries = []
for line in open(f"{base}/discussion_board.jsonl"):
    r = json.loads(line.strip())
    if r.get("msg_type") == "initial_finding" and r.get("symbol") == SYM:
        board_entries.append(r)
# Fields per entry: from (agent name), signal, confidence, key_points[]

# Master stances (Phase 1.5)
master_stances = {}
for line in open(f"{base}/persona_stances.jsonl"):
    r = json.loads(line.strip())
    if r.get("symbol") == SYM and r.get("msg_type") == "persona_stances":
        master_stances = r.get("stances", {})
        # Each stance: {signal, confidence, core_argument, invalidation, stopped_at}

# Entry / exit decisions
entry_path = f"{base}/findings/entry_decision_{date}.json"
entry = json.load(open(entry_path)) if os.path.exists(entry_path) else {}
entry_dec = entry.get("decisions", {}).get(SYM)

exit_path = f"{base}/findings/exit_decision_{date}.json"
exit_data = json.load(open(exit_path)) if os.path.exists(exit_path) else {}
exit_dec = exit_data.get("positions", {}).get(SYM)

# Check if held position
_pos = json.load(open(f"{base}/config/positions.json"))
is_held = SYM in _pos.get("positions", {})
```

## Output Template

```
═══════════════════════════════════════════════
【{SYM} 全面分析报告】{date}
═══════════════════════════════════════════════

【基本面】（quick_fundamentals 输出）
  价格/市值/PE/PEG/营收增速/盈利增速/FCF/分析师目标

【Agent 综合评估】（strategy_result.json → agent_signals）
  TechAgent:      {signal} {confidence}% — {key_points[0]}
  FundAgent:      {signal} {confidence}% — {key_points[0]}
  MacroAgent:     {signal} {confidence}% — {key_points[0]}
  RiskAgent:      {signal} {confidence}% — {key_points[0]}
  SentimentAgent: {signal} {confidence}%
  板块信号: {sector_info.signal}（{sector_info.confidence}%）← sector_info 字段

【大师综合立场】（persona_stances.jsonl → stances[masterName]）
  {master}: {signal}({confidence}%) — {core_argument}
  （遍历全部大师：minervini/druckenmiller/marks/lynch/soros/livermore/taleb）

【统一评估】
  信号: {strategy.signal} | 置信度: {strategy.confidence}% | 评分: {strategy.score}/100

【持仓出场评估】（如持仓，exit_decision.positions[SYM]）
  {exit_dec.decision} | 硬止损: ${exit_dec.hard_stop}（{stop_source_label}）
  距硬线: {exit_dec.hard_dist_pct:+.1f}%

【入场决策】（entry_decision.decisions[SYM]）
  {entry_dec.decision} | {entry_dec.reason}

【叙述摘要】（report_agent 输出）
  {report_agent narrative text}
═══════════════════════════════════════════════
```

stop_source_label: manual_gtc→"GTC已挂" | node1→"node1" | auto_atr→"⚠️ATR估算"

## Error Handling

- CIO takes too long (>8 min): show "CIO 超时，可尝试 --phases 01（跳过综合评分）"
- persona_stances.jsonl not found or empty for SYM: show "大师立场未生成（Phase 1.5 可能失败）"
- strategy_result.json not found: show "综合评分未生成（Phase 3 可能失败）"
- SYM not held: skip 【持仓出场评估】 section entirely
- Any JSON field missing: show "N/A"
SKILLEOF
echo "Created: ~/.claude/skills/stock-deep-research.md"
```

- [ ] **Step 2: 验证文件**

```bash
ls -la ~/.claude/skills/stock-deep-research.md
grep -c "When to Invoke\|Instructions\|Output Template\|Error Handling" ~/.claude/skills/stock-deep-research.md
```
Expected: 4

- [ ] **Step 3: Commit（empty commit，skill 文件在 git 外）**

```bash
cd ~/stock_team
git commit --allow-empty -m "feat(skill): add stock-deep-research skill - CIO phases013 + 7 masters + fixed report template"
```

---

## Task 2: stock-backtest skill

**Files:**
- Create: `~/.claude/skills/stock-backtest.md`

- [ ] **Step 1: 创建 skill 文件**

```bash
cat > ~/.claude/skills/stock-backtest.md << 'SKILLEOF'
---
name: stock-backtest
description: 策略回测和阈值优化。用户说"回测"、"信号扫描"、"找最优阈值"、"验证策略"时触发。运行backtest_engine的scan+simulate+update三步，输出信号最优阈值和框架模拟结果。
user-invocable: true
---

# Stock Backtest Skill

## When to Invoke

Trigger when user says:
- "回测" / "信号扫描" / "找最优阈值" / "验证策略"
- "backtest" / "阈值优化"
- "历史验证 [股票]"

Extract symbols if provided; if none, use positions + watchlist top stocks.

## Instructions

Execute these commands IN ORDER:

**Step 1: 信号参数扫描（找最优阈值）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/backtest_engine.py scan {SYM1} {SYM2} ...
```
Writes: `findings/signal_thresholds_optimized.json`
Fields: ma20_dev_max{optimal,win_rate,n_samples}, rs5_min{optimal,win_rate,n_samples}, vol_ratio_max{optimal,win_rate,n_samples}

**Step 2: 框架简化回测**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/backtest_engine.py simulate {SYM1} {SYM2} ...
```
Writes: `findings/backtest_results_{date}.json`
Fields: win_rate, n_entries, mean_ret_pct, note(limitation note)

**Step 3: 更新阈值配置（仅当胜率≥55%）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/backtest_engine.py update
```
Updates `config/decision_thresholds.json` if win_rate >= 0.55

## Reading JSON Files

```python
import json, os
from datetime import datetime
date = datetime.now().strftime("%Y-%m-%d")
base = "/home/lirawang/stock_team"

opt_path = f"{base}/findings/signal_thresholds_optimized.json"
thresholds = json.load(open(opt_path)) if os.path.exists(opt_path) else {}
# Fields: scan_date, symbols_scanned, n_total_samples
# ma20_dev_max: {optimal, win_rate, n_samples, mean_ret, scan[]}
# rs5_min: {optimal, win_rate, n_samples, mean_ret, scan[]}
# vol_ratio_max: {optimal, win_rate, n_samples, mean_ret, scan[]}

bt_path = f"{base}/findings/backtest_results_{date}.json"
backtest = json.load(open(bt_path)) if os.path.exists(bt_path) else {}
# Fields: win_rate, n_entries, mean_ret_pct, note, thresholds_used, scan_date

current_thresholds = json.load(open(f"{base}/config/decision_thresholds.json"))
# soft_vetoes: ma20_dev_max, rs5_min, max_headwinds
```

## Output Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【策略回测报告】{date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
扫描标的: {thresholds.symbols_scanned}（{thresholds.n_total_samples}个样本，{years}年）

【信号最优阈值】
  MA20乖离上限: {thresholds.ma20_dev_max.optimal} → 胜率{thresholds.ma20_dev_max.win_rate:.0%}（n={thresholds.ma20_dev_max.n_samples}）
  RS5超额下限:  {thresholds.rs5_min.optimal}% → 胜率{thresholds.rs5_min.win_rate:.0%}（n={thresholds.rs5_min.n_samples}）
  量比上限:     {thresholds.vol_ratio_max.optimal}x → 胜率{thresholds.vol_ratio_max.win_rate:.0%}（n={thresholds.vol_ratio_max.n_samples}）

【框架模拟结果】
  入场次数: {backtest.n_entries}
  胜率: {backtest.win_rate:.0%}
  均收益: {backtest.mean_ret_pct:.2f}%
  ⚠️ {backtest.note}

【当前阈值配置】（config/decision_thresholds.json）
  MA20乖离上限: {current_thresholds.soft_vetoes.ma20_dev_max}
  RS5下限:      {current_thresholds.soft_vetoes.rs5_min}%

【阈值更新结果】
  {update_status}  ← "✅ 已更新（胜率≥55%）" 或 "ℹ️ 未更新（胜率未达55%基线）"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 局限说明：回测仅使用技术信号（MA20/RS5/量比），不含消息面/催化剂。
```

## Error Handling

- scan fails: show error, skip simulate
- No symbols provided: use default_symbols from config/poll_config.json (first 10)
- backtest_results not found after simulate: show "模拟结果未生成"
- win_rate < 0.55 after update: show "胜率{win_rate:.0%}未超过55%基线，阈值保持不变"
SKILLEOF
echo "Created: ~/.claude/skills/stock-backtest.md"
```

- [ ] **Step 2: 验证**

```bash
ls -la ~/.claude/skills/stock-backtest.md
grep -c "When to Invoke\|Instructions\|Output Template\|Error Handling" ~/.claude/skills/stock-backtest.md
```

- [ ] **Step 3: Commit**

```bash
cd ~/stock_team
git commit --allow-empty -m "feat(skill): add stock-backtest skill - scan+simulate+update with threshold report template"
```

---

## Task 3: position-builder skill

**Files:**
- Create: `~/.claude/skills/position-builder.md`

- [ ] **Step 1: 创建 skill 文件**

```bash
cat > ~/.claude/skills/position-builder.md << 'SKILLEOF'
---
name: position-builder
description: 新建仓位引导。用户说"新建仓位X"、"加X"、"建仓X"、"我要买X"时触发。引导填写论点/催化剂/证伪条件/止损，写入positions.json。这是唯一有交互环节的skill。
user-invocable: true
---

# Position Builder Skill

## When to Invoke

Trigger when user says:
- "新建仓位 [股票]" / "加 [股票]" / "建仓 [股票]"
- "我要买 [股票]" / "想建 [股票] 仓位"

Extract the stock symbol.

## Instructions

**Step 1: 拉取基本面数据（给用户参考）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/quick_fundamentals.py {SYM}
```
Show the output so user has fundamental data for writing their thesis.

**Step 2: 计算初始止损（ATR-based）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_order_sheet.py {SYM}
```
Read `findings/order_sheet_{date}.json → symbols[SYM].stop_loss` for ATR-based stop suggestion.

**Step 3: 交互引导（按序问以下问题，每次等待用户回答后再问下一个）**

Ask these questions ONE AT A TIME:

Q1: "**论点（一句话）**：这只股票为什么值得持有？（例：NVDA AI数据中心垄断，Blackwell供不应求）"

Q2: "**催化剂类型**：选一个：
- earnings（业绩驱动）
- order（订单/客户驱动）
- policy（政策驱动）
- capital（资本运作）"

Q3: "**宏观类型**：选一个：
- 成长型
- 防御型
- 大宗商品型
- 趋势型"

Q4: "**证伪条件**（至少1条，建议包含1条时间条件）：什么情况下你会承认论点错了？
例：
- 【技术】NVDA跌破MA20且SOXX跑输超2%
- 【路径/时间】截止2026-08-01前收入增速未恢复到50%以上
- 【基本面】大客户公开削减GPU采购"

Q5: "**仓位信息**：
- 买入价格：$___
- 股数：___股
- 仓位类型：thesis（论点型）/ trend（趋势型）/ catalyst（催化剂型）"

**Step 4: 写入 positions.json**

```python
import json
from datetime import datetime
base = "/home/lirawang/stock_team"

pos_path = f"{base}/config/positions.json"
data = json.load(open(pos_path))

# Build new position entry from user answers
new_pos = {
    "cost":                   float(entry_price),
    "shares":                 int(shares),
    "date":                   datetime.now().strftime("%Y-%m-%d"),
    "t1_cost":                float(entry_price),
    "t1_shares":              int(shares),
    "position_type":          position_type,  # from Q5
    "thesis":                 thesis_text,     # from Q1
    "thesis_status":          "intact",
    "thesis_updated":         datetime.now().strftime("%Y-%m-%d"),
    "daily_action":           "B",
    "catalyst_type":          catalyst_type,   # from Q2
    "macro_type":             macro_type,      # from Q3
    "falsification_conditions": falsification_list,  # from Q4
    "t1_stop_snapshot":       stop_loss_from_order_sheet,  # from Step 2
    "stop_note":              "ATR估算，建议挂GTC实单",
    "gtc_stop_placed":        False,
    "falsification_updated":  datetime.now().strftime("%Y-%m-%d"),
}

data["positions"][SYM.upper()] = new_pos
with open(pos_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

## Output After Completion

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【{SYM} 仓位已建立】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
成本: ${entry_price} × {shares}股
论点: {thesis}
催化剂: {catalyst_type} | 宏观: {macro_type}
止损（ATR估算）: ${stop_loss} ⚠️ 建议立即挂 GTC 实单

【证伪条件】
  {falsification_condition_1}
  {falsification_condition_2}
  ...

⚠️ 下一步：
  1. 挂 GTC 止损单 ${stop_loss}
  2. 说"今天 {SYM} 盘前"获取盘前分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Error Handling

- SYM already in positions.json: ask "已有 {SYM} 持仓（成本${cost}×{shares}股），是否新建加仓记录？"
- order_sheet step fails: use "未知" for stop_loss, note "止损需手动填入"
- User skips a question: ask again, do not proceed with empty required fields
SKILLEOF
echo "Created: ~/.claude/skills/position-builder.md"
```

- [ ] **Step 2: 验证**

```bash
ls -la ~/.claude/skills/position-builder.md
grep -c "When to Invoke\|Instructions\|Output After Completion\|Error Handling" ~/.claude/skills/position-builder.md
```

- [ ] **Step 3: Commit**

```bash
cd ~/stock_team
git commit --allow-empty -m "feat(skill): add position-builder skill - interactive 5-question flow writes to positions.json"
```

---

## Task 4: portfolio-health skill

**Files:**
- Create: `~/.claude/skills/portfolio-health.md`

- [ ] **Step 1: 创建 skill 文件**

```bash
cat > ~/.claude/skills/portfolio-health.md << 'SKILLEOF'
---
name: portfolio-health
description: 组合整体健康检查。用户说"组合健康"、"持仓检查"、"整体风险"、"周报"时触发。运行portfolio_risk_agent和所有持仓的出场评估，输出全仓健康报告。
user-invocable: true
---

# Portfolio Health Skill

## When to Invoke

Trigger when user says:
- "组合健康" / "持仓检查" / "整体风险" / "周报"
- "全部持仓怎么样" / "仓位健康"

No symbol needed - evaluates ALL current positions.

## Instructions

**Step 1: 组合风险指标**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/portfolio_risk_agent.py
```
Prints: total exposure, leverage ratio, VaR 5%, sector concentration, top correlation pair, warnings

**Step 2: 所有持仓出场评估**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_exit_sheet.py
```
(No symbols = evaluates ALL positions with shares > 0)
Writes: `findings/exit_decision_{date}.json`

## Reading JSON Files

```python
import json, os
from datetime import datetime
date = datetime.now().strftime("%Y-%m-%d")
base = "/home/lirawang/stock_team"

# All positions
pos_data = json.load(open(f"{base}/config/positions.json"))
positions = {k: v for k, v in pos_data.get("positions", {}).items()
             if (v.get("shares") or v.get("t1_shares") or 0) > 0}

# Exit decisions for all positions
exit_path = f"{base}/findings/exit_decision_{date}.json"
exit_all = json.load(open(exit_path)) if os.path.exists(exit_path) else {}
all_exit = exit_all.get("positions", {})
# Keys: SYM → {decision, hard_stop, stop_source, hard_dist_pct, soft_triggers, hard_triggers}
```

## Output Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【组合健康报告】{date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【风险指标】（portfolio_risk_agent 输出）
  （直接展示 portfolio_risk_agent 的格式化输出）

【持仓出场评估汇总】
  {SYM1}: {icon} {decision} — {reason}
       硬止损: ${hard_stop}（{stop_source_label}）  距硬线: {hard_dist_pct:+.1f}%
  {SYM2}: {icon} {decision} — {reason}
  ...（遍历所有持仓）

【需要行动】
  ❌ 应出场: {应出场的标的列表，无则"无"}
  ⚠️ 考虑减仓: {考虑减仓的标的列表，无则"无"}
  ✅ 继续持有: {继续持有的标的列表}

【止损设置状态】
  已有 GTC 止损: {gtc_placed_list}
  ⚠️ ATR估算止损（需设 GTC）: {auto_atr_list}
  ⚠️ 无止损数据: {no_stop_list}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

stop_source_label:
- manual_gtc → "GTC 已挂"
- node1 → "node1"
- auto_atr → "⚠️ ATR估算"

Icon: 应出场→❌ | 考虑减仓→⚠️ | 继续持有→✅

## Error Handling

- portfolio_risk_agent fails: show error, continue with exit evaluation
- No positions found: show "无当前持仓"
- exit_decision not found: show "出场评估未运行，请检查 premarket_exit_sheet.py"
- Any position missing hard_stop: show "止损未设置" for that position
SKILLEOF
echo "Created: ~/.claude/skills/portfolio-health.md"
```

- [ ] **Step 2: 验证**

```bash
ls -la ~/.claude/skills/portfolio-health.md
grep -c "When to Invoke\|Instructions\|Output Template\|Error Handling" ~/.claude/skills/portfolio-health.md
```

- [ ] **Step 3: Commit**

```bash
cd ~/stock_team
git commit --allow-empty -m "feat(skill): add portfolio-health skill - all-position exit eval + risk metrics"
```

---

## Task 5: 更新 CLAUDE.md 路由表（追加 P2 行）

**Files:**
- Modify: `~/stock_team/CLAUDE.md`

- [ ] **Step 1: 找到路由表并追加 P2 行**

在现有路由表的"全面分析 X ... (P2，待实现)"那行，将括号内的"待实现"改为"已实现"；同时为 position-builder 和 portfolio-health 追加触发词。

将：
```
| 全面分析 X / 调研 X / 深度看 X / 研究 X | invoke stock-deep-research skill（P2，待实现）|
```
改为：
```
| 全面分析 X / 调研 X / 深度看 X / 研究 X | invoke stock-deep-research skill |
| 回测 / 信号扫描 / 找最优阈值 / 验证策略 | invoke stock-backtest skill |
| 新建仓位 X / 加 X / 建仓 X / 我要买 X | invoke position-builder skill |
| 组合健康 / 持仓检查 / 整体风险 / 周报 | invoke portfolio-health skill |
```

同时删除原表中的两行（已被 skill 接管）：
```
| 历史回测 / 信号扫描 / 找最优阈值 | `python3.12 agents/backtest_engine.py scan SYM1 SYM2` |
| 框架模拟 / 回测决策框架 | `python3.12 agents/backtest_engine.py simulate SYM`... |
| 更新阈值 / 用回测结果更新配置 | `python3.12 agents/backtest_engine.py update`... |
```

- [ ] **Step 2: 验证路由表完整**

```bash
grep "invoke stock-" ~/stock_team/CLAUDE.md
```
Expected: 7 行（premarket / intraday / postmarket / deep-research / backtest / position-builder / portfolio-health）

- [ ] **Step 3: Commit**

```bash
cd ~/stock_team
git add CLAUDE.md
git commit -m "feat(claude-md): add P2 skill routing - deep-research/backtest/position-builder/portfolio-health"
```

---

## 验收标准

| Skill | 验证方式 | 期望 |
|-------|---------|------|
| stock-deep-research | 说"全面分析 NVDA" | 触发 CIO，输出7大师立场，格式固定 |
| stock-backtest | 说"回测 NVDA MRVL" | 运行扫描+模拟，显示最优阈值 |
| position-builder | 说"新建仓位 RKLB" | 引导5个问题，完成后 positions.json 有 RKLB |
| portfolio-health | 说"组合健康" | 显示全部持仓出场状态+VaR |
| CLAUDE.md 路由 | 说"验证策略" | 触发 stock-backtest，不跑 backtest_engine 命令行 |
