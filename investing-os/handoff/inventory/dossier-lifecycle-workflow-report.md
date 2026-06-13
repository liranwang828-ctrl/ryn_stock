# Branch Report: Company And Industry Dossier Lifecycle

Date: 2026-06-05

## Summary

Created lifecycle workflows for turning company and industry research into durable dossiers.

This connects `stock_team` research capabilities with `investing-os` knowledge structures without dumping generated reports into the wiki.

## Created Files

- `system/workflows/company-dossier-lifecycle.md`
- `system/workflows/industry-dossier-lifecycle.md`
- `wiki/companies/company-dossier-template.md`
- `wiki/industries/industry-dossier-template.md`

## Updated Files

- `system/workflows/company-research.md`
- `system/workflows/README.md`

## Design Choices

- A company report is not automatically a thesis.
- An industry note is not automatically a buy list.
- Dossiers move through lifecycle states before becoming active references.
- Company dossiers require value capture, risk, falsification, valuation frame, and monitoring plan.
- Industry dossiers require supply chain, bottlenecks, value capture, counter-thesis, and monitoring plan.

## Company Lifecycle

- research candidate
- dossier draft
- thesis candidate
- active dossier
- invalidated or archived

## Industry Lifecycle

- theme candidate
- industry map draft
- value-capture thesis
- active industry dossier
- obsolete or invalidated

## Next Branch Items

- journal-to-principle promotion workflow
- active snapshot approval dry run

