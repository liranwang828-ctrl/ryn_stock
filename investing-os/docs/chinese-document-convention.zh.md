# Chinese Document Convention

## Purpose

Keep Chinese repository documents readable, reviewable, and low-noise across Git, terminal inspection, and browser rendering.

## Repository Rule

- Chinese markdown, text, and structured documents should be saved as UTF-8.
- Repository text normalization is handled through the root `.gitattributes`.
- This convention is forward-looking and does not require bulk rewriting historical files.

## Verification Rule

Do not treat default PowerShell `Get-Content` rendering as the final source of truth for Chinese documents.

When checking Chinese markdown, json, txt, yaml, or similar files locally, use the UTF-8 inspection helper under `investing-os/tools/`.

## Recommended Scope

This rule applies especially to:

- daily reports
- workflow documents
- methodology files
- handoff files
- specs and plans

## Local File Link Rule

When referencing a local workspace file for Codex app reading:

- use a direct absolute local path
- do not prepend synthetic prefixes such as `/abs/path/`
- do not mix markdown file-link style with browser `file:///` URL style

Correct browser-openable example:

- `file:///C:/Users/rriww/Documents/STOCK/investing-os/dashboards/reports/TSM-reality-layer-report.html`

Incorrect example:

- `file:///C:/abs/path/C:/Users/rriww/Documents/STOCK/investing-os/dashboards/reports/TSM-reality-layer-report.html`

Interpretation:

- markdown file links are for Codex message rendering
- `file:///` URLs are for browser address bars
- they are not interchangeable

## Minimal Working Practice

When a Chinese document looks garbled in the terminal:

1. assume the file may still be correct
2. verify the file through the UTF-8 helper
3. only treat it as a broken file if the UTF-8 helper also shows corruption
