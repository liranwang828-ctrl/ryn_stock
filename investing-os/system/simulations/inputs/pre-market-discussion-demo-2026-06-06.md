# Pre-Market Discussion Demo

Date: 2026-06-06

Purpose:

Simulate the brain-side discussion before calling `stock_team`.

This is not a real trading plan. It is a workflow demo for defining input/output boundaries.

## Simulated User Focus

User wants to focus on:

- MU
- NVDA
- COHR
- INTC

## Brain-Side Questions

### 1. What is the current permission state?

Assumption for demo:

- Permission state: Red / Yellow boundary after major drawdown.
- New short-term and leveraged risk remain restricted.
- Main goal is evidence, risk awareness, and plan discipline.

### 2. Which positions require attention?

Core / strategic:

- NVDA: core AI leader. Intraday attention should be low unless thesis-level evidence changes.

Swing / theme exposure:

- COHR: AI optical infrastructure swing candidate. Needs peer and market confirmation.
- INTC: semiconductor turnaround / tactical exposure. Requires role clarification because it may drift between swing and short-term.

Theme / tactical watch:

- MU: memory / storage cycle exposure. Interesting, but must not become loss-repair trading.

### 3. What is allowed today?

Allowed:

- gather evidence
- observe planned levels
- reduce risk if pre-planned
- research and update thesis
- generate intraday guidance sheet

Restricted:

- new discretionary short-term risk
- leverage expansion
- averaging down to repair loss
- unplanned re-entry after stop-loss

### 4. What does stock_team need to calculate?

For all four symbols:

- gap percentage
- ATR
- relative strength vs QQQ / SOXX
- recent high / low
- volume context
- data freshness

For MU / INTC:

- semiconductor / memory peer context where available

For COHR:

- optical peer context: LITE / AAOI if available

For NVDA:

- core holding context only; no short-term action interpretation

## Brain Decision

Generate a decision sheet for MU / NVDA / COHR / INTC.

`stock_team` may compute candidate factors and rule collisions.

`stock_team` must not decide whether to trade.
