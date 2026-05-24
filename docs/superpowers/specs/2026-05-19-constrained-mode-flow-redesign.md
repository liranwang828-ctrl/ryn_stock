# Constrained Mode 盘前系统重构 — Design Spec

**Date**: 2026-05-19
**Status**: Draft
**Scope**: 盘前流程从 Active Mode 架构迁移到 Constrained Mode，移除过时组件，打通数据链路

---

## Goal

当前系统是在 Active Mode 框架上逐步堆砌的，大量组件（A-H 场景、CIO 每日全量、ML 模型）已失效或不适合 Constrained Mode。本次重构目标：

1. Node 0 ≤15 分钟完成，每步输出写入 JSON 供后续脚本读取
2. entry_decision 成为中心输出，poll 是它的下游（不是每天默认跑）
3. 移除所有 Active Mode 遗留的死代码和无效组件

---

## 核心逻辑链

```
Node 0 盘前分析（≤15分钟）
    ↓
findings/entry_decision_{date}.json（每只焦点股 ✅/⚠️/❌）
    ↓
今日是否需要 poll？（系统自动判断）
    ↓ 需要                    ↓ 不需要
poll 监控焦点股+持仓         GTC 单接管，提示无需轮询
```

---

## 设计原则

- **输出必须有去处**：每个脚本的关键输出写入 JSON 文件，不能只打印到控制台
- **新股发现是研究动作**：盘前不做股票发现，只从已有 watchlist 评分选股
- **poll 是 entry_decision 的下游**：决策全为"不入场"且持仓稳定 → 无需 poll
- **移除死代码**：intuition_agent（ML 从未跑通）、communityAgent（对机构股无意义）

---

## 新 Node 0 流程（8步，≤15分钟）

| 步骤 | 内容 | 输出文件 | 下游消费方 |
|------|------|---------|-----------|
| Step 1 昨日复盘 | harvest 确认 + observation_outcomes 信号正确率 | — | — |
| Step 2 宏观快照 | macro + VIX + regime；大盘昨日跌>1% 触发压力测试 | macro.json（已有）| premarket_decision |
| Step 3 持仓健康 | portfolio_risk + thesis_status 总览；thesis=weakening 显示 CIO 建议；周一运行 CIO Phase 1 | findings/holdings_review_{date}.json | node 0 下次判断是否重跑 |
| Step 4 焦点选股 | check_leader_triggers() 快速触发检查 + premarket_watchlist_score | findings/today_focus.json（已有）| Step 5-8 |
| Step 5 盘前分析 | premarket.py，只跑焦点股+持仓（非全量 35 只）| premarket_analysis_{date}.json（已有）| checklist/order_sheet |
| Step 6 论点+brief | premarket_checklist.py（持仓+焦点股）| daily_checklist_{date}.json（已有）| 用户 |
| Step 7 条件订单表 | premarket_order_sheet.py（焦点股）| findings/order_sheet_{date}.json（新）+ daily_plan_{date}.json（compat，新）| poll.py 止损/目标 |
| Step 8 入场决策 | premarket_decision.py（焦点股）| findings/entry_decision_{date}.json（新）| poll.py 是否启动 |
| 结语 | 读 entry_decision，自动判断今日 poll 需求，输出启动命令或无需轮询提示 | — | 用户 |

---

## 移除的组件

### 永久移除（死代码）

| 组件 | 原因 |
|------|------|
| IntuitionAgent | ML 模型从未跑通，只是架子 |
| CommunityAgent | 机构驱动股无社群信号价值 |
| Model health check（node 0 Step 0）| ML 从未运行，检查无意义 |

### 从 Node 0 移除（保留为独立工具）

| 组件 | 新触发方式 |
|------|-----------|
| CIO 每日全量（5分钟）| 周一 Phase 1（无辩论）+ 按需手动 |
| candidate_scanner 全量扫描 | 只保留 `check_leader_triggers()` 在 Step 4 |
| watchlist_permanent 晨检 | `python3.12 agents/review_watchlist.py` 手动调用 |
| A-H 场景预测（daily_plan.py Step 8）| 场景生成退休；poll 盘中追踪实际场景保留 |

---

