# Phase 3 Report: Principles Absorption

Date: 2026-06-05

## Summary

Five inbox principle sources from `stock_team` were rewritten into durable `investing-os` principle files.

The source files remain unchanged in `wiki/inbox/principles/`.

## Created Files

| Source | Durable principle |
|---|---|
| `wiki/inbox/principles/leveraged_tool_rules_zh.md` | `wiki/principles/PRIN-001-leveraged-tool-discipline.md` |
| `wiki/inbox/principles/hand_feel_trade_zh.md` | `wiki/principles/PRIN-002-hand-feel-trade-limit.md` |
| `wiki/inbox/principles/profit_taking_regret_loop_zh.md` | `wiki/principles/PRIN-003-profit-taking-cooling-period.md` |
| `wiki/inbox/principles/sector_sympathy_catalyst_zh.md` | `wiki/principles/PRIN-004-sector-sympathy-rules.md` |
| `wiki/inbox/principles/vwap_volume_confirmation_zh.md` | `wiki/principles/PRIN-005-vwap-volume-rules.md` |

## Design Choices

- Preserved discipline intent.
- Separated runtime parameters from principles.
- Avoided turning signals into trade commands.
- Added drift audit sections.
- Added falsification or revision conditions.
- Linked related workflows and templates.

## Next Step

Absorb the three historical cases and link them back to the relevant principles.

