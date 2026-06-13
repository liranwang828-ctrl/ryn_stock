# Market Mode Action Center Design

> Date: 2026-05-25
> Scope: Dashboard UX and workflow semantics
> Status: Design note for future implementation

## Problem

The dashboard currently presents work as a mostly linear trading-day SOP. This makes the system feel inactive before the market opens or during overnight/closed sessions, even though most non-polling work can still be done.

The intended rule is:

- Intraday polling is the only task that truly depends on regular market hours.
- Research, scans, report generation, price snapshot refreshes, knowledge capture, backtests, watchlist maintenance, and premarket preparation can run during closed, overnight, postmarket, or premarket sessions.

## Goal

Add a market-aware action layer that tells the user what can be done now.

The dashboard should become a phase-aware workbench:

- Market clock explains the current phase and countdown.
- Action Center shows the best available tasks for that phase.
- SOP remains available as progress context, but it should not be the only workflow entry point.

## Market Phases

Use the existing market-clock concept and normalize the product behavior around these phases:

- `closed` / `weekend`: research and preparation mode.
- `overnight`: research and early preparation mode.
- `premarket`: preparation and optional report refresh mode.
- `regular`: live monitoring mode.
- `postmarket`: review and learning mode.

## Action Groups

### Research Mode Actions

Shown during `closed`, `weekend`, and `overnight`.

- Refresh latest price snapshot.
- Scan candidates.
- Collect news and research materials.
- Generate or complete deep research reports.
- Update watchlist and tomorrow focus.
- Record Observation or Decision.
- Run backtests or parameter review.
- Reuse existing premarket reports when available.

### Premarket Actions

Shown during `premarket`.

- Refresh premarket prices.
- Choose between using existing reports or regenerating reports.
- Confirm focus list.
- Generate premarket summary.
- Generate order sheet and strategy nodes.
- Prepare poll but do not require it to start.

### Regular Session Actions

Shown during `regular`.

- Start or stop intraday poll.
- View intraday signals.
- Check entry gate and strategy nodes.
- Record trade execution.
- Refresh dashboard from cache.

### Postmarket Actions

Shown during `postmarket`.

- Run postmarket review.
- Complete Outcome records.
- Update Lessons and KnowledgeNodes.
- Review signal accuracy.
- Prepare next-day watchlist candidates.

## Dashboard Behavior

The Action Center should be near the top of the dashboard, close to the market clock.

It should answer one user question:

> What useful work can I do right now?

The visible actions should be phase-aware, but the system should avoid hiding valid tasks completely. If a task is useful but less relevant in the current phase, it can appear in a secondary group.

Network-heavy actions should be explicit button clicks. The dashboard should not automatically start broad scans or report generation simply because the page is open.

## Data And Load Rules

- Do not increase intraday polling load.
- Dashboard rendering should continue to prefer local cache, snapshots, and existing reports.
- Network or LLM-heavy work should be user-triggered from buttons or agent conversation.
- Closed/overnight scans are allowed, but they should be explicit low-frequency research actions, not background polling.

## Agent Conversation Integration

The dashboard is the operation surface. The agent conversation is the research and interpretation surface.

When the user brings new reading, research notes, holding changes, or judgment updates through conversation, the agent should structure them as:

- `Observation`
- `Decision`
- `Outcome`
- `Lesson`
- `KnowledgeNode`

These records should later feed dashboard learning views, reports, and premarket context.

## Initial Implementation Shape

1. Extend or reuse `/api/market-clock` as the phase source.
2. Add a `Market Mode Action Center` block to the dashboard overview.
3. Map each phase to a small set of primary and secondary action buttons.
4. Wire buttons only to existing endpoints first.
5. Add missing endpoints later for research material collection and journal entry capture.

## Acceptance Criteria

- During closed or overnight sessions, the dashboard clearly shows useful research and preparation actions.
- The user can distinguish "poll unavailable or unnecessary" from "system unavailable".
- Premarket offers both "use existing report" and "refresh/regenerate report" paths.
- Regular session keeps poll controls prominent without increasing server load.
- No broad network or LLM work starts automatically on page load.

