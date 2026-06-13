# stock_team 系统全流程文档

> 生成日期：2026-05-15 | 框架更新：2026-05-16  
> 精细度：函数级别，每个关键调用对应流程节点

---

## 零、框架版本说明

**当前版本：论点驱动 + Flex仓框架（2026-05-16）**

旧版本（趋势跟随）已废弃：strategy_gate() 的入场信号不再是主要决策依据。

### 新框架核心流程

```
盘前：premarket_checklist.py 为每只股票生成五步清单（Node 0 Step 6.5）
      ├─ 持仓类型分类（论点/催化剂/Flex独立/趋势）
      ├─ 论点状态检查（intact / weakening / broken）
      ├─ 市场环境评估（顺风/中性/逆风 → 今日仓位上限）
      ├─ 今日行动预设（A主动操作 / B被动守护 / C评估日）
      └─ 关键价位写入 daily_checklist_{date}.json

盘中：poll.py 每2分钟监控（角色：监控器，不再主动决策入场）
      ├─ check_flex_signals()：4维度超买/超卖检测
      │  ├─ RSI14_5m > 80 / < 25（动量极端）
      │  ├─ VWAP偏离 > +2% / < -2%（空间极端）
      │  ├─ vol_ratio < 0.7（量萎缩，买卖压枯竭）
      │  └─ MACD顶/底背离（macd_fail / macd_cross）
      │  → 满足3/4触发：Flex减仓 or Flex加仓
      ├─ evaluate_thesis_health()：论点健康状态动态评估
      └─ 黑天鹅监控（VIX急升 / 大盘跳水 / 停止Flex加仓）

盘后：harvest → postmarket_review → master_accuracy更新 → 论点状态评估
```

### 旧框架（已废弃的核心逻辑）
```
strategy_gate() 5条全亮才入场：RS/MACD/RSI3/VIX/QQQ5m
→ 问题：滞后性陷阱 + 技术止损被猎杀 + 事件驱动市场负期望
→ 现在：strategy_gate()保留作参考，但入场决策由论点+Flex信号驱动
```

### positions.json 新增字段（2026-05-16）
```json
{
  "position_type": "thesis|catalyst|flex|trend",
  "thesis":        "论点文本说明",
  "thesis_status": "intact|weakening|broken",
  "flex_min":      20,
  "flex_max":      30,
  "daily_action":  "A|B|C"
}
```

---

---

## 一、系统整体架构

### 1.1 数据流向总图（ASCII）

```
                        ┌─────────────────────────────────────┐
                        │         用户自然语言输入              │
                        └─────────────┬───────────────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────────┐
                        │   session_manager.py        │
                        │   handle_text()             │
                        │   run_node(node)            │
                        └────┬──────────────┬─────────┘
                             │              │
                   ┌─────────▼───┐   ┌──────▼──────────┐
                   │translator.py│   │entry_guard.py    │
                   │handle()     │   │parse_trade_input │
                   │意图识别     │   │record_trade()    │
                   └──────┬──────┘   └────────┬─────────┘
                          │                   │
         ┌────────────────┼───────────────────┼──────────────┐
         │                │                   │              │
         ▼                ▼                   ▼              ▼
   [Node 0]         [Node 1]           config/           knowledge/
   晨间准备          盘前分析           positions.json    trading_history.jsonl
         │                │
         ▼                ▼
   candidate_scanner.py  premarket.py
   portfolio_risk_agent  → premarket_analysis_{date}.json
   health_check.py
   harvest_agent.py
   CIO并行分析
   daily_plan.py
         │
         ▼
   [Node 2/3]
   开盘/盘中
         │
         ▼
   poll.py  ←──────────── /loop 2m
   snap() 实时数据
   strategy_gate()
   render_opening_block()
   evaluate_thesis_health()
   quick_persona_score()
   trigger_quick_debate()
         │
         ├─→ session_recorder.write_snapshot()
         │   → knowledge/snapshots_{date}.jsonl
         │
         ├─→ _write_observation_log()
         │   → learning/observation_log.jsonl
         │
         └─→ quick_debate.py (异步)
             → quick_debate_{sym}.json

   [Cron 4:35 PM ET]
   harvest_agent.py
   record_intraday_outcome()
   record_swing_outcome()
   update_master_accuracy()
   process_observation_log()
   → learning/daily_harvest.jsonl
   → learning/master_accuracy.json
   → learning/observation_outcomes.jsonl

   [Node 6]
   postmarket_review.py
   run_review()

   [每周五 Cron]
   learning_agent.py
   retrain()
   → learning/model_intraday.pkl
   → learning/model_swing.pkl

   [月度/变更后]
   bootstrap_agent.py
   → learning/historical_features.parquet
   → learning/case_library.json
```

