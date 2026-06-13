# 2026-06-07 Backtest System Session Record

Purpose: record how we discussed and built the first usable backtest contract so a future Codex / ChatGPT / account can continue without losing context.

## 1. Why We Needed This

The user questioned whether the intraday monitoring factors, entry levels, VWAP, QQQ / VIX state, sector strength, and RS filters should be ad hoc or validated.

We agreed:

- The dashboard should not monitor random indicators.
- The brain should not invent intraday levels without evidence.
- The muscle should not invent trade recommendations.
- Factors and tactics need a validation path before becoming live trading guidance.
- A tactic should move through statuses such as candidate, paper test, limited live, approved, disabled, retired.

Core design principle:

```text
investing-os defines meaning, hypothesis, boundary, and adoption.
stock_team calculates evidence, event statistics, and validation segments.
```

## 2. Existing stock_team Backtest Review

Codex inspected the current `stock_team` backtest system and found useful but fragmented parts:

- `backtest/backtest_engine.py`: daily signal scan, MA20 deviation, RS5, volume ratio.
- `backtest/backtest_macro.py`: macro filters, VIX / SPY / QQQ style gates, 80/20 train-test split, by-period and by-sector analysis.
- `backtest/backtest_micro.py`: intraday signals, VWAP, 5m volume, RSI, slippage, leverage decay, structural nodes.
- `backtest/run_tactic_backtest.py`: old RS pullback rebound backtest, but it is multi-day / swing-like, not strict intraday.
- `backtest/walk_forward_analysis.py`: walk-forward pattern that can be reused later.
- `backtest/factor_ic_analyzer.py`: factor IC / IR analysis, useful for periodic factor review.

Conclusion:

The system had useful pieces, but no clean investing-os-facing contract. It could not yet serve as the disciplined evidence engine we needed.

## 3. Key Boundary Decisions

We decided not to build another loose script.

Instead, we created a unified contract:

```powershell
python -m stock_team.cli tactic-backtest --request "<brain request json>" --out "<evidence packet md>" --json-out "<machine summary json>"
```

Rules:

- Input is a brain-authored `tactic_backtest_request.json`.
- Output is evidence-only.
- No buy / sell / hold language.
- No tactic approval.
- No config mutation.
- No portfolio action.
- No trading permission change.
- No psychological interpretation.

This matches the brain-muscle architecture.

## 4. Files Created in stock_team

Core implementation:

- `D:\gemini\lianghua\stock_team\backtest\tactic_backtest_system.py`

CLI:

- `D:\gemini\lianghua\stock_team\cli.py`
  - added `tactic-backtest`

Contract docs:

- `D:\gemini\lianghua\stock_team\docs\tactic-backtest-contract.md`
- `D:\gemini\lianghua\stock_team\docs\ACTIVE_WORKSPACE.md`

Examples:

- `D:\gemini\lianghua\stock_team\config\tactic_backtest_request.example.json`
- `D:\gemini\lianghua\stock_team\config\tactic_backtest_intraday_ohlcv_request.example.json`
- `D:\gemini\lianghua\stock_team\config\tactic_backtest_rs_intraday_demo_v1.json`

Tests:

- `D:\gemini\lianghua\stock_team\tests\unit\core\test_tactic_backtest_system.py`
- updated `D:\gemini\lianghua\stock_team\tests\unit\core\test_cli.py`

Archive / cleanup:

- `D:\gemini\lianghua\stock_team\archive\cleanup_2026-06-07\README.md`
- `D:\gemini\lianghua\stock_team\archive\cleanup_2026-06-07\ARCHIVE_MANIFEST.md`

## 5. What Is Minimum Viable Now

The system currently supports two data modes:

### `fixture_events`

Use case:

- validate packet shape
- validate train/test segmentation
- validate regime segmentation
- validate statistics

Input provides already-generated trade events.

### `intraday_ohlcv_fixture`

Use case:

- validate event generation from OHLCV bars without network/API dependency

Current implemented trigger:

