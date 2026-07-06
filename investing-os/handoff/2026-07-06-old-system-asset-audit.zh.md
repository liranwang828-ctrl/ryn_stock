# 旧系统资产审计 v2（内容归纳 + 文件分类台账）

日期：2026-07-06

目的：

1. 回答“旧系统里到底已经有什么完整资产”。
2. 回答“这轮重做到底吸收了多少旧系统成果”。
3. 给后续接管、复用、重构建立一份可追溯的文件级台账。

---

## 0. 审计范围与方法

这不是按文件名猜目录用途的清点。

本轮按“内容角色”做分类，方法是：

- 先枚举 `investing-os/**` 全部候选文件；
- 再分批阅读 root 文档、workflow、template、dashboard、cognition、wiki、traceability、integration、legacy dashboard/runtime 相关文件；
- 对于大量同构文件（例如 journal、principle、schema、simulation fixture、handoff inventory），不是只看文件名，而是确认其内部结构模式一致后，按“文件族”入账；
- `system/runtime/**` 这类运行时产物不作为“旧系统主资产”主体，但会单独标记为运行样本或历史状态。

本台账的四个判断字段：

- `类别`：文件在系统里的实际角色。
- `成熟度`：是主资产、辅助协议、样例、历史记录，还是运行产物。
- `处置建议`：
  - `K` = 保留为 canonical 主资产
  - `R` = 作为参考/吸收来源
  - `T` = 接管式重构
  - `A` = 归档/历史保留
- `本轮利用情况`：这轮 DAILY / coordinator / dashboard 接线里到底有没有真实用上。

---

## 1. 先给结论

结论很明确：

1. 旧系统不是“做过几个页面”，而是已经有一套相当完整的主脑产品层、认知层、知识层、工作流层和旧 Dashboard 运行层。
2. 这轮重做确实继承了旧系统的一部分边界思想，但主要继承的是“概念、职责划分、协议语言”；真正成熟的页面、数据脚本、认知追踪链、旧 dashboard 运行层，并没有被系统性接管。
3. 用户感觉“旧系统明明已经很完整，但这轮像没怎么用上”，这个判断基本成立。
4. 后续如果只盯着修 DAILY 主链，而不做“旧系统资产接管”，项目会持续卡在：
   - 新链路不断补洞；
   - 旧成品长期闲置；
   - 主入口、认知 dashboard、运行 dashboard 三套东西继续分裂。

一句话判断：

> 这轮不是完全推倒重来，但对旧系统成熟资产的吸收明显不足，尤其不足在产品面、认知可视化面、以及旧 dashboard 运行体系。

---

## 2. 旧系统资产的实际分层

旧系统的真实分层已经很清楚：

1. `root docs`：项目身份、WHY、框架、行动纲领。
2. `cognition/ decision/ execution/ evolution/`：主脑知识与决策内核。
3. `system/workflows + checks + data + traceability`：操作协议、数据契约、吸收闭环、schema、lesson lineage。
4. `templates/`：把思考和流程压成结构化输入输出的表单层。
5. `wiki/`：长期知识层，含原则、案例、研究、复盘、方法论、来源吸收。
6. `dashboards/ + tools/`：旧产品面与旧认知 dashboard 数据生成链。
7. `integrations/`：主脑与 `stock_team` 的边界图。
8. `stock_team/server/*dashboard* + templates/*`：旧运行面，不是空壳，而是一套已经膨胀但有价值的 legacy runtime surface。
9. `handoff/`：项目迁移、审计、任务分发、历史决策记录层。

本总审计对应的三份细拆附录：

- [`2026-07-06-old-system-audit-dashboards-tools.zh.md`](./2026-07-06-old-system-audit-dashboards-tools.zh.md)
- [`2026-07-06-old-system-audit-system-layer.zh.md`](./2026-07-06-old-system-audit-system-layer.zh.md)
- [`2026-07-06-old-system-audit-wiki-templates.zh.md`](./2026-07-06-old-system-audit-wiki-templates.zh.md)

---

## 3. 重点结论：哪些是真正成熟资产

### 3.1 A 类：应视为主资产继续接管

- `investing-os/PROJECT-CHARTER.zh.md`
- `investing-os/WHY.md`
- `investing-os/OPERATING-MODEL.md`
- `investing-os/framework.md`
- `investing-os/constitution.md`
- `investing-os/dashboards/operating-console.html`
- `investing-os/dashboards/growth-dashboard-draft.html`
- `investing-os/dashboards/assets/operating-console-data.js`
- `investing-os/dashboards/assets/growth-dashboard-data.js`
- `investing-os/dashboards/assets/growth-dashboard-indexes.js`
- `investing-os/tools/generate-growth-dashboard-data.ps1`
- `investing-os/system/traceability/schema.md`
- `investing-os/templates/lesson-lineage.md`
- `investing-os/templates/review-report-standard.md`
- `investing-os/system/workflows/command-router.md`
- `investing-os/system/workflows/intraday-guidance-protocol.md`
- `investing-os/integrations/stock-team-capability-map.md`

判断依据：

- 它们不是说明性草稿，而是已经定义系统身份、入口产品、认知展示、traceability 结构和 brain-muscle 协议的“骨架文件”。

### 3.2 B 类：成熟但属于“协议 / 约束 / 桥接资产”

- `investing-os/system/workflows/*`
- `investing-os/system/checks/*`
- `investing-os/system/data/schemas/*`
- `investing-os/system/data/packets/*`
- `investing-os/evolution/*`
- `investing-os/wiki/principles/*`