## Sub-spec A：输出标准化

### A1：premarket_order_sheet.py 新增输出

**新增文件 1**：`findings/order_sheet_{date}.json`

```json
{
  "date": "2026-05-19",
  "symbols": {
    "LITE": {
      "entry_range": [860.0, 920.0],
      "entry_base": 870.0,
      "stop_loss": 855.0,
      "target_price": 922.0,
      "rr_ratio": 3.5,
      "cancel_conditions": ["QQQ 开跌 > -1.5%", "XAR 开盘跌超 -2%"],
      "overnight_note": "已在目标区间",
      "narrative_hit": true
    }
  }
}
```

**新增文件 2**：`daily_plan_{date}.json`（兼容格式，解除 poll.py 对 daily_plan.py 的依赖）

经验证，`poll.py` 的 `load_plan_for_sym()` 读取结构为 `plan.get("stocks", {}).get(sym)`，使用字段：`stop`、`t1_target`、`t2_target`（均有 `.get()` fallback，缺失时降级计算，不会 KeyError）。

兼容格式：
```json
{
  "stocks": {
    "LITE": {
      "stop": 855.0,
      "t1_target": 922.0,
      "t2_target": 959.0
    }
  }
}
```

`t2_target` = `round(target_price * 1.04, 2)`（简单估算，无需场景推导）。

### A2：premarket_decision.py 新增输出

**新增文件**：`findings/entry_decision_{date}.json`

```json
{
  "date": "2026-05-19",
  "decisions": {
    "LITE": {
      "decision": "可入场",
      "hard_vetoes": [],
      "soft_vetoes": ["Regime错位"],
      "reason": "1个软否决，信号基本通过",
      "score": 74,
      "rr_ratio": 3.5
    },
    "MRVU": {
      "decision": "不入场",
      "hard_vetoes": ["thesis_status=weakening"],
      "soft_vetoes": [],
      "reason": "硬否决触发",
      "score": 45,
      "rr_ratio": 1.2
    }
  },
  "poll_needed": true,
  "poll_symbols": ["LITE", "BABA", "NVDA"]
}
```

`decisions`：仅包含焦点股（今日 today_focus.json 中的推荐标的），不含持仓股。
`poll_needed`：任意焦点股决策为"可入场"/"观察"，或有持仓存在（需止损监控）。
`poll_symbols`：决策非"不入场"的焦点股 + 所有持仓（持仓默认进入监控模式）。

---

## Sub-spec B：CIO 重构

### B1：删除死亡 Agent

从 `agents/cio.py` 的 `AGENTS` 列表中删除：
- `intuition_agent`（ML 死代码）
- `community_agent`（无效信号）

从 `agents/candidate_scanner.py` 的 `score_candidate()` 删除 intuition_agent 加分逻辑。

### B2：holdings_review 输出

CIO Phase 1（周一自动触发）写入 `findings/holdings_review_{date}.json`：

```json
{
  "date": "2026-05-19",
  "symbols": {
    "BABA": {
      "fund_signal": "neutral",
      "macro_concern": "dollar_strong 逆风仍在",
      "sector_signal": "中性",
      "risk_note": "估值安全边际充足",
      "recommendation": "hold"
    }
  }
}
```

`recommendation` 三值：`hold` / `review_needed` / `update_thesis`

Node 0 Step 3 先检查本周 holdings_review 是否已存在，存在则跳过重跑。

### B3：thesis=weakening 提示（不自动跑）

当任何持仓 thesis_status = "weakening"，Step 3 显示：
```
⚠️ MRVU：论点弱化 — 建议运行深度审查：
   python3.12 agents/cio.py MRVU --phases 0123
```

---

## Sub-spec C：poll.py 集成 entry_decision

### C1：poll.py 读取 entry_decision

**实现位置**：`run_poll()` 入口处，读取 entry_decision 后传入 per-symbol 处理循环。

**标的分类逻辑**（按 entry_decision.decisions 查询）：

