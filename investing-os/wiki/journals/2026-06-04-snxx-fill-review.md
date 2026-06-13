# 2026-06-04 SNXX Fill Review

## Metadata

```yaml
symbol: SNXX
review_date: 2026-06-05
trade_window: 2026-06-04 22:28:37 to 2026-06-05 03:56:56
source: user-provided broker screenshots
related_journal: wiki/journals/2026-06-04-daily-review.md
related_principle: wiki/principles/PRIN-006-cognitive-attention-budget.md
status: reviewed_first_pass
```

## Source Screenshots

- `D:/Wechat/xwechat_files/wxid_9598415986812_47b1/temp/RWTemp/2026-06/9e20f478899dc29eb19741386f9343c8/566ed1284f523086292527bd2ef5ae48.jpg`
- `D:/Wechat/xwechat_files/wxid_9598415986812_47b1/temp/RWTemp/2026-06/9e20f478899dc29eb19741386f9343c8/c1f1833e08dbfdc7a2957ee19df93c1b.jpg`
- `D:/Wechat/xwechat_files/wxid_9598415986812_47b1/temp/RWTemp/2026-06/9e20f478899dc29eb19741386f9343c8/c254029c17aa9f6a309ffdf85c13f20a.jpg`

## Calculation Note

This review uses values visible in the screenshots.

Small differences may exist because screenshots round prices and commissions.

## Fill Table

| Time | Side | Quantity | Price | Visible Amount | Visible P/L |
|---|---:|---:|---:|---:|---:|
| 2026-06-04 22:28:37 | Buy | 100 | 31.44 | 3,144.00 |  |
| 2026-06-04 22:37:27 | Buy | 50 | 30.64 | 1,532.00 |  |
| 2026-06-04 22:42:15 | Buy | 50 | 30.10 | 1,504.85 |  |
| 2026-06-05 01:27:25 | Buy | 100 | 31.14 | 3,114.00 |  |
| 2026-06-05 02:03:43 | Sell | 100 | 31.40 | 3,140.00 | +39.30 |
| 2026-06-05 02:12:13 | Sell | 50 | 31.65 | 1,582.50 | +31.65 |
| 2026-06-05 02:26:34 | Buy | 100 | 31.11 | 3,111.00 |  |
| 2026-06-05 02:40:24 | Buy | 50 | 30.60 | 1,530.00 |  |
| 2026-06-05 03:00:11 | Buy | 100 | 30.19 | 3,019.00 |  |
| 2026-06-05 03:54:01 | Buy | 100 | 29.77 | 2,977.00 |  |
| 2026-06-05 03:55:03 | Sell | 150 | 29.33 | 4,399.00 | -189.25 |
| 2026-06-05 03:56:22 | Sell | 250 | 29.50 | 7,375.50 | -271.16 |
| 2026-06-05 03:56:56 | Sell | 100 | 29.40 | 2,940.00 | -119.17 |

## Summary Statistics

Approximate values from screenshot-visible amounts:

```yaml
total_buy_quantity: 650
total_sell_quantity: 650
estimated_buy_amount: 19931.85
estimated_average_buy_price: 30.66
estimated_sell_amount: 19437.00
estimated_average_sell_price: 29.90
visible_realized_pnl: -508.63
round_trip_notional: 39368.85
```

## Trade Path

```text
initial VWAP / momentum idea
|
first buy at 31.44
|
averaging down to 30.64 and 30.10
|
later buy again at 31.14
|
partial sells at 31.40 and 31.65
|
rebuild/add at 31.11, 30.60, 30.19, 29.77
|
forced exit cluster around 29.33-29.50
|
full exit with visible loss around -508.63
```

## Decision Audit

### What Went Right

- The trade was eventually closed.
- Partial sells at 31.40 and 31.65 show there were chances to reduce exposure profitably.
- The final exit prevented further overnight or next-session exposure.

### What Went Wrong

- Initial entry did not have a recorded thesis.
- Add behavior was not governed by a prewritten add rule.
- The trade kept receiving attention after the original opportunity quality had degraded.
- Partial profitable exits did not end the risk cycle; exposure was rebuilt afterward.
- The final loss came after repeated re-entry/add decisions, not only from the first entry.

## Critical Observation

The key failure was not simply buying high.

The deeper failure was that the trade did not have a stable identity.

It moved through several roles:

```text
signal trade
|
cost-basis management
|
temporary recovery trade
|
rebuilt exposure
|
forced exit
```

Because the role was unstable, risk could not be managed cleanly.

## Cognitive Pattern

This trade confirms:

- FOMO can start the trade.
- Loss aversion can extend the trade.
- Small position framing can hide large attention risk.
- Partial recovery can invite re-risking.
- A signal without thesis cannot be falsified cleanly.

## System Decision

SNXX remains:

```yaml
decision_state: blocked_pending_review
allowed_actions:
  - review fills
  - create historical case
  - extract checklist updates
forbidden_actions:
  - new trade without thesis
  - new trade without invalidation
  - new trade without add rule
  - new trade without attention budget
```

## Follow-Up

- Compare SNXX chart with each fill timestamp.
- Mark which entries were planned vs emotional.
- Review whether any alert or stock_team signal would have changed behavior.
- Confirm whether this pattern appears in the last 20 short-term trades.
- Complete contextual review with market chart and trader interview:
  - `wiki/journals/2026-06-04-snxx-contextual-review.md`
