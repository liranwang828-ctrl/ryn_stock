# Stock Team Agent 系统介绍

> 面向新开发者的快速入门文档 | 更新日期：2026-05-21

---

## 1. 系统概述

Stock Team 是一个**美股自动交易决策系统**，由多个协作的 AI Agent 组成。系统通过"阶段+轮询"架构，在盘前、盘中、盘后不同时间节点自动进行数据采集、多维分析、集体讨论和交易决策。

**核心特点：**
- **多 Agent 辩论机制**：6个 Domain Agent（技术/基本面/宏观/情绪/风险/板块）独立分析，通过讨论板异步互动
- **大师 Persona 系统**：模拟 Minervini、Druckenmiller、Marks 等 7 位投资大师评估
- **论点驱动持仓**：持仓绑定可证伪的论点（thesis），实时监控论点状态
- **宏观策略节点**：所有交易价位从 TA 系统性计算，不用任意百分比

---

## 2. 核心脚本架构

### 数据层（Phase 0）
| 脚本 | 输入→输出 |
|------|----------|
| `data_agent.py` | yfinance API → `data_raw_primary.json` / `data_raw_secondary.json` |
| `verifier_agent.py` | 双数据源 → `data_verified.json`（字段级质量检验）|
| `quick_fundamentals.py` | 股票代码 → 终端基本面摘要（CLI工具）|
| `company_profile_fetcher.py` | 股票代码 → `findings/company_profile_{sym}.json`（护城河/风险/bull/bear）|

### 分析层（Phase 1，6个Agent并行）
| Agent | 专注领域 | 输出 |
|-------|---------|------|
| `tech_agent.py` | MACD/RSI/MA/VCP/量价 | `findings/TechAgent_{sym}_{date}.json` |
| `fund_agent.py` | PE/FCF/增速/内部交易 | `findings/FundAgent_{sym}_{date}.json` |
| `macro_agent.py` | 利率/美元/地缘对个股影响 | `findings/MacroAgent_{sym}_{date}.json` |
| `sentiment_agent.py` | 新闻/分析师/短线情绪 | `findings/SentimentAgent_{sym}_{date}.json` |
| `risk_agent.py` | Beta/波动率/止损建议 | `findings/RiskAgent_{sym}_{date}.json` |
| `sector_agent.py` | 行业周期/相对强弱 | `findings/SectorAgent_{sym}_{date}.json` |

### 决策层（Phase 2）
| 脚本 | 作用 |
|------|------|
| `debate_engine.py` | Agent 互相质证（challenge/endorsement），驱动立场修订 |
| `persona_engine.py` | 应用7位大师人设，生成各自买卖建议 |
| `strategy_agent.py` | 整合所有立场，输出最终信号到 `strategy_result.json` |

### 盘前执行链
```
premarket_watchlist_score.py → premarket.py → premarket_order_sheet.py
→ premarket_decision.py → premarket_exit_sheet.py → premarket_checklist.py
→ macro_strategy.py --refresh → premarket_summary.py
```

### 盘中执行层
| 脚本 | 作用 |
|------|------|
| `poll.py` | 每2分钟轮询，集成论点健康/Flex信号/全局否决/战术入场计划 |
| `entry_guard.py` | 双重守卫（宏观+个股）防止追涨追跌 |
| `harvest_agent.py` | 盘后复盘，更新论点准确率 |

### 宏观策略节点层（新功能）
| 脚本 | 作用 |
|------|------|
| `macro_strategy.py` | 从 TA 系统计算 13 个交易节点（止损/加仓/目标/情景降级等）|
| `strategic_memo_writer.py` | 整合 CIO 分析结果生成 `strategic_memo_{sym}.json` |
| `report_viewer.py` | 将 memo 渲染为 `reports/research_{sym}.html`（Notion 风格研报）|

### 回测优化层（新功能）
| 脚本 | 作用 |
|------|------|
| `backtest_runner.py` | 统一入口：全量回测 / --apply 写回 / --restore 恢复 |
| `backtest_macro.py` | 5年日线扫描宏观参数（VIX阈值/MA20/场景质量等）|
| `backtest_micro.py` | 5年结构位模拟 + 60天盘中信号扫描 |

