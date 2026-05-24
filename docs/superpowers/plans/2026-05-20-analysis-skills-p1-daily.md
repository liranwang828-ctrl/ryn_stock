# 分析 Skills P1（每日三个）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建三个每日使用的 Claude skill 文件（stock-premarket / stock-intraday / stock-postmarket），并更新 CLAUDE.md 路由表，确保触发词→固定格式报告的链路完全确定。

**Architecture:** Skill 文件存于 `~/.claude/skills/`，每个 skill 定义：触发条件 + 按序调用的脚本命令 + 固定输出模板。脚本产出 JSON，skill 读 JSON 填模板，输出格式完全确定。现有 `translator.py` 只保留交易记录文本路由，分析工作流全部由 skill 接管。

**Tech Stack:** Claude skill 文件（YAML frontmatter + Markdown），Python 3.12（通过 Bash 调用现有脚本）

---

## File Map

| 状态 | 路径 | 职责 |
|------|------|------|
| 新建 | `~/.claude/skills/stock-premarket.md` | 盘前摘要 skill |
| 新建 | `~/.claude/skills/stock-intraday.md` | 盘中状态 skill |
| 新建 | `~/.claude/skills/stock-postmarket.md` | 盘后复盘 skill |
| 修改 | `~/stock_team/CLAUDE.md` | 加路由表 |

---

## Task 1: stock-premarket skill

**Files:**
- Create: `~/.claude/skills/stock-premarket.md`

- [ ] **Step 1: 创建 skill 文件**

```bash
cat > ~/.claude/skills/stock-premarket.md << 'SKILLEOF'
---
name: stock-premarket
description: 盘前股票分析。用户说"今天X"、"盘前X"、"X今日分析"、"X今天怎么看"时触发。调用6个盘前脚本，输出固定格式的一页纸盘前摘要。
user-invocable: true
---

# Stock Pre-Market Analysis Skill

## When to Invoke

Trigger when user says:
- "今天 [股票]" / "盘前 [股票]" / "[股票] 今日分析"
- "[股票] 今天怎么看" / "看一下 [股票] 今天"
- "盘前摘要 [股票]"

Extract the stock symbol (2-5 uppercase letters) from the user's message.

## Instructions

Execute these commands IN ORDER for symbol {SYM}. Run each command and wait for completion before proceeding.

**Step 1: 6维评分**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_watchlist_score.py {SYM} --no-interactive --output findings/today_focus.json
```

**Step 2: 场景预测 + 入场区间**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket.py {SYM}
```
Writes: `premarket_analysis_{date}.json`

**Step 3: 条件订单表**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_order_sheet.py {SYM}
```
Writes: `findings/order_sheet_{date}.json` + `daily_plan_{date}.json`

**Step 4: 入场决策（分层否决）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_decision.py {SYM}
```
Writes: `findings/entry_decision_{date}.json` → read `decisions["{SYM}"]`

**Step 5: 出场评估（如持仓）**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_exit_sheet.py {SYM}
```
Writes: `findings/exit_decision_{date}.json` → read `positions["{SYM}"]`

**Step 6: 论点清单 + 取消条件**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/premarket_checklist.py {SYM}
```
Writes: `daily_checklist_{date}.json`

## Output Template

Read the JSON files produced above and format using EXACTLY this template.
Do NOT add extra commentary or deviate from this structure.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【{SYM} 盘前摘要】{YYYY-MM-DD}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
评分: {entry_decision.decisions[SYM].score}分  ← 来自 entry_decision（更可靠，today_focus.selected 只含推荐股）
场景: {premarket_analysis.stocks[SYM].pred_scene} | Gap: {premarket_analysis.stocks[SYM].gap_pct}%

【入场决策】  {icon} {entry_decision.decisions[SYM].decision}
  {entry_decision.decisions[SYM].reason}
  硬否决: {entry_decision.decisions[SYM].hard_vetoes}（空则"无"）
  软否决: {entry_decision.decisions[SYM].soft_vetoes}（空则"无"）

【出场评估】  {icon} {exit_decision.positions[SYM].decision}（如持仓，否则跳过）
  硬止损: ${exit_decision.positions[SYM].hard_stop}（{stop_source_label}）
  距硬线: {exit_decision.positions[SYM].hard_dist_pct:+.1f}%

【条件订单表】
  入场条件: {order_sheet.symbols[SYM].entry_conditions[0]}  ← entry_range 字段为 null，用 entry_conditions 文本
  止损 GTC: ${order_sheet.symbols[SYM].stop_loss}  目标: ${order_sheet.symbols[SYM].target_price}  RR={order_sheet.symbols[SYM].rr_ratio}x

【论点状态】  {thesis_status_icon} {daily_checklist[SYM].thesis_status}  ← thesis_status 在 checklist
  {order_sheet.symbols[SYM].thesis}  ← thesis 文本在 order_sheet

【取消条件】  ← cancel_conditions 列表在 order_sheet.symbols[SYM].cancel_conditions
  × {order_sheet.symbols[SYM].cancel_conditions[0]}
  × {order_sheet.symbols[SYM].cancel_conditions[1]}
  ...（遍历 cancel_conditions 数组）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Icon mapping:
- 可入场 / 继续持有 / intact → ✅
- 观察 / 考虑减仓 / weakening → ⚠️
- 不入场 / 应出场 / broken → ❌

stop_source_label:
- manual_gtc → "GTC 已挂"
- node1 → "node1"
- auto_atr → "⚠️ ATR估算，建议设 GTC"

## Error Handling

If a script fails: show error message for that step, continue with remaining steps.
If SYM is not in positions.json: skip Step 5 (出场评估), omit that section from template.
If today_focus.json is empty or missing SYM: show "评分: N/A".
SKILLEOF
echo "stock-premarket.md created"
```

