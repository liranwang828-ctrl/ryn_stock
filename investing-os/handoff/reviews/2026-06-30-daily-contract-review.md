# DAILY 契约高阶审核记录

日期：2026-06-30
审核对象：commit `93306e2`
结论：`changes_required`

## 已核验交付

- `DAILY-AUDIT-0` 至 `DAILY-AUDIT-4` 五个 commit 均只新增各自审计报告，没有修改业务代码或共享契约。
- `93306e2` 只新增 `DAILY-CONTRACT.zh.md` 并修改 `WORKFLOW-STATUS.zh.md`，没有代码改动。
- 五份报告记录合计 89 tests passed、0 failed；本次审核核对了报告中的命令与结果，但没有把该数字当作 DAILY 可运行的证明。
- 契约保持“待批准”状态，并列出了八项高阶决策，结构可以作为修订基础。

## 阻断问题

### R1 — `record_plan_approval` 的 bug 结论不成立

涉及：

- `DAILY-AUDIT-1.md`
- `DAILY-CONTRACT.zh.md` 已知冲突 2、H4
- `WORKFLOW-STATUS.zh.md` DAILY-1

报告认为 `complete_transition()` 没有为 `record_plan_approval` 添加成功映射，因此状态不会进入 `PLAN_APPROVED`。实际执行顺序是：

```text
begin_transition("STAGE1_READY", "record_plan_approval")
→ "PLAN_APPROVED"

complete_transition("PLAN_APPROVED", "record_plan_approval", success=True)
→ "PLAN_APPROVED"
```

协调器在调用 adapter 前已保存 `PLAN_APPROVED`。本次直接运行上述两个函数得到：

```text
begin= PLAN_APPROVED
complete= PLAN_APPROVED
```

因此 H4 不是待修 bug。不得向低阶模型派发“为 SUCCESS_TRANSITIONS 添加 record_plan_approval 映射”的任务。

### R2 — 缓存不能替代 IBKR 正式账户与交易事实

涉及：

- DAILY-0 允许降级路径和失败恢复
- DAILY-4 失败恢复

契约允许 IBKR 不可达时使用缓存 `positions.json` 或日末成交缓存继续确认。行动纲领规定 IBKR 是持仓与交易记录的唯一正式来源。

缓存只能：

- 以 `stale_unverified` 或等价状态只读展示；
- 帮助用户回忆和排查；
- 进入观察、维护或延后复盘路径。

缓存不得：

- 完成正式账户事实确认；
- 授予新风险权限；
- 作为正式成交事实完成复盘或经验吸收；
- 冒充 IBKR 获取结果。

### R3 — observation 模式被错误截断

契约规定 observation 只到 DAILY-1 的市场环境证据包，不进入 DAILY-2/3；又规定无批准计划时 DAILY-2 不可用。

统一架构原文规定：

- Observation 可以刷新市场事实，但不存在新增交易授权；
- 没有已批准计划时，盘中只能进入观察模式。

因此 observation 应允许进入 DAILY-2/3 的事实观察路径，但必须：

- 不授予交易权限；
- 不生成或改写交易计划；
- 不改写盘前锚点；
- 不把观察状态升级为 trading。

具体状态表达仍需用户与高阶模型决定。

### R4 — 低阶 Task 6 提前作出了高阶决定

原计划明确 Task 6 由“高阶模型 + 用户”执行。当前契约在“已知冲突”中多次使用“决定”，包括：

- 以当前代码路径为 canonical 路径；
- 保持 DAILY-2 隐式状态；
- 添加 9:30–10:00 强制闸门；
- 指定 IBKR 与行情供应商分工；
- 保留 `post_open_adj` 并规定写入者；
- 要求 Dashboard server 创建盘中 JSON；
- 增加多个复盘状态和归档机制。

这些内容可以保留为“候选修正”，但在用户批准前不能称为决定，也不能作为低阶实现任务依据。

### R5 — 经验候选的所有权越过 Brain–Muscle 边界

DAILY-4 收尾链写为 `stock_team` 生成 lesson、thesis status 等经验候选。

`stock_team` 可以生成成交匹配、价格对比、执行偏差等事实证据；经验意义、心理归因、论点状态和教训候选应由 `investing-os` 在用户参与下形成。契约需要拆开：

```text
stock_team：复盘事实包
investing-os：解释、分类和候选经验草稿
用户：确认结论与是否进入 LEARNING
```

### R6 — 全局 `data_source` schema 要求尚无批准依据

契约要求所有产物都新增必填 `data_source` 字段，但没有列出受影响 schema、兼容策略或既有产物迁移范围。

这可以作为数据真实性设计候选，不能在本契约中直接升级为所有产物的生效要求。应先盘点 DAILY 固定产物，再由高阶模型决定统一 provenance envelope 或逐 schema 扩展。

## 非阻断修订

- “状态机修正清单”应改名为“候选修正清单”，逐项标注 `verified_bug`、`missing_capability` 或 `design_decision`。
- 当前代码路径不能因为“实际存在”就自动成为 canonical 路径；canonical runtime 路径应独立决策。
- 9:30–10:00 是原 Node 2 的时间节奏，是否作为硬拒绝条件需要用户确认。迟到恢复和非美东时区操作不能被无意阻断。
- `WORKFLOW-STATUS.zh.md` 中的下一动作应引用审核记录，删除 H4，并避免在契约批准前写成确定实现方案。

## 接受标准

修订版契约必须：

1. 删除不存在的 H4 bug；
2. 明确缓存账户与成交仅可作非正式参考；
3. 为 observation 保留 DAILY-2/3 的只读事实路径；
4. 把未经批准的“决定”降级为候选方案；
5. 恢复 `stock_team` 只产事实、`investing-os` 产解释与经验候选的边界；
6. 把 provenance schema 作为待批准设计，不直接要求全量迁移；
7. 将真正需要用户决定的问题整理成少量、可逐个回答的选项；
8. 经用户逐段批准后，才允许拆分代码任务。

## 下一步

先修订文档，不改业务代码。修订完成后由高阶模型再次审核，再把必要的用户决策逐项提交用户确认。
