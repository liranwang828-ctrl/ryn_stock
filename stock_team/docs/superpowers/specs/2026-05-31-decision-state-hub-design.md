# Decision State Hub Design

> Date: 2026-05-31
> Scope: Unify stock thesis, factor evidence, backtest evidence, execution state, and LLM orchestration into one decision contract
> Status: Draft approved for planning

## 中文摘要

本设计要解决的问题是：现在系统已经有个股研究、因子、回测、盘前/盘中执行和 dashboard，但它们还没有一个统一的“每日每只股票决策状态”。结果是 dashboard 到处拼 JSON，LLM 也容易在没有硬边界的情况下把叙事、因子和回测混在一起解释。

本轮优先做 **Decision State Hub 决策状态中枢**。它不是新策略，也不改同事的回测系统，而是新增一个规范化的日级输出：`findings/decision_state_{date}.json`。每只股票都按同一结构记录：

- 个股 thesis：核心逻辑、催化、风险、反证、LLM 置信度。
- 因子证据：RS、波动率、价格位置、OBV、情绪等，并标明强弱、样本不足和可信度。
- 回测证据：当前信号组合是否有历史支持、样本外表现、回撤、参数稳定性。
- 执行状态：今日能不能动、入场区、止损、目标、等待条件、仓位上下文。
- LLM 主控裁决：综合证据、指出冲突、降级置信度、生成需要人工复核的问题。

核心原则是先保留结构化证据，不急着压成一个黑箱总分。LLM 负责综合、质疑和解释，但不能绕过缺失因子、缺失回测或风险门控来强行给高 conviction。

可视化先后置，但本设计已经给 dashboard 优化 agent 留好了字段：`primary_action`、`why_now`、`risk_flag`、`evidence_alignment`、`missing_inputs`、`level_map`、`review_questions`。后续 dashboard 可以围绕“当前最重要动作、证据是否一致、风险是否阻断、人工要复核什么”来设计，而不是继续堆信息。

延期待办包括三块：回测/因子可信度强化、LLM 主控纪律、dashboard 数据底座和可视化优化。

### 实施状态

第一版实现范围：新增 `agents/decision_state_hub.py` 生成 `findings/decision_state_{date}.json`，并让 `dashboard_writer.py` 加载该状态进 dashboard context。此阶段不改回测计算、不改 dashboard UI、不改变交易规则。

## Problem

The current trading system has the right major pieces:

- individual stock research through CIO/domain agents
- factor evidence and weekly backtest validation
- intraday and premarket execution helpers
- a dashboard and a dashboard experience optimization loop

The weak point is that these pieces do not yet share one explicit decision state. The dashboard reads from many JSON artifacts, the LLM can explain across evidence without a strict contract, and older confidence scoring collapses unlike evidence into one number too early.

This makes the system harder to inspect, harder to test, and harder to visualize.

## Goal

Create a **Decision State Hub**: a normalized daily per-symbol contract that says, for each stock, what the system believes, what evidence supports it, what contradicts it, what the backtest says, and what action is allowed today.

The first implementation should clarify the decision loop without changing trading rules or touching teammate-owned backtest engines.

## Non-Goals

This project will not:

- change backtest engine behavior
- retune factor parameters
- create a new trading strategy
- automate order placement
- redesign the dashboard UI in this phase
- replace CIO/domain agent research

## Core Contract

Each symbol should have one decision-state object with these sections.

### 1. Identity

- `symbol`
- `date`
- `market_phase`
- `track`: intraday, swing, or portfolio
- `source_freshness`: timestamps and missing-source flags

### 2. Thesis Layer

This captures the individual stock story from CIO/domain analysis.

- `base_thesis`: concise bullish/bearish/neutral thesis
- `key_catalysts`
- `main_risks`
- `contradictions`
- `llm_confidence`
- `llm_confidence_reason`

The LLM may summarize and challenge the thesis. It should not mark a stock actionable when evidence gates fail.

### 3. Factor Evidence Layer

This captures quantitative factor evidence without overclaiming.

- `factor_scores`: RS, volatility, price position, OBV, sentiment catalyst, and future factors
- `factor_direction`: supportive, neutral, or adverse
- `factor_quality`: strong, usable, weak, insufficient
- `factor_notes`

Factor quality must include sample caveats. For example, sentiment catalyst evidence should be marked low-confidence until it has enough observed weeks.

### 4. Backtest Evidence Layer

This captures whether current conditions have historical support.

- `strategy_family`
- `matched_signal_set`
- `in_sample_summary`
- `out_of_sample_summary`
- `drawdown_profile`
- `parameter_stability`
- `backtest_verdict`: supportive, caution, reject, or unavailable
- `backtest_notes`

The first phase should read existing reports and summaries only. It should not modify backtest generation.

### 5. Execution Layer

This captures what the user can do today.

- `current_price`
- `entry_zone`
- `stop_level`
- `target_zone`
- `wait_conditions`
- `action_state`: act, wait, monitor, avoid
- `action_reason`
- `position_context`: no position, starter, full, reduce-watch, exit-watch

