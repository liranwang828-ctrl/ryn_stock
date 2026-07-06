# 旧系统拆解附录 B：System / Workflows / Data / Traceability

日期：2026-07-06

作用：

- 细拆旧系统协议层、数据契约层、schema 层、traceability 层；
- 回答“旧系统真正稳定的骨架到底在哪里”；
- 区分 canonical 契约、示例、历史样本和运行语料。

---

## 1. 总判断

这一块是旧系统最扎实的骨架层。

它已经包含：

- workflow 路由与执行协议；
- checks / gates；
- packet contracts；
- runtime snapshot 契约；
- schemas；
- traceability indexes；
- lesson candidate 层；
- 市场上下文历史语料；
- 一部分模拟输入和历史运行样本。

最重要的判断：

1. `command-router.md`、`intraday-guidance-protocol.md`、`stock-team-orchestration.md`、`brain-muscle-handshake-protocol.md` 这几份文件已经把系统边界写得很成熟。
2. `system/data/packets/*`、`schemas/*`、`runtime-snapshot-contract.md` 说明旧系统不是随意调用 `stock_team`，而是已经在做正式契约化。
3. `system/traceability/*` 说明旧系统已经有教训、报告、文件血缘、能力变化的追踪结构。

---

## 2. 分类代码

- `WF-CANON`：主 workflow / route / protocol
- `WF-STATUS`：当前实施台账
- `CHK`：check / gate
- `DATA-CONTRACT`：数据契约 / packet contract / snapshot contract
- `SCHEMA`：JSON schema
- `TRACE`：traceability 主索引
- `LESSON`：候选教训层
- `DATA-SAMPLE`：历史样例 / demo / 示例
- `MARKET-CORPUS`：市场上下文语料

---

## 3. system/checks

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/system/checks/README.md` | `CHK` | checks 层入口 | `R` |
| `investing-os/system/checks/ai-trading-response-checklist.md` | `CHK` | AI 涉及交易时的总闸门 | `K` |
| `investing-os/system/checks/position-role-checklist.md` | `CHK` | 仓位角色闸门 | `K` |
| `investing-os/system/checks/short-term-trade-checklist.md` | `CHK` | 短线交易闸门 | `K` |
| `investing-os/system/checks/signal-to-action-checklist.md` | `CHK` | signal 不能直接变 action 的闸门 | `K` |
| `investing-os/system/checks/snapshot-approval-checklist.md` | `CHK` | runtime snapshot 批准闸门 | `R` |
| `investing-os/system/checks/why-alignment-checklist.md` | `CHK` | WHY 对齐闸门 | `K` |

判断：

- checks 层并非附属文档，而是系统“防越界”的关键层；
- 这部分应该继续作为主脑硬约束保留。

---

## 4. system/workflows

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/system/workflows/README.md` | `WF-CANON` | workflow 总入口 | `R` |
| `investing-os/system/workflows/trading-day.md` | `WF-CANON` | 跨时区交易日主节奏 | `K` |
| `investing-os/system/workflows/pre-market.md` | `WF-CANON` | 正式盘前流程 | `K` |
| `investing-os/system/workflows/intraday.md` | `WF-CANON` | 盘中流程 | `R` |
| `investing-os/system/workflows/post-market.md` | `WF-CANON` | 盘后流程 | `K` |
| `investing-os/system/workflows/weekend-review.md` | `WF-CANON` | 周末深复盘流程 | `R` |
| `investing-os/system/workflows/signal-processing.md` | `WF-CANON` | 信号处理流程 | `R` |
| `investing-os/system/workflows/runtime-snapshot-approval.md` | `WF-CANON` | snapshot 批准流程 | `R` |
| `investing-os/system/workflows/stock-team-orchestration.md` | `WF-CANON` | 主脑调用肌肉的工作流 | `K` |
| `investing-os/system/workflows/brain-muscle-handshake-protocol.md` | `WF-CANON` | 通用脑-肌握手协议 | `K` |
| `investing-os/system/workflows/command-router.md` | `WF-CANON` | 自然语言请求路由器 | `K` |
| `investing-os/system/workflows/intraday-guidance-protocol.md` | `WF-CANON` | 认知系统投影到盘中指导的协议 | `K` |
| `investing-os/system/workflows/evidence-request-lifecycle.md` | `WF-CANON` | evidence 请求生命周期 | `R` |
| `investing-os/system/workflows/company-research.md` | `WF-CANON` | 公司研究流程 | `R` |
| `investing-os/system/workflows/company-research-rebuild-2026-06-05.md` | `DATA-SAMPLE` | 重建草案/历史说明 | `A` |
| `investing-os/system/workflows/company-dossier-lifecycle.md` | `WF-CANON` | company dossier 生命周期 | `R` |
| `investing-os/system/workflows/industry-dossier-lifecycle.md` | `WF-CANON` | industry dossier 生命周期 | `R` |
| `investing-os/system/workflows/journal-to-principle-promotion.md` | `WF-CANON` | journal → principle 晋升 | `R` |
| `investing-os/system/workflows/packet-absorption.md` | `WF-CANON` | packet 吸收 | `R` |
| `investing-os/system/workflows/post-market-trade-review.md` | `WF-CANON` | 盘后交易复盘流程 | `R` |
| `investing-os/system/workflows/daily-report.md` | `WF-CANON` | 日报工作流 | `R` |
| `investing-os/system/workflows/wiki-update.md` | `WF-CANON` | wiki 更新流程 | `R` |
| `investing-os/system/workflows/DAILY-CONTRACT.zh.md` | `WF-CANON` | 当前新 DAILY 正式契约 | `K` |
| `investing-os/system/workflows/WORKFLOW-STATUS.zh.md` | `WF-STATUS` | 实施追溯台账 | `R` |

