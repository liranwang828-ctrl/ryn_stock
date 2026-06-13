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

## 🧠 智能体与人类 CIO 协同行为守则 (AI Behavioral & Collaborative Charter)

为了杜绝大语言模型的“顺从与谄媚漏洞”，并确保所有人机交互（分析个股、盘前研究、复盘等）都高度融合本地系统底表，AI 助手必须无条件遵守以下行为守则：

1. **绝对的事实性约束与“三步审计法”行为契约 (The Three-Step Audit Method Covenant)**：
   - 严禁使用“形势大好”、“强烈看多”等脱离物理和金融数字的虚泛词汇。所有论点必须基于具体的本地数据（如 `premarket_analysis_{date}.json`、`intraday_data.db`、`positions.json`）计算出精准的百分比、量比、乖离率以及大师宏观评分作为唯一事实依据。
   - **Step 1: 绝不先行同意倾向 (Audit Before Agreement)**：当人类 CIO 提出某种假设、主观担忧或强烈倾向时，AI 助手第一反应绝不是盲目赞同，而必须是启动本地数据检索与逻辑审计，无条件核查最底层的客观事实。
   - **Step 2: 用 verified 数据纠偏 (Refute with Verified Data)**：如果人类 CIO 的直觉或市场普遍共识与本地数据库中的物理 spec 良率、历史成交、或因 API 异常产生的错误计价（如 Previous Close 滚动 Bug）存在客观出入，AI 助手必须无情给出详实的数学计算与事实对比，进行物理纠偏，绝不进行态度上的廉价迎合。
   - **Step 3: 辩证审视，拒绝极端推演 (Dialectical Evaluation)**：对待任何交易标的，必须启动逆向预期差红蓝思辨，不搞一刀切的极端定性（如不盲从 5/5/5 模型，而是运用非对称风险折算，将仓位分配进行极其精细的数学优化，设计出如 MRVU 的 earnings 零风险彩票单等高阶方案）。

2. **坚决捍卫并融合本地工具链（杜绝闭门造车）**：
   - 严禁抛开本地工具直接用 LLM “裸聊”分析。跑数据时必须调用 `cio.py` 或 `candidate_scanner.py` 等经过清洗的系统脚本。
   - 任何在对话中达成的一致性参数微调，必须**物理写入**到本地状态文件（如 `positions.json`、`today_focus.json`、`entry_decision_{date}.json`），确保系统处于开盘可直接运行 `poll.py` 盯盘的完全对齐状态。

3. **收盘复盘启动“强反馈闭环”核验**：
   - 严禁凭记忆或泛泛而谈来敷衍收盘复盘。
   - 复盘时必须自动提取 `knowledge/trading_history.jsonl` 中的实盘/模拟盘真实成交记录，与晨间对齐决策进行**逐笔配对交叉核验**，统计信号正确率并归档到学习库中。

4. **讨论结束前必须完成"数据落盘 + Dashboard 可用"（第五戒律的执行层）**：
   - **额度紧张或 Dashboard 暂缓期间的例外流程**：如果用户明确表示近期不完善 Dashboard、只靠盘前/盘中/盘后与 Agent 沟通，则 Agent 仍必须完成“显式确认”，但可以不强行改 Dashboard。显式确认必须包含：今日关注标的、每只标的动作、触发价、时间窗口、哪些标的需要盘中重点盯、哪些只是手动观察、以及“Dashboard/本地文件是否已同步”的状态。
   - **盘前沙盒最高优先级**：`premarket_sandbox_{date}.md` 或用户在聊天中粘贴的盘前沙盒讨论，是当日交易构思的最高优先级 source of truth。它优先于 `daily_plan_{date}.json`、`daily_checklist_{date}.json`、`premarket_summary_{date}_{SYM}.json` 和旧 `session_lock.json`。不得只看自动 JSON 后判断“今日无策略”。
   - 每次讨论产出价格节点或交易决策后，**在结束对话前**必须按顺序完成：
     1. 写入 `premarket_summary_{date}_{SYM}.json`（价格节点 + 分析摘要）
     2. 写入 `macro_strategy_{SYM}.json`（宏观策略节点）
     3. 写入 `daily_plan_{date}.json`（per_symbol key_levels + action_now）
     4. 运行 `dashboard_writer.py`
     5. 运行 `apply_session_lock.py`（**必须在 Step 4 之后**，否则会被覆盖）
     6. **自动验证**：读取 HTML，确认 `tab-intraday` 区域有价格节点 ≥4，`session-lock-banner` 存在
   - **历史教训 (2026-05-26)**：讨论完 VST/SYM/GOOGL/COHR 的完整 5/5/5 方案，但 AI 未写入任何 per-symbol 数据文件，导致 dashboard 只渲染 CIO 标签而无价格节点，讨论成果无法在 dashboard 上呈现。

5. **IBKR 期权实操防爆仓铁律（期权风控契约）**：
   - **绝对禁止到期行权 (No Expiration Hold)**：所有多腿期权（Spreads, Butterflies 等）必须在**到期前 24-48 小时**（或最迟在到期日周五下午 15:00 之前），或者在**达到 85%-90% 最大利润**时，无条件通过组合单平仓落袋，绝对禁止持有至到期收盘！以完全规避行权与指派风险（Exercise & Assignment Risk）、钉线风险（Pin Risk）以及 broker 端的自动强制平仓风险。
   - **必须使用组合单执行 (Unified Combo Execution)**：所有的多腿期权建仓与平仓，必须在 IBKR 中通过 **“Combo Builder”** 作为一个统一组合订单（Combo Order）进行整体提交，绝对禁止分腿单双向裸交易，以完全杜绝单腿成交踩空（Leg risk）的滑点损失。
   - **保证金与购买力严密核算 (Precise Buying Power Check)**：任何期权推荐方案，必须显式标注所需的 IBKR 期权交易等级（如 Spread 对应 Option Level 3），并精准计算出最大 Reg-T 保证金占用（Buying Power Reduction）和净权利金流入/流出，确保绝对不突破组合当前的战术现金极限（如当前的 $11,577.57 现金限额）。
   - **强制生成期望与多场景盈亏矩阵 (Mandatory P&L Scenario Matrix)**：任何期权推荐或深潜研究，必须强制生成详尽的多场景到期盈亏对比大表（P&L Scenario Matrix），清晰且无死角地标注“在什么具体正股价格区间下会发生亏损、最大亏损是多少、盈亏平衡临界点（Breakeven）在哪，以及不同概率下的收益期望值（EV）”，使下行回撤风险与潜在套利收益高度直观化，坚决杜绝“只谈大方向、不列数字精算”的业余推演。
