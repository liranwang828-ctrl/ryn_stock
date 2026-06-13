# Stock Team TODO

> 按优先级排列。P0 = 下次开盘前必须完成；P1 = 本周完成；P2 = 条件成熟后。

---

## P0 — 最高优先（影响下次交易）

（P0 全部完成 ✅）

---

## TODO — 已设计但未完整实施的功能

### 1. post_open_adj 9:30/10:00 完整校准逻辑
**背景**：Spec 定义了详细的开盘校准流程（9:30 实际开盘价 → 分支判断 → 10:00 entry_go 决策），但 poll.py 目前只写了 actual_open，没有完整实施三路分支（高开超2%/破位/低开）和10:00 entry_go 写入逻辑。
**影响**：post_open_adj 字段填写不完整 → premarket_summary Full 模式无法正常触发 entry_go。

### 2. postmarket learning_notes / llm_review LLM 生成
**背景**：`postmarket_summary.py` 里 `learning_notes` 和 `llm_review` 是空字符串存根，Claude API 未接入。
**影响**：复盘报告缺少 LLM 生成的关键洞察，盘后复盘价值大幅降低。

### 3. suggestion_applier 仅实施 6/12 类建议
**背景**：目前 `suggestion_applier.py` 只实施了 thesis_status / stop_move / lesson_record / trigger_deep_research / tomorrow_risk_calendar，缺少 master_weight / scene_calibration / node_reset / stage_alert 四类。
**影响**：这四类建议确认后无法自动写回，需要用户手动执行。

### 4. backtest vs_baseline / median / sharpe 存根
**背景**：`backtest_result.py` 里这三个字段是 null 存根，需要对原始 DataFrame 做无筛选基线计算和分布统计，但 `simulate_decision_framework` 没有返回原始数据。
**影响**：无法评估策略相对基准的真实改善幅度。

### 5. portfolio_weekly signal_accuracy_week 依赖 LLM 数据
**背景**：`portfolio_weekly.py` 聚合 postmarket_summary 的 signal_accuracy 字段，但 postmarket_summary 的 LLM 部分是存根，信号准确率数据质量有限。
**前置条件**：postmarket learning_notes LLM 实施后再做。

### 6. dashboard 节点历程 Tab（spec 有，未实施）
**背景**：Brainstorm 设计了 5 个 Tab，当前实施了 4 个，缺"节点历程"Tab（entry_base/stop/flex 节点随时间变化的时间轴）。
**数据来源**：`intraday_snapshot_{date}_{sym}.jsonl` 的 `node_snapshot` 字段。

### 7. dashboard 深度分析 Tab（spec 有，等 strategic_memo 完善后做）
**背景**：Spec 设计了"深度分析 Tab"展示 strategic_memo 全量内容，当前以链接形式临时替代。
**前置条件**：strategic_memo 内容质量提升后集成进 Tab。

### 9. 研究报告内容大幅扩充（当前内容远少于 CIO 实际产出）

**问题**：`research_{sym}_{date}.html` 目前只展示了摘要级别的数据，丢失了大量 CIO 实际生成的深度内容。

**根本原因**：
1. `findings/{Agent}.json` 每次只保存最后一只标的的数据，并行跑多标的时互相覆盖，导致 `strategic_memo_writer.py` 只能从 `cio_signals`（仅含 signal/confidence）获取数据
2. Phase 2 大师辩论（`discussion_board.jsonl`）和 Phase 3 综合内容没有按标的保存到独立文件
3. 报告没有拉取以下内容：
   - 各 Agent 完整分析文本（analysis 段落，现在的报告只有信号颜色）
   - 大师辩论对话（Phase 2 的 round1/round2 具体发言）
   - 加仓/减仓具体策略（在什么价格/条件下加仓/减仓，分批计划）
   - 公司深度调研（商业模式/护城河/竞争格局/营收结构）
   - 多情景分析（牛市/基准/熊市三种价格目标）
   - 技术关键位（支撑/压力/止损/目标的具体计算依据）

