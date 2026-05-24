# Skill 格式标准化 Brainstorm 进度记录

**最后更新**: 2026-05-20
**状态**: 进行中，已完成 stock-deep-research，正在进行 stock-premarket

---

## 已完成决策

### 总体框架
- A+B 混合，每个 skill 特异化
- B 级（字段级固定）：JSON 输出文件，集成关键字段，可编程读取
- A 级（章节级固定）：人类可读报告，叙述性内容，不参与集成
- 永不使用 C 级（纯代码生成叙述）

### 可复现性约束（最重要原则）
- LLM 不自由生成判断文字，而是从预定义枚举集合中选择
- 规则驱动推导（第一条命中即停止）
- 相同输入数据 → 相同结构化输出

### stock-deep-research 输出契约（已有 spec）
- Spec 路径：`docs/superpowers/specs/2026-05-20-skill-format-standardization-deep-research.md`
- 输出：`strategic_memo_{sym}.json`（19字段，4层结构）
- 合成机制：主要矛盾枚举选择 + 大师投票（3题结构化）+ 规则推导综合结论
- 战术层（entry_decision/exit_decision）每天刷新，不存入 strategic_memo

---

## stock-premarket 进度（进行中）

### 现有 6 个输出文件（stock-premarket skill 运行 6 个脚本产出）
1. `findings/today_focus.json` — 6维评分（watchlist_score）
2. `premarket_analysis_{date}.json` — gap/场景/新闻/catalyst（per stock）
3. `findings/order_sheet_{date}.json` — 入场条件/价位/止损/目标/取消条件
4. `findings/entry_decision_{date}.json` — 入场决策三态 + hard/soft vetoes
5. `findings/exit_decision_{date}.json` — 出场评估三态 + stop levels
6. `daily_checklist_{date}.json` — thesis_status/daily_action

### 已决定
- 需要合并成一个 `premarket_summary_{date}.json`，作为 stock-intraday 和 trading-day 的统一输入
- 结构草案：
  ```json
  {
    "date", "sym",
    "market_context": {spy_pre_chg, env, regime},
    "stock_snapshot": {gap_pct, pred_scene, news_type, catalyst_strength, watchlist_score, overnight_note},
    "entry": {decision, hard_vetoes[], soft_vetoes[], entry_base, stop_loss, target_price, rr_ratio, entry_conditions[], cancel_conditions[]},
    "exit": {decision, hard_stop, stop_source, hard_dist_pct, hard_triggers[], soft_triggers[]},  // 仅持仓
    "thesis": {status, daily_action}
  }
  ```

### 待决定的两个问题（下次继续）
1. **每日一个文件 vs 每股一个文件**？
   - `premarket_summary_2026-05-20.json`（含所有标的）
   - 还是 `premarket_summary_2026-05-20_NVDA.json`（每股单独）
2. **谁生成这个文件**？
   - premarket_decision.py 最后一步写入
   - 还是 stock-premarket skill 自己合并写入（新建 premarket_summary.py）

---

## 剩余 skill 格式定义顺序（按依赖关系）

1. ✅ stock-deep-research（strategic_memo）— 已完成
2. 🔄 stock-premarket（premarket_summary）— 进行中，有两个待决定问题
3. ⬜ stock-intraday — 依赖 premarket_summary 作为输入
4. ⬜ stock-postmarket
5. ⬜ portfolio-health
6. ⬜ stock-backtest
7. ⬜ position-builder
8. ⬜ trading-day（编排层）

---

## 如何恢复 brainstorm

清空上下文后说：**"继续 skill 格式标准化 brainstorm，从 premarket_summary 开始"**

然后我会读取：
- 本文件（进度记录）
- `docs/superpowers/specs/2026-05-20-skill-format-standardization-deep-research.md`（已完成的 spec）

先回答两个待决定问题，再继续 stock-premarket 的完整 spec。
