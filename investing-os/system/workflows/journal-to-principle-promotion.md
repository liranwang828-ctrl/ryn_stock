# Journal To Principle Promotion Workflow

## Purpose

Define when a journal observation should become a principle, checklist, historical case, or only remain a journal note.

The goal is to prevent two opposite errors:

- letting important repeated mistakes disappear in journals
- turning every emotional observation into a permanent rule

## Core Rule

A journal insight becomes a principle only when it describes a repeatable behavioral, cognitive, or risk pattern.

One painful event can create a principle candidate.

It should become an active principle only after review.

## Promotion Path

```text
journal observation
|
file growth health check
|
pattern candidate
|
principle candidate
|
active principle / checklist / historical case / reject
```

Before promoting or moving any durable lesson, run:

```powershell
./tools/check-file-growth.ps1
```

## Step 1: Extract Observation

From a journal or post-market packet, identify:

- what happened
- what decision error or high-quality judgment appeared
- what emotion or bias was involved
- what system boundary failed or worked
- what could happen again

## Step 2: Classify The Observation

Use this map:

| Observation type | Destination |
|---|---|
| one-time narrative | keep in `wiki/journals/` |
| concrete trade lesson | `wiki/historical-cases/` |
| repeatable behavior rule | `wiki/principles/` candidate |
| execution guardrail | `system/checks/` |
| workflow gap | `system/workflows/` |
| template gap | `templates/` |
| runtime-measurable boundary | `system/data/runtime-parameter-map.md` candidate |

## Step 3: Create Principle Candidate

Use:

- `templates/principle-candidate.md`

Store candidates in:

- `wiki/principles/candidates/`

Do not assign a final `PRIN-*` ID until promoted.

## Step 4: Candidate Review Questions

Ask:

1. Is this a repeatable pattern?
2. Does this improve cognition or discipline?
3. Does it reduce future risk?
4. Can it be abused or over-applied?
5. What would falsify or revise it?
6. Does it belong as a principle, checklist, case, or workflow instead?

## Step 5: Promotion Decision

Use one:

- `promote_to_active_principle`
- `keep_as_candidate`
- `convert_to_case`
- `convert_to_checklist`
- `convert_to_workflow`
- `reject`

## Step 6: Active Principle Requirements

Before creating a `PRIN-*` file, require:

- core assertion
- why it exists
- trigger conditions
- execution constraints
- what it forbids
- falsification or revision conditions
- drift audit
- related journal or case source
- related workflow/checklist if applicable

## Step 7: Runtime Parameter Candidate

Only after a principle exists, decide whether it has runtime parameters.

Runtime parameters should be added to:

- `system/data/runtime-parameter-map.md`

Do not put unvalidated hard numbers directly into the principle unless they are explicitly manual guardrails.

## Rejection Criteria

Reject or avoid promotion when:

- the lesson is just regret after a bad outcome
- the rule would overfit one trade
- the observation is not repeatable
- the rule would block valid planned execution
- the rule increases emotional pressure
- the rule turns AI into decision maker

## Review Cadence

Review principle candidates:

- during weekend review
- after three related journal mentions
- after a major repeated mistake
- before converting any candidate into runtime parameters

## Safety Boundary

Principles guide judgment and discipline.

They do not authorize trades.

They can restrict actions, require review, or create checklists, but final risk remains human-owned.