**需要做的改动**：
1. **cio.py 改造**：每个 Agent 运行后同时保存 `findings/{Agent}_{sym}_{date}.json`（按标的+日期命名，不覆盖），Phase 2 辩论内容保存到 `findings/debate_{sym}_{date}.json`
2. **strategic_memo_writer.py 扩充**：读取上述文件，把 Agent 完整分析文本、辩论摘要写入 memo 的 A 级字段
3. **report_viewer.py 扩充**：
   - 展示各 Agent 完整分析段落（当前只有信号 badge）
   - 展示大师辩论关键发言
   - 从 premarket_summary + positions.json 生成加仓/减仓策略区块
   - 从 fundamentals 展示完整公司概况（业务/营收结构/增速/竞争对手）
   - 从 positions.json.thesis + falsification_conditions 生成完整论点追踪区
4. **加仓/减仓策略区块**（新增）：
   - T2/T3 加仓条件（来自 positions.json.t2_conditions）
   - Flex 加减仓触发价（来自 premarket_summary exit 字段）
   - 时间止损计划（来自 falsification_conditions 时间条件）

**优先级**：P1（内容太稀薄，影响实用性）

### 8. strategic_memo stance 推导规则优化
**背景**：当前 tech_stage=2（上升趋势）+ 6 大师全看多 → 仍推导出 stance=reduce，规则过于保守。需要结合退出决策的三层过滤逻辑（论点型/杠杆门槛/催化剂）重新设计推导权重。

---

## TODO — JSON 报告的可读性优化

**背景**：Dashboard 里的"📄盘前"和"🔬深度"链接直接打开原始 JSON 文件，浏览器渲染结果难以阅读（无格式、无层次、无高亮）。

**目标**：找到适合人类阅读的展示形式，让用户点开链接后能快速获取关键信息。

**候选方案**：
1. **专用 HTML 查看器**：`dashboard_writer.py` 额外生成 `reports/view_{sym}_{date}.html`，把 JSON 各字段渲染为有格式的报告页（类似现有的 analysis report HTML），在 dashboard 链接到这个 HTML 而不是原始 JSON
2. **内嵌弹窗（Modal）**：dashboard 里点击链接时用 JS fetch JSON 并渲染为格式化表格/卡片，不离开当前页面
3. **浏览器 JSON 格式化插件**：依赖用户安装插件（不推荐，不可控）

**推荐**：方案 2（内嵌 Modal），点击即展开，不跳页，可以针对不同 JSON 结构定制展示模板：
- `premarket_summary` → 展示：行动/节点价格/论点/盘前场景/建议
- `strategic_memo` → 展示：综合结论/大师投票/主要矛盾/证伪条件/有效期
- CIO 全量分析 HTML → 现有 `reports/*.html` 已有格式，但 dashboard 链接需要能找到对应标的最新报告

**优先级**：P2（dashboard 基础功能稳定后再做）

---

## P1 — 盘前报告加入全市场扫描推荐

**背景**：当前盘前分析只覆盖用户已有持仓和手动指定关注列表，用户无法看到系统主动推荐的新候选标的。今天 MRVU +18.5% 是系统已知但没有主动推送给用户的典型案例。

**目标**：盘前报告（Node 0 / daily_plan）中加入一个"今日推荐关注"区块，显示候选池扫描结果和评分，让用户可以在自有候选之外做选择。

**实现思路**：
1. Node 0 自动运行 `candidate_scanner.py` 扫描全市场，生成 `candidates_{date}.json`
2. 运行 `premarket_watchlist_score.py` 对候选池和持仓标的综合评分
3. 在 `daily_plan_{date}.json` 新增 `recommended_candidates[]` 字段：按分数排序，显示 Top 5-10
4. Dashboard 总览 Tab 加入"今日推荐"卡片，每个标的显示：symbol / 分数 / gap / 理由 / 链接到盘前分析

