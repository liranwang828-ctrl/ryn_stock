# Traceability Schema / 可追溯系统结构

## Purpose / 目的

Traceability connects:

```text
event / report
-> lesson
-> candidate decision
-> target file
-> adopted rule or observation
-> later review
```

可追溯系统的目的不是自动替用户做决定。

它的目的是保证：

- 每条经验知道来自哪次复盘或研究
- 每条规则知道为什么存在
- 每次系统成长都能反查来源
- 候选经验和正式规则不会混淆
- dashboard 可以展示 investing-os 如何成长

## Core Objects / 核心对象

### 1. Report

A standard review, research, or trading event report.

```yaml
report_id:
report_type: daily_review / trade_review / major_drawdown / research / weekend_review
title:
market_date:
created_date:
source_files:
status: draft / reviewed / absorbed / archived
summary:
market_context:
event_timeline:
decisions:
emotions:
system_failures:
lessons:
open_tasks:
absorption_status:
```

### 2. Lesson

A single extractable learning from a report.

```yaml
lesson_id:
source_report:
source_event:
title:
summary:
area: cognition / decision / execution / risk / tactic / principle / wiki
severity: low / medium / high / critical
status: observed / candidate / pending_user_approval / adopted / rejected / keep_observing
recommended_landings:
  - target_file:
    reason:
    update_type: observation / checklist_rule / permission_rule / principle_candidate / tactic_candidate
user_decision:
adopted_files:
review_due:
```

### 3. File Lineage

Source metadata for a rule, checklist item, pattern, or principle inside a file.

```yaml
target_file:
entry_id:
entry_title:
entry_type: pattern / rule / checklist_item / principle / tactic / note
source_lessons:
  - lesson_id:
    source_report:
    adopted_date:
status: candidate / adopted / retired
review_due:
```

### 4. Capability Change

Score movement for the six-axis radar chart.

```yaml
date:
source_report:
dimension: research / risk / discipline / execution / emotion / review
previous_score:
new_score:
delta:
reason:
related_lessons:
```

## Index Files / 索引文件

Future implementation may generate:

```text
system/traceability/
  reports-index.json
  lesson-index.json
  file-lineage-index.json
  capability-history.json
```

For now, markdown templates may be used manually.

## Absorption Status / 吸收状态

Every major report should end with:

```yaml
report_created: yes/no
lessons_extracted: yes/no
promotion_queue_updated: yes/no
cognition_updated: yes/no
decision_updated: yes/no
execution_updated: yes/no
risk_updated: yes/no
wiki_updated: yes/no
lineage_recorded: yes/no
dashboard_refresh_needed: yes/no
absorption_complete: yes/no
```

## Rule / 规则

A review is not complete until absorption status is explicit.

复盘没有明确吸收状态之前，不能称为结束。