判断依据：

- 这些文件不是最终 UI，但它们构成系统的可执行规则与吸收闭环，是主脑契约层。

### 3.3 C 类：值得接管，但不能继续“边补边堆”

- `stock_team/server/dashboard_server.py`
- `stock_team/server/dashboard_writer.py`
- `stock_team/server/dashboard_cache.py`
- `stock_team/server/dashboard_experience_loop.py`
- `stock_team/server/dashboard_experience_paths.py`
- `stock_team/templates/daily_dashboard.html.j2`
- `stock_team/templates/scripts.js.j2`
- `stock_team/templates/styles.css.j2`

判断依据：

- 这些不是无用旧代码，而是已经形成 server + writer + template + cache + UX feedback 的运行面体系；
- 但已经明显膨胀，不适合再用“遇到问题加一点”方式继续维护；
- 更适合单独做“旧运行面接管 / 拆分 / 收敛审计”。

---

## 4. 文件分类代码

为避免以后再次混淆，这里统一分类代码：

- `ROOT`：项目根身份/纲领文件
- `AGENT`：AI 角色定义
- `COG`：认知内核
- `DEC`：决策内核
- `EXE`：执行约束
- `EVO`：经验进化
- `WF`：workflow / protocol / route
- `CHK`：checklist / gate
- `DATA`：数据契约 / schema / packet contract
- `TRACE`：traceability / lineage / lessons
- `TPL`：结构化模板
- `WIKI-KNOW`：长期知识
- `WIKI-SRC`：来源吸收 / inbox / source review
- `DASH`：产品页面 / 可视化资产
- `TOOL`：生成/治理脚本
- `INT`：集成边界
- `SIM`：模拟输入 / demo / fixture
- `RUNTIME-SAMPLE`：历史运行时样本
- `HANDOFF`：迁移/审计/任务记录
- `LEGACY-RUNTIME`：旧 `stock_team` dashboard/runtime 资产

---

## 5. 文件级归纳台账（按文件族）

说明：

- 下面不是按文件名生搬硬套；
- 每个文件族都基于实际内容结构归类；
- 对高价值文件逐个单列；
- 对大量同构历史文件，按“内部结构一致的文件族”列出具体文件。

### 5.1 root 主纲文件

- `investing-os/README.md` — `ROOT`；仓库总入口与阅读顺序；`K`；本轮部分利用。
- `investing-os/PROJECT.md` — `ROOT`；项目管理边界，明确什么属于主项目；`R`。
- `investing-os/PROJECT-CHARTER.zh.md` — `ROOT`；当前最高优先级行动纲领；`K`；本轮大量利用。
- `investing-os/WHY.md` — `ROOT`；系统存在理由与认知优先级；`K`。
- `investing-os/USAGE.md` — `ROOT`；日常使用地图；`R`。
- `investing-os/OPERATING-MODEL.md` — `ROOT`；四大系统模型；`K`。
- `investing-os/framework.md` — `ROOT`；投资框架主线；`K`。
- `investing-os/constitution.md` — `ROOT`；禁止事项与身份边界；`K`。
- `investing-os/AGENTS.md` — `ROOT`；全局 AI 行为与边界；`K`。
- `investing-os/.gitignore` — 工程治理辅助，不属于认知主资产；`A`。

### 5.2 agents/

- `investing-os/agents/README.md` — `AGENT`；agent 团队定位说明；`R`。
- `investing-os/agents/model-boundary.md` — `AGENT`；低阶模型可做/不可做边界；`K`；本轮协作方法高度相关。
- `investing-os/agents/pre-market-planning-agent.md` — `AGENT`；Stage 0→1 的辅助角色，不授予建议权；`R`。
- `investing-os/agents/risk-boundary-plan-approval-agent.md` — `AGENT`；风险边界与计划确认角色；`R`。
- `investing-os/agents/stock-team-evidence-agent.md` — `AGENT`；主脑调用肌肉的证据代理；`R`。

### 5.3 cognition/

- `investing-os/cognition/README.md` — `COG`；认知层总说明；`K`。
- `investing-os/cognition/self-model.md` — `COG`；投资者身份与 edge 假设；`K`。
- `investing-os/cognition/bias-map.md` — `COG`；偏差库；`K`。
- `investing-os/cognition/emotional-patterns.md` — `COG`；情绪模式库；`K`。
- `investing-os/cognition/mistake-patterns.md` — `COG`；错误模式库；`K`。
- `investing-os/cognition/strengths-and-weaknesses.md` — `COG`；能力/弱点盘点；`K`。

### 5.4 decision/

- `investing-os/decision/README.md` — `DEC`；决策系统入口；`K`。
- `investing-os/decision/current-watchlist.md` — `DEC`；关注池及允许动作状态；`K`。
- `investing-os/decision/decision-log.md` — `DEC`；重要判断变化日志；`R`。
- `investing-os/decision/falsification-map.md` — `DEC`；论点失效图；`K`。
- `investing-os/decision/portfolio-thesis.md` — `DEC`；组合层 thesis；`K`。
- `investing-os/decision/position-roles.md` — `DEC`；仓位角色系统；`K`。
- `investing-os/decision/risk-budget.md` — `DEC`；风险预算；`K`。
- `investing-os/decision/factors/README.md` — `DEC`；因子层定义入口；`R`。
- `investing-os/decision/factors/factor-library.md` — `DEC`；可测因子词表；`R`。
- `investing-os/decision/tactics/README.md` — `DEC`；战术目录说明；`R`。
- `investing-os/decision/tactics/rs-pullback-rebound-candidate.md` — `DEC`；候选战术，不是已批准运行规则；`R`。
- `investing-os/decision/tactics/rs-pullback-rebound-intraday.md` — `DEC`；paper-test 战术条目；`R`。
- `investing-os/decision/tactics/validation-records/rs-pullback-rebound-intraday.md` — `DEC`；战术验证记录；`R`。
- `investing-os/decision/plans/2026-06-08-pre-market-plan.md` — 历史计划草稿，已明确 superseded；`A`。
- `investing-os/decision/plans/2026-06-08-pre-market-plan.INTC-MU-COHR.v2.md` — 历史 workflow practice draft；`A`。
- `investing-os/decision/trade-plans/COHR-swing-plan-candidate-2026-06-05.zh.md` — 中文计划候选，不是执行许可；`R`。