**数据字段（recommended_candidates[]）**：
```json
{
  "sym": "MRVU",
  "score": 85,
  "gap_pct": 18.5,
  "catalyst": "strategic_invest",
  "catalyst_strength": 3,
  "reason": "高开+18.5%+强催化剂→VWAP回踩机会",
  "pred_scene": "B",
  "is_held": false  // 标注是持仓还是新候选
}
```

**优先级**：P1（下次盘前前完成，避免再次错过主动推荐）

---

## TODO — 回测冷启动（待 backtest spec 实施后执行）

### 历史冷启动回测（从未运行过）

**背景**：`backtest_engine.py` 当前使用的阈值（ma20_dev_max、rs5_min、vol_ratio_max）是手动设定的默认值，从未经过历史数据验证。

**待执行**：
1. **2年历史回测**（full bootstrap）：`python3.12 agents/backtest_engine.py scan NVDA MRVL NBIS ANEL LITE ...`，验证当前阈值是否合理
2. **10年历史回测**（bootstrap）：用 yfinance 拉取 10 年日线数据，建立初始阈值基准（需实施新版 backtest_engine 支持 `--years 10` 参数）

**前置条件**：backtest spec 实施完成（`backtest_result_{date}.json` 格式就位）

**优先级**：P2（条件成熟后，即 backtest spec 实施后）

---

## P1 — 本周完成

### 简化交易框架（Constrained Mode）
**背景：** 全天高强度盯盘不可持续。设计"约束模式"：只在开盘前一小时交易，交易后 GTC 单接管，不再盯盘。
**核心设计（已确认）：**
- 盘前（09:00-09:25）：深度分析 + 输出条件订单表（含取消条件）
- 前30分钟（09:30-10:00）：观察+参数校准，不轻易入场，宏观拐点监控
- 后30分钟（10:00-10:30）：执行窗口，条件满足则挂 GTC 单
- 10:30 之后：轮询停止/降频，GTC 单自动管理
**需要新建/改造的组件：**
1. `premarket_order_sheet.py`（新建）— 输出条件订单表（入场条件/价格/止损/目标/取消条件）
2. `poll.py` 加 `trading_mode` 开关（constrained/active）— 10:30 后屏蔽入场信号
3. `get_time_window()` 简化为两段（前30分钟观察 / 后30分钟执行）
4. `calc_trading_state()` 改为近N笔交易质量（不再是当日矛盾计数）
5. 大师盘前分析改为深度一次性分析（不再是2分钟快照）
6. `premarket_checklist.py` 加"取消条件"输出
**保留不删除的：** 所有现有指标和大师评分，在第一小时内继续使用；active 模式作为可选的高频交易选项
**spec 路径：** `docs/superpowers/specs/2026-05-18-constrained-trading-mode.md`（待写）

### learning/ 目录 30 天滚动清理
**背景：** 日期类文件（poll_state/master_score_log/cio_signals 等）每天生成，长期不清理会积累。
**实现：** 在 `harvest_agent.py` 末尾加一个 `_cleanup_old_files(days=30)` 函数，每次盘后 harvest 运行时自动删除超过30天的日期文件。
**保留：** model_*.pkl / historical_features.parquet / master_accuracy.json / case_library.json / daily_harvest.jsonl 不清理。

### 盘前关注列表综合评分（premarket_watchlist_score）
**背景：** 当前 quick_persona_score() 是盘中短期信号，不适合盘前筛选关注列表。
**实现：** 新建 `premarket_watchlist_score(sym)` 函数，三维评分：技术结构（Stage2/10日RS/乖离率）+ 基本面（PEG/FCF/营收增速/分析师目标）+ 宏观适配（macro_sensitivity vs 当前regime）。
**触发：** 盘前手动调用，对 sector_watchlist.json 全量扫描，输出前10名。

