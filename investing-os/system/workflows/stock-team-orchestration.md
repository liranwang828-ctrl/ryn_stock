# Stock Team Orchestration Workflow

## Purpose

Define how `investing-os` invokes `stock_team` as an evidence and tooling layer.

The user should start from `investing-os`.

`stock_team` provides data, calculations, reports, and dashboards.

`investing-os` performs cognition, decision, execution, and evolution work.

## Core Rule

Do not ask the user to manually coordinate two systems.

All user-facing entrypoints start from `investing-os`.

`stock_team` must not become a second daily operating interface. It may expose scripts, exporters, dashboards, or monitors for implementation and diagnostics, but normal use is always:

```text
user -> investing-os -> approved stock_team evidence call -> evidence packet -> investing-os absorption
```

The user can say:

- review this trade
- build pre-market plan
- check intraday state
- analyze this company
- summarize the week
- study this industry

Then `investing-os` decides whether `stock_team` evidence is needed.

`stock_team` must not independently:

- tell the user to buy / sell / hold
- start a new trading workflow
- promote a tactic
- change permission state
- bypass `investing-os` call logging and absorption

## Trust Rule

The user does not need to trust that a call happened.

Every `stock_team` call must leave:

- call log entry
- input description
- command or script used
- output artifact path
- data source
- missing data
- how the result was used

Use:

- `integrations/stock-team-call-log.md`

## Flow

```text
user request
|
investing-os identifies use case
|
determine needed evidence
|
call stock_team read-only or request Antigravity implementation
|
record call log
|
receive evidence packet / output artifact
|
packet review
|
update cognition / decision / execution / evolution / wiki
```

After every workflow, run:

- `evolution/experience-output-map.md`

## Use Cases

### Trade Review

User says:

- "复盘 SNXX"
- "帮我看今天这笔交易"
- "这些成交有问题吗"

`stock_team` may provide:

- fills normalization
- 1-minute / 5-minute bars
- VWAP
- SPY / QQQ / VIX context
- underlying / sector context
- late-session behavior

Required packet:

- `system/data/packets/contextual-trade-evidence-packet.md`

`investing-os` updates:

- `cognition/`
- `decision/`
- `execution/`
- `evolution/`
- `wiki/journals/`
- `wiki/historical-cases/`

### Pre-Market Planning

User says:

- "做盘前"
- "今晚怎么计划"
- "帮我看盘前"

`stock_team` may provide:

- pre-market board
- holdings news
- market context
- watchlist scoring
- order/exit sheet data

Required packet:

- `system/data/packets/pre-market-packet.md`

`investing-os` updates:

- `decision/current-watchlist.md`
- `decision/position-roles.md`
- `execution/pre-market.md`
- `templates/trading-day-plan.md`

### Intraday Check

User says:

- "现在还能按计划吗"
- "盯一下 X"
- "X 现在是不是破坏了"

`stock_team` may provide:

- live or delayed price
- VWAP / volume / RSI / relative strength
- SPY / QQQ context
- existing alerts

Intraday monitoring is allowed only as a read-only evidence source after `investing-os` defines:

- monitored symbols
- allowed data fields
- alert conditions
- output packet path
- refresh cadence
- call log requirement
- no-trade-command boundary

Until explicitly approved, runtime / IBKR / polling work remains design-only or diagnostic-only.

Required packet:

- `system/data/packets/runtime-monitor-packet.md`

`investing-os` updates:

- `decision/decision-log.md` if state changes
- `execution/intraday.md` if behavior rule changes
- `wiki/journals/` if review is needed

### Company Analysis

User says:

- "研究 MSFT"
- "今天研究一家公司"
- "帮我看 COHR thesis"

`stock_team` may provide:

- company report
- fundamentals
- recent news
- peer comparison
- generated research draft

Required packet:

- `system/data/packets/company-research-packet.md`

`investing-os` updates:

- `wiki/companies/`
- `decision/portfolio-thesis.md`
- `decision/falsification-map.md`
- `decision/current-watchlist.md`

### Industry Analysis

User says:

- "研究 AI GPU"
- "看一下物理 AI"
- "这个行业谁捕获价值"

`stock_team` may provide:

- industry report
- sector map
- peer comparison
- macro/sector context

Required packet:

- `system/data/packets/industry-research-packet.md`

`investing-os` updates:

- `wiki/industries/`
- `wiki/methodologies/`
- `wiki/companies/` research priorities
- `decision/current-watchlist.md`

### Weekly Summary

User says:

- "周末复盘"
- "总结这一周"
- "本周系统有什么进化"

`stock_team` may provide:

- trades summary
- portfolio movement
- realized P/L
- candidates reviewed
- market regime summary

Potential packets:

- `post-market-packet.md`
- `contextual-trade-evidence-packet.md`
- company / industry packets if research happened

`investing-os` updates:

- `evolution/system-update-log.md`
- `cognition/`
- `decision/`
- `execution/`
- `wiki/journals/`
- `wiki/principles/candidates/`

### Learning Session

User says:

- "学习一家公司"
- "复盘一个错误模式"
- "总结我的弱点"

`stock_team` may provide evidence if data or reports are needed.

`investing-os` owns:

- self-model update
- bias map update
- mistake pattern update
- methodology update
- principle candidate review

## Missing Evidence Rule

If `stock_team` data is unavailable:

- say what is missing
- do not infer facts from absent data
- proceed with subjective review only if clearly labeled
- create follow-up task for evidence collection

## Experience Output Rule

Every orchestration should end with an experience decision:

```yaml
experience_decision:
  cognition_update:
  decision_update:
  execution_update:
  evolution_update:
  wiki_update:
  checklist_update:
  runtime_candidate:
  no_update_reason:
```

Use:

- `evolution/experience-output-map.md`

## Secret Rule

API keys remain in `stock_team`.

`investing-os` must not store API keys, broker credentials, or account secrets.
