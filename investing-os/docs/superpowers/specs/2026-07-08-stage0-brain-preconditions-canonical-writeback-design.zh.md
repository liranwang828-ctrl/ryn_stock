# Stage0 Brain Preconditions Canonical Writeback 设计

> **状态**：设计稿，待用户审阅  
> **范围**：把 Stage0 brain-side preconditions 从 blocker / 过桥层回写到 `investing-os` canonical 层  
> **关联文件**：
> - [`2026-07-08-minimal-usable-entry-and-stage0-design.zh.md`](./2026-07-08-minimal-usable-entry-and-stage0-design.zh.md)
> - [`../../../handoff/2026-07-06-stage0-brain-precondition-blocker.zh.md`](../../../handoff/2026-07-06-stage0-brain-precondition-blocker.zh.md)
> - [`../../../handoff/2026-07-06-investing-os-takeover-priority-ledger.zh.md`](../../../handoff/2026-07-06-investing-os-takeover-priority-ledger.zh.md)
> - [`../../../handoff/decisions/2026-07-06-old-system-reuse-principle.md`](../../../handoff/decisions/2026-07-06-old-system-reuse-principle.md)

---

## 1. 设计目标

这份设计只做一件事：

> 把已经在真实运行中暴露出来的 Stage0 brain-side preconditions，正式写回 `investing-os` 的 canonical workflow / template / packet contract。

这里的 preconditions 是：

- `positions`
- `prior_review`
- `cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

设计目标不是一次性整理完整 Stage0 所有 schema，而是先把这五个前提恢复成主脑正典的一部分。

---

## 2. 为什么现在要做

第一批最小入口已经实现了：

- 用户可以从 `operating-console` 进入；
- 可以看到 today mode / current step / readiness / missing items / next action；
- blocker 已经可以变成用户可见缺口。

但现在这些缺口还主要存在于：

- blocker 文档
- 过桥逻辑
- runtime 最小解释层

这还不够。

如果不把它们回写到 canonical 层，后面会持续出现三个问题：

1. Stage0 的真实前提只存在于“最近修出来的知识”里；
2. 新旧 workflow 会继续分裂；
3. `investing-os` 无法把这些前提稳定吸收到自己的成长系统里。

所以第二批最合理的动作不是继续扩 UI，也不是先重构 `stock_team`，而是把这五个前提写回主脑正式层。

---

## 3. 本批只改 3 个 canonical 落点

为避免扩散，这一批只碰 3 个文件：

1. [`investing-os/templates/pre-market-universe.json`](/C:/Users/rriww/Documents/STOCK/investing-os/templates/pre-market-universe.json)
2. [`investing-os/system/workflows/pre-market.md`](/C:/Users/rriww/Documents/STOCK/investing-os/system/workflows/pre-market.md)
3. [`investing-os/system/data/packets/pre-market-context-packet.md`](/C:/Users/rriww/Documents/STOCK/investing-os/system/data/packets/pre-market-context-packet.md)

不改的：

- `DAILY-CONTRACT.zh.md`
- `dashboard_server.py`
- `start_stage0_from_snapshot`
- 其它 schema / packet / review 文件

理由：

- 这三处分别代表结构、流程理由、brain→muscle 交接边界；
- 已经足够承接这五个 preconditions；
- 先不把变化扩散到消费层，避免又出现“还没定 canonical 就先到处补逻辑”。

---

## 4. 三个落点各自负责什么

### 4.1 `pre-market-universe.json`：定义结构

这是 Stage0 最直接的 brain-owned input 容器。

这一层负责回答：

- Stage0 开始前，主脑要交给系统的正式结构里必须有哪些前置字段；
- 哪些字段属于“看市场之前就已经存在的主脑状态”。

在这一层里，这五个 preconditions 不应再被理解为“可选补充”，而应被理解为：

> Stage0 brain input 的正式组成部分。

这份文件里应明确保留：

- `source_inputs.positions`
- `source_inputs.prior_review`
- `source_inputs.cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

并强调：

- 这不是交易权限列表；
- 这是 Stage0 market context universe 的主脑输入边界。

### 4.2 `pre-market.md`：定义流程理由

这份 workflow 文件负责回答：

- 为什么 Stage0 不能被理解成“拿到行情就开跑”；
- 为什么这些前提在盘前流程里必须先被装载。

它不负责定义字段 JSON 细节，而负责把规则从“blocker 经验”提升成正式流程语言：

- 先装载主脑已有状态；
- 再请求市场环境；
- 缺少关键主脑状态时，Stage0 只能停在不可正式继续的状态。

