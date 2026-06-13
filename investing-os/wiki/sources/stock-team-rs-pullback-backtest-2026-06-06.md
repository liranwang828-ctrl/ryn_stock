# Stock Team RS Pullback Backtest Evidence

```yaml
source_repo: D:\gemini\lianghua\stock_team
source_file: findings/rs_pullback_backtest_report.md
source_script: scripts/run_tactic_backtest.py
received_date: 2026-06-06
used_for:
  - decision/tactics/rs-pullback-rebound-candidate.md
  - evolution/promotion-queue.md
  - system/traceability/lessons/CAND-2026-06-06-005-rs-rebound-tactic.md
status: evidence_received_pending_review
```

## What Was Tested

Historical daily-data test from 2021-01-01 to 2026-06-01 for the RS pullback rebound tactic across NVDA, AMD, COHR, AAOI, SOXX, and related leveraged / benchmark instruments.

## Key Results

- Total trades: 213.
- Win rate: 62.91%.
- Profit factor: 1.33.
- Average win: 7.11%.
- Average loss: -9.05%.
- Max drawdown: -65.67%.
- Mean MAE: 6.65%.
- Max MAE: 28.11%.

## Regime Lessons

- `high_volume_risk_off` had negative expectancy: -0.71% average return.
- `qqq_uptrend_low_vix` had positive expectancy: 1.40% average return.
- `qqq_downtrend_vix_rising` had positive expectancy in this dataset: 1.64% average return.
- `qqq_flat_low_vix` was slightly negative: -0.21% average return.

## Leveraged Product Lessons

Leveraged products showed higher average return but lower reliability and larger adverse movement:

- Leveraged average return: 1.97% versus 1.11% for underlying stocks.
- Leveraged win rate: 52.58% versus 62.91% for underlying stocks.
- Leveraged max MAE: 38.40% versus 28.11% for underlying stocks.

## Interpretation For Investing-OS

This evidence supports keeping the tactic as a restricted candidate, not promoting it into an unrestricted rule.

The strongest confirmed boundary is:

- Disable the tactic when QQQ is in high-volume risk-off.

The leveraged-product result supports stricter instrument-fit controls. Higher upside does not compensate for lower win rate and materially larger adverse excursion when emotional resilience is already impaired.

The `re_entry_stop` result is not automatically adopted as a live permission rule. A mechanical backtest may not capture the user's emotional contamination after a stop-loss. This remains a research question, not a reason to weaken the current no-trade-after-short-term-stop guard.

## Open Questions

- Does the result survive intraday data, realistic fills, spreads, and slippage?
- Does the `re_entry_stop` edge remain after separating mechanical re-entry from emotional revenge / repair trading?
- What exact QQQ volume threshold defines `high_volume_risk_off`?
- Should leveraged products require a separate, smaller position-size model even when the underlying tactic is allowed?