### 1.2 模块层级

```
┌──────────────────────────────────────────────────────────┐
│ 编排层   session_manager.py / translator.py              │
├──────────────────────────────────────────────────────────┤
│ 信号层   poll.py / quick_debate.py                       │
│          premarket.py / candidate_scanner.py             │
├──────────────────────────────────────────────────────────┤
│ 分析层   CIO 流程: cio.py → 8个 domain agent              │
│          (tech/fund/macro/sentiment/community/risk/      │
│           sector/intuition) + 7位大师 persona             │
│          debate_engine.py → strategy_agent.py            │
├──────────────────────────────────────────────────────────┤
│ 学习层   harvest_agent.py / learning_agent.py            │
│          bootstrap_agent.py / intuition_agent.py         │
│          learning/features.py                            │
├──────────────────────────────────────────────────────────┤
│ 记录层   session_recorder.py / entry_guard.py            │
│          paper_trader.py                                 │
├──────────────────────────────────────────────────────────┤
│ 配置层   config/*.json / personas/*/ knowledge/          │
└──────────────────────────────────────────────────────────┘
```

---

## 二、每日完整工作流

### Node 0 — 晨间准备（8:00-9:00 ET）

入口：`session_manager.run_node(0)` 或用户说"早上好/晨间"（由 `translator.handle()` 路由）

```
Node 0 整体流程（8步）
├── Step 0/7  宏观状态 + 模型健康检查
├── Step 1/7  昨日 harvest 确认（补录）
├── Step 2/7  永久观察列表 pending_review 检查
├── Step 3/7  组合风险快照
├── Step 4/7  候选池扫描
├── Step 5/7  恐慌压力测试（条件触发）
├── Step 6/7  盘前分析（含直觉评分）
├── Step 7    CIO 全量分析（持仓+固定关注，并行）
└── Step 8    今日交易计划（价位预设）
```

#### Node 0 代码对应表

| 步骤 | 触发方式 | 文件 | 函数 | 输入 | 输出 |
|------|---------|------|------|------|------|
| Step 0-宏观状态 | run_node(0) 内部调用 | `session_manager.py` L207-224 | `get_macro_regime(spy_h, idx)` | yfinance SPY 1年历史 | macro 字符串 / VIX 数值 |
| Step 0-模型健康 | run_node(0) 内部 | `session_manager.py` L217-224 | 直接读文件 | `learning/daily_harvest.jsonl` | 正例率 pos_rate |
| Step 1-harvest补录 | run_node(0) 内部 | `harvest_agent.py` | `run()` | `knowledge/snapshots_{date}.jsonl` | `learning/daily_harvest.jsonl` |
| Step 2-永久列表 | run_node(0) 内部 | `session_manager.py` L244-254 | 直接读文件 | `watchlist_permanent.json` | 控制台输出 |
| Step 3-组合风险 | subprocess 调用 | `portfolio_risk_agent.py` | `_load_positions()` `_fetch_prices()` | `config/positions.json` `config/leveraged_pairs.json` | 控制台风险摘要 |
| Step 4-候选池扫描 | subprocess 调用 | `candidate_scanner.py` | `load_all_symbols()` `get_stock_snapshot()` `check_leader_triggers()` `rank_candidates()` | `config/poll_config.json` `config/sector_watchlist.json` | `candidates_{date}.json` |
| Step 5-恐慌压力测试 | 条件(SPY<-1%)触发 | `candidate_scanner.py` | `panic_pressure_test()` | 实时 yfinance 数据 | 控制台输出 |
| Step 6-盘前分析 | subprocess 调用 | `premarket.py` | `fetch_google_news()` `classify_news()` `predict_scenario()` `check_sector_leader_gap()` | yfinance + Google News RSS | `premarket_analysis_{date}.json` |
| Step 7-CIO并行 | Python import 调用 | `cio.py` | `run_parallel(cio_syms)` | symbols 列表 | `runs/{sym}_{date}/strategy_result.json` |
| Step 7-CIO内部Phase0 | run_parallel 内部 | `data_agent.py` | `fetch_primary()` `fetch_secondary()` | yfinance API | `data_raw_primary.json` `data_raw_secondary.json` |
| Step 7-CIO内部Phase0验证 | data_agent 后 | `verifier_agent.py` | `verify()` | `data_raw_*.json` | `data_verified.json` |
| Step 7-CIO内部Phase1 | cio.phase1() | `tech_agent.py` 等8个 | 各自 `main()` | `data_verified.json` | `findings/{AgentName}.json` |
| Step 7-CIO Phase1.5 | cio.phase1_5() | `debate_engine.py` | `collect_domain_findings()` `collect_persona_stances()` | `findings/*.json` | `persona_stances.jsonl` |
| Step 7-CIO内部Phase2辩论 | cio.phase2() | `debate_engine.py` | `detect_contradictions()` `run_targeted_response()` `weighted_synthesis()` | `discussion_board.jsonl` `persona_stances.jsonl` | `persona_synthesis.json` |
| Step 7-CIO Phase3汇总 | cio.main() | `strategy_agent.py` `report_agent.py` | `main()` | `discussion_board.jsonl` `persona_synthesis.json` | `strategy_result.json` |
| Step 7-CIO信号保存 | Phase3后 | `cio.py` L391-407 | 直接写文件 | `strategy_result.json` | `learning/cio_signals_{date}_{sym}.json` |
| Step 8-交易计划 | subprocess 调用 | `daily_plan.py` | `generate_plan()` `_build_stock_plan()` `calc_stop()` | `premarket_analysis_{date}.json` | `daily_plan_{date}.json` |

