# 旧系统拆解附录 C：Wiki + Templates

日期：2026-07-06

作用：

- 细拆长期知识层和结构化模板层；
- 回答“旧系统的认知、研究、案例、原则到底是不是已经沉淀好了”；
- 区分 canonical wiki、source/inbox、模板层。

---

## 1. 总判断

这一块说明旧系统不只是协议，也不只是页面。

它已经有：

- 长期知识 wiki；
- active principles；
- journals / historical cases；
- 公司与行业 dossier；
- source absorption 层；
- 配套模板层。

最重要的判断：

1. `wiki/principles/*` 已经不是草稿，而是 active principle 层。
2. `wiki/journals/*`、`wiki/historical-cases/*`、`wiki/sources/*` 已经构成了 review → case → principle → source absorption 的知识体系。
3. `templates/*` 不是普通参考文案，而是把主脑流程变成结构化输入输出的表单层。

---

## 2. 分类代码

- `TPL-CANON`：结构化模板主资产
- `WIKI-CANON`：长期知识 canonical 层
- `WIKI-CASE`：历史案例层
- `WIKI-JOURNAL`：日记/复盘层
- `WIKI-SOURCE`：source review / absorption 层
- `WIKI-INBOX`：待吸收来源层
- `WIKI-METHOD`：方法论层

---

## 3. templates/

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/templates/README.md` | `TPL-CANON` | 模板层总入口 | `R` |
| `investing-os/templates/brain-request.md` | `TPL-CANON` | 主脑请求模板 | `R` |
| `investing-os/templates/chatgpt-review-prompt.md` | `TPL-CANON` | AI 复盘提示模板 | `R` |
| `investing-os/templates/company-research.md` | `TPL-CANON` | 公司研究模板 | `R` |
| `investing-os/templates/contextual-trade-review.md` | `TPL-CANON` | 情境化交易复盘模板 | `R` |
| `investing-os/templates/daily-report.md` | `TPL-CANON` | 日报模板 | `R` |
| `investing-os/templates/event-reconstruction-request.json` | `TPL-CANON` | 事件重构请求模板 | `R` |
| `investing-os/templates/falsification.md` | `TPL-CANON` | 证伪模板 | `R` |
| `investing-os/templates/historical-case.md` | `TPL-CANON` | 历史案例模板 | `R` |
| `investing-os/templates/import-source-note.md` | `TPL-CANON` | 来源吸收模板 | `R` |
| `investing-os/templates/industry-research.md` | `TPL-CANON` | 行业研究模板 | `R` |
| `investing-os/templates/intraday-guidance-sheet.md` | `TPL-CANON` | 盘中指导表单 | `K` |
| `investing-os/templates/intraday-guidance-to-stock-team.json` | `TPL-CANON` | 主脑→肌肉 guidance 结构桥 | `K` |
| `investing-os/templates/journal-entry.md` | `TPL-CANON` | 日记模板 | `R` |
| `investing-os/templates/lesson-lineage.md` | `TPL-CANON` | lesson 血缘模板 | `K` |
| `investing-os/templates/packet-review.md` | `TPL-CANON` | packet 吸收模板 | `R` |
| `investing-os/templates/post-market-review.md` | `TPL-CANON` | 盘后复盘模板 | `R` |
| `investing-os/templates/post-market-trade-evidence-request.json` | `TPL-CANON` | 盘后事实请求模板 | `K` |
| `investing-os/templates/pre-market-decision-sheet.json` | `TPL-CANON` | Stage 1 决策单 | `K` |
| `investing-os/templates/pre-market-plan.md` | `TPL-CANON` | 盘前计划模板 | `K` |
| `investing-os/templates/pre-market-universe.json` | `TPL-CANON` | Stage 0 universe 模板 | `K` |
| `investing-os/templates/principle.md` | `TPL-CANON` | principle 模板 | `R` |
| `investing-os/templates/principle-candidate.md` | `TPL-CANON` | principle candidate 模板 | `R` |
| `investing-os/templates/review-report-standard.md` | `TPL-CANON` | 标准复盘报告模板 | `K` |
| `investing-os/templates/risk-checklist.md` | `TPL-CANON` | 风险检查模板 | `R` |
| `investing-os/templates/signal-review.md` | `TPL-CANON` | 信号复核模板 | `R` |
| `investing-os/templates/stock-team-evidence-request.md` | `TPL-CANON` | 肌肉证据请求模板 | `R` |
| `investing-os/templates/tactic-event-summary-request.json` | `TPL-CANON` | 战术事件总结请求模板 | `R` |
| `investing-os/templates/thesis.md` | `TPL-CANON` | 论点模板 | `R` |
| `investing-os/templates/trade-plan.md` | `TPL-CANON` | 交易计划模板 | `R` |
| `investing-os/templates/trading-day-plan.md` | `TPL-CANON` | 交易日计划模板 | `K` |
| `investing-os/templates/valuation.md` | `TPL-CANON` | 估值模板 | `R` |
| `investing-os/templates/weekend-review.md` | `TPL-CANON` | 周末复盘模板 | `R` |

判断：

- 模板层已经很完整；
- 当前 DAILY 重做并不是从“没有表单结构”的状态开始的。

---

## 4. wiki 根层

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/README.md` | `WIKI-CANON` | 长期知识层入口 | `K` |

