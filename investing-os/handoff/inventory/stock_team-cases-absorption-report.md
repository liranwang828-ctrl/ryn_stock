# Phase 3 Report: Historical Cases Absorption

Date: 2026-06-05

## Summary

Three inbox case sources from `stock_team` were rewritten into durable `investing-os` historical case files.

The source files remain unchanged in `wiki/inbox/cases/`.

## Created Files

| Source | Durable case |
|---|---|
| `wiki/inbox/cases/2026-06-02_cohr_profit_taking_zh.md` | `wiki/historical-cases/CASE-001-cohr-profit-taking.md` |
| `wiki/inbox/cases/2026-06-02_crdu_fomo_pullback_zh.md` | `wiki/historical-cases/CASE-002-crdu-fomo-pullback.md` |
| `wiki/inbox/cases/2026-06-02_pltr_trend_switch_exit_zh.md` | `wiki/historical-cases/CASE-003-pltr-trend-switch-exit.md` |

## Principle Links Updated

- `PRIN-003-profit-taking-cooling-period.md` links to `CASE-001`.
- `PRIN-002-hand-feel-trade-limit.md` links to `CASE-002`.
- `PRIN-005-vwap-volume-rules.md` links to `CASE-002` and `CASE-003`.

## Design Choices

- Separated decision motivation from execution quality.
- Preserved subjective psychology as review material.
- Avoided converting cases into price-pattern rules.
- Linked cases to principles where the case improves future discipline.

## Next Step

Absorb AI boundary documents from `wiki/inbox/ai/` into `AGENTS.md`, `agents/`, and `system/checks/`.