---

### Node 1 — 盘前分析（9:00-9:25 ET）

入口：`session_manager.run_node(1)` 或 translator 识别"盘前分析"意图

| 步骤 | 触发方式 | 文件 | 函数 | 输入 | 输出 |
|------|---------|------|------|------|------|
| 盘前分析 | subprocess 调用 | `premarket.py` | `fetch_google_news(sym)` | Google News RSS | headlines 列表 |
| 新闻分类 | premarket 内部 | `premarket.py` | `classify_news(headlines)` | headlines | (news_type, catalyst_strength) |
| 领头羊联动检查 | premarket 内部 | `premarket.py` | `check_sector_leader_gap(sym)` | yfinance 盘前价 | fired 领头羊列表 |
| 场景预测 | premarket 内部 | `premarket.py` | `predict_scenario(gap_pct, news_type, catalyst_strength, sector_gap, pre_vol_ratio)` | 上述所有数据 | (scenario A-H, confidence, reasoning) |
| 直觉评分 | premarket 内部（若模型存在） | `intuition_agent.py` | `score_symbol(sym, features)` | `learning/model_intraday.pkl` `learning/model_swing.pkl` | {intraday: 0-1, swing: 0-1} |
| 统一置信度 | premarket 集成 | `unified_confidence.py` | `compute(sym, track)` | CIO结果 + ML分数 + 历史胜率 | 0-100 统一置信度 |
| 输出写入 | premarket 最后 | `premarket.py` | 直接写文件 | 所有分析结果 | `premarket_analysis_{date}.json` |

---

### Node 2 — 开盘观察（9:30-10:00 ET）

入口：`session_manager.run_node(2)` 或 translator 识别"开盘了/9:30/启动监控"

| 步骤 | 触发方式 | 文件 | 函数 | 输入 | 输出 |
|------|---------|------|------|------|------|
| 生成当日计划 | subprocess 调用 | `daily_plan.py` | `generate_plan(date, symbols)` | `premarket_analysis_{date}.json` | `daily_plan_{date}.json` |
| 计划价位计算 | generate_plan 内部 | `daily_plan.py` | `_build_stock_plan(pre_data)` `calc_stop(vwap, atr14)` `infer_scene(...)` | 盘前VWAP/ATR | 止损价/T1/T2目标价 |

---

### Node 3 — 盘中监控（10:00+ ET）

入口：`session_manager.run_node(3)` 启动一次 poll，然后用户用 `/loop 2m` 持续运行

