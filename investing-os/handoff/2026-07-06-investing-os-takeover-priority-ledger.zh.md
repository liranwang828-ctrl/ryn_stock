# `investing-os` 接管优先级清单

日期：2026-07-06
状态：执行排序台账

依据：

- [`2026-07-06-old-system-asset-audit.zh.md`](./2026-07-06-old-system-asset-audit.zh.md)
- [`decisions/2026-07-06-old-system-reuse-principle.md`](./decisions/2026-07-06-old-system-reuse-principle.md)
- [`2026-07-06-recent-work-disposition-ledger.zh.md`](./2026-07-06-recent-work-disposition-ledger.zh.md)

目的：

1. 把项目从“审计阶段”推进到“接管阶段”。
2. 明确在“`investing-os` 默认全量优先复用”原则下，哪些资产先恢复、哪些后接回、哪些最后重构。
3. 为后续高低阶模型任务分发提供正式排序依据。

---

## 0. 排序原则

本清单只给 `investing-os` 接管排序，不给 `stock_team` 旧运行面做完整重构计划。

排序规则：

- `P0`：立即恢复 canonical 地位，否则后续所有工作继续漂浮
- `P1`：在 `P0` 之上接回主链，解决 DAILY / cognition / dashboard 断裂
- `P2`：在主链接回后再收敛、合并、重构，避免过早整理

一句话理解：

> 先恢复主脑本体，再接回运行链，最后才收尾和收敛。

---

## 1. P0：立即恢复 canonical 地位

这些不是“以后考虑复用”，而是应立即被重新承认为主系统正式资产。

### P0-1 项目身份与主脑纲领

文件：

- `investing-os/PROJECT-CHARTER.zh.md`
- `investing-os/WHY.md`
- `investing-os/OPERATING-MODEL.md`
- `investing-os/framework.md`
- `investing-os/constitution.md`
- `investing-os/AGENTS.md`

目标：

- 确认这些文件是项目级最高身份层；
- 后续 DAILY / dashboard / cognition 改动不得绕开它们另起一套系统语言。

原因：

- 如果连主脑身份层都不先恢复 canonical，后面任何接线都会继续边修边漂。

### P0-2 workflow / route / brain-muscle 协议层

文件：

- `investing-os/system/workflows/trading-day.md`
- `investing-os/system/workflows/pre-market.md`
- `investing-os/system/workflows/post-market.md`
- `investing-os/system/workflows/command-router.md`
- `investing-os/system/workflows/intraday-guidance-protocol.md`
- `investing-os/system/workflows/stock-team-orchestration.md`
- `investing-os/system/workflows/brain-muscle-handshake-protocol.md`

目标：

- 确认这几份文件是旧系统正式 workflow/route/protocol 主轴；
- 当前 DAILY 契约与 Stage0/Stage1 接线以后要向它们回并，而不是长期平行存在。

原因：

- 这是旧系统最成熟的骨架层之一；
- 当前很多新契约本质上是在重新表述这里已有的东西。

### P0-3 主脑输入输出模板层

文件：

- `investing-os/templates/pre-market-universe.json`
- `investing-os/templates/pre-market-decision-sheet.json`
- `investing-os/templates/pre-market-plan.md`
- `investing-os/templates/trading-day-plan.md`
- `investing-os/templates/intraday-guidance-sheet.md`
- `investing-os/templates/intraday-guidance-to-stock-team.json`
- `investing-os/templates/post-market-trade-evidence-request.json`
- `investing-os/templates/review-report-standard.md`
- `investing-os/templates/lesson-lineage.md`

目标：

- 恢复这些模板为正式主脑表单层；
- 当前 blocker 中暴露出的 precondition 字段，应回写到这些 canonical 模板和 contract 中。

原因：

- 这些模板已经是主脑结构化接口；
- 后续修 DAILY 不应继续临时拼表单。

### P0-4 认知与长期知识主层

文件：

- `investing-os/cognition/*`
- `investing-os/evolution/*`
- `investing-os/wiki/principles/*`
- `investing-os/wiki/methodologies/company-research-14-dimensions.md`
- `investing-os/wiki/industries/ai-sector-map.md`

目标：

- 恢复认知、进化、原则层在系统里的主地位；
- 明确这些不是静态资料库，而是 DAILY、review、growth dashboard 的来源层。

原因：

- 如果主脑知识层继续只存在于仓库角落，后面接回 dashboard 也只是空壳。

### P0-5 traceability 主索引层

文件：

- `investing-os/system/traceability/schema.md`
- `investing-os/system/traceability/reports-index.json`
- `investing-os/system/traceability/lesson-index.json`
- `investing-os/system/traceability/file-lineage-index.json`
- `investing-os/system/traceability/capability-history.json`

目标：

- 重新承认这套索引为 growth / review / lesson absorption 的正式底座。

原因：

- 这决定后面认知 dashboard 是否有真实数据来源，而不只是页面恢复。

---

## 2. P1：在 P0 之上接回主链

### P1-1 恢复 `operating-console` 为正式主入口

文件：

- `investing-os/dashboards/operating-console.html`
- `investing-os/dashboards/assets/operating-console-data.js`

目标：

- 不再把当前 dashboard/coordinator 入口视为唯一用户入口；
- 以旧 operating console 为正式主入口基底，重新挂接当前 DAILY / session / action 状态。

