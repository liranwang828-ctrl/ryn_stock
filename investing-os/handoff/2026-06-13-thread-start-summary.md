# 2026-06-13 Thread Start Summary

> 已归档：当前有效入口是 `CURRENT-CONTEXT.zh.md`。除非任务明确需要历史背景，否则不要从本文件启动。

This file is the short handoff for a fresh thread.
Keep the next session centered on the live operating loop, not the full conversation history.

## One-Line Purpose

`investing-os` is the cognition and decision system.
`stock_team` is the evidence and calculation engine.
We are first making the workflow run cleanly end to end, then improving validation and factors.

## System Meaning

This is not an auto-trading bot.
It is a personal cognition system plus AI support plus disciplined execution.

The user owns:
- worldview
- final judgment
- final risk
- lesson acceptance

The agents own:
- fact gathering
- calculations
- packet production
- dashboard output
- workflow consistency checks

## Division of Labor

### investing-os

Role:
- cognition
- decision framework
- risk and permission logic
- pre-market and intraday interpretation
- post-market review and lesson absorption

### stock_team

Role:
- evidence engine
- market data and cache integration
- backtest runner
- packet producer
- dashboard producer

Must not:
- replace the user's cognition
- issue trading recommendations on its own
- absorb lessons without user confirmation
- become a second brain

## Current Main Goal

First make the workflow stable:

`stage0 -> discussion -> stage1 -> dashboard -> review`

Only after that should we invest heavily in full factor optimization and deeper backtesting.

## Confirmed Rules

- `stage0` gives market and environment facts first.
- `stage1` is created only after `stage0` and cognition discussion.
- Do not jump straight into `stage1`.
- Do not treat intraday as a place for ad hoc backtesting.
- Backtest is for validating a tactic or factor outside active trading.
- For now, assume `stage0` and `stage1` do not refresh intraday.
- Keep the workflow simple before making it smart.

## Current Pain Points

- Polygon intraday 1m bars can be slow or missing.
- Dashboard has had fallback and stage-packet readiness issues.
- Earlier runs sometimes mixed open-day data into pre-market flow.
- The user is specifically worried about us taking the wrong entry point again.

## Backtest State

The backtest system exists as a bridge from tactic hypothesis to validation.
It is currently more useful as a validation layer than as a live trading engine.

Current direction:
- start with macro `stage0` factor validation
- use environment factors such as `QQQ`, `SPY`, `IWM`, `VIXY`
- combine cognition and catalyst logic for entry judgment
- do not jump straight to fine-grained intraday entry optimization

Current concern:
- the system still needs better windows, regime splits, Sharpe-style reporting, and relative-to-QQQ framing
- the current outputs are not yet detailed enough for a confident final trading rule

## Workflow That Should Be Preserved

1. `stock_team` produces factual `stage0`
2. User and cognition system discuss the facts
3. `stage1` is created from that discussion
4. Dashboard shows the live operating state
5. Post-market review turns outcomes into lessons
6. Lessons only enter the system after user confirmation

## What To Read First

If the next thread needs orientation, read these first:

- `C:\Users\rriww\Documents\STOCK\investing-os\handoff\2026-06-07-system-overview-for-next-agent.md`
- `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\brain-muscle-handshake-protocol.md`
- `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\stock-team-orchestration.md`
- `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\trading-day.md`
- `C:\Users\rriww\Documents\STOCK\investing-os\system\workflows\intraday.md`
- `C:\Users\rriww\Documents\STOCK\investing-os\handoff\2026-06-07-backtest-system-session-record.md`

## Next Best Step

Keep the next thread narrow.
Start with the current workflow shape, then decide whether to fix `stage0`, `stage1`, dashboard readiness, or backtest validation first.