```
poll.py run_poll() 每轮执行顺序：
├── snap(SPY/QQQ) + vix_snap()        ← 大盘基准数据
├── snap(sym) × N                      ← 各标的实时数据
├── get_macro_regime()                  ← 宏观状态判断
├── portfolio_risk_agent (--summary-only) ← 组合VaR快速查询
├── write_snapshot()                    ← 写快照层1
├── render_opening_block()              ← 盘初30分钟场景框架
│   ├── determine_macro()
│   ├── classify_pattern() × N
│   ├── get_rs_streak()
│   ├── STRATEGY_MATRIX 查表
│   ├── update_premarket_obs()          ← 回填盘前分析
│   └── save_daily_scenarios()
├── evaluate_thesis_health() × 持仓标的
│   ├── load_plan_for_sym()
│   ├── classify_pattern()
│   └── 止损/T1/T2/RR 判断
├── atr_stop_suggestion() × 杠杆ETF持仓
├── pullback_diagnosis()
├── master_thesis_judgment()            ← 持仓论点大盘vs个股判断
├── quick_persona_score()               ← 三大师傅实时评分
│   (Minervini/Marks/Druckenmiller)
├── trigger_quick_debate()              ← 条件触发(score≥6 AND rs>1.5%)
│   └── 异步 Popen: quick_debate.py
├── read_quick_debate()                 ← 读取上轮辩论结果
├── check_mode_switch()                 ← swing/intraday 模式切换
├── _write_observation_log()            ← 写观察日志到 learning/
├── paper_trader.try_enter/check_exits()← 模拟盘三账号
└── session_manager.push_alert()        ← 推送提醒到 discussion_board

```

#### Node 3 代码对应表

| 步骤 | 文件 | 函数 | 输入 | 输出 |
|------|------|------|------|------|
| 实时快照 | `poll.py` | `snap(sym)` | yfinance 1分钟/5日/30日 K线 | dict: cur/chg/rsi3/hist/atr14 等 |
| VIX快照 | `poll.py` | `vix_snap()` | yfinance ^VIX | dict: cur/chg/trend/bars |
| ATR止损建议 | `poll.py` | `atr_stop_suggestion(a, spy_chg, lev)` | snap dict | (止损价, 类型, 描述, RR) |
| 形态分类 | `poll.py` | `classify_pattern(a, spy_chg, sector_chg)` | snap dict | (A-H, confidence) |
| 宏观判断 | `poll.py` | `determine_macro(vix_data, spy_chg, qqq_chg)` | VIX/SPY/QQQ | (UP/NEUTRAL/DOWN, reasons) |
| 场景框架 | `poll.py` | `render_opening_block(stocks, ...)` | 所有 snap | 控制台输出 + `opening_scenarios_{date}.json` |
| 回调诊断 | `poll.py` | `pullback_diagnosis(stock_2m, qqq_2m)` | 2分钟涨跌幅 | (diagnosis_label, action_hint) |
| 论点健康度 | `poll.py` | `evaluate_thesis_health(sym, a, spy_chg, position)` | snap + positions.json | {status, signals, action, rr_ratio} |
| 大师论点判断 | `poll.py` | `master_thesis_judgment(sym, a, spy_chg, diag_label)` | snap + premarket数据 | 格式化文本行 |
| 实时三大师评分 | `poll.py` | `quick_persona_score(a, spy_chg, qqq_chg, vix_cur, vix_dir, rs_streak)` | snap 数据 | {Minervini, Marks, Druck 各评分} |
| 策略门控 | `poll.py` | `strategy_gate(a, spy_chg, vix_cur, vix_dir, qqq5m, macro_state)` | snap + 宏观 | (passed, n_req, checks_dict, block) |
| 快速辩论触发 | `poll.py` | `trigger_quick_debate(sym, a, ...)` | snap + 宏观 | 异步启动 quick_debate.py |
| 快速辩论本体 | `quick_debate.py` | `minervini_debate()` `marks_debate()` `druckenmiller_debate()` | DATA_JSON | `quick_debate_{sym}.json` |
| RS连续强度 | `poll.py` | `get_rs_streak(sym, saved, current_rs)` | saved 场景数据 | streak 连续次数 |
| 模式切换检查 | `poll.py` | `check_mode_switch(sym, a, current_mode, et_h, et_m)` | snap + 时间 | (new_mode, reasons) |
| 观察日志写入 | `poll.py` | `_write_observation_log(stocks, spy_chg, vc, vt, qqq5m, macro_state)` | 所有snap数据 | `learning/observation_log.jsonl` |
| 快照写入 | `session_recorder.py` | `write_snapshot(stocks_data, vix_data, spy_chg, qqq_chg)` | snap dict | `knowledge/snapshots_{date}.jsonl` |
| 模拟盘入场 | `paper_trader.py` | `try_enter(sym, score, price, ...)` | 评分+价格 | `paper_trading/{acct}/portfolio.json` `trades.jsonl` |
| 模拟盘退出检查 | `paper_trader.py` | `check_exits(live_prices, ...)` | 实时价格 | 同上，触发止损平仓 |
| 提醒推送 | `session_manager.py` | `push_alert(type_, symbol, message, data)` | 信号数据 | `discussion_board.jsonl` + session_state |

