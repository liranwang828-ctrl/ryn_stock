# Dashboard Premarket To Intraday Experience Loop Design

> Date: 2026-05-31
> Scope: Controlled two-agent dashboard optimization loop for premarket-to-intraday workflow
> Status: Draft for review

## Problem

The dashboard has become hard to optimize by intuition alone. The hardest part is not isolated visual polish, but the comfort of the full path from:

- premarket orientation
- focus confirmation
- symbol drill-down
- intraday monitoring and action readiness

The user wants a multi-agent workflow that can improve this path with less manual effort.

However, a fully autonomous system is risky if it:

- optimizes vague visual preferences instead of real task flow
- makes too many changes per round
- increases intraday load
- touches unrelated systems

The user also provided an important boundary:

> A teammate is actively working on the backtest system. This project must not modify that area.

## Goal

Build a **controlled small closed loop** for dashboard self-optimization:

1. an experience agent uses the real dashboard
2. it identifies concrete usability issues in the premarket-to-intraday workflow
3. an implementation agent fixes only the highest-value issues
4. the experience agent re-checks the same workflow
5. the system reports whether the flow actually became easier

This is intentionally **Version 1 of mode 2**, not full unattended mode 3.

## Non-Goals

This project will not:

- redesign trading strategy logic
- change market polling architecture
- expand dashboard scope into a broader product redesign
- create a fully autonomous continuous optimizer
- modify the backtest system or any teammate-owned backtest work

## Hard Constraints

### 1. No Backtest Interference

The implementation must avoid touching teammate-owned backtest work.

Protected areas include any files or directories clearly related to:

- `backtest`
- `joint_backtest`
- parameter sweeps used for backtesting
- backtest result pipelines
- strategy simulation modules

If a shared utility appears to affect both dashboard and backtest behavior, the safer dashboard-local option should be preferred.

### 2. No Intraday Load Increase

The optimization loop may inspect UI behavior, but it must not introduce:

- broader symbol polling
- higher polling frequency
- hidden auto-refresh logic
- background scans that increase CPU or network load during intraday use

### 3. Small-Batch Change Discipline

Each loop should:

- report at most 3 high-priority issues
- implement at most 2 issues per round
- run one re-check on the same task paths

This prevents fragmentation and runaway micro-optimization.

## Version 1 Review Focus

The first version should optimize only the **premarket-to-intraday workflow**.

It should answer:

- When I open the dashboard, do I know what phase I am in?
- Do I know what the next useful action is?
- Can I confirm today’s focus list without confusion?
- Can I move from premarket context into symbol-level intraday action smoothly?
- Can I return from a symbol detail view to the global intraday view without getting lost?

## Agent Roles

### Experience Agent

The experience agent is a usability scout.

It should:

- open the real dashboard
- follow fixed task paths
- identify friction
- report issues in a strict format

It should not:

- edit code
- invent unrelated features
- judge trading logic quality
- give vague aesthetic commentary

### Implementation Agent

The implementation agent is a constrained executor.

It should:

- take only the highest-value issues from the experience report
- apply focused dashboard changes
- stay within dashboard UX, navigation, and information hierarchy scope

It should not:

- widen scope
- rework unrelated systems
- touch backtest-owned code

### Re-check Stage

After implementation, the experience agent should re-run the same task paths and answer:

- Is the next action clearer?
- Is hesitation reduced?
- Did the number of jumps or mental steps decrease?
- Did any old issue remain unresolved?

## Fixed Task Paths

Version 1 should use exactly these task paths.

### Path A: Premarket Orientation

`Open dashboard -> identify current market phase -> locate the current top action`

### Path B: Premarket Readiness

`Inspect today focus -> determine which symbols are ready -> identify which ones deserve primary attention`

### Path C: Move Into Symbol-Level Action

`Enter a focus symbol detail page -> find price / node / action-relevant information`

### Path D: Return To Global Monitoring

`Return from symbol detail -> recover global context -> decide what to monitor next`

These paths are intentionally narrow. They are enough to expose real friction without opening broad redesign scope.

## Experience Report Format

Each issue must be reported as:

- `Page / Module`
- `Task Path`
- `Problem`
- `Why It Hurts`
- `Severity: High / Medium / Low`
- `Suggested Direction`

Example:

- Page / Module: 今日关注仪表盘
- Task Path: Path B
- Problem: 看到很多状态，但不知道先点哪里
- Why It Hurts: 无法快速完成盘前关注确认，影响后续进入盘中盯盘
- Severity: High
- Suggested Direction: 将“当前推荐动作”抬升为主入口，其余状态降为次级信息

## Loop Output

Each run should produce three artifacts:

1. a structured experience issue list
2. an implementation summary
3. a re-check result summary

The workflow should optimize for clarity over volume.

## Implementation Shape

Version 1 should likely include:

- one driver for running the experience review task paths
- one structured issue output format
- one constrained handoff for implementation
- one re-check pass using the same paths

Whether this is implemented through scripts, structured markdown/json artifacts, or lightweight orchestration helpers should follow existing repo patterns and avoid introducing unnecessary machinery.

## Success Criteria

This project succeeds if:

1. dashboard review becomes concrete instead of intuition-only
2. the premarket-to-intraday path gets easier in repeated checks
3. the loop does not increase intraday system load
4. the loop does not touch the teammate’s backtest work
5. it becomes realistic to extend this controlled mode 2 loop toward a safer mode 3 later