| 标的类型 | decisions 中的状态 | poll 行为 |
|---------|------------------|---------|
| 焦点股，decision="不入场" | 存在，不入场 | 跳过 strategy_gate()，只显示一行状态摘要 |
| 焦点股，decision="可入场" | 存在，可入场 | 正常运行 strategy_gate()，显示完整信号 |
| 焦点股，decision="观察" | 存在，观察 | 运行 strategy_gate()，在输出头部附加取消条件提醒 |
| 持仓股 | 不在 decisions 中 | 默认"持仓监控模式"：只跑止损/论点监控，不跑入场信号 |

**伪代码接口**：

```python
# run_poll() 入口
entry_dec = _load_entry_decision()  # 读 findings/entry_decision_{date}.json，失败返回 {}
decisions = entry_dec.get("decisions", {})

# per-symbol 循环中
for sym in poll_symbols:
    sym_decision = decisions.get(sym)          # None 表示持仓股（监控模式）
    if sym_decision and sym_decision.get("decision") == "不入场":
        print(f"  [{sym}] 盘前决策：不入场，跳过信号")
        continue                                # 不调用 strategy_gate()
    # 否则正常处理（持仓监控 或 可入场/观察）
    if sym_decision and sym_decision.get("decision") == "观察":
        print(f"  [{sym}] 盘前决策：观察中 — 软否决：{sym_decision.get('soft_vetoes')}")
    run_symbol_analysis(sym, ...)              # 包含 strategy_gate()
```

`_load_entry_decision()` 失败时返回空 dict → 所有标的按原有逻辑处理（向后兼容）。

### C2：node 0 结语自动输出 poll 建议

读取 `entry_decision_{date}.json` 的 `poll_needed` 和 `poll_symbols`，在 node 0 最后输出：

```
# poll_needed = True 时：
✅ 今日需要轮询
启动命令：/loop 2m /tool/pandora/bin/python3.12 agents/poll.py LITE BABA NVDA --session 2>&1 | tail -60

# poll_needed = False 时：
✅ 今日无入场机会，GTC 单已接管，无需轮询
若持仓有异常可手动启动：python3.12 agents/poll.py BABA NVDA --session
```

---

## Sub-spec D：session_manager.py node 0 重写

按新 8 步流程重写 `run_node(0)`：

- Step 3 加周一判断 + holdings_review 读取/写入逻辑
- Step 4 用 `check_leader_triggers()` 替代完整 `candidate_scanner.scan()`
- Step 5 只传 `focus_syms + pos_syms`，不传 `all_syms`（节省时间）
- Step 7 调用 premarket_order_sheet.py，该脚本同时写 order_sheet + daily_plan compat
- Step 8 调用 premarket_decision.py，写 entry_decision_{date}.json
- 结语：读 entry_decision，输出 poll 建议
- 删除：model health check、watchlist_permanent 晨检、CIO 全量、daily_plan.py Step 8

---

## Validation

1. **Sub-spec A**：运行 `premarket_order_sheet.py LITE` 后，`findings/order_sheet_{date}.json` 和 `daily_plan_{date}.json` 均存在且包含正确字段；运行 `premarket_decision.py LITE` 后 `findings/entry_decision_{date}.json` 存在，`poll_needed` 字段为 bool
2. **Sub-spec B**：运行 `cio.py MRVL --phases 1` 后，IntuitionAgent 和 CommunityAgent 不在输出中；周一 `holdings_review_{date}.json` 被生成
3. **Sub-spec C**：对决策为"不入场"的标的，poll.py 不产生 buy signal；node 0 结语包含 poll 启动命令或"无需轮询"提示
4. **Sub-spec D**：node 0 完成后，`findings/entry_decision_{date}.json` 和 `findings/order_sheet_{date}.json` 均存在；premarket.py 不再对全量 35 只 watchlist 运行（日志显示标的数 ≤ 焦点股+持仓数量）；IntuitionAgent 和 CommunityAgent 不出现在任何 node 0 输出中

---

## Out of Scope

- poll.py 的全面重构（只改入口读取 entry_decision，不改信号计算逻辑）
- 历史 daily_plan_{date}.json 文件的迁移（旧文件保留，只影响新日期）
- A-H 场景系统在 poll 盘中追踪部分（保留不动，只退休盘前预测部分）
- 社群情绪数据源（CommunityAgent 删除后，无替代方案，作为已知缺口接受）
