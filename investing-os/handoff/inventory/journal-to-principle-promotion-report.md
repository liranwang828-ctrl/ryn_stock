# Branch Report: Journal To Principle Promotion

Date: 2026-06-05

## Summary

Created the workflow for promoting journal observations into principle candidates, active principles, checklists, historical cases, workflows, or rejection.

## Created Files

- `system/workflows/journal-to-principle-promotion.md`
- `templates/principle-candidate.md`
- `wiki/principles/candidates/README.md`

## Updated Files

- `system/workflows/README.md`
- `templates/README.md`
- `templates/journal-entry.md`
- `handoff/phase-tracker.md`

## Design Choices

- One painful event can create a principle candidate.
- Active principles require review.
- Repeated behavior patterns are promoted; one-off regret is not.
- Candidates do not receive `PRIN-*` IDs until promoted.
- Runtime parameters come only after a principle exists and are tracked separately.

## Promotion Options

- promote to active principle
- keep as candidate
- convert to historical case
- convert to checklist
- convert to workflow
- reject

## Note

The existing `2026-06-04` daily review file appears to contain mojibake/encoding corruption.

It should be repaired in a separate cleanup step before relying on it as a long-term source.

## Next Branch Items

- active snapshot approval dry run
- repair corrupted daily review encoding

