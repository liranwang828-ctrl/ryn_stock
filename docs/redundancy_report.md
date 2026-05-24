# 冗余文件评估报告 — 2026-05-16

> 基于框架从"趋势跟随"迁移到"论点驱动+Flex仓"的评估

## 已确认可归档/删除的文件

| 文件 | 行数 | 原因 | 建议 |
|------|------|------|------|
| `agents/auto_trigger.py` | 172 | 完全被 translator + session_manager 替代，无任何引用 | **删除** |
| `agents/multi_stock.py` | 70 | CIO run_parallel() 直接并行，无引用 | **删除** |
| `agents/cleanup.py` | 106 | 手动维护成本高，无引用 | **删除** |
| `agents/report_analyst.py` | 608 | 仅被 stock_report.py 调用，随之废弃 | **归档** |
| `agents/stock_report.py` | 1881 | 功能与 report_agent 重叠，体积过大，无新增引用 | **归档** |
| `agents/market_scanner.py` | 456 | 被 candidate_scanner 替代；已从 premarket.py 移除调用 | **归档** |
| `agents/strategy_council.py` | 215 | 功能内嵌到 CIO debate_engine，仅测试引用 | **归档** |

**可删除总计：约 348 行（3文件）**
**可归档总计：约 3,160 行（4文件）**

## 仍有价值保留的文件

| 文件 | 保留原因 |
|------|---------|
| `agents/session_recorder.py` | write_snapshot() 仍被 poll.py 活跃调用，不可删 |
| `agents/strategy_gate()` 函数 | 保留作"二次确认"和历史参考，已不是主决策 |

## 新框架新增文件（2026-05-16）

| 文件 | 功能 |
|------|------|
| `agents/premarket_checklist.py` | 盘前五步清单生成，Node 0 Step 6.5 的核心 |
| `agents/poll_state.py` | 轮询状态持久化，跨轮次连续性 |
| `agents/timeline_analyst.py` | 今日时间线分析（大师历史进程分析） |
| `learning/daily_checklist_{date}.json` | 每日盘前清单输出 |
| `learning/master_score_log_{date}.jsonl` | 大师评分时间序列（每2分钟记录） |
| `learning/master_timeline_judgments_{date}.json` | 大师明日关键判断存档 |
| `learning/observation_log.jsonl` | 盘中观察信号日志 |
| `learning/observation_outcomes.jsonl` | 盘后信号配对验证 |
| `config/daily_focus.json` | 每日固定关注5只股票 |
| `docs/TODO.md` | 系统待办（Phase B调节层为P0） |
| `docs/SYSTEM_FLOWCHART.md` | 系统全流程文档（已更新框架说明） |

## 执行计划

### 立即（今天）
- [x] SYSTEM_FLOWCHART.md 加入框架版本说明
- [x] 本报告创建

### 近期（1-2周）
- [ ] 确认 log_action/log_thought 功能已被 decision_trace.jsonl 完全覆盖
- [ ] 创建 `archive/deprecated_2026-05-16/` 目录
- [ ] 将7个废弃文件移入归档目录

### 长期（1个月后）
- [ ] 删除确认无用的归档文件（届时再做最终确认）
