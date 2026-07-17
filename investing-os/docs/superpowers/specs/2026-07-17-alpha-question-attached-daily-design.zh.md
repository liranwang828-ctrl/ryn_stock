# Alpha Question Attached Daily Design

## Status

- Date: 2026-07-17
- Status: proposed
- Scope: DAILY main report layer only
- Out of scope:
  - Dashboard rendering changes
  - Evidence card schema redesign
  - Hypothesis card schema redesign

## Background

Current daily work can still become isolated by date.

Even when pre-market, intraday, and review content is produced, the report can still answer:

- what happened today

but fail to answer:

- which long-horizon question today's work is serving
- whether today's evidence supports or weakens the current near-term plan
- whether confidence changed for the active research line

V3 Alpha has already narrowed the current research spine to three active questions:

1. AI profits ultimately settle where
2. Whether hyperscaler capex is truly slowing
3. Whether inference creates the second round of hardware demand

The daily report should become the main attachment layer between day-level activity and these active questions.

## Goal

Make every Alpha-line daily report explicitly attach to one to three active research questions, so daily work stops operating as isolated notes and instead accumulates along a stable research spine.

## Approach Options

### Option A1 — Light structure, strong constraint

Keep the current daily report architecture, but add mandatory Alpha question attachment and question-oriented summaries.

Pros:

- smallest change surface
- easy to adopt immediately
- aligns with "daily report is main report layer"

Cons:

- dashboard will not immediately visualize the new structure
- cards remain loosely coupled for one more phase

### Option A2 — Daily plus dashboard

Add Alpha question attachment to daily and update dashboard to show question linkage and confidence changes.

Pros:

- stronger visibility
- easier daily reading experience

Cons:

- wider change surface
- higher chance of getting distracted by frontend presentation details

### Option A3 — Full question-driven data model

Unify daily, evidence, and hypothesis around one research-database model immediately.

Pros:

- most structurally complete

Cons:

- too heavy for the current phase
- delays actual daily usage

## Chosen Approach

Use Option A1 first.

The system should first ensure that every daily report has a stable attachment to one to three Alpha questions.

After that runs reliably in real daily usage, later work may extend the same structure into dashboard and cards.

## Design

### 1. Daily frontmatter additions

The daily template frontmatter should add explicit question-attachment fields:

- `alpha_questions`
- `near_term_plan_ref`
- `question_status_summary`

`alpha_questions` contains one to three active Alpha question identifiers.

`near_term_plan_ref` points to the currently active near-term operating plan document.

`question_status_summary` is a compact status map indicating whether today's work is:

- supporting
- weakening
- mixed
- uninformative

for each attached question.

### 2. New fixed section near the top of the daily report

Add a new top-level section before the time-sliced sections:

`## Alpha Questions / Research Spine`

This section should state:

- which Alpha questions are attached today
- why they are the right questions for today's session
- what the most important validation target is for today
- whether today's session is expected to support, challenge, or refine the near-term plan

This section becomes the bridge from long-horizon research to day-level execution.

### 3. Pre-market / intraday / review are no longer free-floating

Each of the three main sections should continue to record:

- evidence
- counter evidence
- hypotheses
- confidence
- next validation

But they should do so in relation to the attached Alpha questions rather than as isolated observations.

In practice, each section should answer:

- what new evidence appeared
- which attached question it affects
- whether it supports or weakens the current working hypothesis
- whether confidence changed

### 4. Workflow rule update

The daily workflow should formally state:

- if a daily report cannot attach to at least one active Alpha question, it does not enter the V3 Alpha mainline

This does not mean the day is invalid.

It means the report is outside the current Alpha research spine and should not be mistaken for progress on the active research program.

### 5. Near-term operating plan becomes an explicit upstream dependency

The active near-term operating plan should be referenced directly from the daily report rather than only being remembered conversationally.

This ensures each day can answer:

- does today's evidence support the current near-term plan
- does today's evidence weaken the current near-term plan
- does the plan need revision before the next session

## Intended File Changes

If implementation proceeds, the expected first files are:

- `investing-os/templates/daily-report.md`
- `investing-os/system/workflows/daily-report.md`
- `investing-os/system/workflows/README.md`
- one new Alpha question attachment guidance file under `investing-os/system/workflows/`

## Testing / Validation

This phase is documentation and workflow-structure only.

Validation should confirm:

1. the new template makes Alpha question attachment explicit
2. the workflow text requires at least one active Alpha question
3. the near-term plan becomes an explicit reference, not implicit memory
4. the resulting structure is still light enough for real daily use

## Risks

### Risk 1: Too much structure too early

Mitigation:

Keep the change at the daily main-report layer only.

### Risk 2: Daily becomes repetitive

Mitigation:

Use compact question status summaries and avoid duplicating the same text in each section.

### Risk 3: Questions become a checkbox ritual

Mitigation:

Require the report to state whether today's evidence actually changed support, weakness, or confidence rather than only listing the question ID.

## Success Criteria

This design is successful if:

1. every Alpha-line daily report clearly links to one to three active questions
2. daily analysis no longer reads like isolated day notes
3. the near-term plan is explicitly checked against daily evidence
4. later dashboard and card work can reuse this structure without redesigning daily again