### 5.5 execution/

- `investing-os/execution/README.md` — `EXE`；执行系统入口；`K`。
- `investing-os/execution/daily-operating-loop.md` — `EXE`；日常执行循环；`K`。
- `investing-os/execution/pre-market.md` — `EXE`；执行视角盘前规则；`K`。
- `investing-os/execution/intraday.md` — `EXE`；执行视角盘中权限与注意力规则；`K`。
- `investing-os/execution/post-market.md` — `EXE`；执行层向复盘层交接；`K`。
- `investing-os/execution/weekly-use-cases.md` — `EXE`；周度场景集合；`R`。

### 5.6 evolution/

- `investing-os/evolution/README.md` — `EVO`；进化系统入口；`K`。
- `investing-os/evolution/learning-loop.md` — `EVO`；经验如何喂回四大系统；`K`。
- `investing-os/evolution/experience-output-map.md` — `EVO`；经验产物落点映射；`K`。
- `investing-os/evolution/promotion-queue.md` — `EVO`；候选教训 staging area；`K`。
- `investing-os/evolution/promotion-rules.md` — `EVO`；何时晋升 durable cognition；`K`。
- `investing-os/evolution/system-update-log.md` — `EVO`；系统结构更新记录；`R`。

### 5.7 integrations/

- `investing-os/integrations/README.md` — `INT`；集成总入口；`R`。
- `investing-os/integrations/lianghua.md` — `INT`；外部项目关系说明；`R`。
- `investing-os/integrations/stock-team-capability-map.md` — `INT`；旧系统最重要的 brain-muscle 能力地图之一；`K`。
- `investing-os/integrations/stock-team-call-log.md` — `INT`；调用审计日志；`R`。
- `investing-os/integrations/stock-team-latest-dashboard-manifest.md` — `INT`；主脑引用最新 evidence dashboard 的桥接 manifest 契约；`R`。

### 5.8 dashboards/

- `investing-os/dashboards/operating-console.html` — `DASH`；旧系统主入口成品，不是 demo；`K`；本轮未真正接管。
- `investing-os/dashboards/growth-dashboard-draft.html` — `DASH`；认知成长 dashboard 成品；`K`；本轮概念借用多，实体接管少。
- `investing-os/dashboards/intraday-dashboard.html` — `DASH`；盘中显示面；`R`。
- `investing-os/dashboards/latest_evidence_dashboard.html` — `DASH`；承接 `stock_team` evidence dashboard 的本地桥页；`R`。
- `investing-os/dashboards/assets/operating-console-data.js` — `DASH`；console view-model；`K`。
- `investing-os/dashboards/assets/growth-dashboard-data.js` — `DASH`；growth dashboard 静态认知视图数据；`K`。
- `investing-os/dashboards/assets/growth-dashboard-indexes.js` — `DASH`；reports / lessons / lineage / capability history 聚合索引；`K`。
- `investing-os/dashboards/reports/intraday-guidance-demo.html` — `DASH`；intraday guidance 展示样本；`R`。
- `investing-os/dashboards/reports/2026-06-05-major-drawdown-review.html` — `DASH`；review HTML 阅读层成品；`R`。
- `investing-os/dashboards/report-fragments/RPT-2026-06-05-MAJOR-DRAWDOWN.zh.html` — `DASH`；报告片段；`R`。

### 5.9 tools/

- `investing-os/tools/check-file-growth.ps1` — `TOOL`；文件膨胀治理工具；`R`。
- `investing-os/tools/generate-growth-dashboard-data.ps1` — `TOOL`；growth dashboard 数据生成器，关键旧资产；`K`。
- `investing-os/tools/generate-report-html.ps1` — `TOOL`；report markdown→HTML 阅读视图生成器；`R`。

### 5.10 templates/

这些文件大多不是“参考文案”，而是把 workflow 压成结构化输入输出的表单层。