为什么是 P1 而不是 P0：

- 它依赖 P0 已先确认主脑纲领和 workflow 主轴；
- 否则只是“恢复旧页面”，不是恢复正式入口。

### P1-2 恢复 growth dashboard 为正式认知入口

文件：

- `investing-os/dashboards/growth-dashboard-draft.html`
- `investing-os/dashboards/assets/growth-dashboard-data.js`
- `investing-os/dashboards/assets/growth-dashboard-indexes.js`
- `investing-os/tools/generate-growth-dashboard-data.ps1`

目标：

- 让 lesson lineage / report archive / capability history / promotion queue 重新进入正式可视面；
- 把旧 traceability 层重新投影到认知 dashboard。

为什么是 P1：

- 它依赖 P0 的 cognition/evolution/traceability 已先恢复 canonical。

### P1-3 把当前 DAILY 契约回并到旧 workflow 主轴

对象：

- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`
- 与之相关的 daily audit / implementation review / approved decisions

目标：

- 不是删除近期 DAILY 契约；
- 而是把其中真正持久的顺序、产物、闸门、恢复规则回并到旧 `trading-day / pre-market / post-market / command-router / intraday-guidance-protocol` 体系。

原因：

- 当前 DAILY 是近期成果中的 `KEEP + MERGE-BACK` 混合体；
- 应继续保留，但长期不应与旧 workflow 主轴并列为两套正典。

### P1-4 把 Stage0 brain precondition 正式接回 canonical input contract

对象：

- `positions`
- `prior_review`
- `cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

目标：

- 将这些字段从 blocker 文档/实现补丁层提升为 canonical 输入契约；
- 优先落在 `pre-market-universe.json`、相关 packet contract、pre-market workflow 中。

原因：

- 这是近期真实运行暴露出的最关键主脑前置条件；
- 不接回 canonical contract，之后仍会在代码层反复补洞。

### P1-5 明确当前 `start_stage0_from_snapshot` 链的未来归宿

对象：

- `6500238`
- `aa17a22`
- `b79ce9c`
- `2220118`
- `3dbe9b8`

目标：

- 明确这条链继续作为 `TRANSITIONAL` 过桥逻辑存在；
- 等 operating console / old workflows 接回后，再判断是否吸收或退休。

原因：

- 它当前有价值，但不该误升格为长期主入口方案。

---

## 3. P2：接回主链后再收敛和重构

### P2-1 整理 handoff 与 canonical 的边界

对象：

- repair charter
- task packets
- blocker notes
- review handoff
- recent disposition ledger

目标：

- 保留 handoff 历史；
- 但把其中沉淀出的长期规则回写到 canonical files，避免“规则只存在于 handoff 文档”。

### P2-2 收敛重复表述

对象：

- 新 DAILY 契约与旧 workflows 间的重复定义
- 新解释文档与旧 protocol 文件间的重复规则

目标：

- 逐步把重复内容收敛成单一 canonical 描述源。

### P2-3 再进入 `stock_team` 旧运行面接管

对象：

- `stock_team/server/dashboard_server.py`
- `stock_team/server/dashboard_writer.py`
- `stock_team/server/dashboard_cache.py`
- `stock_team/server/dashboard_experience_loop.py`
- `stock_team/templates/daily_dashboard.html.j2`

目标：

- 在 `investing-os` 主脑本体已恢复 canonical 后，再决定哪些原样沿用、哪些接管式重构。

原因：

- 如果太早碰这里，很容易又回到“在膨胀运行面里边补边堆”。

---

## 4. 推荐执行顺序

### 第一批：必须先做

1. 重新确认 `P0-1` 到 `P0-5` 的 canonical 地位
2. 把 Stage0 brain precondition 回写到正式 contract
3. 定义“当前 DAILY 契约哪些要 merge-back 到旧 workflows”

### 第二批：主入口与认知入口接回

4. 恢复 operating console 为正式入口基底
5. 恢复 growth dashboard 为正式认知入口
6. 让 traceability / lesson / report indexes 真正驱动 growth dashboard

### 第三批：过桥层与运行面收尾

7. 重新定位 `start_stage0_from_snapshot` 过桥链
8. 收敛 handoff/contract 的重复表述
9. 再进入 `stock_team` legacy runtime 接管

---

## 5. 哪些适合低阶模型先做

### 可以给低阶模型的

- canonical 文件定位与引用补链
- P0/P1 相关文档对齐
- 把 blocker 字段回写到模板/contract 的基础编辑
- growth dashboard / traceability / indexes 的静态接线检查
- operating console / growth dashboard 与现有文件的映射梳理

### 应由高阶模型主导的

- 哪些文件真正升为 canonical
- DAILY 契约哪些 merge-back、哪些保留为独立台账
- `start_stage0_from_snapshot` 的最终命运判断
- `investing-os` 与 `stock_team` 的责任边界调整

---

## 6. 最终判断

在当前阶段，最正确的项目动作不是继续直接修某个零散 bug。

而是：

1. 先恢复 `investing-os` 的 canonical 本体；
2. 再把这几天做出来的 DAILY / blocker / bridge 逻辑接回去；
3. 最后才去整理 legacy runtime。

一句话总结：

> 先让主脑重新成为主脑，再让近期修补链找到归宿。

