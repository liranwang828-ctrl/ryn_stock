# Dashboard Experience Agent Checklist Design

> Date: 2026-05-31
> Scope: Dashboard usability review workflow
> Status: Design note for future review workflow

## Problem

The dashboard has grown into a dense operating surface with multiple phases, modules, and decision layers.

The current pain is not just implementation difficulty. It is also review difficulty:

- it is hard to tell which part of the dashboard actually feels awkward
- it is hard to verify whether a change made the flow easier or just changed the shape of the complexity
- ad hoc review tends to drift into vague comments like “a bit messy” or “not intuitive enough”

The user wants a lightweight multi-agent review model where one agent acts like a dashboard user and surfaces concrete usability problems, while another agent implements fixes.

## Goal

Define a stable checklist for a dedicated **experience agent** that reviews the dashboard from a usage perspective.

The checklist should make the review:

- concrete
- repeatable
- useful for implementation handoff
- grounded in actual page use rather than code-only judgment

## Core Principle

The experience agent is a **usability scout**, not a product dictator.

It should:

- open the real dashboard
- follow real user tasks
- identify friction
- report problems in a structured format

It should not:

- redesign strategy logic
- invent major new features without context
- judge investment correctness
- give purely aesthetic opinions detached from usage

## Review Scope

The experience agent should review six dimensions.

### 1. Next Action Clarity

Questions:

- After opening the page, is the next useful action obvious?
- Does the page surface the current highest-priority task?
- Does the user hesitate before knowing where to look or click?

### 2. Information Hierarchy

Questions:

- What is visually emphasized first?
- Is the most prominent information actually the most important?
- Are secondary modules stealing attention from the primary task?

### 3. Workflow Friction

Questions:

- Can the user move through a real task without unnecessary jumps?
- Which step creates hesitation?
- Which action technically exists but feels annoying to use?

Typical tasks:

- confirm today’s focus list
- see whether a report is ready
- inspect a symbol detail page
- decide whether to monitor, wait, or act

### 4. Module Usefulness

Questions:

- Does this module help a real decision right now?
- Is it informative but not actionable?
- Should it stay, shrink, move, or become secondary?

### 5. Market-Phase Fitness

Questions:

- Does the dashboard correctly express what matters during premarket, regular session, postmarket, and closed periods?
- Does the current phase suggest the right type of work?
- Are phase-specific actions mixed together in a confusing way?

### 6. Post-Change Relief

Questions:

- Is the page easier after the change?
- Is hesitation reduced?
- Are the number of clicks or mental steps reduced?
- Is complexity truly lower, or only rearranged?

## Required Output Format

The experience agent should report each issue using this structure:

- `Page / Module`
- `Task Path`
- `Problem`
- `Why It Hurts`
- `Severity: High / Medium / Low`
- `Suggested Direction`

Example:

- Page / Module: 今日关注仪表盘
- Task Path: 盘前确认今日关注标的
- Problem: 能看到很多状态，但不知道先点哪里
- Why It Hurts: 用户无法快速进入当天最高优先级动作
- Severity: High
- Suggested Direction: 将“当前推荐动作”抬为主入口，其余状态降为次级信息

## Workflow Proposal

Use the checklist in a simple loop:

1. Experience agent opens the live dashboard
2. Experience agent runs 2-4 real task paths
3. Experience agent records issues with the required format
4. Implementation agent fixes the highest-value items
5. Experience agent re-checks the same task paths
6. Keep only issues that still cause friction

## Non-Goals

This checklist is not meant to:

- replace trading judgment
- score portfolio quality
- choose research conclusions
- serve as a general code review template

Its role is specifically dashboard usability review.

## Success Criteria

This checklist is successful if:

1. dashboard review comments become concrete instead of vague
2. implementation handoff becomes faster because issues are already structured
3. change verification becomes easier because the same task paths are reused
4. the user spends less energy manually explaining what feels awkward each round