---

## 3. 数据文件地图

### 配置（`config/`）
| 文件 | 作用 |
|------|------|
| `positions.json` | 当前持仓（cost/shares/thesis/thesis_status/falsification_conditions）|
| `macro_strategy_params.json` | 宏观环境参数（VIX阈值/观察期/场景质量映射）|
| `micro_strategy_params.json` | 盘中信号参数（RSI/VWAP/量比阈值/时间窗口）|
| `leveraged_pairs.json` | 杠杆ETF → 底层标的映射（MRVU→MRVL / LITX→LITE）|
| `poll_config.json` | 轮询标的列表、板块映射 |
| `decision_thresholds.json` | 信号置信度门槛（由回测更新）|

### 关键输出（`findings/`）
| 文件模式 | 生成者 | 内容 |
|---------|--------|------|
| `premarket_summary_{date}_{sym}.json` | premarket_summary.py | 盘前汇总（入场/出场/论点监控层）|
| `exit_decision_{date}.json` | premarket_exit_sheet.py | 所有持仓的出场评估（merge写入，并行安全）|
| `entry_decision_{date}.json` | premarket_decision.py | 入场决策（merge写入，并行安全）|
| `macro_{sym}_{date}.json` | macro_agent.py | 宏观分析 |
| `backtest_trades_{sym}.json` | backtest_micro.py | 结构位回测逐笔交易记录（含时间/价格/依据）|
| `backtest_report_{date}.json` | backtest_runner.py | 回测对比报告（含推荐参数）|
| `params_backup_{date}.json` | backtest_runner.py | 参数变更前自动备份 |

### 关键根目录文件
| 文件模式 | 内容 |
|---------|------|
| `strategic_memo_{sym}.json` | 每只股票的完整研究备忘录（六维分析+大师观点+持仓策略）|
| `macro_strategy_{sym}.json` | 13个交易节点 + k值进化参数（每次运行更新）|
| `discussion_board.jsonl` | CIO运行时的Agent辩论全记录 |

### 报告（`reports/`）
| 文件 | 内容 |
|------|------|
| `research_{sym}.html` | 覆盖式研报（每次分析覆盖上次）|
| `trading_nodes_guide.html` | 13个交易节点独立使用说明页 |

---

## 4. Skills 触发规则（来自 CLAUDE.md）

| 用户说 | 触发 Skill | 核心脚本 |
|--------|-----------|---------|
| "开始今天" / "早上好" / "来了" | `trading-day` | morning.py 节点编排 |
| "X 盘前" / "X 今天怎么看" | `stock-premarket` | premarket 6步链 + macro_strategy --refresh |
| "X 现在如何" / "X 盘中" | `stock-intraday` | 只读 findings/ JSON，不重跑脚本 |
| "收盘" / "盘后" / "复盘" | `stock-postmarket` | harvest_agent + postmarket_review |
| "全面分析 X" / "深度研究 X" | `stock-deep-research` | cio.py phases013 + strategic_memo_writer + macro_strategy + report_viewer |
| "回测" / "参数优化" | `stock-backtest` | backtest_runner.py（人工确认后写回）|
| "组合健康" / "持仓检查" | `portfolio-health` | portfolio_risk_agent + exit_sheet |
| "新建仓位 X" / "建仓 X" | `position-builder` | quick_fundamentals + 交互5问 → positions.json |
| "记录这次操作" | `trading-decision-capture` | trading_lessons.json 追加 |

---

## 5. 完整交易日流程