**B轨道（用户文本）并行处理：**

| 步骤 | 文件 | 函数 | 触发词示例 | 输出 |
|------|------|------|-----------|------|
| 意图识别 | `translator.py` | `handle(text)` → `translate(text)` | 任意自然语言 | 路由到对应动作 |
| 交易记录 | `entry_guard.py` | `parse_trade_input(text)` `handle_trade_text(text)` | "买了MRVL $178 20股" | `config/positions.json` `knowledge/trading_history.jsonl` |
| 入场核对 | `entry_guard.py` | `generate_entry_card(sym, price, shares, ...)` | 买入记录触发 | 控制台格式化入场卡 |
| 盘前分析 | `translator.py` → subprocess | `premarket.py main()` | "盘前看看MRVL" | `premarket_analysis_{date}.json` |
| CIO分析 | `translator.py` → subprocess | `cio.py main()` | "大师看看ANET" | `strategy_result.json` |
| 候选池扫描 | `translator.py` → subprocess | `candidate_scanner.py` | "今天有什么机会" | `candidates_{date}.json` |
| 持仓风险 | `translator.py` → subprocess | `portfolio_risk_agent.py` | "看看持仓" | 控制台输出 |

---

### Node 6 — 收盘复盘（16:00 ET 后）

入口：`session_manager.run_node(6)` 或用户说"收盘了/盘后"

| 步骤 | 文件 | 函数 | 输入 | 输出 |
|------|------|------|------|------|
| 加载日记 | `postmarket_review.py` | `load_session_log(date_str)` | `knowledge/session_{date}.md` | session 文本 |
| 加载方法论 | `postmarket_review.py` | `load_methodology()` | `knowledge/trading_methodology.md` | methodology 文本 |
| 提取未知条件 | `postmarket_review.py` | `extract_unknowns(session_log)` | session_log 文本 | unknowns 列表 |
| 生成复盘 prompt | `postmarket_review.py` | `generate_review_prompt(session_log, methodology)` | 上述 | 结构化 prompt 字符串 |
| 运行复盘 | `postmarket_review.py` | `run_review(date_str)` | session + methodology | 控制台输出（各大师有条件发言） |

---

### Cron 4:35 PM ET — Harvest

入口：crontab 调用 `python3.12 agents/harvest_agent.py`

```
harvest_agent.run() 执行顺序：
├── get_today_symbols()           ← 从 snapshots_{date}.jsonl 取今日关注标的
│   └── 若无快照则回退 config/poll_config.json
├── record_intraday_outcome(sym)  × N  ← 记录日内涨跌 + label
├── record_swing_outcome(sym)     × N  ← 记录5日波段涨跌 + label
├── record_short_interest(syms)        ← 记录空头比例
├── update_master_accuracy(sym)   × N  ← 比较昨日CIO信号 vs 今日结果
│   └── 读 learning/cio_signals_{yesterday}_{sym}.json
│   └── 写 learning/master_accuracy.json
└── process_observation_log()          ← 盘后配对 observation_log
    ├── 读 learning/observation_log.jsonl
    ├── 匹配实际收盘价
    └── 写 learning/observation_outcomes.jsonl
```

| 步骤 | 文件 | 函数 | 输入 | 输出 |
|------|------|------|------|------|
| 获取今日标的 | `harvest_agent.py` | `get_today_symbols()` | `knowledge/snapshots_{date}.jsonl` | sym 列表 |
| 日内结果 | `harvest_agent.py` | `record_intraday_outcome(sym, date_str)` | yfinance 2日数据 | `learning/daily_harvest.jsonl` 追加 |
| 波段结果 | `harvest_agent.py` | `record_swing_outcome(sym, entry_date_str)` | yfinance 10日数据 | `learning/daily_harvest.jsonl` 追加 |
| 空头比例 | `harvest_agent.py` | `record_short_interest(syms)` | yfinance info | `learning/short_interest_history.jsonl` |
| 大师精度更新 | `harvest_agent.py` | `update_master_accuracy(sym, actual_label, date_str)` | `learning/cio_signals_{yesterday}_{sym}.json` | `learning/master_accuracy.json` |
| 观察日志配对 | `harvest_agent.py` | `process_observation_log()` | `learning/observation_log.jsonl` | `learning/observation_outcomes.jsonl` |

---

