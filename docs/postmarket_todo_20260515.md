# 盘后待办 — 2026-05-15

## 0. 大师时间线分析 + 准确率追踪（高优先，盘后立即做）

**背景：** 今天 NBIS 完整 A-B-C 反转，7位大师需要分析今日时间线并给出明日判断，供明天验证。

**实现：**
- 新增 `agents/timeline_analyst.py` — 读取 `learning/poll_state_{date}.json` 和 `knowledge/snapshots_{date}.jsonl`，提取今日关键节点（日高/日低/场景切换/量放大时刻）
- 7位大师各自分析时间线（规则驱动，~500 token 总计），每人给出"明日关键判断"（带条件）
- 保存到 `learning/master_timeline_judgments_{date}.json`
- 明日 harvest 时核对判断，更新 `master_accuracy.json`（新增"时间线判断"类别，与 CIO 预测并列）

**长期价值：** 积累 N 天数据后，可以看到：
- Minervini 在 A-B-C 形态下准确率 X%
- Druckenmiller 在宏观逆风+个股强势组合下准确率 Y%
- 哪位大师在哪种盘面下最可信

## 1. 反转入场系统设计（高优先）
- 背景：今天 NBIS 完成了完整 A-B-C 反转，C点（12:30-13:00，$211）是绝佳入场机会，但现有门控完全没有捕捉到
- 目标：设计"底部猎手"模式，与当前趋势跟随模式并列
- 核心信号：
  - RSI14_5m < 25（极端超卖）
  - 量比 < 0.3x（卖方枯竭）
  - 价格不创新低（第二次测试守住）
  - MACD 底背离（价格创新低但MACD不创新低）
  - 首根长下影线 5分钟K线
- 数据：今天 NBIS 的5分钟K线是训练集

## 2. 盘中逻辑重构 Phase B（中优先）
- 调节层：时间段/VWAP位置/催化剂/CIO/RS趋势/R:R
- 模式引擎：动态 swing/intraday 切换（每次poll重新评估）
- 浮亏 > max(3%, 0.5×ATR_pct) → 自动降级日内模式
- 15:45 ET 日内仓位减仓提醒

## 3. 疑惑点复盘
- 上午止损触发 vs 应守住的判断：保本止损（软线）vs 结构止损（硬线）逻辑混乱
- 今天系统多次说"收盘了"但还有几小时（时间系统修复后复盘是否有遗漏）

## 4. 知识文件利用（低优先）
- reports/research_MRVL_*.md 等深度报告接入 CIO
- company_profiles.json 已接入 data_agent，验证 CIO agent 是否实际读取

## 5. positions.json T1/T2/T3 分层结构（中优先）
- NBIL 已有 T2 条件字段，需要扩展所有持仓
- 结构设计：T1/T2/T3 各自入场价、股数、止损

---
生成时间: 2026-05-15 盘中
