# DAILY 现有文件内容级分类台账

日期：2026-07-11

标签：

- `reuse-now`：首轮 DAILY 直接使用；
- `merge-later`：有价值，但应在主链跑通后合并；
- `reference-only`：规范、示例或测试证据；
- `retire-later`：重复或被替代，未经用户单独批准不得删除。

## Canonical brain/workflow

| 文件 | 内容级职责与证据 | 分类 |
|---|---|---|
| `system/workflows/DAILY-CONTRACT.zh.md` | DAILY-0..4 顺序、确认点、产物、失败恢复与 brain-muscle 边界 | `reuse-now` |
| `system/workflows/pre-market.md` | Stage 0 前置认知、universe、Stage 0→讨论→Stage 1→计划顺序 | `reuse-now` |
| `system/workflows/intraday.md` | IBKR streaming primary、pull fallback、snapshot contract | `reuse-now` |
| `system/workflows/intraday-guidance-protocol.md` | 认知投影、权限状态、Dashboard split 和 manifest 契约 | `reuse-now` |
| `system/workflows/post-market-trade-review.md` | 事实包、用户访谈、lesson extraction 与 archive | `reuse-now` |
| `templates/pre-market-universe.json` | Stage 0 universe 与五项脑侧前置 canonical 结构 | `reuse-now` |
| `templates/pre-market-decision-sheet.json` | 标的角色、行动模式、manual confirm、exception 与风险预算的丰富 canonical 模板 | `reuse-now` |
| `templates/intraday-guidance-to-stock-team.json` | investing-os 权限投影到 stock_team evidence monitor 的 contract | `reuse-now` |
| `system/data/packets/pre-market-context-packet.md` | Stage 0 packet 边界与 brain-owned preconditions | `reuse-now` |
| `system/data/packets/intraday_snapshot.md` | 盘中事实输出说明/样本 | `reference-only` |
| `system/data/packets/intraday-dashboard-packet.md` | 旧 dashboard packet contract，可辅助统一 manifest 设计 | `reference-only` |

## Orchestration and factual production

| 文件 | 内容级职责与证据 | 分类 |
|---|---|---|
| `stock_team/orchestration/models.py` | session/action/daily4 schema 与 constructors | `reuse-now` |
| `stock_team/orchestration/transitions.py` | DAILY 状态转换与确认动作集合 | `reuse-now` |
| `stock_team/orchestration/adapters.py` | Stage 0/1、focus/plan validation、intraday CLI adapter | `reuse-now` |
| `stock_team/orchestration/coordinator.py` | 执行、artifact ledger、exception、review、archive gates | `reuse-now` |
| `stock_team/orchestration/protocol.py` | canonical runtime root 与 DAILY-4 path；目前范围很薄 | `merge-later` |
| `stock_team/cli.py` | 实际盘前、Stage 0/1、盘中 snapshot/evidence dashboard 生产器；首轮只复用相关 handlers | `reuse-now` |

## Daily trading Dashboard/runtime

| 文件 | 内容级职责与证据 | 分类 |
|---|---|---|
| `dashboards/operating-console.html` | investing-os 主入口；已有 workflow/entry/task 展示，但含主动推进按钮 | `reuse-now` |
| `dashboards/assets/operating-console-data.js` | operating console 静态 view model、workflow 与 links | `reuse-now` |
| `stock_team/server/dashboard_server.py` | 现成 API、Stage 0 universe/snapshot、current task 与 coordinator summary 接线点；职责过大 | `reuse-now` |
| `dashboards/intraday-dashboard.html` | 直接轮询 intraday snapshot 的账户、持仓、alerts monitor | `merge-later` |
| `dashboards/latest_evidence_dashboard.html` | Stage 0/1 readiness、source health 与标的 evidence 条件展示 | `merge-later` |
| `stock_team/server/dashboard_writer.py` | legacy daily context 聚合、fallback/cache、focus readiness、learning state | `merge-later` |
| `stock_team/templates/daily_dashboard.html.j2` | legacy 成熟日内 UI、symbol drilldown 与导航 | `merge-later` |
| `stock_team/server/dashboard_cache.py` | last-successful operational cache；降级显示有用，但不能成为正式事实 | `merge-later` |
| `stock_team/server/dashboard_experience_paths.py` | 四条 Dashboard 用户体验路径与修复上限 | `reference-only` |
| `stock_team/server/dashboard_experience_loop.py` | 自动生成体验 round、检测 UI 问题与有限修复建议 | `reference-only` |

## Cognition Dashboard

| 文件 | 内容级职责与证据 | 分类 |
|---|---|---|
| `dashboards/growth-dashboard-draft.html` | 结构图、lineage、报告、能力雷达、任务；实际是可用认知 Dashboard | `reuse-now` |
| `dashboards/assets/growth-dashboard-data.js` | cognition/decision/execution/evolution 静态结构和说明 | `reuse-now` |
| `dashboards/assets/growth-dashboard-indexes.js` | reports/lessons/file-lineage/capability-history 聚合数据 | `reuse-now` |
| `tools/generate-growth-dashboard-data.ps1` | 从四个 traceability JSON 生成 indexes JS | `reuse-now` |

## Tests used as evidence

| 文件 | 证明的能力 | 分类 |
|---|---|---|
| `tests/unit/orchestration/test_models.py` | action/session/daily4 schema | `reference-only` |
| `tests/unit/orchestration/test_transitions.py` | Stage 0/1、intraday、review/archive transitions | `reference-only` |
| `tests/unit/orchestration/test_adapters.py` | 命令构造、as-of、focus/plan validation | `reference-only` |
| `tests/unit/orchestration/test_coordinator.py` | exception、daily4、archive gates 和 artifacts | `reference-only` |
| `tests/unit/orchestration/test_coordinator_cli.py` | 跨日恢复矩阵 | `reference-only` |
| `tests/unit/core/test_dashboard_refresh_prices.py` | Stage 0 action、entry_state、summary 与 snapshot 路径 | `reference-only` |
| `tests/integration/test_daily_e2e.py` | coordinator DAILY 主链与 observation 路径 | `reference-only` |
| `tests/integration/test_dashboard_experience_loop.py` | legacy dashboard 体验验收工具 | `reference-only` |

## 当前未分配 `retire-later` 的原因

本批次没有发现仅凭已读内容就可安全判定应退役的文件。多个页面存在职责重叠，但 `intraday-dashboard`、`latest_evidence_dashboard` 和 legacy daily dashboard 仍分别包含独有的事实监控、evidence health、focus/readiness 与 drilldown 能力，因此先标记 `merge-later`。任何 `retire-later` 结论必须等首个真实 DAILY pass 证明替代链完整后再提出，且不得自动删除。
