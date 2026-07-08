# 第一批入口接线文件标签台账

日期：2026-07-08
状态：第一批最小入口接线标签

---

## 1. 标签说明

- `canonical-entry`
  - 用户正式入口壳
- `runtime-source`
  - 当前运行状态来源
- `evidence-source`
  - 当前 snapshot / packet / readiness 来源
- `active-constraint`
  - 当前 blocker / gate / missing items 来源
- `legacy-runtime`
  - 当前先消费、不深改的旧 runtime 资产
- `reference-only`
  - 当前不进入主链，只作历史/参考

处置状态沿用：

- `keep`
- `transitional`
- `merge-back`
- `retire-later`

---

## 2. 第一批接线文件

| file | tag | disposition | reason |
|---|---|---|---|
| `investing-os/dashboards/operating-console.html` | `canonical-entry` | `keep` | 用户正式入口壳，第一批直接承载 today status，并保留 growth / review / principles 接回空间 |
| `investing-os/dashboards/assets/operating-console-data.js` | `canonical-entry` | `keep` | 入口 view-model，适合加入最小 entry-state shape |
| `stock_team/server/dashboard_server.py` | `runtime-source` | `transitional` | 当前先作为只读状态聚合来源 |
| `stock_team/server/dashboard_writer.py` | `legacy-runtime` | `reference-only` | 本批不深改，只在必要时参考现有数据组织 |
| `stock_team/server/dashboard_cache.py` | `legacy-runtime` | `reference-only` | 本批不深改，只在必要时参考缓存结构 |
| `stock_team/templates/daily_dashboard.html.j2` | `legacy-runtime` | `reference-only` | 当前不作为主入口，只作旧运行面对照 |
| `investing-os/handoff/2026-07-06-stage0-brain-precondition-blocker.zh.md` | `active-constraint` | `keep` | 当前真实 blocker 来源之一 |
| `investing-os/handoff/2026-07-06-recent-work-disposition-ledger.zh.md` | `active-constraint` | `keep` | 近期成果处置与 bridge 定位依据 |
| `investing-os/handoff/2026-07-08-entry-source-map.zh.md` | `active-constraint` | `keep` | 第一批来源映射台账 |

---

## 3. 当前不进入第一批主链的文件族

| file family | tag | disposition | reason |
|---|---|---|---|
| `investing-os/wiki/inbox/*` | `reference-only` | `keep` | 作为来源层保留，但不进入第一批入口接线 |
| `investing-os/system/simulations/*` | `reference-only` | `keep` | 作为 fixture / replay 参考，不进入口主链 |
| `investing-os/handoff/daily-audit/*` | `reference-only` | `keep` | 作为审计依据保留，不直接作为 UI 数据源 |
| `investing-os/system/runtime/*` 历史样本 | `reference-only` | `keep` | 作为历史运行样本保留，不当作实时主源 |

---

## 4. 第一批后续预期

第一批完成后，应能据此继续筛：

- 哪些文件已经进入最小主链，属于高价值保留
- 哪些文件只是过渡桥，需要后续 merge-back 或退休
- 哪些文件当前只保留参考，不应再继续膨胀
