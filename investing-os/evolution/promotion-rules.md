# Promotion Rules

## Purpose

Decide where learning should land.

## Destination Rules

| Learning type | Destination |
|---|---|
| self-understanding | `cognition/` |
| thesis or risk change | `decision/` |
| execution gap | `execution/` or `system/checks/` |
| repeated behavioral rule | `wiki/principles/candidates/` then `wiki/principles/` |
| concrete trade lesson | `wiki/historical-cases/` |
| company understanding | `wiki/companies/` |
| industry structure | `wiki/industries/` |
| method improvement | `wiki/methodologies/` |
| runtime boundary candidate | `system/data/runtime-parameter-map.md` |

## Approval Gate

Not every review insight is automatically part of the user's durable cognition.

Use three levels:

| Level | Meaning | Allowed Without User Approval |
|---|---|---|
| `observation` | factual record, journal note, evidence summary | yes |
| `candidate` | possible pattern, possible rule, possible checklist change | yes, but must be marked pending |
| `adopted` | personal cognition, durable principle, execution rule, risk constraint | no |

Default rule:

- Journals may be written immediately.
- Decision state may be updated conservatively when it prevents action, such as `plan_required` or `blocked_pending_review`.
- Durable cognition, principles, checklist rules, and risk constraints require explicit user approval before being treated as adopted.

Any candidate that affects future behavior must be listed in:

- `evolution/promotion-queue.md`

The user decides whether to:

- adopt
- revise
- reject
- keep observing

## Anti-Overfitting Rule

Do not promote one emotional event into a permanent rule unless it reveals a repeatable pattern or serious safety boundary.

## Anti-Forgetting Rule

Do not leave repeated mistakes buried in journals.

Repeated patterns must create:

- principle candidate
- checklist update
- workflow update
- risk budget update
