# 最小可用入口与 Stage0 接回设计

> **状态**：设计稿，待用户审阅  
> **范围**：先让系统“真正用起来”，优先复用现有 `investing-os + stock_team`，不先全面重构  
> **关联台账**：
> - [`../../../handoff/2026-07-06-old-system-asset-audit.zh.md`](../../../handoff/2026-07-06-old-system-asset-audit.zh.md)
> - [`../../../handoff/decisions/2026-07-06-old-system-reuse-principle.md`](../../../handoff/decisions/2026-07-06-old-system-reuse-principle.md)
> - [`../../../handoff/2026-07-06-investing-os-takeover-priority-ledger.zh.md`](../../../handoff/2026-07-06-investing-os-takeover-priority-ledger.zh.md)
> - [`../../../handoff/2026-07-06-recent-work-disposition-ledger.zh.md`](../../../handoff/2026-07-06-recent-work-disposition-ledger.zh.md)

---

## 1. 设计目标

这份设计不追求先把所有 canonical / contract / schema 一次性整理干净。

第一目标只有一个：

> 让现有系统基于 `investing-os + stock_team` 形成一条真正可用的最小主链，让用户能进入系统、看到当天状态、知道卡点、并继续下一步。

这里的“可用”定义为：

1. 用户有唯一入口；
2. 系统能显示当天所处模式和步骤；
3. 系统能显示 readiness / blocker / missing items；
4. 系统能给出唯一最主要的 next action；
5. 所有接入文件都同时打上用途标签，为后续筛选“有用/无用文件”做准备。

---

## 2. 非目标

这份设计当前明确不做以下事情：

1. 不先全面重构 `stock_team/server/dashboard_server.py`、`dashboard_writer.py`、`daily_dashboard.html.j2`；
2. 不先统一整个旧系统所有 contract、workflow、handoff 的重复表述；
3. 不先把所有 Stage0 precondition 全部沉到最终 canonical contract；
4. 不先做完整的 growth dashboard 接回；
5. 不先清理所有旧文件。

这些都重要，但都排在“先用起来”之后。

---

## 3. 核心设计判断

### 3.1 入口先统一，不先求完整

用户入口优先直接复用：

- `investing-os/dashboards/operating-console.html`
- `investing-os/dashboards/assets/operating-console-data.js`

理由：

- 旧 `operating-console` 已经是成品级主入口；
- 相比继续把零散 CLI / dashboard action 当用户入口，恢复旧主入口更符合“`investing-os` 全量优先复用”原则；
- 入口统一后，后续无论接 Stage0、DAILY、review 还是 growth，都有稳定承载面。

### 3.2 `stock_team` 继续提供事实，`investing-os` 负责解释事实

这条主线不改变脑-肌边界。

`stock_team` 继续负责：

- session / coordinator 运行状态
- snapshot / formal-ready / readiness 判断
- market context / evidence / packet / runtime state
- 现有 dashboard 相关运行产物

`investing-os` 继续负责：

- 当前模式是什么
- 当前在哪一步
- 是否能继续
- 卡在哪
- 用户下一步该补什么

一句话：

> `stock_team` 提供事实与运行态，`investing-os` 把它解释成“今天怎么继续”。

### 3.3 先把 Stage0 precondition 变成“可见缺口”，再沉回 canonical contract

近期已经确认的 Stage0 brain-side preconditions 包括：

