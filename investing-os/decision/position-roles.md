# Position Roles

## Purpose

Define what each symbol is allowed to be.

Position role protects the system from turning long-term holdings into intraday trades or short-term signals into core beliefs.

## Role Types

- `core_long_term`
- `swing`
- `short_term_trade`
- `research_only`
- `no_trade`
- `blocked_pending_review`

## Current Known Roles

| Symbol | Role | Allowed | Forbidden | Review Need |
|---|---|---|---|---|
| MSFT | core_long_term | Hold, thesis review, valuation review | Intraday emotional sell | Company dossier |
| NVDA | core_long_term | Hold, thesis review, valuation review | Intraday emotional sell | Company dossier |
| GOOGL | core_long_term | Hold, thesis review, valuation review | Intraday emotional sell | Company dossier |
| COHR | swing | Company research lifecycle, then swing plan if thesis survives | Re-enter from rebound impulse | Company research packet |
| ORCL | swing | Company research lifecycle, then swing plan if thesis survives | Re-enter from rebound impulse | Company research packet |
| INTC | short_term_trade / swing | Company research lifecycle, then short-term or swing plan if setup survives | Treat as core without thesis | Company research packet + time stop |
| SNXX | blocked_pending_review | Review only | New trade without full plan | Full fill review |

## Update Rule

Every symbol in a plan or watchlist should have a role before action is allowed.

If the role is unclear, default state is `research_only` or `no_trade`, not `short_term_trade`.