- `investing-os/templates/README.md` — `TPL`；模板层入口；`R`。
- `investing-os/templates/brain-request.md` — `TPL`；主脑请求模板；`R`。
- `investing-os/templates/chatgpt-review-prompt.md` — `TPL`；AI 复盘提示模板；`R`。
- `investing-os/templates/company-research.md` — `TPL`；公司研究模板；`R`。
- `investing-os/templates/contextual-trade-review.md` — `TPL`；情境化交易复盘模板；`R`。
- `investing-os/templates/daily-report.md` — `TPL`；日报模板；`R`。
- `investing-os/templates/event-reconstruction-request.json` — `TPL`；事件重构请求结构；`R`。
- `investing-os/templates/falsification.md` — `TPL`；论点证伪模板；`R`。
- `investing-os/templates/historical-case.md` — `TPL`；历史案例模板；`R`。
- `investing-os/templates/import-source-note.md` — `TPL`；来源吸收模板；`R`。
- `investing-os/templates/industry-research.md` — `TPL`；行业研究模板；`R`。
- `investing-os/templates/intraday-guidance-sheet.md` — `TPL`；盘中指导表单；`K`。
- `investing-os/templates/intraday-guidance-to-stock-team.json` — `TPL`；主脑→肌肉 guidance 结构桥；`K`。
- `investing-os/templates/journal-entry.md` — `TPL`；日记模板；`R`。
- `investing-os/templates/lesson-lineage.md` — `TPL`；lesson 血缘模板，关键旧资产；`K`。
- `investing-os/templates/packet-review.md` — `TPL`；packet 吸收模板；`R`。
- `investing-os/templates/post-market-review.md` — `TPL`；盘后复盘模板；`R`。
- `investing-os/templates/post-market-trade-evidence-request.json` — `TPL`；盘后证据请求模板；`K`。
- `investing-os/templates/pre-market-decision-sheet.json` — `TPL`；Stage 1 决策单结构；`K`。
- `investing-os/templates/pre-market-plan.md` — `TPL`；盘前计划模板；`K`。
- `investing-os/templates/pre-market-universe.json` — `TPL`；Stage 0 universe 结构；`K`。
- `investing-os/templates/principle.md` — `TPL`；原则模板；`R`。
- `investing-os/templates/principle-candidate.md` — `TPL`；原则候选模板；`R`。
- `investing-os/templates/review-report-standard.md` — `TPL`；标准复盘报告模板，关键旧资产；`K`。
- `investing-os/templates/risk-checklist.md` — `TPL`；风险检查模板；`R`。
- `investing-os/templates/signal-review.md` — `TPL`；信号复核模板；`R`。
- `investing-os/templates/stock-team-evidence-request.md` — `TPL`；肌肉证据请求模板；`R`。
- `investing-os/templates/tactic-event-summary-request.json` — `TPL`；战术事件总结请求结构；`R`。
- `investing-os/templates/thesis.md` — `TPL`；论点模板；`R`。
- `investing-os/templates/trade-plan.md` — `TPL`；交易计划模板；`R`。
- `investing-os/templates/trading-day-plan.md` — `TPL`；交易日计划模板；`K`。
- `investing-os/templates/valuation.md` — `TPL`；估值模板；`R`。
- `investing-os/templates/weekend-review.md` — `TPL`；周末复盘模板；`R`。

### 5.11 wiki/（长期知识层）

#### 5.11.1 wiki 根说明

- `investing-os/wiki/README.md` — `WIKI-KNOW`；知识层总入口；`K`。

#### 5.11.2 wiki/principles/

- `investing-os/wiki/principles/README.md` — `WIKI-KNOW`；原则体系入口；`K`。
- `investing-os/wiki/principles/PRIN-001-leveraged-tool-discipline.md` — 已吸收的 active principle；`K`。
- `investing-os/wiki/principles/PRIN-002-hand-feel-trade-limit.md` — 已吸收的 active principle；`K`。
- `investing-os/wiki/principles/PRIN-003-profit-taking-cooling-period.md` — 已吸收的 active principle；`K`。
- `investing-os/wiki/principles/PRIN-004-sector-sympathy-rules.md` — 已吸收的 active principle；`K`。
- `investing-os/wiki/principles/PRIN-005-vwap-volume-rules.md` — 已吸收的 active principle；`K`。
- `investing-os/wiki/principles/PRIN-006-cognitive-attention-budget.md` — 已吸收的 active principle；`K`。
- `investing-os/wiki/principles/candidates/README.md` — principle candidate 容器说明；`R`。

#### 5.11.3 wiki/methodologies/

- `investing-os/wiki/methodologies/README.md` — `WIKI-KNOW`；方法论索引；`R`。
- `investing-os/wiki/methodologies/company-research-14-dimensions.md` — 公司研究方法论；`K`。
- `investing-os/wiki/methodologies/ai-swing-valuation-temperature.zh.md` — 估值温度计方法候选；`R`。

#### 5.11.4 wiki/industries/

- `investing-os/wiki/industries/README.md` — 行业研究目录说明；`R`。
- `investing-os/wiki/industries/ai-sector-map.md` — 已吸收行业地图；`K`。
- `investing-os/wiki/industries/ai-gpu-compute.md` — 已吸收行业研究；`R`。
- `investing-os/wiki/industries/physical-ai.md` — 已吸收行业研究；`R`。
- `investing-os/wiki/industries/industry-dossier-template.md` — 行业 dossier 模板；`R`。

#### 5.11.5 wiki/companies/

- `investing-os/wiki/companies/README.md` — 公司 dossier 目录说明；`R`。
- `investing-os/wiki/companies/company-dossier-template.md` — 公司 dossier 模板；`R`。
- `investing-os/wiki/companies/COHR.md` — 公司研究 dossier；`R`。
- `investing-os/wiki/companies/COHR.zh.md` — 中文 dossier；`R`。
- `investing-os/wiki/companies/COHR-valuation-temperature.zh.md` — 估值温度读数；`R`。
- `investing-os/wiki/companies/INTC.md` — 公司 dossier；`R`。
- `investing-os/wiki/companies/ORCL.md` — 公司 dossier；`R`。

#### 5.11.6 wiki/journals/

这些文件内部都有 metadata / source / review 结构，属于历史复盘与日记资产，不是流程契约。