### 大师2分钟评分时间序列（poll 每次 append）
**背景：** 当前只存最后一轮评分到 poll_state.json，无法验证盘中每个时刻评分的准确性。
**实现：** 在 `_write_observation_log()` 或 poll 末尾，把大师评分 append 到 `learning/master_score_log_{date}.jsonl`（时间序列），而不是只覆盖 poll_state。
**盘后验证：** harvest 时对每条记录，取"评分时刻+10分钟"的价格，判断高分是否对应上涨。

### ~~止损显示区分软硬线（系统级）~~ ✅
~~evaluate_thesis_health() 已加 soft_stop/hard_stop，软线触发 weakening，硬线触发 broken~~

### 量比修复验证
**背景：** 今天量比多次显示 0x，已改为用前一根完整5min K线（iloc[-2]），需要明天盘中验证是否稳定。
**验证方式：** 明天 poll 后查看 learning/observation_log.jsonl 里的 vol_ratio 字段是否有意义。

### 建仓引导：系统辅助构建证伪条件
**背景：** 买入决策是整个持仓周期里情绪最平静的时刻，但当前 positions.json 的 thesis 字段只记录"是什么"，没有"什么情况下我承认错了"。叙事锁定和近期偏差会让事后的止损决策完全情绪化，结构性修复是在建仓时就写好证伪条件。
**实现：** 新建 `agents/position_builder.py`，建仓或更新仓位时交互式引导：
- 根据 `position_type` 提问：趋势型→关键技术支撑价位；催化剂型→哪种事件结果证明催化剂失败；论点型→哪个可观测的基本面事实会让论点失效
- 根据 `catalyst_type` 细化：earnings→"同期公司 miss 幅度"；order→"客户取消或延迟"；policy→"政策反转信号"
- 输出写入 `positions.json` 的新字段 `falsification_conditions: [str]`
- 同时要求填写技术止损价并确认是否已挂 GTC 单
**触发：** 手动调用，每次新建仓位或调整仓位时使用

### Skill 内容与格式标准化（→ 战略分析集成层前置条件）
**背景：** 当前 8 个分析 skill（trading-day / premarket / intraday / postmarket / deep-research / backtest / position-builder / portfolio-health）的输出格式独立设计，缺乏统一的"契约"定义，导致：
1. 各 skill 输出章节不一致，无法可靠互相引用
2. 全面分析（stock-deep-research）和盘前分析（stock-premarket）的结论可能矛盾而无法解释
3. 无法建立集成层（strategic_memo）
**需要定义的内容：** 每个 skill 的固定输出章节（顺序+名称）、各章节的字段边界、数据来源和有效期、与其他 skill 的依赖关系
**后续目标：** 在格式标准化基础上，建立两层分析架构：
  - 战略层（stock-deep-research，周期性）→ 产出 `strategic_memo_{sym}.json`，含论点质量评分/主要风险/大师共识
  - 战术层（stock-premarket，每日）→ 读取 strategic_memo 作为输入之一，叠加当日实时数据，产出统一的一致性结论
  - 关键：集成层不是"并排展示两个结论"，而是让深度分析的洞察成为盘前决策的背景输入
**优先级：** 先 brainstorm 格式标准化，再实施集成层

---

## P2 — 条件成熟后（需30+天数据）

### 阈值矩阵自动调整
需要足够的 observation_outcomes.jsonl 数据，才能判断哪些阈值组合的胜率更高。

### 场景预测准确率改进
需要30+天 scene_development.json 积累后，才能有意义地改进 predict_scenario()。

### 大师权重基于时间线判断准确率调整
master_accuracy.json 中 `{master}_timeline` 键积累30天后，才能判断哪位大师的时间线判断更可信。

---

## P6 — 借鉴 daily_stock_analysis（待 brainstorm 后实施）

> 来源：ZhuLinsen/daily_stock_analysis (36k⭐) 金融知识萃取，2026-05-17

### 1. 乖离率过滤器（追涨防护）
**方向：** `strategy_gate()` 加入距 MA20 乖离率门槛（<2% 最优 / 2-5% 小仓 / >5% 禁止追高），同时加入月线乖离率计算（>30% 警示均值回归压力）。

