# Stock Team 未来发展方向与工作计划路线图

**日期**：2026-06-05  
**负责人**：Antigravity  
**目标仓库**：`D:\gemini\lianghua\stock_team`  

为了实现“大脑与肌肉”的彻底物理去耦，量化执行引擎 `stock_team` 现已完成根目录重构与文件清理。本文件定义了 `stock_team` 的未来架构蓝图、文件资产清理结果、以及后续的具体开发路线图。

---

## 1. 物理结构整理成果 (Restructuring Results)

我们已经对 `stock_team` 进行了深度大扫除，清除冗余，理清架构：

1.  **高价值认知资产收集**：
    *   将 18 个隐藏在 `docs/`、`learning/`、`findings/` 和 `scratch/` 目录下的核心认知文件（包括交易员心理反思、美光重估教训、SpaceX 防 FOMO 案例、行业存储芯片分析、多智能体历史辩论纪实、以及交易节点图解 HTML）统一**只读复制收集**到了：
        *   `D:\gemini\lianghua\stock_team\archive\cognitive_assets\`
        *   这批资产已被集中保护起来，随时等待 `investing-os` 的 Codex 实例恢复 Token 后提取并标准化吸收到 Wiki 永久目录中。
2.  **根目录冗余清除**：
    *   将此前平铺在根目录的 47 个历史运行缓存文件（包括 5 月至 6 月的历史 candidates、checklist、daily_plan、opening_scenarios、premarket_analysis、各标的 macro_strategy 与 strategic_memo 等）全部**安全移动归档**到了：
        *   `D:\gemini\lianghua\stock_team\archive\session_history_2026-06\`
    *   **整理后效果**：`stock_team` 的根目录已由 66+ 个杂乱文件缩减至仅 19 个干净的核心配置与运行入口文件（如 `.env`、`CLAUDE.md`、`main.py`、`morning.py` 等），结构极其清晰。

---

## 2. 后续工作开发路线图 (Antigravity Work Plan)

针对 `stock_team` 层面，我们将分期推进以下优化任务：

### Phase A: 测试套件与开发脚本分层 (P1 — 本周)
*   **目标**：重构目前平铺在 `tests/` 下的 60 个测试文件。
*   **行动**：
    *   将测试文件归入四个清晰的子层级：
        1.  `tests/unit/core/`：测试基础行情接口、Polygon API 连接及数学指标计算。
        2.  `tests/unit/agents/`：测试各个大师智能体的 Stance 决策及权重逻辑。
        3.  `tests/unit/sop/`：测试 `session_manager` 工作流节点流转与降级机制。
        4.  `tests/integration/`：测试 Node 1 至 Node 6 的全链路模拟运行。

### Phase B: 导入清理与系统解耦 (P1 — 本周)
*   **目标**：彻底消除代码中混乱的 `sys.path.insert(0, ...)` 导入，并剥离 Wiki 运行时依赖。
*   **行动**：
    *   改造 `agents/` 和 `scripts/` 下的 Python 模块，引入清晰的包相对导入机制。
    *   移除所有对 `investing-os` 原始 Wiki 文件的物理直连读取，实现仅读取 `config/tactical_rules.json`（定量参数快照）。

### Phase C: 实施约束交易模式 (Constrained Mode) (P1 — 本周)
*   **目标**：防止全天盯盘造成的精力和 API 额度过度损耗。
*   **行动**：
    *   开发新模块 `agents/premarket_order_sheet.py`，在开盘前输出清晰的条件订单表。
    *   在 `poll.py` 中增加 `trading_mode` 控制开关（`constrained` 或 `active`）。在 `constrained` 模式下，美东时间 10:30 之后停止主动监测入场信号，将交易自动托管给已挂出的 GTC（Good 'Til Cancelled）限价单，降低盘中轮询压力。

### Phase D: 大数据与历史回测系统重构 (P2)
*   **目标**：解决回测系统（`backtest_engine.py`）中宏观过滤过严导致空结果的 bug，并建立置信度评价体系。
*   **行动**：
    *   重构 `backtest_result.py`，统计基准收益率（vs_baseline）与夏普比率（Sharpe），不再使用 Null 存根。
    *   将历史参数回测与宏观大盘环境进行联动，通过 Monte Carlo（蒙特卡洛）与 Walk-Forward（向前行走）滚动拼接测试，为每个交易因子生成科学的“可信度评估报告”（`evidence_credibility_report.json`）。

---

## 3. 中长期战略发展方向 (Future Directions)

为了让 `stock_team` 成为更强有力的量化工具，建议中长期朝以下三个方向演进：

1.  **大盘环境路由机制 (Regime-Aware Routing)**：
    *   将当前简单的三值宏观定调（normal/bull/bear）升级为 5 值细分市场环境分类（`trending_up` / `trending_down` / `sideways` / `volatile` / `sector_hot`）。
    *   量化引擎根据当前的市场 Regime，动态路由并载入完全不同的策略参数组合（例如：单边牛市放大追高门槛，震荡市收紧仓位门槛并采用缩量回踩入场），实现对市场状态的主动适配。
2.  **建仓时强制证伪条件引导 (Falsification Enforcement)**：
    *   开发交互式建仓工具 `agents/position_builder.py`。
    *   用户在建立新仓位或加仓时，系统会根据仓位属性（趋势/催化剂/低吸）强制提问并录入具体的定性证伪事件（例如：“对于 NVDA，若 Blackwell 芯片由于技术原因延迟发货达一个季度，则判定论点破裂”），并写入 `positions.json` 的 `falsification_conditions` 列表中。这能在交易之初就锁定退出红线，锁死情绪化决策。
3.  **多源因子置信度分层 (Factor Confidence Tiering)**：
    *   在 Decision State Hub 中，将交易因子的计算结果按数据质量与回测样本数进行分级（如 Tier 1：高频历史回测支持的 VWAP 门控；Tier 3：实时抓取的社交情绪热度）。
    *   当大模型主控分析时，如果发现主要决策信号来源于低置信度（Tier 3）的因子，强制在审计日志中输出风险警告，限制narrative（叙事性）分析对量化事实证据的劫持。
