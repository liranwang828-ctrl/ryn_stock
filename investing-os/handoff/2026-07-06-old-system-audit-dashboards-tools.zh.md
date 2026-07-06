# 旧系统拆解附录 A：Dashboards + Tools

日期：2026-07-06

作用：

- 细拆旧系统产品面；
- 区分成品页面、桥接页面、报告阅读页、前端数据层、生成脚本；
- 回答“旧 dashboard 到底哪些是成品，哪些只是 demo”。

---

## 1. 总判断

这一块不是“做过几个页面”。

它实际上已经包含：

1. 一个主入口：`operating-console.html`
2. 一个认知成长面：`growth-dashboard-draft.html`
3. 一个盘中面：`intraday-dashboard.html`
4. 一个 evidence bridge 页：`latest_evidence_dashboard.html`
5. 报告阅读页与片段页
6. 对应的前端数据层 JS
7. 报告/认知 dashboard 的生成脚本

最重要的判断：

- `operating-console.html` 和 `growth-dashboard-draft.html` 都应按“成品级旧资产”看待；
- `generate-growth-dashboard-data.ps1` 不是随手脚本，而是旧认知 dashboard 的数据刷新链；
- 当前重做并没有真正接管这条产品线。

---

## 2. 分类代码

- `DASH-CANON`：应保留为 canonical 的旧产品资产
- `DASH-BRIDGE`：桥接/承接页面
- `DASH-DEMO`：展示样本
- `DASH-READ`：报告阅读层
- `DASH-DATA`：前端 view-model / index 数据层
- `TOOL-GEN`：生成器脚本
- `TOOL-GOV`：治理脚本

处置建议：

- `K` = 保留为主资产
- `R` = 参考吸收
- `T` = 接管式重构
- `A` = 归档

---

## 3. 文件级台账

| 文件 | 分类 | 实际内容角色 | 判断 | 处置 |
|---|---|---|---|---|
| `investing-os/dashboards/operating-console.html` | `DASH-CANON` | 主入口页面，内含 hero、workflow steps、coordinator/task、snapshot、认知区与导航逻辑 | 成品，不是 demo | `K` |
| `investing-os/dashboards/growth-dashboard-draft.html` | `DASH-CANON` | 认知成长 dashboard，内含 structure map、lesson lineage inspector、capability radar、report archive、current tasks | 成品，不应当作草图废弃 | `K` |
| `investing-os/dashboards/intraday-dashboard.html` | `DASH-DEMO` | 独立盘中监控面，说明旧系统已考虑 intraday 可视面 | 有价值，但成熟度低于前两者 | `R` |
| `investing-os/dashboards/latest_evidence_dashboard.html` | `DASH-BRIDGE` | 承接 `stock_team` evidence dashboard 的本地页面 | 适合做 bridge，不适合做主入口 | `R` |
| `investing-os/dashboards/reports/2026-06-05-major-drawdown-review.html` | `DASH-READ` | 已生成的系统级复盘报告 HTML 阅读页 | 证明旧系统已有“复盘阅读面” | `R` |
| `investing-os/dashboards/reports/intraday-guidance-demo.html` | `DASH-DEMO` | intraday guidance 展示样本 | 可作交互原型参考 | `R` |
| `investing-os/dashboards/report-fragments/RPT-2026-06-05-MAJOR-DRAWDOWN.zh.html` | `DASH-READ` | 中文阅读片段页 | 说明 report fragments 体系存在 | `R` |
| `investing-os/dashboards/assets/operating-console-data.js` | `DASH-DATA` | operating console 的 view-model，含入口、permission、路线和任务信息 | 页面数据层，不是杂项脚本 | `K` |
| `investing-os/dashboards/assets/growth-dashboard-data.js` | `DASH-DATA` | growth dashboard 的静态认知视图数据，含 lesson、tasks、permission、structure graph 等 | 认知 dashboard 的数据蓝本 | `K` |
| `investing-os/dashboards/assets/growth-dashboard-indexes.js` | `DASH-DATA` | reports / lessons / fileLineage / capabilityHistory 的聚合索引 | 接近“认知 dashboard 读模型层” | `K` |
| `investing-os/tools/generate-growth-dashboard-data.ps1` | `TOOL-GEN` | 将 traceability 索引编译为前端 JS，刷新 growth dashboard 数据源 | 关键生成链，不是普通脚本 | `K` |
| `investing-os/tools/generate-report-html.ps1` | `TOOL-GEN` | 将 markdown 报告转成 HTML 阅读页 | 报告阅读层生成器 | `R` |
| `investing-os/tools/check-file-growth.ps1` | `TOOL-GOV` | 按软/硬阈值检查 md 文件膨胀 | 仓库治理工具 | `R` |

---

## 4. 深层判断

### 4.1 哪些文件说明“旧系统已经有产品面”

- `operating-console.html`
- `growth-dashboard-draft.html`
- `operating-console-data.js`
- `growth-dashboard-data.js`
- `growth-dashboard-indexes.js`

这五个文件一起说明：

- 旧系统不是只有协议文档；
- 它已经有主入口、认知入口、前端数据层和索引层；
- 缺的不是“有没有页面”，而是“有没有把这些页面重新接上现行主链”。

### 4.2 哪些文件说明“旧系统已经形成阅读闭环”

- `generate-report-html.ps1`
- `dashboards/reports/2026-06-05-major-drawdown-review.html`
- `dashboards/report-fragments/RPT-2026-06-05-MAJOR-DRAWDOWN.zh.html`

它们说明旧系统已经有：

- 报告归档；
- HTML 阅读面；
- 中文片段层；
- 可以与 growth dashboard 回链的阅读体验。

### 4.3 哪些文件说明“旧系统已经形成认知 dashboard 数据刷新链”

- `system/traceability/*.json`
- `generate-growth-dashboard-data.ps1`
- `dashboards/assets/growth-dashboard-indexes.js`
- `growth-dashboard-draft.html`

也就是说，旧认知 dashboard 不是单页静态 mock，而是已有数据来源与刷新脚本。

---

## 5. 接管建议

### A 级：优先恢复为正式主资产

- `investing-os/dashboards/operating-console.html`
- `investing-os/dashboards/growth-dashboard-draft.html`
- `investing-os/dashboards/assets/operating-console-data.js`
- `investing-os/dashboards/assets/growth-dashboard-data.js`
- `investing-os/dashboards/assets/growth-dashboard-indexes.js`
- `investing-os/tools/generate-growth-dashboard-data.ps1`

### B 级：保留为桥接与参考

- `investing-os/dashboards/latest_evidence_dashboard.html`
- `investing-os/dashboards/intraday-dashboard.html`
- `investing-os/dashboards/reports/intraday-guidance-demo.html`
- `investing-os/tools/generate-report-html.ps1`

### C 级：保留为治理或历史辅助

- `investing-os/tools/check-file-growth.ps1`
- `investing-os/dashboards/report-fragments/RPT-2026-06-05-MAJOR-DRAWDOWN.zh.html`
- `investing-os/dashboards/reports/2026-06-05-major-drawdown-review.html`

---

## 6. 本块最终结论

旧系统在 dashboard/product 面上已经不算起步阶段。

更准确地说：

- 主入口已经做过；
- 认知 dashboard 已经做过；
- 报告阅读层已经做过；
- 认知索引生成链已经做过；
- 当前缺的是“把这些旧成品重新接回现行主链”，不是从零重新发明页面。

