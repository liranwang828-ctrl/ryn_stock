# Daily Report Workflow

## Purpose

Create one daily report when the day contains trading, research, analysis, review, or system changes.

If there was no trading, no research, no analysis, and no system update, skip the daily report.

## Required First Step

Run:

```powershell
& .\tools\check-file-growth.ps1
```

## Rule

Daily reports are now the main report layer.

Detailed journals, trade reviews, company research, research topics, and evidence packets can remain separate, but the daily report links them together by date.

Cards and topic links remain separate artifacts, but the daily report must summarize:

- primary topics
- key questions
- evidence and counter evidence
- next validation

## Flow

```text
day activity
|
collect market context if trading or market analysis happened
|
collect trade log if trades happened
|
collect research log if research happened
|
link the main report to the relevant cards and research topics
|
extract candidate lessons
|
record system absorption
|
update traceability indexes
|
refresh dashboard index
|
generate HTML reading view
```

## Output Location

Use:

```text
wiki/journals/YYYY-MM-DD-daily-report.md
```

After the report enters `system/traceability/reports-index.json`, generate the readable HTML version:

```powershell
.\tools\generate-report-html.ps1 -ReportId <REPORT_ID>
.\tools\generate-growth-dashboard-data.ps1
```

The HTML output should live in:

```text
dashboards/reports/<report-name>.html
```

If a Chinese reading fragment exists in `dashboards/report-fragments/<REPORT_ID>.zh.html`, the HTML view should show it first and keep the original markdown render in a collapsible section.

## Dashboard Behavior

The dashboard should not show every source inline.

It should show:

- date
- report title
- status
- number of lessons
- latest linked files

Clicking a report opens the full daily report.

The dashboard should link to the HTML reading view by default, while preserving the source markdown link inside the HTML report.

Clicking a file node shows the latest lineage entries and links back to the daily reports.

## When To Create

Create if any are true:

- trades happened
- a post-market review happened
- company / industry research happened
- stock_team evidence was absorbed
- a principle, checklist, tactic, or permission state changed
- a meaningful emotional / cognition pattern was identified

Skip if all are false.
