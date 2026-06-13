# 盘前规划流程固化 Runbook

日期：2026-06-01
语言：中文为主，英文简版附后
适用场景：用户要求“用完整系统做盘前规划”时，Codex/LLM 主控必须先按本流程补齐当日数据，再给交易规划。

## 1. 核心原则

盘前规划不能从旧文件直接推断。只要今天的 `premarket_summary_{date}_{sym}.json` 或 `entry_decision_{date}.json` 不存在、不新鲜、解析失败，就不能输出交易结论。

价格源优先级：
1. Polygon/Massive 付费 API 快照
2. 券商实时报价（用户提供或未来接入）
3. yfinance fallback

如果 yfinance 与 Polygon/Massive 冲突，当日交易规划以 Polygon/Massive 为准，并在运行产物中保留 yfinance 原值用于审计。

## 2. 标的池确定

先读取真实持仓与今日关注，而不是沿用旧 portfolio snapshot。

必读文件：
- `config/positions.json`
- `config/daily_focus.json`
- `today_focus.json`（若存在）

2026-06-01 实际采用标的：

```text
NVDA COHR IAU SGOV NOW VST MSFT GOOGL ZS TSM
```

注意：若 `positions.json` 明确说明某些标的已清仓，不得再把旧 snapshot 里的 BABA / FUTU / SYM 当作当前持仓。

## 3. 当日必须生成的产物

完整盘前规划至少需要以下文件：

```text
findings/polygon_snapshot_{date}.json
premarket_analysis_{date}.json
findings/order_sheet_{date}.json
daily_checklist_{date}.json
findings/entry_decision_{date}.json
findings/exit_decision_{date}.json
findings/premarket_summary_{date}_{SYM}.json
findings/decision_state_{date}.json
```

其中 `premarket_summary` 必须覆盖所有持仓和今日关注标的，`decision_state` 必须显示：

```text
identity.source_freshness.premarket_summary.status = fresh
identity.source_freshness.entry_decision.status = fresh
```

## 4. 标准执行顺序

### Step 1：刷新 Polygon/Massive 快照

使用 `.env` 中的 `POLYGON_API_KEY`，不要打印 API key。

输出：

```text
findings/polygon_snapshot_{date}.json
```

快照应包含 SPY / QQQ 以及全部持仓和关注标的。若批量接口缺单票，例如 ZS，则单独调用 ticker snapshot，并优先使用可用的 `lastTrade.p` / `min.c` / `todaysChangePerc` 字段。

### Step 2：生成基础盘前分析

```powershell
python agents\premarket.py NVDA COHR IAU SGOV NOW VST MSFT GOOGL ZS TSM
```

输出：

```text
premarket_analysis_{date}.json
```

如果脚本内部使用 yfinance 价格，应在生成后用 Polygon/Massive 快照修正：
- `gap_pct`
- `polygon_price`
- `polygon_prev_close`
- `price_source`
- 原 yfinance 值保留为 `*_yfinance_original`

### Step 3：生成 order sheet

```powershell
$env:PYTHONIOENCODING='utf-8'
python agents\premarket_order_sheet.py NVDA COHR IAU SGOV NOW VST MSFT GOOGL ZS TSM
```

输出：

```text
findings/order_sheet_{date}.json
```

同样需要用 Polygon/Massive 修正：
- `current_price`
- `overnight_price`
- `overnight_chg`
- `price_source`

### Step 4：生成 checklist

```powershell
python agents\premarket_checklist.py NVDA COHR IAU SGOV NOW VST MSFT GOOGL ZS TSM
```

输出：

```text
daily_checklist_{date}.json
```

### Step 5：生成 entry / exit decision

```powershell
$env:PYTHONIOENCODING='utf-8'
python agents\premarket_decision.py NVDA COHR IAU SGOV NOW VST MSFT GOOGL ZS TSM
```

输出：

```text
findings/entry_decision_{date}.json
findings/exit_decision_{date}.json
```

