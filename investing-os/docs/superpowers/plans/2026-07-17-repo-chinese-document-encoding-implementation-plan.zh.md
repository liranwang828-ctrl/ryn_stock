# Repo Chinese Document Encoding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal repository-wide Chinese document encoding convention, line-ending normalization rule, and one standard UTF-8 inspection entry point for local review.

**Architecture:** Keep the solution intentionally small and forward-looking. Use one root Git attribute file for text normalization, one operational convention document under `investing-os/`, and one PowerShell helper under `investing-os/tools/` that reads files as UTF-8 for local verification. Avoid bulk rewriting historical files or touching unrelated active work.

**Tech Stack:** Git attributes, Markdown, PowerShell

---

## File Structure

- Create: `.gitattributes`
  - Define Git-side text normalization for repository document and structured-text formats.
- Create: `investing-os/docs/chinese-document-convention.zh.md`
  - Document the repository convention for Chinese markdown/text/json review.
- Create: `investing-os/tools/show-utf8-file.ps1`
  - Provide one standard UTF-8 file inspection entry point.
- Verify with:
  - `Get-Content -Raw <file>`
  - `powershell -ExecutionPolicy Bypass -File ...`
  - `git diff --stat`
  - `git status --short`

### Task 1: Add repository-level text normalization

**Files:**
- Create: `.gitattributes`

- [ ] **Step 1: Confirm there is no existing `.gitattributes`**

Run:

```powershell
Test-Path '.gitattributes'
```

Expected:

- `False`

- [ ] **Step 2: Create the minimal Git attributes file**

Create `.gitattributes` with:

```gitattributes
* text=auto

*.md text
*.txt text
*.json text
*.yml text
*.yaml text
*.ps1 text
```

- [ ] **Step 3: Verify the file content**

Run:

```powershell
Get-Content -Raw '.gitattributes'
```

Expected:

- The file contains the seven lines above.
- No unrelated file patterns are added.

- [ ] **Step 4: Commit the `.gitattributes` change**

Run:

```powershell
git add -- '.gitattributes'
git commit -m "docs: add repository text normalization rules"
```

Expected:

- One commit is created with only `.gitattributes` staged if no other files were intentionally added.

### Task 2: Add the Chinese document convention

**Files:**
- Create: `investing-os/docs/chinese-document-convention.zh.md`

- [ ] **Step 1: Create the convention document**

Create `investing-os/docs/chinese-document-convention.zh.md` with:

```md
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

## Minimal Working Practice

When a Chinese document looks garbled in the terminal:

1. assume the file may still be correct
2. verify the file through the UTF-8 helper
3. only treat it as a broken file if the UTF-8 helper also shows corruption
```

- [ ] **Step 2: Read the convention document back**

Run:

```powershell
Get-Content -Raw 'investing-os/docs/chinese-document-convention.zh.md'
```

Expected:

- The document clearly defines UTF-8, the `.gitattributes` relationship, and the verification rule.

- [ ] **Step 3: Commit the convention document**

Run:

```powershell
git add -- 'investing-os/docs/chinese-document-convention.zh.md'
git commit -m "docs: add chinese document convention"
```

Expected:

- One commit is created for the convention document.

### Task 3: Add the UTF-8 inspection helper

**Files:**
- Create: `investing-os/tools/show-utf8-file.ps1`

- [ ] **Step 1: Create the helper script**

Create `investing-os/tools/show-utf8-file.ps1` with:

```powershell
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$resolved = Resolve-Path -LiteralPath $Path
$content = [System.IO.File]::ReadAllText($resolved, [System.Text.Encoding]::UTF8)
Write-Output $content
```

- [ ] **Step 2: Run the helper against an existing Chinese markdown file**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\journals\2026-07-17-daily-report.md'
```

Expected:

- The output renders the Chinese text from the file through explicit UTF-8 reading.
- If the terminal still has font/display issues, the helper remains the repository-standard read path because it removes ambiguous default decoding behavior.

- [ ] **Step 3: Commit the helper script**

Run:

```powershell
git add -- 'investing-os/tools/show-utf8-file.ps1'
git commit -m "tools: add utf8 file inspection helper"
```

Expected:

- One commit is created for the helper script.

### Task 4: Final verification and handoff

**Files:**
- Verify:
  - `.gitattributes`
  - `investing-os/docs/chinese-document-convention.zh.md`
  - `investing-os/tools/show-utf8-file.ps1`

- [ ] **Step 1: Check the final diff scope**

Run:

```powershell
git diff --stat HEAD~3..HEAD
```

Expected:

- The diff range shows only the intended encoding-rule, convention, and helper files, plus any already-committed spec/plan docs for this work.

- [ ] **Step 2: Verify all three files exist**

Run:

```powershell
Test-Path '.gitattributes'
Test-Path 'investing-os/docs/chinese-document-convention.zh.md'
Test-Path 'investing-os/tools/show-utf8-file.ps1'
```

Expected:

- All three commands return `True`.

- [ ] **Step 3: Re-run the UTF-8 helper on one Chinese file**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\journals\2026-07-17-daily-report.md'
```

Expected:

- The repository now has one standard UTF-8 inspection path for local review.

- [ ] **Step 4: Check repository status**

Run:

```powershell
git status --short
```

Expected:

- No unrelated active user files were staged by this work.
- Only intended files were part of the implementation sequence.

## Self-Review

Spec coverage check:

- Repository-level normalization: covered in Task 1
- Chinese-document convention: covered in Task 2
- Standard UTF-8 inspection entry point: covered in Task 3
- Migration-light boundary: enforced in Tasks 1-4

Placeholder scan:

- No `TODO`, `TBD`, or incomplete implementation references remain.

Type and naming consistency:

- `.gitattributes`, `chinese-document-convention.zh.md`, and `show-utf8-file.ps1` are used consistently across the plan.