- `investing-os/wiki/journals/README.md` — 日记目录说明；`R`。
- `investing-os/wiki/journals/2026-06-04-daily-review.md` — 历史日复盘；`R`。
- `investing-os/wiki/journals/2026-06-04-snxx-fill-review.md` — fill review；`R`。
- `investing-os/wiki/journals/2026-06-04-snxx-contextual-review.md` — contextual review；`R`。
- `investing-os/wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md` — exit review；`R`。
- `investing-os/wiki/journals/2026-06-05-major-drawdown-review.md` — 高价值系统级风险复盘；`K`。
- `investing-os/wiki/journals/2026-06-08-market-rebound-cognition-review.md` — 认知复盘草稿；`R`。

#### 5.11.7 wiki/historical-cases/

- `investing-os/wiki/historical-cases/README.md` — 历史案例目录说明；`R`。
- `investing-os/wiki/historical-cases/CASE-001-cohr-profit-taking.md` — 案例资产；`R`。
- `investing-os/wiki/historical-cases/CASE-002-crdu-fomo-pullback.md` — 案例资产；`R`。
- `investing-os/wiki/historical-cases/CASE-003-pltr-trend-switch-exit.md` — 案例资产；`R`。
- `investing-os/wiki/historical-cases/CASE-004-snxx-attention-capture.md` — 案例资产；`R`。

#### 5.11.8 wiki/sources/

- `investing-os/wiki/sources/README.md` — source review 目录说明；`R`。
- `investing-os/wiki/sources/packet-review-COHR-2026-06-05.md` — packet 吸收记录；`R`。
- `investing-os/wiki/sources/packet-review-COHR-2026-06-05.zh.md` — 中文 packet 吸收记录；`R`。
- `investing-os/wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md` — 外部 backtest 证据吸收；`R`。

#### 5.11.9 wiki/inbox/

这里不是长期 canonical 层，而是吸收前暂存层。

- `investing-os/wiki/inbox/README.md` — inbox 规则说明；`R`。
- `investing-os/wiki/inbox/system/README_zh.md` — 中文系统总说明；`R`。
- `investing-os/wiki/inbox/system/00_system_overview_zh.md` — 原始系统总纲来源；`R`。
- `investing-os/wiki/inbox/system/02_portfolio_framework_zh.md` — 原始仓位框架来源；`R`。
- `investing-os/wiki/inbox/system/03_daily_workflow_zh.md` — 原始每日流程来源；`R`。
- `investing-os/wiki/inbox/system/04_company_research_method_zh.md` — 原始公司研究法来源；`R`。
- `investing-os/wiki/inbox/reports/05_market_sector_map_zh.md` — 原始板块地图来源；`R`。
- `investing-os/wiki/inbox/reports/AI_GPU_compute_industry_2026-05-26.md` — 原始行业长文来源；`R`。
- `investing-os/wiki/inbox/reports/Physical_AI_industry_2026-05-26.md` — 原始行业长文来源；`R`。
- `investing-os/wiki/inbox/principles/leveraged_tool_rules_zh.md` — 原始原则来源；`R`。
- `investing-os/wiki/inbox/principles/hand_feel_trade_zh.md` — 原始原则来源；`R`。
- `investing-os/wiki/inbox/principles/profit_taking_regret_loop_zh.md` — 原始原则来源；`R`。
- `investing-os/wiki/inbox/principles/sector_sympathy_catalyst_zh.md` — 原始原则来源；`R`。
- `investing-os/wiki/inbox/principles/vwap_volume_confirmation_zh.md` — 原始原则来源；`R`。
- `investing-os/wiki/inbox/cases/2026-06-02_cohr_profit_taking_zh.md` — 原始案例来源；`R`。
- `investing-os/wiki/inbox/cases/2026-06-02_crdu_fomo_pullback_zh.md` — 原始案例来源；`R`。
- `investing-os/wiki/inbox/cases/2026-06-02_pltr_trend_switch_exit_zh.md` — 原始案例来源；`R`。
- `investing-os/wiki/inbox/ai/01_ai_usage_protocol_zh.md` — AI 协作原始说明；`R`。
- `investing-os/wiki/inbox/ai/answer_checklist_zh.md` — AI 回答原始说明；`R`。
- `investing-os/wiki/inbox/ai/llm_controller_discipline_zh.md` — AI 控制边界原始说明；`R`。
- `investing-os/wiki/inbox/ai/low_model_boundary_zh.md` — 低阶模型边界原始说明；`R`。
- `.gitkeep` 文件仅用于目录保留；`A`。

### 5.12 system/

#### 5.12.1 system 根文件

- `investing-os/system/README.md` — `WF`；系统层总入口；`K`。
- `investing-os/system/architecture.md` — `WF`；可扩展架构说明；`R`。
- `investing-os/system/closed-loop-operating-architecture.md` — `WF`；主脑-肌肉闭环蓝图；`K`。
- `investing-os/system/evolution-loop.md` — `WF`；进化回路总述；`R`。
- `investing-os/system/file-growth-policy.md` — `WF`；文件治理规则；`R`。

#### 5.12.2 system/checks/

- `investing-os/system/checks/README.md` — `CHK`；检查项入口；`R`。
- `investing-os/system/checks/ai-trading-response-checklist.md` — `CHK`；AI 涉及交易时的总闸门；`K`。
- `investing-os/system/checks/position-role-checklist.md` — `CHK`；仓位角色闸门；`K`。
- `investing-os/system/checks/short-term-trade-checklist.md` — `CHK`；短线交易闸门；`K`。
- `investing-os/system/checks/signal-to-action-checklist.md` — `CHK`；信号不能直接变动作的总闸门；`K`。
- `investing-os/system/checks/snapshot-approval-checklist.md` — `CHK`；runtime snapshot 批准闸门；`R`。
- `investing-os/system/checks/why-alignment-checklist.md` — `CHK`；WHY 对齐闸门；`K`。

