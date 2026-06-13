# Packet Absorption Workflow

## Purpose

Convert incoming packets into the right `investing-os` destination.

Packets may come from:

- `stock_team`
- ChatGPT
- manual research
- broker/exported review notes

Packets are not durable knowledge by default. They are review envelopes.

## Core Rule

No packet should enter the wiki, journal, principles, cases, templates, or runtime snapshots without an absorption decision.

## Flow

```text
incoming packet
|
file growth health check
|
packet review
|
absorption decision
|
destination update or rejection
|
file growth health check
|
follow-up task
|
if report archived: render HTML and refresh dashboard index
```

Before and after durable absorption, run:

```powershell
./tools/check-file-growth.ps1
```

If absorption creates or updates a report archive entry, also run:

```powershell
./tools/generate-report-html.ps1 -ReportId <REPORT_ID>
./tools/generate-growth-dashboard-data.ps1
```

## Step 1: Identify Packet Type

Supported packet contracts:

- company research
- industry research
- pre-market
- post-market
- runtime monitor

If the packet type is unclear, keep it in review and do not absorb it.

## Step 2: Separate Fact, Inference, And Suggestion

Classify each important claim:

- fact
- inference
- action suggestion
- emotion / behavior observation
- system update candidate

Facts can support wiki updates.

Inferences require review.

Action suggestions require discipline checks.

## Step 3: Run WHY And Boundary Checks

Ask:

1. Does this improve cognition?
2. Does this improve discipline?
3. Does this improve risk control?
4. Does this preserve human final judgment?
5. Does this avoid turning AI or signals into decision makers?

If no, reject or keep as temporary context.

## Step 4: Choose Destination

Use this map:

| Packet content | Destination |
|---|---|
| daily execution, emotion, mistakes | `wiki/journals/` |
| durable behavioral rule | `wiki/principles/` |
| concrete mistake or success pattern | `wiki/historical-cases/` |
| company thesis / dossier | `wiki/companies/` |
| industry structure / value capture | `wiki/industries/` |
| repeatable method | `wiki/methodologies/` |
| checklist improvement | `system/checks/` |
| workflow improvement | `system/workflows/` |
| template improvement | `templates/` |
| runtime parameter candidate | `system/data/runtime-parameter-map.md` |
| not durable yet | `wiki/inbox/` or reject |

## Step 5: Decide Absorption Status

Use one:

- `absorb_now`: update destination immediately
- `split`: packet contains multiple durable pieces
- `keep_in_inbox`: useful but not mature enough
- `reject`: not useful, duplicated, unsupported, or outside WHY
- `request_more_data`: cannot decide without missing evidence

## Step 6: Write Review Record

Use:

- `templates/packet-review.md`

Store important packet review records in:

- `wiki/sources/`

Short-lived reviews may stay in working notes until absorbed or rejected.

## Step 7: Update Destination

When absorbing:

- preserve source reference
- avoid dumping raw generated text
- rewrite into `investing-os` voice and structure
- link related principles, cases, journals, or templates
- keep uncertainty explicit

## Step 8: Create Follow-Up Tasks

Common follow-ups:

- review trades
- inspect source data
- create company dossier
- create industry map
- promote principle candidate
- update checklist
- update runtime parameter map
- ask Antigravity for a `stock_team` packet producer

## Step 9: Render User Reading View

When a packet review, research packet, evidence source, or daily report becomes part of the report archive:

- keep markdown / JSON as the system source of truth
- generate the HTML reading view for the user
- prefer a Chinese reading fragment if available
- keep source markdown linked inside the HTML
- refresh dashboard indexes

## Rejection Criteria

Reject or do not absorb when:

- source is unclear
- facts cannot be separated from speculation
- packet creates action pressure without thesis
- packet conflicts with WHY
- packet encourages automated decision making
- packet is generated output with no durable learning
- packet duplicates existing wiki without adding clarity

## Safety Boundary

Packet absorption never authorizes trades.

Even a high-quality packet can only create:

- knowledge update
- plan draft
- checklist update
- review task
- runtime parameter candidate

Final decision and risk remain human-owned.
