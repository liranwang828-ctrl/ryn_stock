# Ryn Stock Team v2.0 — 多智能体股票交易系统

9-Agent + 2 System Role 的 AI 交易团队，基于 DeepSeek 大模型，覆盖从盘前到盘后的完整交易流程。

## 架构概览

```
                    ┌──────────────────────────────┐
                    │     Orchestrator (主控引擎)    │
                    │  模式调度 M1→M2→M3→M4→M5     │
                    └──────────┬───────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐          ┌──────▼──────┐        ┌──────▼──────┐
   │ 9 Agent │◄────────►│ Debate Loop │◄──────►│  Resonance  │
   │ A1 → A9 │   DV门禁  │  R1→R2→R3   │        │  5组共振     │
   └────┬────┘          └──────┬──────┘        └──────┬──────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Paper Trading 引擎   │
                    │   5账户 × 3建仓策略     │
                    │   8安全过滤器           │
                    └──────────────────────┘
```

## 快速开始

### 环境要求
- Python 3.10+
- 依赖安装：`pip install -r requirements.txt`

### 5 分钟上手
```bash
# 1. 运行指标测试
python indicators/test_indicators.py

# 2. 启动完整会话（模拟模式）
python engine/orchestrator.py

# 3. 回测单个股票
python engine/backtest.py

# 4. 启动终端仪表盘
python engine/dashboard.py
```

## 核心设计

### 9 个 Agent + 2 个系统角色

| ID | 角色 | 专属数据 |
|----|------|----------|
| A1 | 新闻分析师 | market_news, earnings_calendar |
| A2 | 情绪分析师 | social_sentiment, wsb_mentions, options_flow |
| A3 | KOL跟踪 | kol_opinions |
| A4 | 宏观分析师 | macro_indicators |
| A5 | 量化分析师 | factor_scores, correlation_matrix, volume_profile |
| A6 | 基本面/CFA | fundamentals, analyst_estimates |
| A7 | 技术分析师 | technical_indicators, price_history |
| A8 | 风控官 | risk_metrics, trade_log |
| A9 | 复盘教练 | agent_decision_log, trade_log |
| DC | 辩论协调员 | 所有agent输出 |
| DV | 数据验证器 | 编造检测 + 指标白名单 |

### 5 种工作模式

| 模式 | 时段 | 参与Agent | 可交易 |
|------|------|-----------|--------|
| M1 盘前 | 04:00-09:30 | A1,A2,A3,A4,A7 | 否 |
| M2 开盘观察 | 09:30-10:00 | A1,A2,A4,A7,A8 | 否 |
| M3 实时监控 | 10:00-16:00 | A1-A8 + DC + DV | 是 |
| M4 策略执行 | 10:00-16:00 | A1-A9 + DC + DV | 是 |
| M5 盘后复盘 | 16:00+ | A8,A9 + DC | 否 |

### 5 组共振进场逻辑

进场需要多组指标同时看多（AND-gate）：

| 共振组 | 指标 | 权重 |
|--------|------|------|
| G_PRICE | 价格 > VWAP, 高于前收, 更高低点 | 20% |
| G_TECH | ADX > 25, 价格 > MA20, 不在阻力位 | 30% |
| G_SECTOR | 板块跑赢大盘, 广度 > 55% | 15% |
| G_MACRO | VIX < 30, 无深度倒挂, 非FOMC日 | 20% |
| G_SENTIMENT | 社交情绪积极, 新闻正面, P/C < 1 | 15% |

**进场级别**: STRONG (4组) → 满仓 / MODERATE (3组) → 60% / WEAK (2组) → 30%需A8签字

### 5 个模拟盘账户

| 账户 | 风格 | 入场严格度 | 止损(ATR) | 止盈T1/T2/T3 |
|------|------|------------|-----------|--------------|
| A 保守型 | 资本保全 | 1.3× | 1.5× | 1.0/2.0/3.0 |
| B 均衡型 | 基准对照 | 1.0× | 2.0× | 1.5/3.0/5.0 |
| C 激进型 | 放大收益 | 0.7× | 3.0× | 2.0/4.0/7.0 |
| D 动量型 | 追涨趋势 | 0.8× | 2.5× | 3.0/5.0/10.0 |
| E 逆势型 | 抄底均值回归 | 1.2× | 1.5× | 1.5/2.5/4.0 |