判断：

- workflow 层的老资产非常强；
- 当前新 DAILY 是新契约，但它并不是在空白上长出来的，而是立在这些旧协议层之上。

---

## 5. system/data：contracts / packets / schemas / snapshots

### 5.1 核心契约文件

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/system/data/README.md` | `DATA-CONTRACT` | 数据层入口 | `R` |
| `investing-os/system/data/runtime-parameter-map.md` | `DATA-CONTRACT` | 原则 → runtime 参数桥 | `R` |
| `investing-os/system/data/runtime-snapshot-contract.md` | `DATA-CONTRACT` | 主脑向肌肉导出 runtime rule 的边界契约 | `K` |

### 5.2 packet contracts

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/system/data/packets/README.md` | `DATA-CONTRACT` | packets 总说明 | `R` |
| `investing-os/system/data/packets/pre-market-packet.md` | `DATA-CONTRACT` | 盘前 packet contract | `K` |
| `investing-os/system/data/packets/pre-market-context-packet.md` | `DATA-CONTRACT` | Stage 0 市场环境包 contract | `K` |
| `investing-os/system/data/packets/plan-evidence-packet.md` | `DATA-CONTRACT` | Stage 1 evidence contract / example hybrid | `R` |
| `investing-os/system/data/packets/runtime-monitor-packet.md` | `DATA-CONTRACT` | runtime monitor 包 contract | `R` |
| `investing-os/system/data/packets/post-market-packet.md` | `DATA-CONTRACT` | 盘后包 contract | `R` |
| `investing-os/system/data/packets/post-market-trade-evidence-packet.md` | `DATA-CONTRACT` | 盘后事实包 contract | `K` |
| `investing-os/system/data/packets/company-research-packet.md` | `DATA-CONTRACT` | 公司研究包 contract | `R` |
| `investing-os/system/data/packets/industry-research-packet.md` | `DATA-CONTRACT` | 行业研究包 contract | `R` |
| `investing-os/system/data/packets/contextual-trade-evidence-packet.md` | `DATA-CONTRACT` | 情境化交易证据包 contract | `R` |
| `investing-os/system/data/packets/event-reconstruction-packet.md` | `DATA-CONTRACT` | 事件重构包 contract | `R` |
| `investing-os/system/data/packets/tactic-event-summary-packet.md` | `DATA-CONTRACT` | 战术事件总结包 contract | `R` |
| `investing-os/system/data/packets/intraday-dashboard-packet.md` | `DATA-CONTRACT` | dashboard 包说明 | `R` |
| `investing-os/system/data/packets/intraday_snapshot.md` | `DATA-SAMPLE` | intraday snapshot 阅读层样例 | `R` |
| `investing-os/system/data/packets/intraday_snapshot.json` | `DATA-SAMPLE` | intraday snapshot 数据样例 | `A` |
| `investing-os/system/data/packets/ib_event_log.json` | `DATA-SAMPLE` | 原始事件日志 | `A` |
| `investing-os/system/data/packets/drafts/company-research-COHR-2026-06-05.md` | `DATA-SAMPLE` | 草稿 packet | `A` |
| `investing-os/system/data/packets/pre-market-context-packet.2026-06-08.INTC-MU-COHR.v2.md` | `DATA-SAMPLE` | dated example | `A` |
| `investing-os/system/data/packets/pre-market-context-packet.2026-06-08.cognition-v1.md` | `DATA-SAMPLE` | dated example | `A` |
| `investing-os/system/data/packets/plan-evidence-packet.2026-06-08.INTC-MU-COHR.v2.md` | `DATA-SAMPLE` | dated example | `A` |
| `investing-os/system/data/packets/plan-evidence-packet.2026-06-08.cognition-v1.md` | `DATA-SAMPLE` | dated example | `A` |