### 2. 预期重定价框架（论点定价进度）
**方向：** `evaluate_thesis_health()` 加入"市场对论点的定价进度"维度——区分"预期修复（价格未反映好消息）"、"预期兑现（连续大涨已定价）"、"预期转弱（利好不涨）"三种状态，作为 thesis_status 的补充。

### 3. 情绪底部五维核查（逆向布局框架）
**方向：** `premarket_checklist.py` 或 `poll.py` 加入底部情绪核查：换手率/成交量/新闻情绪/价格位置/机构持仓 5 项，满足 3/5 触发逆向布局信号。对美股适配：换手率替换为量比相对历史的百分位。

### 4. 市场环境路由（regime-aware 策略）
**方向：** 将现有 macro_state（normal/bull/bear 3值）升级为 5 值 regime（trending_up / trending_down / sideways / volatile / sector_hot），strategy_gate() 根据 regime 动态选择适合的阈值组合，不同市场用不同策略。

### 5. 缩量回踩入场条件（T2 加仓精确化）
**方向：** T2 加仓条件加入量能门槛：回踩至 MA5 ± 1% + 当日量 < 5日均量 70% + MA5 乖离率 < 2%（三条件同时满足才触发）。

### 6. 大盘三段式复盘（结构化盘后分析）
**方向：** `postmarket_review.py` 加入三段式大盘复盘框架——①趋势结构（SPX/NDX/DJI 同向性）②资金情绪（成交额扩缩 + VIX + 涨跌家数比）③主线板块（领涨板块催化 + 板块扩散程度），替换现有零散大盘判断。

### 7. 催化剂分类（替代单一强度打分）
**方向：** `positions.json` 和 `premarket_checklist.py` 中将催化剂从单一 catalyst_strength(1-5) 扩展为 catalyst_type（业绩/政策/订单/资本运作/监管）+ 持续性评估（一次性 vs 结构性），不同类型持续性完全不同。

### 8. 增收不增利检测（盈利质量预警）
**方向：** `quick_fundamentals.py` 加入 FCF 增速 vs 营收增速对比——若营收增速 > FCF 增速且差距持续扩大，标记为盈利质量恶化风险（应收账款堆出来的增长，经济收缩时风险极大）。

---

## P5 — 借鉴他山之石（待条件成熟）

### 期权链分析（他山之石仓库有，我们完全缺失）
**背景：** 对方系统包含期权链分析：①根据 Put/Call 比率和成交量判断市场对股价的方向预期；②提供期权交易建议（买 Call/Put、卖 Covered Call 等）；③用期权隐含波动率（IV）判断市场对未来事件的定价。
**当前状态：** quick_fundamentals.py 和分析模板均无期权维度，DATA_COVERAGE.md 已标注期权流向为 Tier4。
**方向：**
- 期权基础数据可从 yfinance `option_chain()` 获取（Put/Call 成交量、IV、OI）
- IV percentile 判断期权是否贵（>80% = 贵，不宜买期权；<20% = 便宜，适合买期权）
- PCR（Put/Call Ratio）> 1.5 = 市场悲观；< 0.7 = 市场乐观
- 实现建议：扩展 quick_fundamentals.py 加 `fetch_options_summary(sym)` 函数
**条件：** 需先理清用户是否有期权交易需求，再评估实现深度。



### 分歧地形图（CIO 专用）
**背景：** Layer 1 四个研究员报告完成后，辩论前先画矛盾点地图，让辩论聚焦在真实分歧上。
**条件：** 等 CIO 使用频率提升后再考虑；盘中 poll 场景用处不大。

### MACRO_CHALLENGE 机制
**背景：** 研究员发现微观证据与宏观定调冲突时，打 [MACRO_CHALLENGE] 标签，L4 芒格必须审查。
**条件：** 需等宏观框架（macro_tone）迭代到多维度后才有意义；当前三值枚举粒度不够。