### 每周五 Cron — 模型重训练

入口：crontab 调用 `python3.12 agents/learning_agent.py`

| 步骤 | 文件 | 函数 | 输入 | 输出 |
|------|------|------|------|------|
| 加载数据 | `learning_agent.py` | `load_all_data()` | `learning/historical_features.parquet` + `daily_harvest.jsonl` | 合并 DataFrame |
| 训练模型 | `learning_agent.py` | `retrain(df, label_col, feature_prefix)` | 合并数据 | RandomForest 模型对象 |
| 退化检测 | `learning_agent.py` | `check_model_degradation()` | `learning/daily_harvest.jsonl` | 控制台警告 |
| 保存模型 | `learning_agent.py` | joblib.dump | 训练后模型 | `learning/model_intraday.pkl` `learning/model_swing.pkl` |
| 更新权重日志 | `learning_agent.py` | 直接写文件 | 精度数据 | `learning/weights_log.json` |

---

### 月度/重大变更 — Bootstrap（历史训练）

入口：手动运行 `python3.12 agents/bootstrap_agent.py`

输出：`learning/historical_features.parquet` `learning/case_library.json`

---

## 三、孤儿代码（存在但未被工作流串联的功能）

以下文件/函数有实现但根据 AGENT_STATUS.md 标注为历史遗留或观察后发现未被主流程调用：

| 文件 | 状态 | 原设计用途 | 为何是孤儿 |
|------|------|-----------|----------|
| `auto_trigger.py` | 🔴 deprecated | 盘中自动触发CIO | 已被 translator.py + session_manager.py 替代，不再调用 |
| `strategy_council.py` | 🔴 deprecated | 大师审查交易规则 | 功能已内嵌到 CIO debate_engine，无人调用 |
| `multi_stock.py` | 🔴 deprecated | 多标的并行比较 | CIO 的 run_parallel() 直接并行，此中间层废弃 |
| `market_scanner.py` | 🔴 deprecated | 5维市场扫描 | 被 candidate_scanner.py 替代；仅在 premarket.py 有弱引用但可能已移除 |
| `stock_report.py` | 🔴 deprecated | 生成股票报告（1881行） | 功能与 report_agent 重叠，不再新增调用 |
| `report_analyst.py` | 🔴 deprecated | 格式化报告 | 只被 stock_report.py 调用，随之废弃 |
| `session_recorder.py` | 🔴 过渡期 | 记录 session 快照 | 现在仍被 poll.py 调用（write_snapshot/log_action），但 log_action/log_thought 功能已被 decision_trace.jsonl 替代，部分方法孤儿 |
| `cleanup.py` | 🔴 deprecated | 清理旧文件 | 手动维护成本高，不再使用 |
| `postmarket_review.py` L115 | 部分孤儿 | `run_review()` 中大师发言用占位符 | 实际 LLM 调用逻辑未实现，仅打印占位文字 |
| `unified_confidence.py` | 🟡 弱引用 | 统一置信度 | 设计为 premarket 集成，但 premarket.py 中调用路径不稳定；Node 0 未直接调用 |
| `fundamentals_tracker.py` | 🟡 季度手动 | 基本面追踪 | 正常辅助路径，但主流程不自动触发 |
| `question_router.py` | 🟡 辅助 | 大师问题路由 | 被 cio.phase2_persona() 调用，属于正常辅助，但独立文件易被忽略 |
| `paper_trader.py` — `eod_close_all()` | 🟡 未触发 | 每日收盘平仓 | 函数存在，但未发现主流程自动调用（依赖外部 EOD 触发） |
| `persona_engine.py` | 🟡 独立 | 大师 persona 管理 | 与 debate_engine.py 功能重叠，主要流程走 debate_engine |
| `risk_agent.py` L中的某些高级风险计算 | 🟡 部分 | 高阶风险指标 | 参与 CIO Phase1，但部分高级方法仅在文件内部，不被外部调用 |

---

## 四、数据文件地图

### 4.1 核心 JSON/JSONL 文件