#### 5.12.3 system/workflows/

这里是旧系统最成熟的协议层之一。

- `investing-os/system/workflows/README.md` — `WF`；workflow 总目录；`R`。
- `investing-os/system/workflows/trading-day.md` — `WF`；跨时区交易日主节奏；`K`。
- `investing-os/system/workflows/pre-market.md` — `WF`；盘前正式流程；`K`。
- `investing-os/system/workflows/intraday.md` — `WF`；盘中流程；`R`。
- `investing-os/system/workflows/post-market.md` — `WF`；盘后流程；`K`。
- `investing-os/system/workflows/weekend-review.md` — `WF`；周末复盘；`R`。
- `investing-os/system/workflows/signal-processing.md` — `WF`；信号处理；`R`。
- `investing-os/system/workflows/runtime-snapshot-approval.md` — `WF`；snapshot 批准流程；`R`。
- `investing-os/system/workflows/stock-team-orchestration.md` — `WF`；主脑调用肌肉流程；`K`。
- `investing-os/system/workflows/brain-muscle-handshake-protocol.md` — `WF`；统一脑-肌握手协议；`K`。
- `investing-os/system/workflows/command-router.md` — `WF`；用户自然语言→工作流路由器，关键旧资产；`K`。
- `investing-os/system/workflows/intraday-guidance-protocol.md` — `WF`；认知系统如何投影到盘中指导，关键旧资产；`K`。
- `investing-os/system/workflows/evidence-request-lifecycle.md` — `WF`；证据请求生命周期；`R`。
- `investing-os/system/workflows/company-research.md` — `WF`；公司研究流程；`R`。
- `investing-os/system/workflows/company-research-rebuild-2026-06-05.md` — 重建说明，不是最终主契约；`A`。
- `investing-os/system/workflows/company-dossier-lifecycle.md` — `WF`；company dossier 生命周期；`R`。
- `investing-os/system/workflows/industry-research.md` — `WF`；行业研究流程；`R`。
- `investing-os/system/workflows/industry-dossier-lifecycle.md` — `WF`；industry dossier 生命周期；`R`。
- `investing-os/system/workflows/journal-to-principle-promotion.md` — `WF`；日记→原则晋升流程；`R`。
- `investing-os/system/workflows/packet-absorption.md` — `WF`；packet 吸收流程；`R`。
- `investing-os/system/workflows/post-market-trade-review.md` — `WF`；盘后交易复盘流程；`R`。
- `investing-os/system/workflows/daily-report.md` — `WF`；日报流程；`R`。
- `investing-os/system/workflows/wiki-update.md` — `WF`；wiki 更新流程；`R`。
- `investing-os/system/workflows/DAILY-CONTRACT.zh.md` — 新一轮 DAILY 契约文件，不属于“旧系统原生资产”，但现已成为当前 canonical 契约；`K`。
- `investing-os/system/workflows/WORKFLOW-STATUS.zh.md` — 当前实现状态台账；`R`。

#### 5.12.4 system/data/

##### contracts / maps / packet contracts

- `investing-os/system/data/README.md` — `DATA`；数据层入口；`R`。
- `investing-os/system/data/runtime-parameter-map.md` — `DATA`；原则→runtime 参数桥接；`R`。
- `investing-os/system/data/runtime-snapshot-contract.md` — `DATA`；runtime snapshot 边界契约；`K`。
- `investing-os/system/data/packets/README.md` — `DATA`；packet 总说明；`R`。
- `investing-os/system/data/packets/pre-market-packet.md` — `DATA`；盘前 packet contract；`K`。
- `investing-os/system/data/packets/pre-market-context-packet.md` — `DATA`；Stage 0 context packet contract/shape；`K`。
- `investing-os/system/data/packets/post-market-packet.md` — `DATA`；盘后 packet contract；`R`。
- `investing-os/system/data/packets/post-market-trade-evidence-packet.md` — `DATA`；盘后事实包 contract；`K`。
- `investing-os/system/data/packets/runtime-monitor-packet.md` — `DATA`；盘中 runtime monitor contract；`R`。
- `investing-os/system/data/packets/plan-evidence-packet.md` — `DATA`；Stage 1 evidence packet 示例化合同；`R`。
- `investing-os/system/data/packets/tactic-event-summary-packet.md` — `DATA`；战术事件总结包 contract；`R`。
- `investing-os/system/data/packets/company-research-packet.md` — `DATA`；公司研究包 contract；`R`。
- `investing-os/system/data/packets/industry-research-packet.md` — `DATA`；行业研究包 contract；`R`。
- `investing-os/system/data/packets/contextual-trade-evidence-packet.md` — `DATA`；情境化交易证据包 contract；`R`。
- `investing-os/system/data/packets/event-reconstruction-packet.md` — `DATA`；事件重构包 contract；`R`。

##### dated packet examples / drafts

