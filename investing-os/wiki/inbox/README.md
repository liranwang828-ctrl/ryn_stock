# Wiki Inbox

The inbox is a temporary landing zone for source assets copied from external projects.

It is not the permanent wiki.

## Purpose

Use this directory to hold imported source material before it is rewritten into durable `investing-os` knowledge.

## Rules

- Do not edit source meaning during the copy step.
- Preserve source path, date, and context.
- Do not copy secrets, `.env` files, account state, raw market data, or generated cache files.
- Do not treat copied material as accepted knowledge.
- Every inbox item must pass WHY alignment before promotion.

## Subdirectories

- `principles/`: source discipline and investing rule documents.
- `cases/`: source historical cases and reflection cases.
- `reports/`: source company and industry research reports.
- `ai/`: source AI usage, controller, prompt, and boundary documents.
- `system/`: source workflow, overview, framework, and operating-process documents.

## Promotion Flow

```text
source asset
|
copy to inbox
|
source metadata added
|
WHY alignment check
|
rewrite into durable format
|
move to permanent wiki / system / agents
|
link back to source manifest
```

## Required Metadata

Each promoted item should record:

- Source project
- Source path
- Source sha256
- Original last modified time
- Imported date
- Imported by
- Target destination
- WHY alignment note

## Stop Rule

If destination is unclear, keep the item in inbox and add a note.

Do not force unclear content into `principles/`.