Execution state must be explainable from upstream evidence and current market phase.

### 6. LLM Orchestration Layer

This captures the final controller judgment.

- `controller_verdict`
- `controller_confidence`
- `evidence_alignment`: aligned, mixed, conflicting, insufficient
- `required_human_check`
- `blocked_by`
- `summary_for_dashboard`

The controller is a disciplined synthesizer. It can downgrade, require human review, and explain conflicts. It should not bypass missing factor or backtest evidence by narrative confidence alone.

## Data Flow

The first version should be additive:

1. Existing agents continue writing their current outputs.
2. A new builder reads existing artifacts for the current date.
3. The builder emits one normalized decision-state artifact.
4. The dashboard can later read the normalized artifact instead of reassembling the world itself.
5. The dashboard experience agent can review the normalized state for clarity and missing visual affordances.

Recommended artifact:

- `findings/decision_state_{date}.json`

Recommended builder:

- `agents/decision_state_hub.py`

This keeps the change reversible and avoids changing colleague-owned backtest modules.

## Module Boundaries

### Decision State Builder

Responsibilities:

- load known current artifacts
- normalize missing and stale sources
- produce one per-symbol state
- expose pure helper functions that are easy to test

Non-responsibilities:

- fetch new market data aggressively
- run backtests
- rewrite CIO analysis
- change dashboard layout

### Dashboard Consumer

Responsibilities in a later phase:

- prefer `decision_state_{date}.json` when present
- show the decision state clearly
- degrade gracefully when some evidence is missing

Non-responsibilities:

- infer strategy quality from raw backtest files
- perform new scoring logic in the template

### LLM Controller

Responsibilities:

- summarize evidence
- identify conflicts
- mark human-check requirements
- produce a bounded final verdict

Non-responsibilities:

- override hard risk gates
- invent backtest support
- convert insufficient data into high conviction

## Evidence Semantics

Avoid a single opaque score in phase one. Use structured verdicts first:

- `supportive`
- `neutral`
- `adverse`
- `insufficient`
- `stale`

A score can be added later, but only after the evidence fields are stable and reviewable.

## Error Handling

Missing data should be explicit, not silent.

- Missing CIO thesis: thesis layer becomes `insufficient`.
- Missing factor report: factor layer becomes `unavailable`.
- Missing backtest summary: backtest layer becomes `unavailable`.
- Stale artifact: source freshness marks it stale and controller confidence is capped.
- Contradictory evidence: controller marks `evidence_alignment` as `conflicting`.

The builder should still emit a valid decision-state file whenever possible.

## Testing

Initial tests should cover:

- complete symbol state with all layers present
- missing factor evidence
- missing backtest evidence
- stale source detection
- conflicting evidence downgrade
- dashboard-safe summary fields

Testing should use fixtures or temporary directories and avoid network calls.

## Visual Agent Notes

Visual work is deferred, but every decision-state object should be ready for dashboard rendering.

The future dashboard optimization agent should receive:

- `primary_action`: one short action label per symbol
- `why_now`: the top 1-2 reasons the action matters today
- `risk_flag`: none, caution, high, blocked
- `evidence_alignment`: aligned, mixed, conflicting, insufficient
- `missing_inputs`: list of unavailable or stale sources
- `level_map`: entry, stop, target, and wait levels
- `review_questions`: what the human should verify before acting

Suggested future dashboard visual structure:

1. Command strip: current market phase, global risk, and top action.
2. Symbol decision cards: action state, evidence alignment, risk flag, and next check.
3. Evidence drawer: thesis, factors, backtest, execution levels, and contradictions.
4. Review queue: human checks created by the LLM controller.

The visual agent should optimize for decision clarity, not decorative density.

## Deferred Todo Items

### Factor And Backtest Credibility

- Strengthen factor sample-size labeling.
- Separate robust factors from exploratory factors.
- Add parameter stability summaries.
- Keep style-OOS underperformance visible instead of burying it in aggregate returns.

### LLM Controller Discipline

- Define hard rules for when LLM must downgrade confidence.
- Require explicit contradiction handling.
- Prevent narrative-only upgrades when factor or backtest evidence is missing.
- Add controller audit fields for future postmarket review.

### Dashboard Data Foundation

- Move dashboard toward consuming decision state as its primary input.
- Keep generated visual review outputs in ignored findings/report paths.
- Feed dashboard experience agent with normalized task-oriented fields.

### Later Visualization Work

- Build command-center view around action state and evidence alignment.
- Add symbol drilldown sections for thesis, factors, backtest, and execution.
- Add visual indicators for stale or missing evidence.
- Add a review mode where the dashboard self-optimization agent records usability issues against the decision-state fields.

## Success Criteria

The design is successful when:

1. the system can explain each symbol through the same decision-state structure
2. LLM judgment is bounded by explicit evidence and missing-data rules
3. dashboard work has a stable data contract to consume later
4. backtest work remains untouched
5. future optimization can happen layer by layer without making the repo messy again