```
盘前 (8:00-9:30 ET)
├─ morning.py
│  ├─ health_check.py → 持仓风险快照
│  ├─ candidate_scanner.py → 当日候选池
│  └─ daily_plan.py → 当日止损/目标价
│
├─ stock-premarket skill（每只持仓）
│  ├─ premarket_watchlist_score.py → 观察列表评分
│  ├─ premarket.py → 场景/gap/宏观分析
│  ├─ premarket_order_sheet.py → 条件单草稿
│  ├─ premarket_decision.py → 入场决策（merge写入）
│  ├─ premarket_exit_sheet.py → 出场评估（merge写入）
│  ├─ premarket_checklist.py → 五步清单（持仓类型/论点/行动）
│  └─ macro_strategy.py --refresh → 更新动态节点（Flex/Time/Catalyst）
│
开盘30分钟观察 (9:30-10:00 ET, 禁止操作)
│
盘中主动期 (10:00+ ET)
├─ poll.py（每2分钟）
│  ├─ _global_veto() → 全局否决检查（VIX/QQQ/MA20乖离）
│  ├─ compute_post_open_plan() → 30分钟后战术入场计划
│  ├─ evaluate_thesis_health() → 论点健康（含情景降级/证伪条件）
│  └─ check_flex_signals() → Flex加减仓信号（RSI/VWAP/量比）
│
盘后 (16:00+ ET)
└─ stock-postmarket skill
   ├─ harvest_agent.py → 收割结果/更新论点准确率
   └─ postmarket_review.py → 复盘分析
```

---

## 6. 核心设计原则

**论点驱动（Thesis-Driven）**
- 每个持仓绑定可证伪的论点，记录在 `positions.json.thesis` 和 `falsification_conditions`
- 盘前和盘中实时监控论点状态（intact → weakening → broken）
- 论点破裂 = 止损出场，不等技术信号

**节点精确化（Node Precision）**
- 所有交易价位从 MA50/ATR/Fibonacci 系统计算，不用成本比例（如 -13%）
- 13个主节点：动态止损/Add1-2/Re-entry/TP1-2/Flex/情景降级/催化剂/时间止损
- 节点系数（k1/k_tp等）通过回测优化，写入 `macro_strategy_{sym}.json` evolution 字段

**并行安全（Parallel-Safe）**
- 多标的并行深度分析时，per-sym 文件独立（`{Agent}_{sym}_{date}.json`）
- exit_decision / entry_decision 使用 fcntl 文件锁 + merge 写入，防止覆盖

**人工确认门控**
- 回测结果生成对比报告，用户确认后才执行 `--apply` 写回参数
- 写回前自动备份，支持 `--restore` 快速恢复

---

## 7. 开发环境快速启动

```bash
# Python 路径
/tool/pandora/bin/python3.12

# Git 操作（特殊环境需要）
GIT_DISCOVERY_ACROSS_FILESYSTEM=1 git ...

# 当前开发分支
feat/macro-strategy  # 含宏观策略节点+回测系统

# 快速验证所有测试
cd ~/stock_team && /tool/pandora/bin/python3.12 -m pytest tests/ -q

# 生成所有持仓研报
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/report_viewer.py

# 运行盘中监控
cd ~/stock_team && /tool/pandora/bin/python3.12 agents/poll.py --session

# 查看持仓
python3.12 -c "import json; [print(k, v['cost']) for k,v in json.load(open('config/positions.json'))['positions'].items()]"
```

---

## 8. 关键术语

| 术语 | 含义 |
|------|------|
| **Node** | 交易日状态机（0晨间/1盘前/2观察/3盘中/6复盘）|
| **Phase** | CIO 分析阶段（0数据/1Agent并行/2辩论/3综合）|
| **Thesis** | 持仓论点（可证伪的基本面或技术面逻辑）|
| **Falsification** | 论点失效条件（具体可观测的触发事件）|
| **Flex Signal** | 盘中综合超买/超卖信号（RSI+VWAP+量比，3/4满足触发）|
| **宏观策略** | 制定所有价格节点的策略（替代任意百分比止损）|
| **具体策略** | 盘中具体买卖执行（poll.py + Flex signals）|
| **global_veto** | 全局否决：VIX>25↑ / bear regime / QQQ急跌 / 尾盘 |
| **post_open_plan** | 开盘30分钟后的战术入场计划（场景×结构位×宏观）|

---

*新开发者建议：先从 `poll.py` 主循环（~2200行）和 `premarket_summary.py` 理解数据流，再深入各 Agent 实现。*
