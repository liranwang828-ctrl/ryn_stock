# File Growth Policy / 文件增长治理

## Purpose / 目的

Keep `investing-os` useful as it grows.

Core principle:

```text
Core files stay short.
Detailed evidence lives in reports and lineage.
Dashboard connects them.
```

核心文件保持短小。

详细证据放到复盘报告、案例、血缘记录。

可视化 dashboard 负责连接它们。

## File Size Thresholds / 文件大小阈值

```yaml
soft_limit_lines: 300
hard_limit_lines: 500
```

When a file exceeds the soft limit:

- stop adding long narrative
- convert new entries into index rows or links
- create per-topic files if needed

When a file exceeds the hard limit:

- split it before adding new content
- keep the original file as index / overview
- move detailed entries into subdirectory files

## Core File Rule / 核心文件规则

Core files should contain:

- purpose
- current active rules or patterns
- short summaries
- links to source reports / lineage files
- review status

Core files should not contain:

- long event narratives
- full trade timelines
- raw evidence
- repeated source quotes
- unresolved brainstorms

## Detail File Rule / 细节文件规则

Detailed content belongs in:

- `wiki/journals/`
- `wiki/historical-cases/`
- `system/traceability/lessons/`
- `system/traceability/reports/`
- `decision/tactics/`
- company / industry wiki pages

## Suggested Split Patterns / 推荐拆分模式

### Cognition

```text
cognition/bias-map.md
cognition/biases/
  recent-profit-overconfidence.md
  thesis-instrument-fusion.md
  regime-transfer-error.md

cognition/mistake-patterns.md
cognition/mistakes/
  planless-short-term-entry.md
  repair-desire-after-stop.md
```

### Evolution

```text
evolution/promotion-queue.md
evolution/promotion/
  pending.md
  adopted.md
  rejected.md
  archived/
```

### Checks

```text
system/checks/short-term-trade-checklist.md
system/checks/explainers/
  profit-streak-decomposition.md
  stop-loss-no-trade.md
```

### Traceability

```text
system/traceability/lessons/
system/traceability/reports/
```

## Entry Format Rule / 条目格式

Long explanation should be replaced with:

```yaml
id:
title:
summary:
status:
source:
lineage:
review_due:
```

## Review Cadence / 复查节奏

Run file-growth review:

- after every major review absorption
- before dashboard implementation work
- whenever a core file exceeds 300 lines

Command:

```powershell
./tools/check-file-growth.ps1
```

## Dashboard Rule / 仪表盘规则

The dashboard should read indexes and lineage records.

It should not require core files to store full historical narratives.
