# Repo Chinese Document Encoding Design

## Status

- Date: 2026-07-17
- Status: proposed
- Scope: repository-level document encoding convention and local inspection workflow
- Out of scope:
  - bulk rewriting historical files
  - dashboard rendering changes
  - workflow/business logic changes

## Background

The repository currently has Chinese markdown documents that are stored correctly as UTF-8, but local inspection through default PowerShell commands often displays garbled text.

This creates a repeated failure mode:

- the file itself is fine
- Git can store and diff it
- browser rendering is often fine
- but terminal inspection is misleading

That makes daily review, workflow verification, and research-document maintenance more expensive than they should be.

The root issue is not one single broken file.

It is the absence of repository-level text conventions and the absence of one standard UTF-8 inspection path for Chinese documents.

## Goal

Create the smallest repository-wide solution that:

1. establishes basic text-file normalization rules
2. defines a clear Chinese-document convention
3. gives us one reliable UTF-8 inspection entry point for local review

## Approach Options

### Option A — Rules only

Add repository-level text rules such as `.gitattributes` and stop there.

Pros:

- smallest change
- low risk

Cons:

- does not solve everyday terminal inspection pain by itself

### Option B — Rules plus inspection entry point

Add repository-level text rules, a short Chinese-document convention, and one minimal UTF-8 inspection path.

Pros:

- fixes the recurring practical problem
- still small in scope
- avoids bulk rewrites

Cons:

- adds one more documented utility path to maintain

### Option C — Full cleanup and migration

Add rules and then normalize a large portion of historical Chinese files immediately.

Pros:

- most comprehensive

Cons:

- too wide for the current need
- likely to collide with active user edits
- high diff noise

## Chosen Approach

Use Option B.

This solves the root problem at the repository level without turning the task into a large migration program.

## Design

### 1. Add repository-level text normalization

Create a root `.gitattributes` file.

It should:

- treat common documentation and structured-text formats as text
- normalize line-ending handling through Git
- reduce repeated CRLF/LF churn for markdown-oriented work

The file should be intentionally small and only cover the formats that matter to this repository right now:

- `*.md`
- `*.txt`
- `*.json`
- `*.yml`
- `*.yaml`
- `*.ps1`

### 2. Add a short Chinese-document convention

Add one short repository-facing document under `investing-os/` that defines:

- Chinese documentation should be saved as UTF-8
- terminal inspection should not rely on default `Get-Content` behavior as the final source of truth
- local verification should use the standard UTF-8 inspection entry point

This document should be intentionally operational, not theoretical.

It should help future work on:

- daily reports
- workflow specs
- methodology files
- handoff documents

### 3. Add one standard UTF-8 inspection entry point

Provide a minimal PowerShell-based helper under `investing-os/tools/`.

Its job is simple:

- read one target file as UTF-8
- print it cleanly for terminal inspection

It should not try to solve every encoding problem.

It only needs to become the standard way to inspect Chinese markdown/json/text files during local verification.

### 4. Keep the solution migration-light

Do not bulk rewrite historical documents.

Do not touch unrelated active files.

Do not introduce repo-wide auto-formatting behavior that changes many files at once.

The solution should improve future work immediately while avoiding noisy cleanup churn.

## Intended File Changes

If implementation proceeds, the expected files are:

- `.gitattributes`
- one short Chinese-document convention file under `investing-os/`
- one UTF-8 inspection helper under `investing-os/tools/`

## Validation

Implementation should confirm:

1. the repository has a visible text normalization rule file
2. the Chinese-document convention is easy to find and short enough to use
3. the UTF-8 helper can display an existing Chinese markdown file without garbling
4. no unrelated repository files are rewritten as part of this work

## Risks

### Risk 1: Over-engineering the fix

Mitigation:

Keep the helper single-purpose and avoid building a full encoding framework.

### Risk 2: False sense of cleanup

Mitigation:

State clearly that this is a forward-looking repo convention, not a historical migration.

### Risk 3: New utility is ignored

Mitigation:

Put the usage rule in the convention document and use it in future verification steps.

## Success Criteria

This design is successful if:

1. Chinese repository documents have a clear repo-level convention
2. local UTF-8 inspection has one standard path
3. future daily/spec/handoff review becomes less error-prone
4. the change stays small and does not disturb the user's ongoing work
