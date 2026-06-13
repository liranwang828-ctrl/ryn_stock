# Company Research Workflow

## Goal

Train research ability and identify value capture.

## Steps

0. Run file growth health check: `./tools/check-file-growth.ps1`.
1. Understand the business.
2. Map the industry context.
3. Identify value capture.
4. Study financials.
5. Identify moat and risks.
6. Build valuation scenarios.
7. Define falsification conditions.
8. Save the company dossier.
9. If the research becomes a report archive item, update traceability indexes.
10. Generate the HTML reading view with `./tools/generate-report-html.ps1 -ReportId <REPORT_ID>`.
11. Refresh dashboard data with `./tools/generate-growth-dashboard-data.ps1`.
12. Run file growth health check again if the research is absorbed into wiki or decision files.

## Output

Use `templates/company-research.md`.

## Lifecycle

After research, use:

- `system/workflows/company-dossier-lifecycle.md`

Do not treat a company report as an active thesis until it has passed the dossier lifecycle requirements.

The user-facing default for archived research is the HTML reading view. The markdown company dossier remains the source of truth.