判断：

- packet 层已经相当成熟；
- 真正应继续接管的是“contract 文件”，不是 dated examples。

### 5.3 schemas

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/system/data/schemas/coordinator-action.schema.json` | `SCHEMA` | 协调器动作 schema | `K` |
| `investing-os/system/data/schemas/degraded-mode.schema.json` | `SCHEMA` | fail-closed 降级模式 schema | `R` |
| `investing-os/system/data/schemas/risk-limits.schema.json` | `SCHEMA` | 风险限制 schema | `R` |
| `investing-os/system/data/schemas/session-state.schema.json` | `SCHEMA` | session state schema | `K` |
| `investing-os/system/data/schemas/signal-interpretation.schema.json` | `SCHEMA` | 信号解释 schema | `R` |
| `investing-os/system/data/schemas/tactical-rules.schema.json` | `SCHEMA` | 战术规则 schema | `R` |
| `investing-os/system/data/schemas/watchlist-metadata.schema.json` | `SCHEMA` | watchlist metadata schema | `R` |

### 5.4 snapshots

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/system/data/snapshots/README.md` | `DATA-CONTRACT` | snapshots 总入口 | `R` |
| `investing-os/system/data/snapshots/changelog.md` | `DATA-CONTRACT` | snapshot 变更记录 | `R` |
| `investing-os/system/data/snapshots/active/README.md` | `DATA-CONTRACT` | active 目录规则 | `R` |
| `investing-os/system/data/snapshots/drafts/README.md` | `DATA-CONTRACT` | drafts 目录规则 | `R` |
| `investing-os/system/data/snapshots/retired/README.md` | `DATA-CONTRACT` | retired 目录规则 | `R` |
| `investing-os/system/data/snapshots/approvals/README.md` | `DATA-CONTRACT` | approvals 目录规则 | `R` |
| `investing-os/system/data/snapshots/approvals/snapshot-approval-record-template.md` | `DATA-CONTRACT` | approval 模板 | `R` |
| `investing-os/system/data/snapshots/approvals/dry-run-tactical-rules-20260605-example.md` | `DATA-SAMPLE` | dry-run example | `A` |
| `investing-os/system/data/snapshots/examples/degraded-mode.example.json` | `DATA-SAMPLE` | schema example | `A` |
| `investing-os/system/data/snapshots/examples/risk-limits.example.json` | `DATA-SAMPLE` | schema example | `A` |
| `investing-os/system/data/snapshots/examples/signal-interpretation.example.json` | `DATA-SAMPLE` | schema example | `A` |
| `investing-os/system/data/snapshots/examples/tactical-rules.example.json` | `DATA-SAMPLE` | schema example | `A` |
| `investing-os/system/data/snapshots/examples/watchlist-metadata.example.json` | `DATA-SAMPLE` | schema example | `A` |
| `investing-os/system/data/snapshots/broker/ibkr-readonly-broker-supplement-us-2026-06-05.md` | `DATA-SAMPLE` | broker supplement | `R` |
| `investing-os/system/data/snapshots/broker/ibkr-readonly-broker-report-local-2026-06-09-us-2026-06-08.md` | `DATA-SAMPLE` | broker sample report | `A` |