- [ ] **Step 2: 验证文件存在且格式正确**

```bash
head -5 ~/.claude/skills/stock-premarket.md
```
Expected: YAML frontmatter 的前5行

- [ ] **Step 3: 冒烟测试——手动触发 skill 验证输出结构**

说："今天 NVDA 盘前分析"，确认 Claude 调用 stock-premarket skill，输出包含以下章节：
- `━━━` 分隔线
- `【入场决策】` 含 ✅/⚠️/❌ 标记
- `【条件订单表】` 含 RR 比值
- `【论点状态】`
- `【取消条件】`

- [ ] **Step 4: Commit**

注意：`~/.claude/skills/` 不在 `~/stock_team` git repo 下，skill 文件本身无法被 git 追踪。
只需在 stock_team repo 中记录 CHANGELOG：

```bash
cd ~/stock_team
git commit --allow-empty -m "feat(skill): add stock-premarket skill - 6-step premarket analysis with fixed template"
```

---

## Task 2: stock-intraday skill

**Files:**
- Create: `~/.claude/skills/stock-intraday.md`

- [ ] **Step 1: 创建 skill 文件**

```bash
cat > ~/.claude/skills/stock-intraday.md << 'SKILLEOF'
---
name: stock-intraday
description: 盘中股票状态查询。用户问"X现在如何"、"X盘中状态"、"还按原计划吗"时触发。只读已有JSON文件（不重跑脚本），对比盘前计划与当前状态，输出固定格式状态卡。
user-invocable: true
---

# Stock Intraday Status Skill

## When to Invoke

Trigger when user says:
- "[股票] 现在如何" / "[股票] 现在怎样" / "[股票] 盘中"
- "还按原计划吗" / "[股票] 状态"
- "[股票] 要不要入场" / "该不该进"

Extract the stock symbol from the user's message.

## Instructions

**DO NOT re-run scripts.** poll.py is already running. Only READ existing JSON files.

**Read these files** (use current date for {date}):

1. `~/stock_team/findings/entry_decision_{date}.json` → `decisions["{SYM}"]`
2. `~/stock_team/findings/exit_decision_{date}.json` → `positions["{SYM}"]`
3. `~/stock_team/learning/poll_state_{date}.json` → `symbols["{SYM}"]` (latest poll snapshot)
4. `~/stock_team/learning/observation_log.jsonl` → last 5 lines where `sym == "{SYM}"`
5. `~/stock_team/quick_debate_{SYM}.json` (if exists) → debate result

**Check cancel conditions:**
From `~/stock_team/daily_checklist_{date}.json` → `{SYM}.cancel_conditions`
Compare each condition against current snapshot data to determine if triggered.

## Output Template

```
【{SYM} 盘中状态】{HH:MM} ET
  现价: ${poll_state.last_price}  RS: {poll_state.last_rs:+.1f}%  Vol: {poll_state.last_vol_ratio:.2f}x
  MACD: {poll_state.last_macd:+.3f}  RSI14: {poll_state.last_rsi14_5m:.0f}
  注：字段名以 learning/poll_state_{date}.json 实际为准（last_rs，last_rsi14_5m）

【盘前计划对比】
  入场决策: {icon} {entry_decision}（盘前计划）
  出场评估: {icon} {exit_decision}（如持仓）
  入场区间: ${entry_low} – ${entry_high}（当前价位: {zone_status}）

