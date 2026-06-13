# Command Router Workflow

## Purpose

Map the user's natural requests to the correct `investing-os` workflow and optional `stock_team` evidence call.

The user should not need to know which script, packet, or repository is involved.

## Core Rule

All entries start from `investing-os`.

`stock_team` is called only when the route needs factual evidence.

## Daily Entry Routes

| User Says | Route | Evidence Needed | Output |
|---|---|---|---|
| 做盘前 / 今晚怎么计划 | pre_market | pre-market packet | trading day plan |
| 盘中看 MUU / 现在还能按计划吗 / 看一下 X | intraday_check | runtime monitor packet | permission-aware state check |
| 复盘 SNXX / 复盘这笔交易 / 看这些成交 | trade_review | contextual trade evidence packet | trade review + lessons |
| 盘后复盘 / 今天总结 | post_market | post-market packet + trade packets if needed | daily / post-market report |
| 查 COHR / 研究 ORCL / 每天研究一家公司 | company_research | company research packet | dossier + thesis candidate |
| 研究 AI GPU / 研究存储周期 / 行业结构 | industry_research | industry research packet | industry dossier |
| 周末复盘 | weekly_review | post-market + trade + research packets | weekly report |

## Route Execution

```text
user request
|
classify route
|
check permission state
|
check whether stock_team evidence is needed
|
create evidence request if needed
|
call stock_team only through approved CLI contract
|
record stock-team-call-log
|
absorb packet
|
generate report if archived
|
generate HTML reading view
|
refresh dashboard index
```

## Permission Gate

Before any route that could affect risk:

- check current permission state
- check unresolved risk
- check whether the request is review / research / risk reduction / new risk
- block new short-term or leveraged risk in Red state

## Stock Team Boundary

Allowed:

- fetch data
- normalize fills
- compute indicators
- export evidence packet
- run backtest
- record missing data

Forbidden:

- buy / sell / hold recommendation
- final thesis adoption
- psychological interpretation
- permission state change
- direct user-facing trading workflow

## Required End State

Every route must end with one of:

```yaml
route_result:
  report_created:
  html_created:
  packet_absorbed:
  dashboard_refreshed:
  no_update_reason:
  next_action:
```