---

## 5. wiki/principles

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/principles/README.md` | `WIKI-CANON` | principles 体系入口 | `K` |
| `investing-os/wiki/principles/PRIN-001-leveraged-tool-discipline.md` | `WIKI-CANON` | active principle | `K` |
| `investing-os/wiki/principles/PRIN-002-hand-feel-trade-limit.md` | `WIKI-CANON` | active principle | `K` |
| `investing-os/wiki/principles/PRIN-003-profit-taking-cooling-period.md` | `WIKI-CANON` | active principle | `K` |
| `investing-os/wiki/principles/PRIN-004-sector-sympathy-rules.md` | `WIKI-CANON` | active principle | `K` |
| `investing-os/wiki/principles/PRIN-005-vwap-volume-rules.md` | `WIKI-CANON` | active principle | `K` |
| `investing-os/wiki/principles/PRIN-006-cognitive-attention-budget.md` | `WIKI-CANON` | active principle | `K` |
| `investing-os/wiki/principles/candidates/README.md` | `WIKI-CANON` | principle candidate 容器说明 | `R` |

判断：

- 这一层已是 durability 层，不是 inbox；
- 是认知系统最应该继续继承的部分之一。

---

## 6. wiki/methodologies

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/methodologies/README.md` | `WIKI-METHOD` | 方法论目录 | `R` |
| `investing-os/wiki/methodologies/company-research-14-dimensions.md` | `WIKI-METHOD` | 公司研究方法论 | `K` |
| `investing-os/wiki/methodologies/ai-swing-valuation-temperature.zh.md` | `WIKI-METHOD` | 估值方法候选 | `R` |

---

## 7. wiki/industries

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/industries/README.md` | `WIKI-CANON` | 行业知识目录入口 | `R` |
| `investing-os/wiki/industries/ai-sector-map.md` | `WIKI-CANON` | 板块地图 / active methodology note | `K` |
| `investing-os/wiki/industries/ai-gpu-compute.md` | `WIKI-CANON` | 行业研究吸收结果 | `R` |
| `investing-os/wiki/industries/physical-ai.md` | `WIKI-CANON` | 行业研究吸收结果 | `R` |
| `investing-os/wiki/industries/industry-dossier-template.md` | `WIKI-CANON` | industry dossier 模板 | `R` |

---

## 8. wiki/companies

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/companies/README.md` | `WIKI-CANON` | 公司知识目录入口 | `R` |
| `investing-os/wiki/companies/company-dossier-template.md` | `WIKI-CANON` | dossier 模板 | `R` |
| `investing-os/wiki/companies/COHR.md` | `WIKI-CANON` | 公司 dossier | `R` |
| `investing-os/wiki/companies/COHR.zh.md` | `WIKI-CANON` | 中文 dossier | `R` |
| `investing-os/wiki/companies/COHR-valuation-temperature.zh.md` | `WIKI-CANON` | valuation 温度记录 | `R` |
| `investing-os/wiki/companies/INTC.md` | `WIKI-CANON` | 公司 dossier | `R` |
| `investing-os/wiki/companies/ORCL.md` | `WIKI-CANON` | 公司 dossier | `R` |

---

## 9. wiki/journals

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/journals/README.md` | `WIKI-JOURNAL` | 日志/复盘目录入口 | `R` |
| `investing-os/wiki/journals/2026-06-04-daily-review.md` | `WIKI-JOURNAL` | 历史日复盘 | `R` |
| `investing-os/wiki/journals/2026-06-04-snxx-fill-review.md` | `WIKI-JOURNAL` | fill review | `R` |
| `investing-os/wiki/journals/2026-06-04-snxx-contextual-review.md` | `WIKI-JOURNAL` | contextual review | `R` |
| `investing-os/wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md` | `WIKI-JOURNAL` | exit review | `R` |
| `investing-os/wiki/journals/2026-06-05-major-drawdown-review.md` | `WIKI-JOURNAL` | 系统级高价值复盘 | `K` |
| `investing-os/wiki/journals/2026-06-08-market-rebound-cognition-review.md` | `WIKI-JOURNAL` | 认知复盘草稿 | `R` |

---

## 10. wiki/historical-cases

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/historical-cases/README.md` | `WIKI-CASE` | 历史案例目录入口 | `R` |
| `investing-os/wiki/historical-cases/CASE-001-cohr-profit-taking.md` | `WIKI-CASE` | 正式案例资产 | `R` |
| `investing-os/wiki/historical-cases/CASE-002-crdu-fomo-pullback.md` | `WIKI-CASE` | 正式案例资产 | `R` |
| `investing-os/wiki/historical-cases/CASE-003-pltr-trend-switch-exit.md` | `WIKI-CASE` | 正式案例资产 | `R` |
| `investing-os/wiki/historical-cases/CASE-004-snxx-attention-capture.md` | `WIKI-CASE` | 正式案例资产 | `R` |