---

## 6. system/traceability

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/system/traceability/schema.md` | `TRACE` | report / lesson / file lineage / capability change 的统一 schema | `K` |
| `investing-os/system/traceability/reports-index.json` | `TRACE` | 报告索引 | `K` |
| `investing-os/system/traceability/lesson-index.json` | `TRACE` | lesson 索引 | `K` |
| `investing-os/system/traceability/file-lineage-index.json` | `TRACE` | 文件血缘索引 | `K` |
| `investing-os/system/traceability/capability-history.json` | `TRACE` | 能力变化索引 | `K` |
| `investing-os/system/traceability/lessons/CAND-2026-06-06-001-profit-streak-overconfidence.md` | `LESSON` | 候选教训 | `R` |
| `investing-os/system/traceability/lessons/CAND-2026-06-06-002-short-term-stop-no-trade.md` | `LESSON` | 候选教训 | `R` |
| `investing-os/system/traceability/lessons/CAND-2026-06-06-003-red-permission-state.md` | `LESSON` | 候选教训 | `R` |
| `investing-os/system/traceability/lessons/CAND-2026-06-06-004-thesis-instrument-split.md` | `LESSON` | 候选教训 | `R` |
| `investing-os/system/traceability/lessons/CAND-2026-06-06-005-rs-rebound-tactic.md` | `LESSON` | 候选教训 | `R` |

判断：

- 这是旧系统最像“认知数据库”的一层；
- 未来认知 dashboard 恢复时，必须把这层重新接回去。

---

## 7. system/data/market-context/2026-06-05-major-drawdown

这一组文件内部结构一致：

- 每个标的有 `daily` 和 `5min` JSON；
- 还有 `market-context-summary.md/json`；
- 共同服务于一次重大回撤事件的客观市场环境重建。

具体文件：

- `COHR-5min.json`
- `COHR-daily.json`
- `COHX-5min.json`
- `COHX-daily.json`
- `LITX-5min.json`
- `LITX-daily.json`
- `MU-5min.json`
- `MU-daily.json`
- `MULL-5min.json`
- `MULL-daily.json`
- `MUU-5min.json`
- `MUU-daily.json`
- `NVDA-5min.json`
- `NVDA-daily.json`
- `PLTR-5min.json`
- `PLTR-daily.json`
- `QQQ-5min.json`
- `QQQ-daily.json`
- `SMH-5min.json`
- `SMH-daily.json`
- `SOXX-5min.json`
- `SOXX-daily.json`
- `SPY-5min.json`
- `SPY-daily.json`
- `VIX-5min.json`
- `VIX-daily.json`
- `VRT-5min.json`
- `VRT-daily.json`
- `YAHOO_VIX-5min.json`
- `market-context-summary.json`
- `market-context-summary.md`

统一分类：

- `MARKET-CORPUS`
- 角色：历史事件市场环境证据语料
- 处置：`R`

判断：

- 这些不是主契约文件；
- 但它们是高价值历史证据集，后续做复盘、经验吸收、回放时很值得保留。

---

## 8. 本块最终结论

系统层最成熟的部分不是当前新写出来的 DAILY，而是旧系统早就存在的：

- route / workflow / handshake 协议；
- packet / schema / snapshot contract；
- traceability / lesson / capability history 结构。

换句话说：

> 旧系统真正稳定的骨架在 system layer，不在零散脚本。