【取消条件核查】
  {条件1}: {✅ 未触发 / ❌ 已触发 — 说明}
  {条件2}: {✅ 未触发 / ❌ 已触发 — 说明}

【当前建议】
  {recommendation}
```

zone_status:
- 当前价在入场区间内 → "✅ 在区间内"
- 当前价高于区间 → "⬆️ 高于区间"
- 当前价低于区间 → "⬇️ 低于区间"

recommendation 逻辑：
- 任一取消条件触发 → "❌ 取消条件已触发，不执行今日计划"
- 在执行窗口(10:00-10:30)且价格在区间内且无取消条件 → "✅ 条件满足，可按原计划执行"
- 在观察窗口(09:30-10:00) → "⚠️ 观察期，暂不入场，继续观察取消条件"
- 其他 → 根据具体情况说明

## Error Handling

If poll_state not found for SYM: show "暂无 poll 数据（poll 未运行或 SYM 未在监控列表）"
If entry_decision not found: show "无今日盘前决策（请先运行盘前分析）"
SKILLEOF
echo "stock-intraday.md created"
```

- [ ] **Step 2: 验证文件存在**

```bash
head -5 ~/.claude/skills/stock-intraday.md
```

- [ ] **Step 3: 冒烟测试**

说："NVDA 现在如何"，确认 Claude 调用 stock-intraday skill，输出包含：
- 现价/RS/Vol 数据
- `【盘前计划对比】` 章节
- `【取消条件核查】` 章节
- `【当前建议】` 章节

- [ ] **Step 4: Commit**

```bash
echo "stock-intraday skill created" | git commit --allow-empty -m "feat(skill): add stock-intraday skill - read-only status card from existing JSON"
```

---

## Task 3: stock-postmarket skill

**Files:**
- Create: `~/.claude/skills/stock-postmarket.md`

- [ ] **Step 1: 创建 skill 文件**

```bash
cat > ~/.claude/skills/stock-postmarket.md << 'SKILLEOF'
---
name: stock-postmarket
description: 盘后复盘。用户说"收盘"、"盘后"、"复盘"、"harvest"、"今天结果"时触发。运行harvest收集结果，调用Node 6复盘，输出计划vs实际对比。
user-invocable: true
---

# Stock Post-Market Review Skill

## When to Invoke

Trigger when user says:
- "收盘" / "盘后" / "复盘" / "harvest"
- "今天结果怎样" / "今天表现如何" / "记录今天"

## Instructions

Execute these commands IN ORDER:

**Step 1: 记录今日结果**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/harvest_agent.py
```
Writes:
- `learning/daily_harvest.jsonl` (今日盈亏)
- `learning/observation_outcomes.jsonl` (信号验证)
- `learning/master_accuracy.json` (大师评分准确率更新)

**Step 2: 盘后复盘分析**
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 -c "
from agents.session_manager import run_node
print(run_node(6))
"
```
Calls `postmarket_review.py` internally.

**Step 3: Read results**

Read from:
- `learning/daily_harvest.jsonl` → today's entries (filter by today's date)
- `findings/entry_decision_{date}.json` → today's plan
- `findings/exit_decision_{date}.json` → today's exit evaluations

## Output Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【今日盘后复盘】{YYYY-MM-DD}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【执行对比】
  盘前计划:   {entry_decision} → 实际: {actual_action}
  偏差说明: {deviation_note}

【今日盈亏】
  {sym}: {ret}% ({outcome_label})  ← from daily_harvest

【信号验证】
  入场门通过正确率: {pass_correct}/{pass_total}（{pass_pct}%）
  门控禁止正确率:   {block_correct}/{block_total}（{block_pct}%）
  样本不足(<10)时不显示百分比

【大市复盘】
  {postmarket_review output summary}

【今日教训】
  {lesson — 如无特别教训写"无"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

outcome_label mapping (from daily_harvest `label`):
- 1 → "✅ 信号正确"
- -1 → "❌ 信号错误"
- 0 → "⚪ 中性"

## Error Handling

If harvest_agent fails: show error, still attempt step 2.
If no trades today: show "今日无交易记录".
If observation_outcomes empty: show "今日无 poll 观察记录（poll 未运行）".
SKILLEOF
echo "stock-postmarket.md created"
```

- [ ] **Step 2: 验证文件存在**

```bash
head -5 ~/.claude/skills/stock-postmarket.md
```

- [ ] **Step 3: 冒烟测试**

说："收盘复盘"，确认 Claude 调用 stock-postmarket skill，输出包含：
- `【执行对比】` 章节
- `【今日盈亏】` 章节
- `【信号验证】` 章节