- `investing-os/system/data/packets/pre-market-context-packet.2026-06-08.INTC-MU-COHR.v2.md` — 历史示例；`A`。
- `investing-os/system/data/packets/pre-market-context-packet.2026-06-08.cognition-v1.md` — 历史示例；`A`。
- `investing-os/system/data/packets/plan-evidence-packet.2026-06-08.INTC-MU-COHR.v2.md` — 历史示例；`A`。
- `investing-os/system/data/packets/plan-evidence-packet.2026-06-08.cognition-v1.md` — 历史示例；`A`。
- `investing-os/system/data/packets/intraday-dashboard-packet.md` — dashboard packet 说明；`R`。
- `investing-os/system/data/packets/intraday_snapshot.md` — snapshot 阅读层；`R`。
- `investing-os/system/data/packets/intraday_snapshot.json` — snapshot 样例/历史文件；`A`。
- `investing-os/system/data/packets/ib_event_log.json` — 历史原始事件记录；`A`。
- `investing-os/system/data/packets/drafts/company-research-COHR-2026-06-05.md` — 草稿 packet；`A`。

##### schemas

- `investing-os/system/data/schemas/coordinator-action.schema.json` — `DATA`；协调器动作 schema；`K`。
- `investing-os/system/data/schemas/degraded-mode.schema.json` — `DATA`；降级模式 schema；`R`。
- `investing-os/system/data/schemas/risk-limits.schema.json` — `DATA`；风险限制 schema；`R`。
- `investing-os/system/data/schemas/session-state.schema.json` — `DATA`；session state schema；`K`。
- `investing-os/system/data/schemas/signal-interpretation.schema.json` — `DATA`；信号解释 schema；`R`。
- `investing-os/system/data/schemas/tactical-rules.schema.json` — `DATA`；战术规则 schema；`R`。
- `investing-os/system/data/schemas/watchlist-metadata.schema.json` — `DATA`；watchlist metadata schema；`R`。

##### snapshots

- `investing-os/system/data/snapshots/README.md` — snapshot 目录说明；`R`。
- `investing-os/system/data/snapshots/changelog.md` — snapshot 变更记录；`R`。
- `investing-os/system/data/snapshots/active/README.md` — active snapshot 目录规则；`R`。
- `investing-os/system/data/snapshots/drafts/README.md` — draft snapshot 目录规则；`R`。
- `investing-os/system/data/snapshots/retired/README.md` — retired snapshot 目录规则；`R`。
- `investing-os/system/data/snapshots/approvals/README.md` — approval 目录规则；`R`。
- `investing-os/system/data/snapshots/approvals/snapshot-approval-record-template.md` — approval 记录模板；`R`。
- `investing-os/system/data/snapshots/approvals/dry-run-tactical-rules-20260605-example.md` — 干跑示例；`A`。
- `investing-os/system/data/snapshots/examples/tactical-rules.example.json` — 示例 snapshot；`A`。
- `investing-os/system/data/snapshots/examples/risk-limits.example.json` — 示例 snapshot；`A`。
- `investing-os/system/data/snapshots/examples/watchlist-metadata.example.json` — 示例 snapshot；`A`。
- `investing-os/system/data/snapshots/examples/signal-interpretation.example.json` — 示例 snapshot；`A`。
- `investing-os/system/data/snapshots/examples/degraded-mode.example.json` — 示例 snapshot；`A`。
- `investing-os/system/data/snapshots/broker/ibkr-readonly-broker-supplement-us-2026-06-05.md` — broker 补充说明；`R`。
- `investing-os/system/data/snapshots/broker/ibkr-readonly-broker-report-local-2026-06-09-us-2026-06-08.md` — broker 只读报告样本；`A`。

##### market-context corpus

- `investing-os/system/data/market-context/2026-06-05-major-drawdown/*` — `RUNTIME-SAMPLE`；同一事件的市场上下文证据语料，包含 `SPY/QQQ/VIX/NVDA/MU/COHR/...` 的 daily/5min JSON 以及 summary markdown/json；这些是高价值历史证据语料，但不是当前主契约；`R`。

#### 5.12.5 system/traceability/

- `investing-os/system/traceability/schema.md` — `TRACE`；traceability 统一 schema，关键旧资产；`K`。
- `investing-os/system/traceability/reports-index.json` — `TRACE`；报告索引；`K`。
- `investing-os/system/traceability/lesson-index.json` — `TRACE`；lesson 索引；`K`。
- `investing-os/system/traceability/file-lineage-index.json` — `TRACE`；文件血缘索引；`K`。
- `investing-os/system/traceability/capability-history.json` — `TRACE`；能力演化索引；`K`。
- `investing-os/system/traceability/lessons/CAND-2026-06-06-001-profit-streak-overconfidence.md` — 候选教训；`R`。
- `investing-os/system/traceability/lessons/CAND-2026-06-06-002-short-term-stop-no-trade.md` — 候选教训；`R`。
- `investing-os/system/traceability/lessons/CAND-2026-06-06-003-red-permission-state.md` — 候选教训；`R`。
- `investing-os/system/traceability/lessons/CAND-2026-06-06-004-thesis-instrument-split.md` — 候选教训；`R`。
- `investing-os/system/traceability/lessons/CAND-2026-06-06-005-rs-rebound-tactic.md` — 候选教训；`R`。

#### 5.12.6 system/simulations/

这里不是运行主链，而是演练/fixture 层。

- `investing-os/system/simulations/2026-06-06-brain-muscle-daily-scenario-simulation.md` — `SIM`；场景演练说明；`R`。
- `investing-os/system/simulations/inputs/*` — `SIM`；Stage0/1、intraday guidance、watchlist 等模拟输入与 replay fixture；`A/R`，适合作测试样例，不适合作 canonical 运行状态。
- `investing-os/system/simulations/outputs/stage1-plan-evidence-packet.MU-NVDA.demo.md` — `SIM`；演示输出；`A`。

#### 5.12.7 system/runtime/