---

## 11. wiki/sources

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/sources/README.md` | `WIKI-SOURCE` | source review 目录入口 | `R` |
| `investing-os/wiki/sources/packet-review-COHR-2026-06-05.md` | `WIKI-SOURCE` | packet review 吸收记录 | `R` |
| `investing-os/wiki/sources/packet-review-COHR-2026-06-05.zh.md` | `WIKI-SOURCE` | 中文 packet review 吸收记录 | `R` |
| `investing-os/wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md` | `WIKI-SOURCE` | 外部 backtest 证据吸收 | `R` |

---

## 12. wiki/inbox

这一层是“待吸收来源层”，不是最终 canonical 层。

### 12.1 inbox 根说明

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/inbox/README.md` | `WIKI-INBOX` | inbox 规则说明 | `R` |

### 12.2 inbox/system

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/inbox/system/README_zh.md` | `WIKI-INBOX` | 中文旧系统 wiki 入口 | `R` |
| `investing-os/wiki/inbox/system/00_system_overview_zh.md` | `WIKI-INBOX` | 原始系统总纲 | `R` |
| `investing-os/wiki/inbox/system/02_portfolio_framework_zh.md` | `WIKI-INBOX` | 原始仓位框架 | `R` |
| `investing-os/wiki/inbox/system/03_daily_workflow_zh.md` | `WIKI-INBOX` | 原始每日流程 | `R` |
| `investing-os/wiki/inbox/system/04_company_research_method_zh.md` | `WIKI-INBOX` | 原始公司研究法 | `R` |

### 12.3 inbox/reports

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/inbox/reports/05_market_sector_map_zh.md` | `WIKI-INBOX` | 原始板块地图来源 | `R` |
| `investing-os/wiki/inbox/reports/AI_GPU_compute_industry_2026-05-26.md` | `WIKI-INBOX` | 原始行业长文来源 | `R` |
| `investing-os/wiki/inbox/reports/Physical_AI_industry_2026-05-26.md` | `WIKI-INBOX` | 原始行业长文来源 | `R` |

### 12.4 inbox/principles

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/inbox/principles/leveraged_tool_rules_zh.md` | `WIKI-INBOX` | 原始原则来源 | `R` |
| `investing-os/wiki/inbox/principles/hand_feel_trade_zh.md` | `WIKI-INBOX` | 原始原则来源 | `R` |
| `investing-os/wiki/inbox/principles/profit_taking_regret_loop_zh.md` | `WIKI-INBOX` | 原始原则来源 | `R` |
| `investing-os/wiki/inbox/principles/sector_sympathy_catalyst_zh.md` | `WIKI-INBOX` | 原始原则来源 | `R` |
| `investing-os/wiki/inbox/principles/vwap_volume_confirmation_zh.md` | `WIKI-INBOX` | 原始原则来源 | `R` |

### 12.5 inbox/cases

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/inbox/cases/2026-06-02_cohr_profit_taking_zh.md` | `WIKI-INBOX` | 原始案例来源 | `R` |
| `investing-os/wiki/inbox/cases/2026-06-02_crdu_fomo_pullback_zh.md` | `WIKI-INBOX` | 原始案例来源 | `R` |
| `investing-os/wiki/inbox/cases/2026-06-02_pltr_trend_switch_exit_zh.md` | `WIKI-INBOX` | 原始案例来源 | `R` |

### 12.6 inbox/ai

| 文件 | 分类 | 实际角色 | 处置 |
|---|---|---|---|
| `investing-os/wiki/inbox/ai/01_ai_usage_protocol_zh.md` | `WIKI-INBOX` | 原始 AI 使用协议 | `R` |
| `investing-os/wiki/inbox/ai/answer_checklist_zh.md` | `WIKI-INBOX` | 原始 AI 回答检查表 | `R` |
| `investing-os/wiki/inbox/ai/llm_controller_discipline_zh.md` | `WIKI-INBOX` | 原始 LLM 控制纪律 | `R` |
| `investing-os/wiki/inbox/ai/low_model_boundary_zh.md` | `WIKI-INBOX` | 原始低阶模型边界 | `R` |

---

## 13. 本块最终结论

wiki + templates 这一块说明：

- 旧系统已经有长期知识层；
- 也已经有 active principle 层；
- 还已经有把 workflow 压成结构化模板的输入输出层；
- 所以当前新系统并不是从“没有知识库和没有表单”的空地上重建。

更准确地说：

> 旧系统的知识沉淀已经足够深，当前最缺的是把这些沉淀重新接回现行 workflow 和 dashboard，而不是重写一份新的知识壳。

