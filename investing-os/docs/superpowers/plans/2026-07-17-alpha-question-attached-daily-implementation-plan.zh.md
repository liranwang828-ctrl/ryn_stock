# Alpha Question Attached Daily Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the DAILY main report explicitly attach to one to three Alpha questions and an active near-term plan, so each day contributes to the V3 Alpha research spine instead of remaining isolated by date.

**Architecture:** Keep the current daily-report-centered workflow intact and add the smallest possible question-attachment structure at three layers: the daily template, the daily workflow contract, and the workflow index. Add one lightweight guidance document so future daily writing uses the same question-driven framing. This is a documentation-first workflow change, not a dashboard or schema rewrite.

**Tech Stack:** Markdown, repository workflow docs, Git

---

## File Structure

- Modify: `investing-os/templates/daily-report.md`
  - Add frontmatter fields for Alpha question attachment and near-term plan reference.
  - Add a new top-level `Alpha Questions / Research Spine` section before the time-sliced sections.
- Modify: `investing-os/system/workflows/daily-report.md`
  - Make Alpha question attachment an explicit workflow rule.
  - Require daily sections to relate evidence back to attached questions and the active near-term plan.
- Modify: `investing-os/system/workflows/README.md`
  - Add the Alpha-question-attached daily rule to the workflow index so the rule is visible from the top-level workflow entry point.
- Create: `investing-os/system/workflows/alpha-question-attached-daily.md`
  - Document the smallest usable operating rule for attaching daily work to the three Alpha questions.
- Verify with:
  - `git diff --stat`
  - `Get-Content -Raw <file>`
  - `rg "alpha_questions|near_term_plan_ref|Research Spine|V3 Alpha mainline" investing-os`

### Task 1: Update the daily template

**Files:**
- Modify: `investing-os/templates/daily-report.md`

- [ ] **Step 1: Inspect the current template before editing**

Run:

```powershell
Get-Content -Raw 'investing-os/templates/daily-report.md'
```

Expected:

- The template shows the current frontmatter with `session_id`, `trading_date`, `session_mode`, `status`, `primary_topics`, `current_structural_context`, `allowed_actions`, and `forbidden_actions`.
- The first body section is `## Pre-Market / 盘前`.

- [ ] **Step 2: Add the new frontmatter fields and the research spine section**

Replace the current template content with:

```md
---
session_id:
trading_date:
session_mode:
status: draft
primary_topics:
  - topic_id:
    topic_name:
    priority: primary
alpha_questions:
  - question_id:
    status:
near_term_plan_ref:
question_status_summary:
  Q1:
  Q2:
  Q3:
current_structural_context:
allowed_actions:
  - observe_only
forbidden_actions:
  - revenge_trade
---

# Daily Report Template

## Alpha Questions / Research Spine

- Attached Questions:
- Near-Term Plan Reference:
- Why These Questions Matter Today:
- Main Validation Target:
- Plan Status Today:

## Pre-Market / 盘前

- Questions:
- Evidence:
- Counter Evidence:
- Hypotheses:
- Confidence:
- Next Validation:
- Effect on Attached Questions:

## Intraday / 盘中

- Questions:
- Evidence:
- Counter Evidence:
- Hypotheses:
- Confidence:
- Next Validation:
- Effect on Attached Questions:

## Review / 复盘

- Questions:
- Evidence:
- Counter Evidence:
- Hypotheses:
- Confidence:
- Next Validation:
- Effect on Attached Questions:

## Trade Log

Use this section only if there were trades.

| Time | Symbol | Action | Qty | Price | Intent | Evidence Ref |
|---|---|---:|---:|---:|---|---|

## Research Links

- Evidence Cards:
- Observation Cards:
- Hypothesis Cards:
- Decision Cards:
- Metrics Updated:
```

- [ ] **Step 3: Read the file back and verify the structure**

Run:

```powershell
Get-Content -Raw 'investing-os/templates/daily-report.md'
```

Expected:

- Frontmatter includes `alpha_questions`, `near_term_plan_ref`, and `question_status_summary`.
- Body includes `## Alpha Questions / Research Spine`.
- Each of the three main sections includes `Effect on Attached Questions`.

- [ ] **Step 4: Commit the template update**

Run:

```powershell
git add -- 'investing-os/templates/daily-report.md'
git commit -m "docs: attach alpha questions to daily report template"
```

Expected:

- A commit is created with only the template change if no other files are staged.

### Task 2: Update the daily workflow contract

**Files:**
- Modify: `investing-os/system/workflows/daily-report.md`

- [ ] **Step 1: Inspect the current workflow text**

Run:

```powershell
Get-Content -Raw 'investing-os/system/workflows/daily-report.md'
```

Expected:

- The workflow already says daily reports are the main report layer.
- The workflow does not yet explicitly require Alpha question attachment.

- [ ] **Step 2: Add Alpha-line rules to the workflow**

Update the file so it includes the following new requirements:

```md
## Rule

Daily reports are now the main report layer.

Detailed journals, trade reviews, company research, research topics, and evidence packets can remain separate, but the daily report links them together by date.

Cards and topic links remain separate artifacts, but the daily report must summarize:

- primary topics
- key questions
- evidence and counter evidence
- next validation

For V3 Alpha mainline daily reports, the report must also:

- attach to at least one active Alpha question
- reference the active near-term operating plan explicitly
- state whether today's work supports, weakens, mixes, or does not inform the attached questions
```

And add a new section after `## Rule`:

