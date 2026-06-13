# 盘前流程漏洞待办 / Premarket Workflow TODO

日期：2026-06-01

## 中文

### P0：盘前流程硬门槛修复

背景：第一次完整盘前规划时，系统先读取了旧文件，未先使用付费 Polygon/Massive API 补齐当日 `premarket_summary` 与 `entry_decision`，导致主控被 `stale_premarket_summary` 阻断。

需要做：
1. 盘前主流程必须先刷新 Polygon/Massive 快照，再生成 `premarket_analysis_{date}.json`、`order_sheet_{date}.json`、`entry_decision_{date}.json`、`exit_decision_{date}.json`、`premarket_summary_{date}_{sym}.json`、`decision_state_{date}.json`。
2. 若任一持仓或关注标的缺少当日 summary / entry decision，流程必须停止并提示“先补文件”，不能直接给交易规划。
3. 梳理价格源优先级：Polygon/Massive > broker 实时报价 > yfinance fallback，并在每份运行产物里写入 `price_source`。
4. `premarket_summary.py` 需要测试数字型 macro_strategy 节点，例如 `nodes.flex_reduce = 450.0`。
5. `premarket_decision.py` 的 MA20 乖离输出出现异常大数值，疑似单位不一致；后续修复，但不在盘中临时改交易规则。

## English

### P0: Premarket Workflow Hard Gate

Context: The first full premarket planning pass on 2026-06-01 used stale artifacts before refreshing paid Polygon/Massive data and before generating same-day summaries and entry decisions.

Required:
1. Refresh Polygon/Massive first, then generate all same-day premarket artifacts before any LLM-controlled planning output.
2. Stop the workflow if any held or focused symbol is missing same-day summary or entry decision.
3. Make price-source priority explicit: Polygon/Massive > broker live quote > yfinance fallback.
4. Add coverage for numeric `macro_strategy` nodes in `premarket_summary.py`.
5. Investigate the MA20 deviation unit mismatch in `premarket_decision.py`.