### 芒格自查 8 项完整清单
**背景：** 当前 CIO 芒格自查不如对方系统结构化，缺"L2 反向风险诚实"和"MACRO_CHALLENGE 审查"两项。
**方向：** 在 personas/munger 的 SKILL.md 或 CLAUDE.md 里加入完整 8 项清单：三筐/逆向/Lollapalooza/激励诊断/能力圈/愚蠢清单/L2诚实/MACRO_CHALLENGE。
**条件：** 等分歧地形图和 MACRO_CHALLENGE 机制建立后统一做。

---

## P3 — 借鉴他山之石（✅ 2026-05-17 全部完成）

- ✅ 【架构】大师职责分工 + 表达DNA接入（CLAUDE.md + personas/language.md）
- ✅ 【数据】Dalio 宏观五维度框架（macro_agent B+D + macro_background.json 月度）
- ✅ 【数据】股票定性画像 + 宏观映射表 + 动态拐点触发（positions.json + poll.py）
- ✅ 【输出】大师评分置信度 + 证伪条件（CLAUDE.md 规则3）
- ✅ 【校准】大师诚实边界（personas/blindspots.md 接入 CLAUDE.md）

---

## P4 — 盘中交易原则补充（✅ 2026-05-17 全部完成）

- ✅ 热手/冷手追踪（calc_trading_state：矛盾计数+浮盈峰值，poll_state 存跨轮次）
- ✅ 时间窗口行为（get_time_window：4窗口标签，时间头后显示）
- ✅ 下跌性质四分类（classify_pullback：论点收尾/个股事件/大盘拖累/板块联动）
- ✅ 极端情景分级响应（check_extreme_speed：速度×量能，Level2/Level1/流动性真空）

---

## 已完成（参考）

- ✅ 大师2分钟评分时间序列（master_score_log_{date}.jsonl，每次poll append）
- ✅ 大师评分验证改为时间序列（评分时刻+10分钟后价格对比，非仅收盘对比）
- ✅ T1止损字段改名为 t1_stop_snapshot（明确快照性质，实际止损动态计算）
- ✅ Phase A 动态阈值矩阵（黄金否决权+基础层）
- ✅ 5分钟K线 + RSI14 + 正确量比
- ✅ 观察日志机制（observation_log → outcomes）
- ✅ poll_state 轮询连续性（上轮/今日/大师行）
- ✅ 大师评分每2分钟保存（语料积累）
- ✅ T1/T2/T3 positions 结构化
- ✅ 15:45 日内减仓提醒
- ✅ 反转入场信号（底部猎手5信号）
- ✅ 大师时间线分析 + harvest 核对
- ✅ 场景发展记录
- ✅ 门控正确率早盘显示
- ✅ 保本/结构止损显示区分（ETF持仓+evaluate_thesis_health均已区分软硬线）
- ✅ P3 全部完成（子系统A：大师体系；子系统B：宏观框架；子系统C：股票定性层）
- ✅ P4 全部完成（子系统D：盘中增强四项）

---

_最后更新：2026-05-17_

### 10. 补填各持仓证伪条件（positions.json）
**背景**：strategic_memo 的 falsification_conditions 来自 positions.json，目前除 MRVU 外全部为空，
报告的"证伪条件"section 依赖人工填写。

**需要逐个操作**：
- [ ] NVDA：跌破 MA50（约$210）且放量 + MACD 死叉 → 论点弱化
- [ ] IAU：黄金跌破 $2700 且 VIX<15（风险偏好回归，避险需求消退）→ 论点破裂
- [ ] BABA：连续两季阿里云营收增速低于 15% → 核心增长叙事失效
- [ ] MSFT：Azure 增速连续两季 < 25% → AI变现低于预期
- [ ] LITX：LITE 跌破 $800 且光模块板块跑输 SOXX 超3% → 趋势破坏

**操作方式**：告诉 Claude "更新 NVDA 证伪条件" 即可自动写入 positions.json