- `positions`
- `prior_review`
- `cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

但在这一阶段，它们不先被当成一大套纯契约工程。

它们先转化为用户可见的缺口清单，例如：

- 缺昨日复盘
- 缺权限状态
- 缺持仓事实确认
- 缺 today session
- 缺正式 snapshot

这样做的好处：

- 系统先能告诉用户“为什么不能继续”；
- 后续再把这些缺口正式回写到 `pre-market-universe.json`、`pre-market.md`、`pre-market-context-packet.md`；
- 避免一上来只做架构约束，系统却仍然跑不起来。

---

## 4. 最小可用主链

目标主链：

```text
用户进入 investing-os/operating-console
→ operating-console 读取现有 runtime/evidence state
→ 页面显示 today mode / current step / readiness / missing items / next action
→ 用户按 next action 继续当天流程
```

这条链第一阶段只要求“解释与引导可用”，不要求“所有下游动作一键完成”。

---

## 5. 第一批接入的现有产物

### 5.1 主入口壳

接入：

- `investing-os/dashboards/operating-console.html`
- `investing-os/dashboards/assets/operating-console-data.js`

角色标签：

- `canonical-entry`

作用：

- 成为用户唯一正式入口；
- 承载 today mode / current step / readiness / missing items / next action 五块核心信息。

### 5.2 当天 session / coordinator 状态

接入来源：

- 现有 `stock_team` session / coordinator 输出
- 已存在的 runtime session 状态文件或等价状态来源

角色标签：

- `runtime-source`

作用：

- 回答是否已有今日会话；
- 当前会话在哪一步；
- 当前 next action 是什么；
- 当前是不是 blocked / review required / ready。

### 5.3 当天 snapshot / formal-ready 状态

接入来源：

- 当前 formal snapshot / pre-market snapshot 相关产物
- 现有 dashboard/coordinator 已经在使用的 readiness 判断来源

角色标签：

- `evidence-source`

作用：

- 回答今天有没有可启动的 snapshot；
- 是 `ready / partial / blocked` 哪种状态；
- 缺的是 snapshot 本体，还是 formal-ready 判定条件。

### 5.4 当天 evidence / packet 状态

接入来源：

- `market-context`
- `plan-evidence`
- `runtime-monitor`
- `post-market` / `review` 相关 packet
- 相关 manifest / packet path

角色标签：

- `evidence-source`

作用：

- 回答 Stage0 / Stage1 / review 相关事实包是否存在；
- 帮助生成 missing items 与 next action。

### 5.5 blocker / gate / 缺口说明来源

接入来源：

- 当前 DAILY 状态台账
- 已确认的 blocker 文档
- 已知 gate / review required / failed tool 状态

角色标签：

- `active-constraint`

作用：

- 不重新发明缺口解释体系；
- 直接把最近这轮已经确认过的 blocker 变成用户可见缺口说明。

---

## 6. 第一批先不深碰的文件

### 6.1 暂不全面重构的 legacy runtime

文件：

- `stock_team/server/dashboard_server.py`
- `stock_team/server/dashboard_writer.py`
- `stock_team/server/dashboard_cache.py`
- `stock_team/templates/daily_dashboard.html.j2`

角色标签：

- `legacy-runtime`

当前策略：

- 第一批先消费它们的已有运行状态或已有产物；
- 不先在这些大文件里做深度结构改造。

原因：

- 它们价值高，但已明显膨胀；
- 当前阶段若先深挖，很容易又回到“边补边堆”。

### 6.2 暂不进入主链的大量参考层

包括：

- 大量 `handoff` 历史记录
- 大量 `wiki/inbox`
- 大量 dated packet examples / simulation fixtures

角色标签：

- `reference-only`

当前策略：

- 先保留；
- 只在解释 blocker、对照历史、做文件筛选时引用；
- 不放入第一批最小主链。

---

## 7. 页面第一批只显示的 5 个核心信息

为了避免又做成一个大而全 dashboard，第一批页面只显示 5 项。

### 7.1 Today Mode

显示值示例：

- `trading`
- `observation`
- `review`
- `maintenance`

作用：

- 用户一眼知道今天当前是何种运行模式。

### 7.2 Current Step

显示值示例：

- `DAILY-0`
- `DAILY-1`
- `DAILY-2`
- `REVIEW_REQUIRED`
- `FAILED_TOOL`

作用：

- 用户知道系统当前处于哪一步，而不是只看见一个抽象的 dashboard。

### 7.3 Readiness

显示值示例：

- `ready`
- `partial`
- `blocked`

作用：

- 简化当前状态，不要求用户先理解底层全部状态机。

### 7.4 Missing Items

限制：

- 最多显示 3–5 条

示例：

- 缺昨日复盘
- 缺 permission state
- 缺正式 snapshot
- 缺 market context

作用：

- 把复杂 precondition 先转成用户可补的缺口，而不是先转成抽象 contract。

### 7.5 Next Action

规则：

- 只显示一个最主要 next action

示例：

- 补 yesterday review
- 生成或确认 pre-market snapshot
- 进入 Stage0
- 进入 review_day

作用：

- 系统必须告诉用户“接下来干什么”，而不是只展示状态。

---

## 8. 文件筛选准备：统一标签体系

为了让后续能够筛选“有用文件 / 无用文件 / 过渡桥文件”，第一批接入时同步给文件打用途标签。

统一标签：

- `canonical-entry`
- `runtime-source`
- `evidence-source`
- `active-constraint`
- `legacy-runtime`
- `reference-only`

再配合已有状态分类：

- `keep`
- `transitional`
- `merge-back`
- `retire-later`

后续筛文件时，标准就不是“看起来像有用”，而是：

1. 它是否进入最小可用主链；
2. 在主链里扮演什么角色；
3. 是长期 canonical，还是短期桥接；
4. 接回旧系统后是否还有存在理由。

---

## 9. 第一批实施边界

第一批设计落地时，应严格限制为：

1. 恢复并接线 `operating-console`；
2. 读取现有 session / snapshot / packet / blocker 状态；
3. 显示 5 个核心信息；
4. 给接入文件打标签；
5. 不先扩大成完整重构工程。

这意味着第一批不做：

- growth dashboard 全量恢复
- `stock_team` legacy runtime 深度拆分
- handoff / workflow / contract 的全面去重
- 所有 precondition 的最终 schema 化

---

## 10. 与已有近期成果的关系

这份设计与近期成果并不冲突。

相反，它给最近几天的成果提供了归宿：

- `DAILY-CONTRACT.zh.md` 继续保留为当前实施契约与状态机台账；
- blocker 文档继续作为 `active-constraint` 来源；
- `start_stage0_from_snapshot` 继续保留为 `transitional` 过桥逻辑；
- 新入口恢复后，再决定哪些桥逻辑继续存在、哪些退休。

也就是说：

> 近期成果不是作废，而是变成最小主链的解释层、护栏层和过渡层。

---

## 11. 风险与控制

### 风险 1：又做成一个大而全 dashboard

控制：

- 第一批只允许显示 5 项核心信息；
- 不先做完整多模块大屏。

### 风险 2：过早重构 `stock_team` 大文件

控制：

- 第一批只消费已有产物；
- 不先拆 `dashboard_server.py` / `dashboard_writer.py`。

### 风险 3：只做界面，不解决真实卡点

控制：

- Missing Items 和 Next Action 必须直接来自现有 runtime/evidence/blocker 状态；
- 不允许只做静态页面。

### 风险 4：又回到只写约束、不让系统跑

控制：

- precondition 第一阶段先显示为用户可见缺口；
- contract 回写放在后续批次。

---

## 12. 推荐后续顺序

若本 spec 获批，后续建议执行顺序为：

1. 写 implementation plan
2. 第一批只做最小入口接线
3. 验证 operating-console 是否能稳定显示 5 项核心信息
4. 再进入 Stage0 precondition 的 canonical 回写
5. 最后再推进 growth dashboard 与 legacy runtime 接管

---

## 13. 一句话总结

这份设计的核心不是“先把系统整理正确”，而是：

> 先利用现有 `investing-os + stock_team` 做出一个真正能告诉用户“今天怎么继续”的最小入口，同时为后续筛有用/无用文件和逐步接管旧系统做好标签与边界准备。

