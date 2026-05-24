# Agent 文件状态清单

每次系统变更后更新。分三类：核心路径、辅助路径、历史遗留。

## 🟢 核心路径（每日运行）

| 文件 | 触发方式 | 说明 |
|------|---------|------|
| `poll.py` | 手动/loop | 实时盘中监控主力（新增Flex信号监控） |
| `premarket_checklist.py` | Node 0 Step 6.5 | 盘前五步清单（论点驱动新框架核心）|
| `premarket.py` | Node 0/1 | 盘前分析 |
| `candidate_scanner.py` | Node 0 | 候选池扫描 |
| `portfolio_risk_agent.py` | Node 0 | 组合风险快照 |
| `health_check.py` | Node 0/cron | 系统健康检查 |
| `harvest_agent.py` | cron 4:35 PM ET | 每日收盘记录 |
| `daily_script.py` | Node0/translator/poll | 今日剧本持久化（检查点+状态摘要） |
| `translator.py` | session_manager | 意图识别 |
| `session_manager.py` | 对话入口 | 工作流编排 |
| `entry_guard.py` | 对话/poll | 交易记录 |

## 🟡 辅助路径（按需运行）

| 文件 | 触发方式 | 说明 |
|------|---------|------|
| `quick_fundamentals.py` | 分析前必须调用 | 个股基本面一站式获取（PE/FCF/目标价/增速/内部人），见 DATA_COVERAGE.md |
| `cio.py` | 用户显式调用 | 全量大师分析 |
| `learning_agent.py` | cron 每周五 | 模型重训练 |
| `bootstrap_agent.py` | 手动（月度/重大变更后）| 历史训练 |
| `fundamentals_tracker.py` | 手动（每季度财报后）| 基本面追踪 |
| `unified_confidence.py` | premarket集成 | 统一置信度 |
| `market_calendar.py` | poll/premarket | 时间感知 |
| `intuition_agent.py` | CIO Phase 1 / premarket | 历史胜率推理 |
| `postmarket_review.py` | Node 6 | 收盘复盘 |
| `daily_plan.py` | Node 2 | 日内计划生成 |

## 🔴 历史遗留（标记为 deprecated）

| 文件 | 原设计用途 | 为什么废弃 | 处理建议 |
|------|-----------|-----------|---------|
| `auto_trigger.py` | 盘中自动触发CIO | 已被 translator + session_manager 替代 | 保留但不运行 |
| `strategy_council.py` | 大师审查交易规则 | 功能已内嵌到 CIO debate_engine | 保留参考 |
| `multi_stock.py` | 多标的并行比较 | CIO可直接并行，不需要此中间层 | 可删除 |
| `market_scanner.py` | 5维市场扫描 | 被 candidate_scanner.py 替代 | 被 premarket 引用，暂留 |
| `stock_report.py` | 生成股票报告 | 功能重叠 report_agent，且1881行过重 | 不再新增使用 |
| `report_analyst.py` | 分析报告格式化 | 仅被 stock_report.py 调用 | 随 stock_report 一起存档 |
| `session_recorder.py` | 记录 session 快照 | 已被 decision_trace.jsonl 替代 | 保留至 decision_trace 稳定 |
| `cleanup.py` | 清理旧文件 | 手动维护成本高 | 可删除 |

## 📋 维护规则

1. 新增功能优先集成到核心路径，不新建独立 agent
2. 辅助路径超过3个月未运行 → 移入历史遗留
3. 历史遗留超过6个月 → 删除（备份到 `archive/`）
4. 每次系统元评估时更新此文件
