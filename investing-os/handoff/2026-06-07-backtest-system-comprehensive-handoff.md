# 2026-06-07 Backtest System Comprehensive Handoff

This document captures the step-by-step discussion, architectural boundaries, current codebase state, and future roadmap of the **Tactic Backtest System** co-developed by the user and Antigravity. It is designed to allow any future coding agent to instantly resume work without losing context.

---

## 1. Context: Why We Built the Backtest System

### The Problem
During intraday trading sessions, the user noticed that the trading system (muscle) and brain were generating ad-hoc level checks (such as VWAP, MA20/MA50 crossovers, volume triggers) without robust historical validation. This created two critical risks:
1. **Ad-hoc Decision Making**: Generating trading rules on the fly without checking their historical profitability, win rate, or drawdown statistics.
2. **Role Collision**: The muscle team generating recommendations, or the brain defining execution details without quantitative evidence.

### The Solution: The Handshake Architecture
We established a strict separation of concerns between `investing-os` (the brain) and `stock_team` (the muscle/evidence team):
* **investing-os (Brain)**: Defines the hypothesis, qualitative rules, boundaries, and ultimate adoption decisions (e.g., approving a tactic from `candidate` to `paper_test` or `live`).
* **stock_team (Muscle)**: Performs raw mathematical calculations, processes historical data, runs simulation loops, and emits **evidence only**.

---

## 2. Step-by-Step Discussion & Implementation Progress

### Step 1: Defining the Contract Boundaries (Handshake Schema)
We agreed that `stock_team` must never make recommendation decisions or approve trading permission changes. 
We designed a unified CLI command:
```powershell
python -m stock_team.cli tactic-backtest \
  --request "<path_to_request.json>" \
  --out "<path_to_report.md>" \
  --json-out "<path_to_summary.json>"
```

The request JSON schema enforces strict compliance gates:
```json
"output_contract": {
  "allow_recommendations": false,
  "allow_config_mutation": false
}
```
If these gates are missing or set to `true`, or if any forbidden keys like `approved` or `sizing` exist in the request, the backtest system will crash immediately with a compliance error.

### Step 2: CLI Command Registration
We mapped the new sub-command `tactic-backtest` inside `stock_team/cli.py` to route requests to `tactic_backtest_system.py`.

### Step 3: Implementing Data Adapters
We created `tactic_backtest_system.py` supporting two initial minimum viable data modes:
1. **`fixture_events`**: Directly parses pre-generated trade events from the request JSON to test downstream metrics formatting and window splits.
2. **`intraday_ohlcv_fixture`**: Simulates trading using hardcoded OHLCV bars. The first implemented trigger is:
   - **Tactic**: `rs_pullback_rebound_intraday`
   - **Trigger Condition**: Previous bar close < VWAP, and current bar close > VWAP (reclaim).
   - **Volume Confirmation**: Current volume ratio >= `min_volume_ratio`.
   - **Action Window**: Current time within `action_window_start` and `action_window_end` (e.g., 10:00 to 11:00).
   - **Exit Rules**: Exits immediately when Take Profit (`take_profit_pct`) or Stop Loss (`stop_loss_pct`) is touched, or at the End of Day (`end_of_day`).

### Step 4: Metrics Calculations
The engine automatically calculates the following metrics for the whole backtest, as well as split by **Validation Windows** (train/test splits) and **Market/Sector Regimes**:
- **n_trades**: Number of simulated trades.
- **win_rate**: Percentage of winning trades.
- **avg_return_pct**: Average return per trade.
- **avg_win_pct** / **avg_loss_pct**: Average sizing of wins and losses.
- **profit_factor**: Gross win value divided by gross loss value.
- **avg_mae_pct** (Maximum Adverse Excursion): Average maximum paper loss during trades.
- **avg_mfe_pct** (Maximum Favorable Excursion): Average maximum paper gain during trades.

### Step 5: Compliance and Censorship Sweep
Before exporting, the system performs a regex scan using word boundaries (`\b`) to censor forbidden trading words (like `buy`, `sell`, `hold`) to ensure the report remains strictly evidence-based.

---

## 3. Current File Inventory

All code, tests, and configuration files are checked in and verified:
1. **Backtest Engine**: [tactic_backtest_system.py](file:///D:/gemini/lianghua/stock_team/backtest/tactic_backtest_system.py)
2. **CLI Entrypoint**: [cli.py](file:///D:/gemini/lianghua/stock_team/cli.py)
3. **Contract Docs**: [tactic-backtest-contract.md](file:///D:/gemini/lianghua/stock_team/docs/tactic-backtest-contract.md)
4. **Example Request Configurations**:
   - [tactic_backtest_request.example.json](file:///D:/gemini/lianghua/stock_team/config/tactic_backtest_request.example.json)
   - [tactic_backtest_intraday_ohlcv_request.example.json](file:///D:/gemini/lianghua/stock_team/config/tactic_backtest_intraday_ohlcv_request.example.json)
   - [tactic_backtest_rs_intraday_demo_v1.json](file:///D:/gemini/lianghua/stock_team/config/tactic_backtest_rs_intraday_demo_v1.json)
5. **Unit Tests**:
   - [test_tactic_backtest_system.py](file:///D:/gemini/lianghua/stock_team/tests/unit/core/test_tactic_backtest_system.py)
   - [test_cli.py](file:///D:/gemini/lianghua/stock_team/tests/unit/core/test_cli.py) (includes `test_cli_tactic_backtest_generation` and `test_cli_tactic_backtest_ohlcv_fixture_generation`).

---

## 4. Next Step: The Polygon Historical Data Adapter (Blueprint)

The ultimate goal is to plug in real historical data. The next agent should implement the **Polygon-first historical adapter** under `tactic_backtest_system.py`:

### The Implementation Steps for the Next Agent:
1. **Load API Keys**: Read `POLYGON_API_KEY` from the system using the existing `get_api_key()` helper in [data_agent.py](file:///D:/gemini/lianghua/stock_team/data_ingest/data_agent.py).
2. **Fetch Historical Aggregates**:
   - Implement a fetching function that connects to Polygon's REST API `/v2/aggs/ticker/{symbol}/range/1/minute/{start}/{end}`.
   - Retrieve 1-minute aggregate bars for the requested `date_range` and `symbols`.
3. **Cache the Data**:
   - Save the raw downloaded bars in a local cache directory (e.g., `D:\gemini\lianghua\stock_team\data\cache\{symbol}_1m_{start}_{end}.json`) to prevent repeated API calls and preserve rate limits.
   - Include metadata: source (`polygon`), download timestamp, and freshness.
4. **Normalize to OHLCV**:
   - Transform the Polygon JSON structure (`o`, `h`, `l`, `c`, `v`, `t`) into the normalized dictionary structure expected by `_normalize_bar` in `tactic_backtest_system.py`:
     - `open`, `high`, `low`, `close`, `volume`, `timestamp`.
5. **Compute Regimes**:
   - Retrieve QQQ, SPY, and sector ETF (like SOXX) bars for the same time windows.
   - Label each bar with its `market_regime` (e.g., `qqq_uptrend_low_vix`, `high_volume_risk_off`) and `sector_regime` (e.g., `semis_strong`, `semis_weak`) before feeding it to the simulator.
6. **Simulate & Report**:
   - Pass the normalized and enriched bars to `_first_vwap_reclaim_event` to simulate trades, calculate metrics, and output the standard Markdown and JSON packets.