```md
## Alpha Mainline Constraint

If a daily report cannot attach to at least one active Alpha question, it may still exist as a daily record, but it does not count as progress on the V3 Alpha research mainline.

Pre-market, intraday, and review sections should not behave like isolated note buckets.

Each section should clarify:

- what evidence appeared
- which attached question it affects
- whether it supports or weakens the current working hypothesis
- whether the active near-term plan remains valid
```

- [ ] **Step 3: Verify the workflow wording**

Run:

```powershell
rg "Alpha Mainline Constraint|attach to at least one active Alpha question|near-term operating plan explicitly" 'investing-os/system/workflows/daily-report.md'
```

Expected:

- All three phrases are found in the workflow file.

- [ ] **Step 4: Commit the workflow update**

Run:

```powershell
git add -- 'investing-os/system/workflows/daily-report.md'
git commit -m "docs: add alpha mainline rules to daily workflow"
```

Expected:

- A commit is created with the daily workflow contract update.

### Task 3: Add the workflow index entry and guidance file

**Files:**
- Modify: `investing-os/system/workflows/README.md`
- Create: `investing-os/system/workflows/alpha-question-attached-daily.md`

- [ ] **Step 1: Inspect the current workflow index**

Run:

```powershell
Get-Content -Raw 'investing-os/system/workflows/README.md'
```

Expected:

- The index already lists pre-market planning, daily report, and topic-driven evidence expectations.

- [ ] **Step 2: Add the top-level index bullets**

Add these lines under `## Core Workflows` near the existing daily-report bullets:

```md
- Daily reports in V3 Alpha must attach to one to three active Alpha questions
- Daily reports must explicitly compare day evidence against the active near-term operating plan
```

And add this line under `## Recommended Starting Points`:

```md
- `alpha-question-attached-daily.md`
```

- [ ] **Step 3: Create the guidance file**

Create `investing-os/system/workflows/alpha-question-attached-daily.md` with:

```md
# Alpha Question Attached Daily

## Purpose

Prevent daily work from becoming isolated by date.

Every V3 Alpha mainline daily report should attach day-level work to one to three active Alpha questions.

## Required Inputs

- active daily session
- active near-term operating plan
- one to three Alpha questions from the current Alpha ledger

## Required Output

One daily report that explicitly states:

- which Alpha questions are attached
- why they matter today
- what evidence appeared
- whether the evidence supports or weakens the current hypothesis
- whether the active near-term plan remains valid

## Allowed Daily Attachment Scope

Use at least one and at most three attached questions.

If today's work cannot attach to at least one active Alpha question, record it as a daily artifact if useful, but do not label it as V3 Alpha mainline progress.

## Writing Rule

Pre-market, intraday, and review should each answer:

1. What changed today
2. Which attached question does it affect
3. Does it support, weaken, or leave unresolved the current hypothesis
4. Does it strengthen or challenge the active near-term plan
```

- [ ] **Step 4: Verify the index and guidance file**

Run:

```powershell
rg "one to three active Alpha questions|near-term operating plan|V3 Alpha mainline" investing-os/system/workflows
```

Expected:

- The new workflow guidance file is found.
- The workflow index and daily workflow file show the new Alpha-question rules.

- [ ] **Step 5: Commit the index and guidance update**

Run:

```powershell
git add -- 'investing-os/system/workflows/README.md' 'investing-os/system/workflows/alpha-question-attached-daily.md'
git commit -m "docs: add alpha question attached daily workflow guidance"
```

Expected:

- A commit is created with the index and guidance changes.

### Task 4: Final verification and handoff

**Files:**
- Verify:
  - `investing-os/templates/daily-report.md`
  - `investing-os/system/workflows/daily-report.md`
  - `investing-os/system/workflows/README.md`
  - `investing-os/system/workflows/alpha-question-attached-daily.md`

- [ ] **Step 1: Check the final diff scope**

Run:

```powershell
git diff --stat HEAD~3..HEAD
```

Expected:

- Only the four intended workflow/template files appear in the implementation range, plus any plan/spec docs already committed earlier.

- [ ] **Step 2: Verify the final rule strings exist**

Run:

```powershell
rg "alpha_questions|near_term_plan_ref|Research Spine|Alpha Mainline Constraint|V3 Alpha mainline" investing-os
```

Expected:

- All required strings are present in the intended files.

- [ ] **Step 3: Read the four files once after all edits**

Run:

```powershell
Get-Content -Raw 'investing-os/templates/daily-report.md'
Get-Content -Raw 'investing-os/system/workflows/daily-report.md'
Get-Content -Raw 'investing-os/system/workflows/README.md'
Get-Content -Raw 'investing-os/system/workflows/alpha-question-attached-daily.md'
```

Expected:

- The wording is consistent across template, workflow, and guidance.
- The daily template is still lightweight enough to use in real daily work.

- [ ] **Step 4: Commit the verification-complete state**

Run:

```powershell
git status --short
```

Expected:

- No unintended staged files from unrelated user work.
- Only the intended workflow/template files and any deliberately created docs were part of the completed implementation sequence.

## Self-Review

Spec coverage check:

- Daily frontmatter additions: covered in Task 1
- New research spine section: covered in Task 1
- Question-oriented pre-market / intraday / review framing: covered in Tasks 1 and 2
- Alpha mainline workflow rule: covered in Task 2
- Explicit near-term plan dependency: covered in Tasks 1, 2, and 3
- Lightweight guidance file: covered in Task 3

Placeholder scan:

- No `TODO`, `TBD`, or unresolved references remain.

Type and naming consistency:

- `alpha_questions`, `near_term_plan_ref`, `question_status_summary`, `Research Spine`, and `V3 Alpha mainline` are used consistently across all tasks.
