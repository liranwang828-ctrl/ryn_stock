# General Developer Rules

> Updated: 2026-05-24

These are the default rules for day-to-day software work with Codex. They are meant to be project-agnostic, so you can reuse them across repos.

---

## 1. Work In Small Slices

- Prefer one coherent change at a time.
- Keep edits close to the request.
- Avoid mixing feature work, refactors, and cleanup in one pass unless they are tightly coupled.
- If the task is large, split it into visible milestones.

## 2. Read Before Writing

- Inspect the code that already exists before changing it.
- Match the repo's style, patterns, and file boundaries.
- Check current diffs and recent history before assuming what changed.
- If a file already has a working pattern, extend it instead of inventing a parallel one.

## 3. Separate Code From Noise

- Keep product code, generated files, logs, and temporary artifacts separate in your mental model.
- Do not commit runtime outputs unless they are intentionally part of the work.
- If the worktree is dirty, classify the dirt before editing anything.
- Treat generated data as disposable unless the user explicitly wants it preserved.

## 4. Verify What You Changed

- Run the narrowest useful check that matches the edit.
- For code, prefer syntax checks or focused tests before broad suites.
- For UI work, open the actual page and confirm the interaction.
- Do not claim completion until the changed path has been exercised at least once.

## 5. Keep Commit Boundaries Clean

- Aim for atomic commits with one clear purpose.
- Keep docs, code, and generated outputs in separate commit groups when possible.
- If a diff becomes hard to explain in one sentence, split it.
- Revert only your own accidental changes, and only when the user wants that.

## 6. Communicate Like A Teammate

- Say what you are changing and why before making edits.
- Call out risks early when a change could have hidden fallout.
- Leave enough context for the next person to continue quickly.
- When a session is interrupted, record the state only if the interruption matters.

## 7. Use The Right Tool For The Job

- Prefer existing repo conventions over fresh abstractions.
- Use browser or app verification when the task touches UI behavior.
- Use focused debugging for bugs, not broad rewrites.
- Use plans when the work is multi-step enough that memory alone is fragile.

## 8. Default Decision Rule

When unsure, choose the option that:

1. Changes the least amount of code.
2. Preserves existing behavior.
3. Is easiest to verify.
4. Leaves the cleanest next step for future work.
