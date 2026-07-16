# Runtime State

`investing-os/system/runtime/` stores generated local state for the current
workflow. Runtime files are machine-local and must not be committed.

## Local Runtime Directories

- `sessions/`: coordinator sessions and state transitions.
- `coordinator-decisions/`: generated action decisions.
- `inputs/`: day-specific user, agent, and broker inputs, including Stage 0 bootstrap placeholders such as the daily main report and empty research cards/topics JSON files.
- `packets/`: day-specific Stage 0 and Stage 1 evidence, including topic-driven evidence packets that feed the research database.
- `trade-history/`: private broker execution exports.

Approved rules and long-term traceability remain under `system/data` and
`system/traceability`. If a runtime result becomes durable cognition, move it
through the relevant review workflow instead of committing the runtime copy.

Runtime packets support a main-report plus cards model: the daily report is the durable main report, while card-level artifacts and topic links stay separate until they are promoted through the appropriate workflow. For Stage 0 discussion bootstrap, the runtime input layer may pre-create `{session_id}-daily-main-report.md`, `{session_id}-research-cards.json`, and `{session_id}-research-topics.json` as empty placeholders so the research database flow can start without manual file setup.

Only this README and `sessions/.gitkeep` are tracked from this directory.