```text
previous bar closes below VWAP
current bar reclaims VWAP
current volume ratio >= min_volume_ratio
time is within action window
```

Exit logic:

- stop loss
- take profit
- otherwise end of day

Metrics:

- trade count
- win rate
- average return
- average win / loss
- profit factor
- MAE
- MFE
- train/test window metrics
- regime segment metrics

## 6. First Short-Term Tactic Demo

We ran a first demo for:

```text
rs_pullback_rebound_intraday
```

Demo request:

- `D:\gemini\lianghua\stock_team\config\tactic_backtest_rs_intraday_demo_v1.json`

Outputs:

- `D:\gemini\lianghua\stock_team\findings\tactic_backtest_rs_intraday_demo_v1.md`
- `D:\gemini\lianghua\stock_team\findings\tactic_backtest_rs_intraday_demo_v1.json`

Demo result:

- sample count: 3
- win rate: 66.7%
- average return: +1.03%
- average win: +2.29%
- average loss: -1.50%
- profit factor: 3.05
- qqq_uptrend_low_vix + semis_strong: 2 wins
- high_volume_risk_off + semis_weak: 1 loss

Important caveat:

This was only a system-chain demo using fixture bars. It is not a real historical validation result.

## 7. Current Backtest System Structure

```text
investing-os
  defines tactic hypothesis, status, boundaries, and review decision
      |
      v
tactic_backtest_request.json
      |
      v
stock_team CLI: tactic-backtest
      |
      v
backtest/tactic_backtest_system.py
      |
      +-- fixture_events adapter
      |
      +-- intraday_ohlcv_fixture adapter
              |
              v
          event generator
              |
              v
          trade simulation
              |
              v
          metrics / train-test / regime segmentation
              |
              v
Markdown evidence packet + JSON machine summary
      |
      v
investing-os review and possible absorption
```

## 8. Cleanup Done

The user asked to clean `stock_team`.

Codex moved generated / stale files out of active paths into:

```text
D:\gemini\lianghua\stock_team\archive\cleanup_2026-06-07
```

No files were deleted.

Moved categories:

- root runtime state
- old findings outputs
- old reports / historical HTML / markdown reports

Active `reports/` now only keeps:

- `dashboard.html`
- `index.html`
- `latest_evidence_dashboard.json`

Archive decision:

- archived files are not needed for current active workflow
- they can remain archived
- restore only for explicit historical review

## 9. Verification Performed

Targeted tests passed:

```text
7 passed
```

Relevant commands used:

```powershell
python -m pytest tests\unit\core\test_tactic_backtest_system.py tests\unit\core\test_cli.py::test_cli_tactic_backtest_generation tests\unit\core\test_cli.py::test_cli_tactic_backtest_ohlcv_fixture_generation tests\unit\core\test_cli.py::test_cli_help -q
```

Full-suite note:

- full `stock_team` test suite still has unrelated old agent-path failures
- these are from legacy `agents/*` paths and migration state
- do not treat them as tactic-backtest regressions

## 10. Next Steps

Next technical step:

```text
Polygon-first historical adapter
```

It should:

- read Polygon API key through existing stock_team convention
- fetch 1m / 5m aggregates
- cache raw bars with source and freshness metadata
- convert Polygon bars into the normalized OHLCV shape already used by `intraday_ohlcv_fixture`
- reuse the same event generator and evidence packet output

Next research step:

- use real historical bars for `rs_pullback_rebound_intraday`
- test across MU, NVDA, COHR, and later other semis / AI infrastructure names
- segment by QQQ regime, VIX regime, sector strength, and market volume
- avoid approving the tactic until there is real sample size and out-of-sample validation

Next investing-os step:

- after real backtest evidence exists, update:
  - `decision/tactics/validation-records/rs-pullback-rebound-intraday.md`
  - possibly tactic status from candidate to paper_test only if evidence supports it

## 11. Final State

Minimum viable backtest contract is fixed.

It is ready for the next session to add real Polygon data and run the first genuine historical validation.

Do not redesign the contract unless there is a clear reason.
