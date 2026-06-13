# Standard Review Report / 标准复盘报告

## Metadata / 元数据

```yaml
report_id:
report_type:
title:
market_date:
created_date:
status: draft
permission_state_before:
permission_state_after:
source_files:
related_symbols:
```

## 1. Executive Summary / 摘要

One paragraph summary in Chinese and/or English.

## 2. External Context / 外部市场背景

Required before behavior classification.

```yaml
market_context_status: missing / partial / complete
data_sources:
benchmarks:
sector_refs:
vix_status:
key_time_context:
missing_data:
```

Include:

- traded-symbol intraday K-line
- recent daily K-line
- volume / volume ratio
- QQQ / SPY
- VIX or documented unavailable reason
- sector ETF / peers / underlying
- key trade-time context

## 3. Event Timeline / 事件时间线

| Time | Market Context | Action / Event | Thought At The Time | Emotion | Rule Status |
|---|---|---|---|---|---|
| | | | | | |

## 4. Plan vs Action / 计划 vs 行动

```yaml
original_plan:
actual_action:
deviation:
was_thesis_explicit:
was_risk_predefined:
was_add_rule_predefined:
was_exit_rule_predefined:
```

## 5. Emotional Chain / 情绪链条

Record without self-attack.

```text
trigger
|
emotion
|
interpretation
|
action
|
consequence
```

## 6. System Failure / 系统失效

```yaml
primary_failure:
secondary_failures:
rule_missing:
rule_ignored:
data_missing:
permission_state_should_have_been:
```

## 7. Lessons Extracted / 提炼经验

Each lesson should later get a lesson lineage entry.

| Lesson ID | Lesson | Area | Severity | Recommended Landing | Status |
|---|---|---|---|---|---|
| | | | | | |

## 8. Recommended Landings / 推荐落点

| Lesson ID | Target File | Update Type | Reason | Needs User Approval |
|---|---|---|---|---|
| | | | | |

## 9. Capability Changes / 能力变化

Scores are not based on P/L.

| Dimension | Delta | Reason | Source Lesson |
|---|---:|---|---|
| Research | | | |
| Risk | | | |
| Discipline | | | |
| Execution | | | |
| Emotion | | | |
| Review | | | |

## 10. Open Tasks / 待办

```yaml
before_next_session:
stock_team:
investing_os:
user_decision_required:
```

## 11. Absorption Status / 吸收状态

```yaml
report_created: yes
lessons_extracted:
promotion_queue_updated:
cognition_updated:
decision_updated:
execution_updated:
risk_updated:
wiki_updated:
lineage_recorded:
dashboard_refresh_needed:
absorption_complete:
```

## 12. Final Review State / 最终状态

```yaml
review_status:
permission_state:
unresolved_risk:
next_required_action:
permanent_principle_updates:
candidate_updates_recorded:
```