### 8 个安全过滤器

| ID | 名称 | 触发条件 | 动作 |
|----|------|----------|------|
| F1 | VIX急涨 | VIX > 35 | 禁止所有多头开仓 |
| F2 | 重大新闻冲击 | HIGH级别新闻 < 30分钟 | 禁止所有开仓30分钟 |
| F3 | 大盘熔断 | SPY跌 > 5% | 禁止开仓15分钟 |
| F4 | 低流动性 | 成交量 < 均量50% | 禁止开仓，现有仓位减半 |
| F5 | FOMC管制期 | 发布前后各30/60分钟 | 禁止开仓，收紧止损 |
| F6 | 财报风险 | 48小时内有财报 | 禁止该股开仓 |
| F7 | 隔夜跳空 | 开盘跳空 > 2% | 等待价格稳定 |
| F8 | 相关性融涨 | R² > 0.9 | 禁止所有开仓 |

## 项目结构

```
ryn_stock_team/
├── config/              (13个YAML配置文件)
│   ├── MASTER_CONFIG.yaml          ← 入口配置
│   ├── agent_definitions.yaml      ← Agent定义
│   ├── mode_participation_matrix.yaml
│   ├── debate_protocol_v2.yaml
│   ├── dynamic_weights.yaml
│   ├── fabrication_penalties.yaml
│   ├── observation_framework.yaml
│   ├── trading_strategy.yaml       ← 核心策略
│   ├── paper_trading.yaml
│   ├── paper_accounts_comparison.yaml
│   ├── position_staging.yaml
│   └── data_catalog.yaml
│
├── indicators/          (技术指标引擎)
│   ├── compute_indicators.py       ← 47个指标，本地计算
│   ├── data_fetcher.py             ← 云数据库+Yahoo Finance
│   └── test_indicators.py          ← 冒烟测试
│
├── engine/              (执行引擎)
│   ├── orchestrator.py             ← 主循环控制器
│   ├── paper_engine.py             ← 模拟盘撮合
│   ├── backtest.py                 ← 回测+参数搜索
│   └── dashboard.py                ← 终端仪表盘
│
├── pipelines/           (数据管线)
│   └── news_pipeline.py            ← Finnhub+Reddit+YF
│
├── db/                  (数据库)
│   └── schema.sql                  ← 21表+3视图
│
├── prompts/             (提示词)
│   └── agent_system_prompts.md
│
├── schemas/             (数据结构)
│   └── trade_record_schema.json
│
├── README.md
├── CHANGELOG.md
├── requirements.txt
└── .gitignore
```

## 配置

### 数据源
系统支持三级数据获取策略：
1. **云端数据库** (历史OHLCV) — 配置于 `indicators/data_fetcher.py`
2. **Yahoo Finance** (当日+历史fallback) — 开箱即用
3. **Finnhub/Reddit** (新闻+情绪) — 需API key，配置于 `pipelines/news_pipeline.py`

### 可调参数
所有用户可调参数汇总在 `config/MASTER_CONFIG.yaml` 的 `configurable_parameters_summary`：
- 每笔风险预算 (默认 2%)
- 单标的最大仓位 (默认 25%)
- 硬止损 (默认 2%)
- ATR止损倍数 (默认 2×)
- VIX急涨阈值 (默认 35)
- 辩论共识阈值 (默认 0.6)
- 账户熔断回撤 (默认 6%)
- 编造阈值/停权时长

### 待决策项
6个待用户确认的决策在 `config/MASTER_CONFIG.yaml` → `pending_user_decisions`

## 路线图

- [x] Agent定义 + 参与矩阵
- [x] 3轮辩论协议 + 防编造
- [x] 47个技术指标本地计算
- [x] 5组共振交易策略 + 8安全过滤器
- [x] 5账户模拟盘对比
- [x] 3种分批建仓策略
- [x] 回测框架 + 网格搜索
- [x] 终端仪表盘
- [ ] LLM API 接入
- [ ] 真实券商API
- [ ] Web仪表盘
- [ ] 移动端通知
- [ ] 5年历史数据回测
- [ ] 机器学习市场状态分类器

## 许可证

Internal use. 后续补充开源协议。