| 文件路径 | 类型 | 写入者 | 读取者 | 说明 |
|---------|------|--------|--------|------|
| `premarket_analysis_{date}.json` | JSON | `premarket.py` (main) | `poll.py` (load_premarket) `daily_plan.py` `cio._infer_question_type` | 每日盘前分析结果（场景/催化剂/gap）|
| `candidates_{date}.json` | JSON | `candidate_scanner.py` (rank_candidates写入) | `session_manager.py` (Node0读取) | 每日候选池扫描结果 |
| `daily_plan_{date}.json` | JSON | `daily_plan.py` (generate_plan) | `poll.py` (load_plan_for_sym) `entry_guard.py` (get_plan) | 当日止损/目标价计划 |
| `session_state_{date}.json` | JSON | `session_manager.py` (_save_state) | `session_manager.py` (_load_state) | 工作流节点状态 + 提醒队列 |
| `opening_scenarios_{date}.json` | JSON | `poll.py` (save_daily_scenarios) | `poll.py` (load_daily_scenarios) | 盘中形态分类结果（A-H）|
| `quick_debate_{sym}.json` | JSON | `quick_debate.py` | `poll.py` (read_quick_debate) | 快速三人辩论结果 |
| `strategy_result.json` | JSON | `strategy_agent.py` | `session_manager.py` (CIO 结果读取) `cio.py` (Phase3后保存) | CIO 综合分析结果（全局路径，并行时在 runs/ 子目录）|
| `data_raw_primary.json` | JSON | `data_agent.py` (fetch_primary) | `verifier_agent.py` | CIO Phase0 原始数据层1 |
| `data_raw_secondary.json` | JSON | `data_agent.py` (fetch_secondary) | `verifier_agent.py` | CIO Phase0 原始数据层2 |
| `data_verified.json` | JSON | `verifier_agent.py` | 8个 domain agent | CIO 验证后数据 |
| `discussion_board.jsonl` | JSONL | `session_manager.py` (push_alert) `cio.phase1/phase2` | `session_manager.py` (drain_alerts) `strategy_agent.py` `cio.check_consensus` | 多用途：提醒队列 + CIO agent 辩论板 |
| `persona_stances.jsonl` | JSONL | `debate_engine._log_persona_stances` | `debate_engine.weighted_synthesis` | 大师立场日志 |
| `persona_synthesis.json` | JSON | `debate_engine.weighted_synthesis` `cio.phase2_persona` | `strategy_agent.py` | 大师层综合裁决 |
| `watchlist.json` | JSON | 手动维护 | `candidate_scanner` (间接) | 动态关注列表 |
| `watchlist_permanent.json` | JSON | 手动维护 + entry_guard | `session_manager.py` (Node0 Step2) | 永久关注列表（含 pending_review）|
| `trading_lessons.json` | JSON | 手动维护 | 无自动读取（参考用）| 交易经验库 |

### 4.2 Config 配置文件

| 文件路径 | 写入者 | 读取者 | 说明 |
|---------|--------|--------|------|
| `config/positions.json` | `entry_guard.py` (record_trade) | `portfolio_risk_agent.py` `poll.py` (load_real_positions) `session_manager.py` (Node0 合并持仓) | 真实持仓（成本/股数）|
| `config/positions_mode.json` | `poll.py` (save_positions_mode) | `poll.py` (load_positions_mode) | 每只股票的 swing/intraday 模式 |
| `config/poll_config.json` | 手动维护 | `candidate_scanner.py` `harvest_agent.py` `premarket.py` | 关注列表/板块映射/轮询配置 |
| `config/leveraged_pairs.json` | 手动维护 | `portfolio_risk_agent.py` `session_manager.py` | 底层标的→杠杆ETF 映射 |
| `config/daily_focus.json` | 手动维护 | `session_manager.py` (Node0 Step7) | 固定关注标的（CIO 每日必跑）|
| `config/sector_watchlist.json` | 手动维护 | `candidate_scanner.py` | 板块→标的映射 |

### 4.3 Learning 学习数据文件

