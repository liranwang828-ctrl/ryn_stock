# Weekly Use Cases

## Purpose

Map the user's recurring weekly usage patterns to `investing-os` entrypoints and optional `stock_team` evidence calls.

The user should start with natural requests.

`investing-os` handles orchestration.

## Use Case Map

| User request | Investing OS entrypoint | Optional stock_team evidence | Output |
|---|---|---|---|
| 做盘前 / 今晚计划 | `execution/pre-market.md` | pre-market packet | trading-day plan, watchlist state, no-trade conditions |
| 盘中看一下 X | `execution/intraday.md` | runtime monitor packet | alert review, decision state update |
| 复盘今天 | `execution/post-market.md` | post-market packet | journal, cognition/decision/execution/evolution updates |
| 复盘某笔交易 | `templates/contextual-trade-review.md` | contextual trade evidence packet | fill review, case candidate, system updates |
| 研究一家公司 | `system/workflows/company-dossier-lifecycle.md` | company research packet | company dossier, thesis/falsification updates |
| 研究一个行业 | `system/workflows/industry-dossier-lifecycle.md` | industry research packet | industry dossier, company priorities |
| 周末总结 | `evolution/learning-loop.md` | weekly summary evidence | system update log, principle candidates, cases |
| 学习我的错误模式 | `cognition/mistake-patterns.md` | trade evidence if needed | bias/mistake/emotional pattern updates |

## Weekly Rhythm

### Trading Days

After work:

- build pre-market plan
- update watchlist state
- define no-trade conditions

Before sleep:

- risk lock
- attention budget check
- open order review

During market:

- low intervention
- respond only to predefined triggers
- use stock_team alerts only as evidence

Morning / daytime:

- post-market review if time allows
- otherwise create catch-up task

### Weekend

Use weekend for:

- weekly journal review
- company research
- industry research
- case promotion
- principle candidate review
- decision state cleanup
- watchlist cleanup

## Evidence Rule

If a use case requires facts, `investing-os` may call `stock_team`.

Every call must produce:

- call log entry
- packet or artifact
- explicit missing-data note

If no evidence is available, the output must say so.

## Experience Output Rule

After each use case, decide what experience should be produced.

Use:

- `evolution/experience-output-map.md`

Minimum ending question:

```text
What should change in cognition, decision, execution, or evolution?
```

If nothing changes, record why.

## Theme Trade Rule

If a weekly use case produces a theme idea, such as AI storage or optical modules, it must become one of:

- company research task
- industry research task
- watchlist candidate
- explicit trade plan

It must not become an intraday action unless the trade plan defines:

- symbol choice
- time horizon
- invalidation
- add rule
- re-entry rule
- attention budget

## User Experience Rule

The user does not need to say "use stock_team."

The user can simply say:

- "复盘"
- "做盘前"
- "看一下 X"
- "研究这个公司"
- "总结这周"

`investing-os` decides whether stock_team evidence is needed.

## Boundary

`stock_team` provides evidence.

`investing-os` updates:

- cognition
- decision
- execution
- evolution
- wiki
- checks
- templates

The user owns final judgment.
