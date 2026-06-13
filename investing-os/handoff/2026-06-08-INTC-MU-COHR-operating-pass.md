# 2026-06-08 INTC + MU + COHR Operating Pass

Purpose: preserve the corrected workflow after the user explicitly limited today's focus pool to INTC + MU + COHR, and record the later data-validity correction.

## Critical Correction

Do not treat the earlier leader-subset Stage 1 artifacts as today's official plan.

The assistant initially moved too quickly from Stage 0 to Stage 1 using an agent-selected leader subset. The user corrected the flow:

1. Stage 0 must be requested from `stock_team` first.
2. The brain and user discuss the Stage 0 environment.
3. Only after that discussion may the user/brain confirm the Stage 1 focus pool.
4. `stock_team` then calculates Stage 1 evidence for that confirmed pool.

Today's confirmed pool is:

- INTC
- MU
- COHR

Later correction: this pool can be used for process rehearsal only. It was not formed through the full cognition-system discussion process.

## Data Validity Correction

The Stage 0 packet is not valid as a real 2026-06-08 pre-market environment packet.

Root cause identified during review:

- The packet did not contain true pre-market market data.
- The local market-context cache reused stale / prior-session figures, including QQQ close and return data from 2026-06-05.
- A later external check accidentally used 2026-06-08 post-open / close data, which is also invalid for pre-market reconstruction.

Correct rule:

- Stage 0 must be as-of before the U.S. market open.
- It must include explicit `as_of`, timezone, source, and data window fields.
- If true pre-market evidence is unavailable, Stage 0 must stop with `status: missing_pre_market_data`.
- The system must not backfill a pre-market decision state using post-open or post-close bars.

Implementation guard added in `stock_team` after this review:

- `python -m stock_team.cli market-context` now requires `--as-of` for live Stage 0.
- `--as-of` must be before 09:30 ET on the requested date.
- Live rows must declare `window=pre_market_before_09_30_ET` and matching `as_of_et`.
- Without those rows, the command exits non-zero with `missing_pre_market_data` and does not write the packet.
- `--pre-market-snapshot` now accepts an explicit adapter JSON that can provide those rows.
- The next implementation task is a real Polygon / IBKR pre-market collector that writes this adapter JSON automatically before the open.

Adapter JSON shape:

```json
{
  "as_of_et": "2026-06-08T09:20:00-04:00",
  "window": "pre_market_before_09_30_ET",
  "markets": {
    "QQQ": {"price": 719.2, "prev_close": 705.06, "return_5d": -1.2, "return_20d": 1.4, "volume_ratio": 0.3, "source": "polygon_premarket_snapshot"}
  },
  "themes": {
    "memory": {"proxy": "MU", "return_5d": -2.5, "return_20d": 12.0, "source": "polygon_premarket_snapshot"}
  },
  "catalysts": []
}
```

## Official Files

Stage 0 input:

- `system/simulations/inputs/stage0-pre-market-universe.2026-06-08.INTC-MU-COHR.v2.json`

Stage 1 input:

- `system/simulations/inputs/stage1-pre-market-decision-sheet.2026-06-08.INTC-MU-COHR.v2.json`

Stage 0 packet:

- `system/data/packets/pre-market-context-packet.2026-06-08.INTC-MU-COHR.v2.md`
- standard path synced: `system/data/packets/pre-market-context-packet.md`

Stage 1 packet:

- `system/data/packets/plan-evidence-packet.2026-06-08.INTC-MU-COHR.v2.md`
- standard path synced: `system/data/packets/plan-evidence-packet.md`

Plan:

- `decision/plans/2026-06-08-pre-market-plan.INTC-MU-COHR.v2.md`

Superseded draft:

- `decision/plans/2026-06-08-pre-market-plan.md`

## Evidence State

Stage 0 was generated from `stock_team` market-context evidence but is now considered invalid for real planning. The stale packet showed:

- QQQ: 1D -4.80%, 5D -4.50%, 20D +1.46%, volume ratio 2.4x.
- SPY: 1D -2.58%, 5D -2.50%, 20D +0.82%, volume ratio 1.9x.
- VIXY: 1D +7.23%, 5D +4.38%, 20D -9.46%, volume ratio 2.0x.
- SMH / SOXX were weak over 5D but still positive over 20D.

Stage 1 was generated only for INTC, MU, and COHR. Its status is `fallback_data` because Polygon failed and yfinance sandbox data was used. Because Stage 0 is invalid, Stage 1 is also practice-only.

Stage 1 conclusion is evidence-only:

- Permission state: Yellow / observe-only.
- No pre-authorized actions.
- No trading permission.
- No intraday entry authorization from fallback data.

## Dashboard Status

The HTML intraday evidence dashboard exists and has been opened before:

- `dashboards/latest_evidence_dashboard.html`

Current dashboard status:

- Packet readiness checks were added earlier.
- `--html-out` was added earlier to avoid tests overwriting the live dashboard.
- Core visible labels were localized to Chinese earlier.
- Dashboard must not regenerate Stage 0 or Stage 1 during intraday refresh.
- Dashboard must not run backtests.
- Dashboard remains a facts console: frozen packet readiness, runtime prices, levels, conditions, exposure, data health, warnings, latest manifest, and HTML output.

Remaining dashboard work:

- Revisit after this corrected Stage 0 / Stage 1 flow is stable.
- Ensure the live dashboard reads the official v2 packets for today's focus pool.
- Improve integration into the `investing-os` operating dashboard without letting `stock_team` become a competing user entrypoint.

## Next Correct Step

If continuing intraday today:

1. Keep Stage 0 and Stage 1 frozen.
2. Create or update an intraday guidance artifact only if the brain/user explicitly wants runtime monitoring.
3. Let `stock_team` refresh runtime facts only.
4. Do not backtest inside the trading-day flow.
5. Do not convert observe-only evidence into a trade plan without a fresh user/brain discussion.
