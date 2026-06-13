# Post-Market Trade Review Workflow

## Purpose

Turn completed trading activity into cognition growth.

The workflow separates:

```text
stock_team evidence
-> investing-os interpretation
-> user interview
-> lesson extraction
-> absorption decision
-> archive / dashboard / lineage update
```

## Step 0: File Growth Check

Run:

```powershell
& .\tools\check-file-growth.ps1
```

## Step 1: Request Stock Team Evidence

Use:

- `templates/post-market-trade-evidence-request.json`

`stock_team` should use IBKR when connected to collect orders, fills, positions before / after, account P/L, commissions, and margin / leverage exposure if available.

It should use Polygon or approved market data for traded symbols, QQQ / SPY / VIX proxy, sector ETFs, peers, VWAP, and intraday bars.

## Step 2: Receive Evidence Packet

Expected packet:

- `system/data/packets/post-market-trade-evidence-packet.md`

The packet is evidence only.

If `ibkr_connected=false` or fill data is missing, pause and ask the user for broker screenshots or exports.

## Step 3: Brain Review Frame

`investing-os` compares pre-market plan, intraday guidance, stock_team dashboard / manifest, actual orders and fills, and market context at fill timestamps.

Do not conclude lessons before interviewing the user.

## Step 4: User Interview

Use:

- `templates/contextual-trade-review.md`

Ask about original intent, invalidation, add / reduce reasoning, plan alignment, emotion, attention, unrelated holdings, and best pause timestamp.

## Step 5: Create Review Report

Use:

- `templates/post-market-review.md`
- `templates/review-report-standard.md`

Create a report only when there was trading, analysis, or meaningful system learning.

## Step 6: Lesson Extraction

Extract lesson candidates with source event, recommended landing files, severity, and user decision status.

Do not directly update cognition / decision / execution files without absorption decision.

## Step 7: Optional Secondary Evidence

If the interview raises a factual question, request an event reconstruction packet before extracting a durable lesson.

Use:

- `templates/event-reconstruction-request.json`

Expected packet:

- `system/data/packets/event-reconstruction-packet.md`

Common questions:

- Was the missed opportunity actually valid?
- Did the trigger fail quickly after passing?
- Was the signal quality weak despite pass/fail showing pass?
- Did data staleness or slippage change the result?
- Did a rule exception occur before the fill?

## Step 8: Absorption And Archive

Use:

- `system/workflows/packet-absorption.md`
- `system/traceability/schema.md`

Required outputs when absorbed:

- daily report in `wiki/journals/`
- lesson candidates in traceability
- promotion queue update if needed
- target file updates only after user approval
- HTML reading view
- growth dashboard refresh

## Completion Rule

Review is not complete until:

```yaml
evidence_packet_received: yes/no
secondary_event_reconstruction_needed: yes/no
secondary_event_reconstruction_received: yes/no
user_interview_complete: yes/no
review_report_created: yes/no
lessons_extracted: yes/no
absorption_decision_recorded: yes/no
dashboard_html_generated: yes/no
lineage_updated: yes/no
```