### 11. 回测系统定时调度
**背景**：backtest_runner.py 已实现，但完全手动触发。
**待实现**：
- [ ] 宏观+微观结构位回测：每季度 cron，自动生成报告（不自动写回参数）
- [ ] 盘中信号回测：每2-4周 cron（60天窗口滚动）
- [ ] --apply 写回永远保持人工确认，cron 只生成报告

**操作方式**：告诉 Claude "设置回测定时任务" 即可


### 12. 回测系统基础概念重新设计（待 brainstorm）
**背景**：回测系统已有三层架构（宏观/结构位/盘中），但核心逻辑未想清楚：
- 价格节点（Add1/TP1/Stop）如何与宏观环境过滤联动
- 结构位回测应该只在宏观允许的日子触发
- 三层需要串联而非独立回测
**下次开发时说**："重新 brainstorm 回测设计，从单只股票的完整操作流程反推"

### 13. 宏观回测扫描 bug
**背景**：`scan_macro_params` 返回空结果（all_results=0），原因可能是：
- apply_macro_filter 过滤太严或有 bug
- OOS 时序拆分后数据结构问题
**关联**：fixing 后与TODO#12一起重做

# TODO - Decision State Hub Follow-Ups (2026-05-31)

本轮优先做“决策闭环 / Decision State Hub”。以下方向先记录为后续待办，避免一次性展开导致回测、LLM、dashboard 耦合。

## 1. 回测 / 因子可信度强化

- 给每个因子增加样本量、IC/IR、正向周比例、稳定性标签。
- 区分“已验证因子”和“探索性因子”，避免低样本情绪因子被 dashboard 当成强证据。
- 把 style-OOS 表现和 full lifecycle 表现同时暴露，不能只展示总体收益。
- 给参数稳定性和回撤剖面做统一摘要，供 Decision State Hub 读取。
- 第一阶段先做 `evidence_credibility_report.json` 只读摘要层，不改回测引擎和交易规则。
- 完整系统优化目标：后续重做滚动 IC、分风格/行业/市场状态 IC、参数曲面、walk-forward、bootstrap/Monte Carlo、slippage/latency 压力测试和统一研究档案。

## 2. LLM 主控纪律

- 定义 LLM 必须降级置信度的硬规则：证据缺失、证据冲突、样本不足、风险门控失败。
- 要求 LLM 输出反证、缺失输入和人工复核项。
- 禁止 narrative-only upgrade：仅凭叙事不能绕过因子或回测证据不足。
- 增加 controller audit 字段，方便盘后复盘 LLM 当天裁决是否合理。
- 当前状态：第一阶段已完成，`decision_state_{date}.json` 已包含 `controller.audit`、`allowed_actions`、`forbidden_claims` 和 `llm_output_contract`。真实 LLM 主控 agent 仍作为最终优化方向，后续单独设计。

## 3. Dashboard 数据底座与后续可视化

- dashboard 后续优先消费 `decision_state_{date}.json`，减少直接拼多个原始 JSON。
- 给可视化优化 agent 提供结构化字段：primary_action、why_now、risk_flag、evidence_alignment、missing_inputs、level_map、review_questions。
- dashboard 自优化 agent 的输出继续限制在可用性问题和小批量改动建议，不修改交易逻辑。
- 后续视觉方向：命令条、标的决策卡、证据抽屉、人工复核队列。
- 当前决策：可视化暂不进入实施。现有数据底座已经足够支持日常交易沟通：用户和 Codex 直接围绕 `decision_state_{date}.json`、`evidence_credibility_report.json`、个股 thesis 和执行状态讨论即可。
- 后续触发条件：当日常沟通出现“信息太多、复盘不方便、多个标的难比较、人工复核队列难追踪”等明确痛点时，再启动 dashboard UI / 可视化优化 agent。
- 给未来可视化 agent 的重点：只展示主控动作、证据支持/反对、阻断原因、人工复核项和关键价位，不新增交易逻辑，不把 caution/insufficient 视觉上包装成强信号。