- [ ] **Step 4: Commit**

```bash
echo "stock-postmarket skill created" | git commit --allow-empty -m "feat(skill): add stock-postmarket skill - harvest + node6 review + fixed template"
```

---

## Task 4: 更新 CLAUDE.md 路由表

**Files:**
- Modify: `~/stock_team/CLAUDE.md`

- [ ] **Step 1: 替换 CLAUDE.md 的"脚本触发规则"整个表格**

将 `~/stock_team/CLAUDE.md` 的"脚本触发规则"表替换为以下完整内容（全量替换，不要只修改部分行）：

```markdown
## 脚本触发规则（自然语言 → 我应该执行什么）

| 用户说 | 执行命令 |
|--------|---------|
| 今天 X / 盘前 X / X 今日分析 / X 今天怎么看 | invoke stock-premarket skill |
| X 现在如何 / X 盘中 / 还按原计划吗 / X 状态 | invoke stock-intraday skill |
| 收盘 / 盘后 / 复盘 / harvest / 今天结果 | invoke stock-postmarket skill |
| 全面分析 X / 调研 X / 深度看 X / 研究 X | invoke stock-deep-research skill（P2，待实现）|
| 跑轮询 / 开始监控 / poll / 盘中监控 | `/loop 2m /tool/pandora/bin/python3.12 agents/poll.py --session 2>&1 \| tail -60` |
| morning.py / 跑早间 / 完整早间流程 | `python3.12 morning.py` |
| 看[标的]的基本面 / 研究[标的]数据 | `python3.12 agents/quick_fundamentals.py SYM` |
| 历史回测 / 信号扫描 / 找最优阈值 | `python3.12 agents/backtest_engine.py scan SYM1 SYM2` |
| 框架模拟 / 回测决策框架 | `python3.12 agents/backtest_engine.py simulate SYM`（P2 stock-backtest skill 实现后合并）|
| 更新阈值 / 用回测结果更新配置 | `python3.12 agents/backtest_engine.py update`（P2 实现后合并）|
| 宏观分析 / 今日宏观 / macro | `python3.12 agents/macro_agent.py` |

**注**：买了/卖了/止损了 X 等交易记录由 translator.py 自动路由，无需手动调用。
**注**：`[标的]盘前大师brief` 已整合进 stock-premarket skill Step 6，单独触发词不再需要。
```

- [ ] **Step 2: 验证 CLAUDE.md 格式正确**

```bash
grep -A 5 "invoke stock-premarket" ~/stock_team/CLAUDE.md
```
Expected: 三行 skill 触发条目

- [ ] **Step 3: Commit**

```bash
cd ~/stock_team
git add CLAUDE.md
git commit -m "feat(claude-md): update routing table - analysis trigger words → skill invocations"
```

---

## Task 5: 集成测试

- [ ] **Step 1: 测试 stock-premarket 完整流程**

说："NVDA 今天盘前分析"
- 确认 Claude 读取 6 个脚本的 JSON 输出
- 确认输出包含所有 6 个章节（入场决策/出场评估/条件订单表/论点状态/取消条件）
- 确认格式每次相同（运行两次格式一致）

- [ ] **Step 2: 测试 stock-intraday（需要 poll 已运行过）**

先运行一次 poll：
```bash
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/poll.py NVDA --session 2>&1 | tail -10
```

再说："NVDA 现在如何"
- 确认 Claude 不重跑脚本，只读 JSON
- 确认输出包含现价/RS/Vol 数据

- [ ] **Step 3: 测试 CLAUDE.md 路由正确性**

说："今天 MRVU 盘前"
- 确认触发的是 stock-premarket skill，不是直接调脚本

说："MRVU 现在状态"
- 确认触发的是 stock-intraday skill

- [ ] **Step 4: 最终 Commit**

```bash
cd ~/stock_team
git add CHANGELOG.md
git commit -m "docs: add analysis skills P1 to CHANGELOG"
```

---

## 验收标准

| 验收点 | 验证方式 | 期望结果 |
|--------|---------|---------|
| 格式确定性 | 对同一股票说两次"今天X盘前" | 两次输出结构完全相同 |
| 触发路由 | 说"收盘" | 触发 stock-postmarket，不是直接调 harvest |
| 盘中只读 | 说"X现在如何" | 无新脚本运行，只读 JSON |
| 数据准确 | 入场决策 icon | ✅/⚠️/❌ 与 entry_decision.json 一致 |
| 取消条件 | 盘前分析含取消条件 | 来自 daily_checklist，非通用条件 |