一句话：

- `pre-market-universe.json` 说“长什么样”
- `pre-market.md` 说“为什么必须这样”

### 4.3 `pre-market-context-packet.md`：定义交接边界

这份 packet contract 负责回答：

- 当主脑把 Stage0 market context 任务交给 `stock_team` 时，交接语义是什么；
- `stock_team` 能看到什么，不能改什么。

重点不是让 `stock_team` 拥有这些字段的解释权，而是明确：

- 这些字段属于 brain-owned preconditions；
- `stock_team` 只是在这些边界下生产 Stage0 市场环境证据；
- `stock_team` 不得反向改写 permission、forbidden、cognition judgment。

一句话：

- 这层负责“主脑前提如何传给肌肉，但仍然保持主脑所有权”。

---

## 5. 五个 preconditions 的最小语义

这一批不追求把字段做成超复杂模型，但至少要把语义收紧到不会再漂。

### 5.1 `positions`

最小语义：

- 当前正式持仓背景
- 这些持仓会影响今天 Stage0 该看哪些标的、哪些风险已经在账上

不能被理解为：

- 单纯的 watchlist
- 可由 `stock_team` 任意替代的候选股票池

### 5.2 `prior_review`

最小语义：

- 上一次复盘留下的未关闭风险、结论或限制

不能被理解为：

- 任意历史日记引用
- 可有可无的背景说明

### 5.3 `cognition_state`

最小语义：

- 当前主脑对认知/情绪/恢复状态的总结性输入

不能被理解为：

- 由 runtime 自动推断出的情绪结果
- `stock_team` 输出的心理判断

### 5.4 `permission_state_before_open`

最小语义：

- 今天盘前的权限底色

不能被理解为：

- 盘中由肌肉引擎临时授予的新权限

### 5.5 `forbidden_actions`

最小语义：

- 在今天当前主脑状态下，明确禁止的动作集合

不能被理解为：

- `stock_team` 根据行情临时编造的行动约束

---

## 6. 与现有最小入口的关系

这一批并不是推翻第一批最小入口。

关系应该是：

1. 第一批入口负责把缺口显示出来；
2. 第二批 canonical writeback 负责把这些缺口重新安家到正式主脑结构里；
3. 后续入口再逐渐从“最小解释层”切换为“直接读取 canonical contract 衍生状态”。

也就是说：

> 第一批让系统能说出缺什么；第二批让系统知道这些缺口本来就该写在哪。

---

## 7. 成长性要求

这一批必须继续服从 `investing-os` 成长性优先。

具体要求：

### G1. 不把 preconditions 留在临时 blocker 层

它们要回写进 canonical 层，才能继续进入：

- review
- lesson extraction
- principle update
- growth dashboard

### G2. 不让 `stock_team` 抢走主脑解释权

写回 packet contract 的目的是明确交接边界，而不是把 cognition / permission 的解释权外包。

### G3. 为后续文件筛选继续提供依据

这批完成后，后续就能更明确筛：

- 哪些文件是 canonical Stage0 输入
- 哪些文件只是 bridge / blocker / reference

---

## 8. 风险与控制

### 风险 1：改动再次扩散

控制：

- 本批只允许改 3 个文件；
- 其它消费层以后再同步。

### 风险 2：先写正典，系统又跑不动

控制：

- 不移除第一批最小入口；
- 先保留 blocker → UI 解释链；
- canonical 回写和最小入口并行存在一段时间。

### 风险 3：字段变成抽象口号

控制：

- 每个字段只定义“最小但收紧”的语义；
- 不一次性过度建模。

### 风险 4：又把 `DAILY-CONTRACT.zh.md` 当唯一正典

控制：

- 本批明确绕开 `DAILY-CONTRACT.zh.md`；
- 直接回写旧 `investing-os` canonical files。

---

## 9. 推荐后续顺序

如果这份 spec 获批，实施顺序建议是：

1. 先改 `pre-market-universe.json`
2. 再改 `pre-market.md`
3. 最后改 `pre-market-context-packet.md`
4. 改完后再回头决定最小入口要不要直接消费这些 canonical 字段

这样顺序最稳：

- 先有结构
- 再有流程理由
- 再有交接边界

---

## 10. 一句话总结

这份设计的本质不是“继续补 Stage0 bug”，而是：

> 把已经在真实运行中确认存在的 Stage0 主脑前提，重新写回 `investing-os` 自己的正式结构、正式流程和正式交接边界里，让系统既能继续用，又能继续成长。

