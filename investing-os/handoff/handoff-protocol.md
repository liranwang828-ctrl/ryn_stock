# Handoff Protocol

## Purpose

Handoff documents preserve working context for another collaborator without weakening project boundaries.

## When To Create A Handoff

Create a handoff when:

- A new collaborator takes over.
- The task changes from design to code analysis.
- The project accumulates enough context that a fresh reader may miss the intent.
- External projects such as `lianghua` are involved.

## Required Sections

Each handoff should include:

- Audience
- Objective
- Current state
- Project identity
- File structure
- System boundaries
- User workflow
- Collaboration model
- Immediate next steps
- Risks and non-goals
- Open questions

## Style

Use concise engineering prose.

Do not copy entire source documents when links or summaries are enough.

Do not treat temporary conversation context as durable knowledge unless it changes the system design.

## Boundary Rule

A handoff may describe what should be inspected next.

A handoff should not authorize major architecture changes by itself.

Major changes still require WHY alignment and user approval.

