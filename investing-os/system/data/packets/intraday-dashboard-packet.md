# 盘中证据监控看板 / Intraday Evidence Dashboard (2026-06-08)
边界声明：本看板仅对客观事实与预设条件进行校验呈现，不包含任何交易动作指令。 (Boundary: Objective factual checks only. No trading approval. No [censored]/[censored]/[censored] keywords.)

## 1. 数据包就绪状态与链接 / Packet Readiness & Links
| 数据包 (Packet) | 状态 (Status) | 路径 (Path) |
| :--- | :---: | :--- |
| Stage 0 盘前环境数据包 (Stage 0 Environment Packet) | 已就绪 (Ready) | `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md` |
| Stage 1 盘前计划证据包 (Stage 1 Plan Evidence Packet) | 已就绪 (Ready) | `C:\Users\rriww\Documents\investing-os\system\data\packets\plan-evidence-packet.md` |

## 2. 系统与数据源健康度 / System & Data Health
- Polygon 激活状态 (Polygon Active): **True**
- IBKR 激活状态 (IBKR Active): **False**
- 数据源状态 (Data Source Status): **warning_yfinance_fallback_used**
- 数据时效 (Snapshot Freshness): **模拟历史数据 (stale)** (模拟日期: 2026-06-08, 快照时间: 2026-06-09T15:51:18.346664Z)

### 警告信息 (Warnings)
- SMH_polygon_runtime_failed:ReadTimeout
- IWM_polygon_runtime_failed:ReadTimeout
- SPY_polygon_runtime_failed:ReadTimeout
- SOXX_polygon_runtime_failed:ReadTimeout
- QQQ_polygon_runtime_failed:ReadTimeout
- VIXY_polygon_runtime_failed:ReadTimeout
- INTC_polygon_runtime_failed:ReadTimeout
- MU_polygon_runtime_failed:ReadTimeout
- COHR_polygon_runtime_failed:ReadTimeout
- polygon_runtime_bars_unavailable_for_requested_date_or_symbols; fell back to yfinance/local runtime prices

## 3. 监控标的与事实条件校验 / Symbol Condition Evaluations
### INTC (watchlist)
- 盘中模式 (Intraday Mode Echo): **observe_only**
- 主脑授权状态 (Brain Status Echo): **not_allowed** (evidence_only)

| 条件 ID (Condition ID) | 客观条件描述 (Description) | 状态 (Status) | 核对事实依据 (Fact Checked) |
| :--- | :--- | :---: | :--- |

| 价格位置 ID (Level ID) | 监控含义 (Meaning) | 计算公式 (Formula / Value) | 位置数值 (Computed Value) | 当前价格 (Current Price) | 穿透状态 (State) |
| :--- | :--- | :--- | :---: | :---: | :---: |


### MU (watchlist)
- 盘中模式 (Intraday Mode Echo): **observe_only**
- 主脑授权状态 (Brain Status Echo): **not_allowed** (evidence_only)

| 条件 ID (Condition ID) | 客观条件描述 (Description) | 状态 (Status) | 核对事实依据 (Fact Checked) |
| :--- | :--- | :---: | :--- |

| 价格位置 ID (Level ID) | 监控含义 (Meaning) | 计算公式 (Formula / Value) | 位置数值 (Computed Value) | 当前价格 (Current Price) | 穿透状态 (State) |
| :--- | :--- | :--- | :---: | :---: | :---: |


### COHR (swing)
- 盘中模式 (Intraday Mode Echo): **observe_only**
- 主脑授权状态 (Brain Status Echo): **not_allowed** (evidence_only)

| 条件 ID (Condition ID) | 客观条件描述 (Description) | 状态 (Status) | 核对事实依据 (Fact Checked) |
| :--- | :--- | :---: | :--- |

| 价格位置 ID (Level ID) | 监控含义 (Meaning) | 计算公式 (Formula / Value) | 位置数值 (Computed Value) | 当前价格 (Current Price) | 穿透状态 (State) |
| :--- | :--- | :--- | :---: | :---: | :---: |

