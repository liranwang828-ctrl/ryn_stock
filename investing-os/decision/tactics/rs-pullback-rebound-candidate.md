# RS Pullback Balance-Point Rebound Tactic

```yaml
status: evidence_received_pending_review
source: wiki/journals/2026-06-05-major-drawdown-review.md
lesson_id: CAND-2026-06-06-005
evidence:
  - wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md
```

## Description

During a pullback or selloff:

```text
identify symbols with strong relative strength
|
wait for balance / stabilization point
|
enter for rebound
|
take partial profit near disagreement / resistance
|
let remaining position run only if structure remains valid
```

## Allowed Only If

- QQQ / SPY are supportive or improving.
- VIX is stable or falling.
- Relevant sector ETF is not breaking down.
- The symbol shows real relative strength versus QQQ and sector.
- Entry, stop, partial-profit, and no-add rules are written before entry.
- Position size is small enough that failure cannot trigger repair trading.

## Disabled If

- QQQ / sector are in high-volume risk-off.
- VIX is rising sharply.
- The user has already taken a short-term stop-loss in the session.
- The purpose is to recover earlier losses.
- A leveraged product is used without a separate leveraged-product plan.

## Required Evidence Before Promotion

- win rate by QQQ regime: received from stock_team daily-data backtest
- expectancy by VIX direction: received from stock_team daily-data backtest
- sector confirmation impact: received from stock_team daily-data backtest
- re-entry after stop-loss impact: received from stock_team daily-data backtest, not yet adopted into live permission
- leveraged product versus underlying comparison: received from stock_team daily-data backtest
- max adverse excursion: received from stock_team daily-data backtest
- recommended disable conditions: received from stock_team daily-data backtest

## Evidence Interpretation

Stock Team's 2026-06-06 daily-data backtest showed positive but fragile expectancy:

- 213 trades.
- 62.91% win rate.
- 1.33 profit factor.
- Average win 7.11%, average loss -9.05%.
- `high_volume_risk_off` expectancy was negative.
- Leveraged products had higher average return but lower win rate and materially larger MAE.

Current interpretation:

- The tactic may remain as a restricted research candidate.
- It is disabled during QQQ high-volume risk-off.
- Leveraged products require a separate instrument plan and smaller risk budget.
- Re-entry after stop-loss remains blocked for the user until emotional contamination and intraday execution are separately studied.