这些不是旧系统主资产，而是历史运行样本：

- `investing-os/system/runtime/README.md`
- `investing-os/system/runtime/coordinator-decisions/trading-2026-06-15.json`
- `investing-os/system/runtime/sessions/trading-2026-06-15.json`
- `investing-os/system/runtime/trade-history/*`
- `investing-os/system/runtime/inputs/*`
- `investing-os/system/runtime/packets/*`

统一归类：`RUNTIME-SAMPLE`；作用是帮助恢复历史运行态、理解产物形状、做回归样本；不应与 canonical 文档混淆；`A/R`。

### 5.13 handoff/

`handoff/` 不是旧系统“认知主资产”本身，但它是迁移和审计历史层。

文件族判断：

- `investing-os/handoff/README.md`、`handoff-protocol.md`、`walkthrough.md`、`phase-tracker.md` — `HANDOFF`；迁移/交接协议；`R`。
- `investing-os/handoff/inventory/*` — `HANDOFF`；旧 `stock_team` 吸收、盘点、phase 报告；`R`。
- `investing-os/handoff/reviews/*`、`daily-audit/*`、`decisions/*` — `HANDOFF`；审核与批准链；`R`。
- `investing-os/handoff/2026-06-*`、`2026-07-*`、`CURRENT-CONTEXT.zh.md`、`repository-audit-2026-06-30.md` 等 — `HANDOFF`；阶段性任务/审计/恢复材料；`R`。

结论：

- `handoff/` 很重要，但属于“工程记忆层”，不是最终产品层；
- 不能和 workflow / cognition / dashboard 主资产混在同一优先级。

### 5.14 legacy stock_team dashboard/runtime 资产

这些文件虽然不在 `investing-os/` 下，但和旧系统主入口直接耦合，必须一起看。

- `stock_team/server/dashboard_server.py` — `LEGACY-RUNTIME`；API + Web 入口 + coordinator action + snapshot form + dashboard bridge 的超级入口；`T`；本轮真实接线很多都落在这里。
- `stock_team/server/dashboard_writer.py` — `LEGACY-RUNTIME`；旧 dashboard 上下文构造器；`T`。
- `stock_team/server/dashboard_cache.py` — `LEGACY-RUNTIME`；last-successful operational cache；`R/T`。
- `stock_team/server/dashboard_experience_loop.py` — `LEGACY-RUNTIME`；基于路径体验问题的修正回路，非常有价值但本轮几乎没接管；`R/T`。
- `stock_team/server/dashboard_experience_paths.py` — `LEGACY-RUNTIME`；体验路径定义；`R`。
- `stock_team/server/generate_watchlist_ui.py` — `LEGACY-RUNTIME`；早期 watchlist console 编译器；`A/R`。
- `stock_team/server/report_viewer.py` — `LEGACY-RUNTIME`；研究报告 HTML 阅读器；`R`。
- `stock_team/templates/daily_dashboard.html.j2` — `LEGACY-RUNTIME`；旧运行面主模板；`T`。
- `stock_team/templates/scripts.js.j2` — `LEGACY-RUNTIME`；旧运行面交互层；`R/T`。
- `stock_team/templates/styles.css.j2` — `LEGACY-RUNTIME`；旧运行面样式层；`R/T`。
- `stock_team/templates/report.html.j2` — `LEGACY-RUNTIME`；报告模板；`R`。
- `stock_team/templates/report_discussion.html.j2` — `LEGACY-RUNTIME`；圆桌脑暴纪要模板；`R`。

---

## 6. 这轮到底复用了什么，没复用什么

### 6.1 真正复用到的

- 脑-肌边界概念；
- `investing-os` / `stock_team` 职责划分；
- workflow 命名、Stage/DAILY 契约语言；
- 一部分 packet / schema / session-state 思路；
- `dashboard_server.py` 作为现成接线点。

### 6.2 没有系统性复用到的

- `operating-console.html` 作为真正主入口；
- `growth-dashboard-draft.html` 作为真正认知 dashboard；
- `generate-growth-dashboard-data.ps1` 及其索引链；
- review HTML → lesson lineage → growth dashboard 的完整旧闭环；
- `stock_team` 的 writer / template / cache / experience loop 整体运行面。

---

## 7. 接下来最该做的不是“继续盲修”，而是两条线并行

### 线 A：继续修当前 DAILY 主链

这条线解决“今天到底能不能跑”。

### 线 B：旧系统资产接管审计（二轮）

这条线解决“为什么已经有一堆成熟东西却没真正进入主系统”。

第二轮建议聚焦三个主题：

1. `operating-console.html` 是否恢复为正式主入口。
2. `growth-dashboard-draft.html + generate-growth-dashboard-data.ps1 + traceability indexes` 是否恢复为正式认知 dashboard 链。
3. `dashboard_server.py / dashboard_writer.py / daily_dashboard.html.j2` 是否拆成更干净的 runtime surface，而不是继续一边修 DAILY 一边往里堆。

---

## 8. 最终判断

旧系统不是空白，也不是几份零散笔记。

它已经具备：

- 主脑身份层；
- 决策与认知内核；
- 协议化工作流；
- packet / schema / snapshot / traceability 契约；
- 认知 dashboard 产品面；
- 运行 dashboard legacy 体系；
- 大量已吸收的原则、案例、研究与复盘资产。

所以后续工作不该再默认成“从头搭”。

更准确的项目策略应该是：

> 在修当前 DAILY 主链的同时，把旧系统成熟资产重新识别、重新定级、重新接管。
