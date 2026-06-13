# Post-Market Workflow

## Goal

Turn market experience into cognitive improvement.

## Steps

0. If trades happened, request a post-market trade evidence packet from `stock_team` using `templates/post-market-trade-evidence-request.json`.
0.1. Build the external market context packet before interpreting behavior.
1. Run file growth health check: `./tools/check-file-growth.ps1`.
2. Record what happened.
3. Record what I did.
4. Record what I felt.
5. Compare action with plan.
6. Identify deviations.
7. Update thesis if evidence changed.
8. Extract lessons.
9. Update wiki or templates.
10. If the review is archived as a report, update `system/traceability/reports-index.json`.
11. Generate the HTML reading view with `./tools/generate-report-html.ps1 -ReportId <REPORT_ID>`.
12. Refresh dashboard data with `./tools/generate-growth-dashboard-data.ps1`.
13. Run file growth health check again after durable updates.

## Non-Negotiable Market Context Gate

Post-market review must not begin from fills alone.

If trades happened, post-market review must also not begin from user memory alone.

Preferred objective source:

- `stock_team` post-market trade evidence packet using IBKR fills / orders / positions when available

Workflow:

- `system/workflows/post-market-trade-review.md`

Expected packet contract:

- `system/data/packets/post-market-trade-evidence-packet.md`

Before judging any trade, the review must collect or explicitly mark missing:

- intraday K-line for traded symbols
- daily K-line / recent trend for traded symbols
- volume and volume ratio
- SPY / QQQ same-day behavior
- VIX level and direction, or a documented reason VIX is unavailable
- relevant sector ETF behavior, such as SOXX / SMH for semiconductors
- relevant peer / underlying behavior when using leveraged or derivative-like products
- key trade-time market state, not only end-of-day return

If this packet is missing, the review status must be:

```yaml
review_status: blocked_market_context_missing
allowed_analysis:
  - preserve user narrative
  - preserve fills
  - list missing data
forbidden_analysis:
  - final mistake classification
  - permanent lesson extraction
  - principle promotion
```

This gate exists because fills show what the user did, but not what the market was doing.

## Output

Use `templates/post-market-review.md`.

If the review is meaningful enough to preserve, link it from the daily report and add it to the report archive. The user-facing default is the HTML reading view; the markdown remains the source of truth for the system.
