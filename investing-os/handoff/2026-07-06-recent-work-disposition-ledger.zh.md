# 近期已完成工作的处置台账

日期：2026-07-06
范围：2026-07-01 至 2026-07-06 已完成的 DAILY / H4 / Stage0 / 旧系统审计相关工作

目的：

1. 回答“这两天已经做好的部分怎么办”。
2. 防止在“旧 `investing-os` 全量优先复用”原则下，把近期成果误当成废案。
3. 明确哪些成果继续保留，哪些只是过渡桥，哪些以后需要回收或合并。

---

## 0. 处置分类

本台账统一使用四类：

- `KEEP`
  - 继续保留为当前项目有效成果；
  - 不因旧系统复用原则而作废。
- `TRANSITIONAL`
  - 作为过渡层继续保留；
  - 当前仍有用，但未来应被旧系统 canonical 资产吸收、替换或下沉。
- `MERGE-BACK`
  - 当前成果有价值，但最终应合并回旧 `investing-os` canonical 资产，而不是长期并列存在。
- `RETIRE-LATER`
  - 当前先保留；
  - 等接管路线明确、回归护栏建立后，再考虑下线、归档或仅保留历史记录。

---

## 1. 总判断

这几天做的工作不应该被理解成“白做”或“推翻重来”。

它们的真实价值主要有四类：

1. 把 DAILY 契约、状态机和脑-肌边界说清楚了；
2. 把真实运行时会卡住的点暴露出来了；
3. 把高低阶协作、审计、review、任务分发方法跑通了；
4. 建立了未来接管旧系统时所需的回归护栏。

因此：

- 文档类成果大部分应保留；
- 审计和 blocker 类成果应保留；
- 测试与回归护栏应保留；
- 一部分最近新增的接线逻辑应视为过渡桥，而不是最终产品本体。

---

## 2. KEEP：继续保留为当前有效成果

### 2.1 DAILY 契约与审计骨架

- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`
- `investing-os/handoff/daily-audit/DAILY-AUDIT-0.md`
- `investing-os/handoff/daily-audit/DAILY-AUDIT-1.md`
- `investing-os/handoff/daily-audit/DAILY-AUDIT-2.md`
- `investing-os/handoff/daily-audit/DAILY-AUDIT-3.md`
- `investing-os/handoff/daily-audit/DAILY-AUDIT-4.md`
- `investing-os/handoff/reviews/2026-07-01-daily-implementation-review.md`
- `investing-os/handoff/decisions/2026-07-01-daily-q1-q3-approval.md`

原因：

- 这些文件定义了当前 DAILY 的合法顺序、状态口径、阻断点和用户已批准决策；
- 即便后面全面接回旧 `investing-os`，这些也仍然是“这轮实现与验收发生过什么”的正式记录。

### 2.2 H4 / review / archive 相关修补链

- `e36b770` 对应的 H4 修补成果
- 与 H4 相关的 review 文件与测试护栏
- `investing-os/handoff/2026-07-01-daily-h4-review-contract.zh.md`
- `investing-os/handoff/2026-07-01-daily-h4-task-packets.zh.md`

原因：

- 它们澄清了 daily4 review、artifact ledger、archive 门控的真实要求；
- 后续无论接不接旧系统，这些闸门都仍然有回归价值。

### 2.3 真实运行 blocker 记录

- `investing-os/handoff/2026-07-03-stage0-real-run-blockers-charter.zh.md`
- `investing-os/handoff/2026-07-03-stage0-real-run-blockers-task-packets.zh.md`
- `investing-os/handoff/2026-07-06-stage0-brain-precondition-blocker.zh.md`
- `investing-os/handoff/2026-07-06-stage0-brain-precondition-task-packet.zh.md`

原因：

- 它们不是设想，而是真跑后暴露出的阻断事实；
- 是接回旧系统前必须保留的现场证据。

### 2.4 旧系统接管审计与原则确认

- `investing-os/handoff/2026-07-06-old-system-asset-audit.zh.md`
- `investing-os/handoff/2026-07-06-old-system-audit-dashboards-tools.zh.md`
- `investing-os/handoff/2026-07-06-old-system-audit-system-layer.zh.md`
- `investing-os/handoff/2026-07-06-old-system-audit-wiki-templates.zh.md`
- `investing-os/handoff/decisions/2026-07-06-old-system-reuse-principle.md`

原因：

- 这些文件把“旧系统确实完整”和“`investing-os` 默认全量优先复用”正式写进了仓库；
- 这是项目方向，不是临时讨论。

### 2.5 协作治理方法

- `investing-os/handoff/LOW-TOKEN-REVIEW-TEMPLATE.zh.md`
- 近期所有高低阶任务包、repair charter、review handoff 模板

原因：

- 它们已经形成可复用的协作协议；
- 后续继续接管旧系统时仍然要用。

---

## 3. TRANSITIONAL：作为过渡桥继续保留

### 3.1 Stage0 from snapshot 过桥链

涉及提交：

- `6500238` — 引入 `start_stage0_from_snapshot`
- `aa17a22` — dashboard/coordinator 动作选择接线
- `b79ce9c` — coordinator 隔离验收与 E2E 回归
- `2220118` — `new_trading_session.allowed_actions` 修补
- `3dbe9b8` — `--as-of` adapter tests 回归护栏

涉及文档：

- `investing-os/handoff/2026-07-02-stage0-from-snapshot-design.zh.md`
- `investing-os/handoff/2026-07-02-stage0-from-snapshot-task-packets.zh.md`

处置：`TRANSITIONAL`

原因：

- 这条链并不是没价值；
- 它解决的是“当前主链还没全面接回旧系统时，怎样让 Stage0 勉强能从 formal snapshot 起步”；
- 但长期看，它很可能会被恢复后的旧 `investing-os` 主入口 / workflow / dashboard 吸收。

### 3.2 dashboard/coordinator 层的临时动作选择逻辑

包括但不限于：

- `dashboard_server.py` 中为 formal-ready / from-snapshot 增加的分支；
- 与 `start_stage0_from_snapshot` 绑定的第一动作推断逻辑。

处置：`TRANSITIONAL`

原因：

- 这些逻辑当前有用；
- 但以后如果恢复旧 `operating-console` 作为正式主入口，它们大概率不该继续以现在这种形态常驻。

---

## 4. MERGE-BACK：有价值，但最终应并回旧 canonical 资产

### 4.1 新 DAILY 契约中的旧系统重述部分

对象：

- `DAILY-CONTRACT.zh.md` 中那些其实与旧 `pre-market` / `trading-day` / `command-router` / `intraday-guidance-protocol` 高度重叠的契约表达

处置：`MERGE-BACK`

原因：

- 这些内容现在有必要；
- 但长期不应形成两套平行 canonical 描述；
- 未来应重新合并回旧 `investing-os/system/workflows/*` 的正式体系。

### 4.2 近期围绕 Stage0、DAILY、brain precondition 的解释性文档

对象：

- repair charter
- task packets
- implementation notes
- blocker explanation docs

处置：`MERGE-BACK`

原因：

- 这些文档本身应保留；
- 但其中沉淀出的“真正持久规则”未来应该并回 canonical workflow / contract / checklist，而不是只留在 handoff 层。

### 4.3 新发现的 brain-side precondition 要求

关键字段：

- `positions`
- `prior_review`
- `cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

处置：`MERGE-BACK`

原因：

- 这些不是一次性 blocker；
- 它们本质上属于旧 `investing-os` 主脑输入契约的一部分；
- 未来应写回正式 canonical input contract，而不只是 blocker 文档里提到。

---

## 5. RETIRE-LATER：先保留，后续再回收

### 5.1 仅为补洞而存在、且与旧系统正式入口重复的中间说明

对象特征：

- 它只为解释当前临时链路；
- 与旧 `investing-os` canonical 页面/协议重复；
- 没有独立长期价值。

当前策略：

- 现在不删；
- 等 canonical 接管路线稳定后，再决定归档。

### 5.2 如果旧 `investing-os` 正式接回后失去存在必要的过桥逻辑

对象：

- 某些仅服务于 `start_stage0_from_snapshot` 的路径分支；
- 某些仅服务于“当前 dashboard 先凑合跑”的入口判断。

当前策略：

- 现在先留；
- 等旧主入口恢复、回归测试齐全后，再决定是否退休。

---

## 6. 代码与测试层的处置口径

### KEEP

- 真实新增的回归测试
- H4 / archive / review file 相关测试
- Stage0 from snapshot adapter/coordinator/E2E 回归测试

原因：

- 即使未来替换入口或回接旧页面，这些测试仍然能保护行为不倒退。

### TRANSITIONAL

- 为当前链路补的接线代码
- 为 formal-ready / snapshot 起步加的临时入口逻辑

原因：

- 当前必须存在；
- 长期可能被更正统的旧系统接管方案替换。

### RETIRE-LATER

- 未来若被旧 canonical 入口完全替代的局部判断分支

原因：

- 这些分支的存在价值取决于接管后的新旧接口是否仍并存。

---

## 7. 操作原则

从本台账开始，后续对最近成果的默认处理顺序如下：

1. 先不删；
2. 先分类；
3. 先判断它是“项目知识成果”还是“临时代码桥”；
4. 只有在旧系统 canonical 资产真正接回后，才考虑回收临时桥。

换句话说：

> 这几天做的工作，默认不是废案，而是接管旧系统之前的勘测、桥接、验证和护栏。

---

## 8. 最终判断

在“`investing-os` 默认全量优先复用”的新原则下，最近几天的成果不该被粗暴处理成：

- 全部继续原样推进；或
- 全部推翻重做。

更准确的处置方式是：

- 审计、契约、blocker、测试、决策记录：保留；
- 过桥接线：继续保留但降级为过渡层；
- 其中沉淀出的长期规则：未来并回旧 canonical；
- 真正失去存在理由的临时桥：等接管完成后再退休。