| 文件路径 | 写入者 | 读取者 | 说明 |
|---------|--------|--------|------|
| `learning/daily_harvest.jsonl` | `harvest_agent.py` (run) | `session_manager.py` (Node0 模型健康检查) `learning_agent.py` `health_check.py` | 每日结果标注（label 0/1/-1）|
| `learning/observation_log.jsonl` | `poll.py` (_write_observation_log) | `harvest_agent.py` (process_observation_log) | 每次 poll 的信号快照+门控判断 |
| `learning/observation_outcomes.jsonl` | `harvest_agent.py` (process_observation_log) | bootstrap_agent.py | 盘后配对实际结果 |
| `learning/cio_signals_{date}_{sym}.json` | `cio.py` (Phase3后) | `harvest_agent.py` (update_master_accuracy) | CIO 各agent 信号（供精度追踪）|
| `learning/master_accuracy.json` | `harvest_agent.py` (update_master_accuracy) | `strategy_agent.py` | 各 domain agent 历史精度（Bayesian更新）|
| `learning/model_intraday.pkl` | `learning_agent.py` (retrain) `bootstrap_agent.py` | `intuition_agent.py` (_load_model) | 日内方向 RandomForest 模型 |
| `learning/model_swing.pkl` | `learning_agent.py` (retrain) `bootstrap_agent.py` | `intuition_agent.py` (_load_model) | 波段方向 RandomForest 模型 |
| `learning/historical_features.parquet` | `bootstrap_agent.py` | `learning_agent.py` (load_all_data) `health_check.py` | 历史特征矩阵（Bootstrap 生成）|
| `learning/case_library.json` | `bootstrap_agent.py` | `intuition_agent.py` (find_similar_cases) | 历史相似案例库 |
| `learning/short_interest_history.jsonl` | `harvest_agent.py` (record_short_interest) | `candidate_scanner.py` (间接）| 空头比例历史 |
| `learning/weights_log.json` | `learning_agent.py` | 参考用 | 大师权重更新日志 |
| `learning/quality_archive.json` | `learning_agent.py` (可能) | `bootstrap_agent.py` | 质量存档 |
| `learning/features.py` | 手动维护代码 | `session_manager.py` `poll.py` `learning_agent.py` `intuition_agent.py` | 特征提取函数库（get_macro_regime/extract_*_features）|

### 4.4 Knowledge 知识文件

| 文件路径 | 写入者 | 读取者 | 说明 |
|---------|--------|--------|------|
| `knowledge/snapshots_{date}.jsonl` | `session_recorder.py` (write_snapshot) | `harvest_agent.py` (get_today_symbols) | 日内2分钟快照（>1天后自动删除）|
| `knowledge/trading_history.jsonl` | `entry_guard.py` (record_trade) `session_recorder.py` (log_action) | `postmarket_review.py` (间接) | 永久交易历史 |
| `knowledge/session_{date}.md` | 手动填写（模板） | `postmarket_review.py` (load_session_log) | 每日交易日记 |
| `knowledge/trading_methodology.md` | 手动维护 | `postmarket_review.py` (load_methodology) | 交易方法论知识库 |
| `knowledge/company_profiles.json` | 手动维护 | `poll.py` (_load_company_profile) | 持仓论点/基本面简介 |

### 4.5 Persona 大师文件

| 路径 | 写入者 | 读取者 | 说明 |
|------|--------|--------|------|
| `personas/mark_minervini/` | 手动/bootstrap 初始化 | `debate_engine.py` (collect_persona_stances) `quick_debate.py` | Minervini 大师问题集 + 立场文件 |
| `personas/stan_druckenmiller/` 等共7个 | 同上 | 同上 | 其余6位大师文件夹 |

### 4.6 Paper Trading 模拟盘

| 路径 | 写入者 | 读取者 | 说明 |
|------|--------|--------|------|
| `paper_trading/{strict/base/loose}/portfolio.json` | `paper_trader.py` | `paper_trader.py` `poll.py` | 三账号模拟盘持仓 |
| `paper_trading/{acct}/trades.jsonl` | `paper_trader.py` (log_trade) | `paper_trader.py` (load_trade_history) | 模拟盘交易历史 |
| `paper_trading/{acct}/evolution.jsonl` | `paper_trader.py` | `learning_agent.py` (可能) | 参数进化记录 |

---

## 五、关键约束与注意事项

1. **并行隔离**：CIO `run_parallel()` 为每个标的创建独立 `runs/{sym}_{date}/` 目录，避免全局文件（`strategy_result.json`、`discussion_board.jsonl`）冲突。

2. **锁机制**：CIO 单标的运行通过 `protocol.LOCK_PATH` 加锁（10分钟超时），防止重复分析。

3. **孤儿文件风险**：`discussion_board.jsonl` 兼作"提醒队列"和"CIO辩论板"，功能混合；并行CIO时的写入可能相互污染（已用 rundir 隔离解决）。

4. **模型冷启动**：无 `historical_features.parquet` 时，`intuition_agent` 返回 None，`unified_confidence` 自动跳过 ML 分数；系统可降级运行。

5. **translator.py 优先级**：`session_manager.handle_text()` 优先调用 `translator.handle()`，匹配失败才回退到正则 `_TRADE_PATTERN`。

6. **数据保鲜策略**：快照文件（snapshots_*.jsonl）每日保留，超过1天自动清理；harvest 和 trading_history 永久保留。