如果 `exit_decision` 使用 yfinance 当前价，需要用 Polygon/Massive 增加复核字段：
- `cur_yfinance_original`
- `cur`
- `price_source`
- `polygon_prev_close`
- `polygon_change_pct`
- `hard_dist_pct`
- `polygon_recheck_flags`
- `polygon_recheck_note`

不要在盘中临时改交易规则；若价格源变化导致原出场判断可疑，只增加复核标记并提醒人工确认。

### Step 6：生成 premarket summary

```powershell
$env:PYTHONIOENCODING='utf-8'
python agents\premarket_summary.py NVDA COHR IAU SGOV NOW VST MSFT GOOGL ZS TSM
```

输出：

```text
findings/premarket_summary_{date}_{SYM}.json
```

若某只生成失败，不能继续给盘前规划。先修复或补齐该只 summary。

2026-06-01 暴露的问题：`macro_strategy_{SYM}.json` 里部分 `nodes.flex_reduce` 是数字，不是 `{price: ...}` 字典，旧版 `premarket_summary.py` 会崩。已在汇总层增加数字节点兼容，但后续仍需补测试。

### Step 7：生成 decision state

```powershell
python agents\decision_state_hub.py --date 2026-06-01 --base-dir . NVDA COHR IAU SGOV NOW VST MSFT GOOGL ZS TSM
```

输出：

```text
findings/decision_state_{date}.json
```

这是 LLM 主控与后续 dashboard 的统一输入。交易规划必须以这个文件为准，而不是人工拼多个 JSON。

### Step 8：硬门槛检查

必须检查：

```text
freshness_problems = []
```

检查逻辑：
- 所有标的 `premarket_summary` 均为 `fresh`
- `entry_decision` 为 `fresh`
- `controller.blocked_by` 不包含 `stale_premarket_summary`
- `controller.audit.allowed_actions` 不允许 LLM 绕过纪律

若检查失败，回答用户：“盘前文件还没补齐，我先补文件”，不能直接输出交易建议。

## 5. LLM 输出纪律

当 `decision_state` 中：

```text
controller.evidence_alignment = mixed
controller.controller_verdict = avoid
controller.audit.allowed_actions = ["avoid", "monitor", "wait"]
```

LLM 只能输出：
- 不追入
- 等待
- 监控
- 人工复核项

不能输出：
- 立即买入
- 强信号
- 已完全验证
- 忽略 stale / missing / caution 的判断

## 6. 2026-06-01 盘前结果摘要

当日补齐后，10 个标的的 `premarket_summary` 与 `entry_decision` 均为 fresh，无 stale 阻断。

主控结论：

```text
NVDA  avoid / mixed / 55
COHR  avoid / mixed / 55
IAU   avoid / mixed / 55
SGOV  avoid / mixed / 55
NOW   avoid / mixed / 55
VST   avoid / mixed / 55
MSFT  avoid / mixed / 55
GOOGL avoid / mixed / 55
ZS    avoid / mixed / 55
TSM   avoid / mixed / 55
```

当日纪律结论：所有标的不新开、不追入。重点人工复核 COHR、GOOGL、VST、IAU、SGOV。

## 7. 已记录的后续优化

1. 把 Polygon/Massive 刷新固化成自动脚本，而不是手工 inline patch。
2. 给 `premarket_summary.py` 补数字型 macro node 测试。
3. 修复 `premarket_decision.py` MA20 乖离单位异常。
4. 将“缺少今日 summary / entry decision”升级为主流程硬失败。
5. 后续如接入 broker quote，则把 broker 价格作为 Polygon 后的复核层。

## English Brief

Before any premarket trading plan, refresh paid Polygon/Massive data, regenerate all same-day artifacts, then build `decision_state_{date}.json`. If any held or focused symbol lacks fresh `premarket_summary` or same-day `entry_decision`, stop and generate the missing files first. The LLM controller may only plan from fresh `decision_state`, and must obey `controller.audit.allowed_actions`.
