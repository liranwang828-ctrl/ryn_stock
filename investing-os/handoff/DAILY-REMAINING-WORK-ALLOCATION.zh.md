# DAILY 剩余工作与模型分工

日期：2026-07-01
依据：

- `system/workflows/DAILY-CONTRACT.zh.md`
- `handoff/reviews/2026-07-01-daily-implementation-review.md`
- `handoff/decisions/2026-07-01-daily-q1-q3-approval.md`

## 当前判断

现有代码是一批有价值的候选实现，171 项限定测试通过，但 DAILY 仍为 `partial`。

接下来不应由高阶模型包办所有编码，也不能继续让低阶模型自主推进整条链。正确协作方式是：

```text
高阶模型定义一个窄契约和验收场景
→ 低阶模型用 TDD 实现一个任务
→ 高阶模型审查语义、接线和越界
→ 从公开入口运行回归
→ 审核通过后才更新状态
```

## 必须由高阶模型负责

### H1 跨日恢复状态矩阵

高阶模型必须先定义每种旧状态如何处理：

- `INTRADAY_ACTIVE`
- `OBSERVATION_ACTIVE`
- `MARKET_CLOSED`
- `REVIEW_REQUIRED`
- 盘前中断状态
- `FAILED_TOOL`
- 多个未关闭会话
- 损坏或无法验证的 session

必须明确 freeze、quick_review、full_review 的进入条件、用户确认、结束状态和是否允许创建今日会话。

低阶模型不能自行决定这些状态语义。

### H2 归档契约

高阶模型必须定义：

- 归档只读取 session artifact ledger 中登记的文件；
- manifest schema；
- canonical archive 路径；
- 重名文件处理；
- 缺失、哈希不符和敏感文件处理；
- `archive_day` 成功的完成条件。

低阶模型不能自行决定哪些账户或交易文件可以复制。

### H3 Observation 动作契约

高阶模型必须决定 coordinator 对外动作名称和状态转换。

Dashboard 的 `allowed_actions`、action schema、`ACTION_INTENTS`、transition 和 adapter 必须使用同一契约。不得把底层 CLI 命令名直接混入 coordinator action。

### H4 DAILY-4 对话产物

用户已经批准“对话为主、结构化产物为结果”。高阶模型需要定义：

- 复盘问题；
- 用户确认点；
- 结构化产物 schema；
- 噪声、经验候选和 LEARNING 候选的边界；
- 无 IBKR 正式成交事实时的阻断与欠账。

低阶模型不得生成心理结论、教训或论点状态。

### H5 最终 E2E 验收

高阶模型必须审查并运行公开入口全链：

```text
coordinator_cli / Operating Console
→ coordinator
→ stock_team adapter
→ 固定产物
→ 用户确认闸门
→ observation 或 trading 路径
→ DAILY-4
→ archive manifest
→ 次日恢复
```

测试不能直接调用中间 helper 来假装生产链完成。

## 低阶模型可以胜任

以下任务必须由高阶模型先写清输入、输出、允许文件和验收命令，之后可以交给低阶模型。

### L1 Observation 动作一致性

适合低阶模型。

工作：

- 根据 H3 修改 action schema、models、transitions、adapter 和测试；
- 保证 Dashboard 暴露的每个 action 都能通过 coordinator；
- 保证 observation 永远不能授予交易权限。

### L2 白名单归档接线

适合低阶模型实现，高阶模型重点审核。

工作：

- 按 H2 重写 archiver 输入；
- 由 coordinator 的 `archive_day` 调用；
- 生成并登记 manifest；
- 添加缺失、哈希冲突、重名和越界路径测试。

### L3 跨日恢复实现

适合低阶模型按状态矩阵逐项实现，不适合让其自行设计。

工作：

- 修复 full_review 提前创建今日会话；
- 实现 quick_review 最低检查；
- 支持 `REVIEW_REQUIRED` 和盘前中断；
- 处理多个旧会话；
- 损坏 session 必须显式阻断而不是静默跳过；
- 每个路径使用用户确认并记录 processed action。

### L4 非交易日路径

适合低阶模型。

工作：

- 按已批准契约实现无交易日正常关闭；
- 不制造交易、复盘或经验记录；
- 添加状态和 CLI 测试。

### L5 DAILY-4 结构化产物骨架

部分适合低阶模型。

低阶模型可以：

- 实现高阶模型已定义的 schema；
- 添加模板、校验器、路径和持久化；
- 写缺失字段和版本测试。

低阶模型不能：

- 设计复盘问题；
- 自动判断心理偏差；
- 自动批准经验吸收。

### L6 公开入口 E2E 测试

适合低阶模型编写初稿，高阶模型验收。

必须：

- 只从 CLI、coordinator 或 server API 进入；
- 不直接调用 archiver 等中间 helper；
- 覆盖 trading、observation、no-trade、freeze、quick_review、full_review 和失败恢复；
- 使用明确标记的模拟数据；
- 验证产物、状态、哈希和用户确认记录。

### L7 Dashboard 与 runtime manifest 对接

适合低阶模型。

工作：

- 消除 HTML 消费路径和 CLI 生产路径不一致；
- 读取 coordinator 登记的 canonical manifest；
- 显示 freshness、模式、权限和缺失数据；
- 不在 Dashboard 内产生第二份状态。

## 推荐执行顺序

```text
高阶 H1 + H2 + H3
→ 低阶 L1
→ 低阶 L2
→ 低阶 L3
→ 高阶 H4
→ 低阶 L4 + L5
→ 低阶 L7
→ 低阶 L6
→ 高阶 H5
```

L1、L2、L3 都会触及 coordinator 相关文件，不应并行修改同一分支。应使用独立分支顺序合入，每次合入后运行回归。

## 对低阶模型能力的评估

### 已表现出的优势

- 能快速执行范围明确的文档和代码任务；
- 能补充大量单元测试和保持测试绿；
- 能按文件边界提交独立 commit；
- 对机械性 schema、CLI、adapter、状态枚举和测试工作效率较高；
- 收到具体审核意见后，修订速度快。

### 已表现出的限制

- 会把“测试通过”误认为“完整流程完成”；
- 容易直接调用 helper 编写看似 E2E、实际绕过生产接线的测试；
- 会在没有用户确认时自行批准用户决策；
- 会把设计候选变成既定状态机语义；
- 对跨组件接线、恢复语义和正式数据来源的审查不足；
- 会在状态台账中夸大完成度。

### 适用定位

低阶模型当前适合：

```text
有明确契约、文件范围、失败测试和验收命令的实现者
```

不适合：

```text
系统架构师
交易状态机决策者
用户批准代理
最终集成审核者
完成状态裁定者
```

粗略评价：

- 窄范围编码与测试：较强；
- 文档和机械性迁移：较强；
- 跨模块接线：中等，需要重点审核；
- 状态机与恢复语义：偏弱；
- 自主判断完成度：不可靠；
- 遵守用户确认闸门：不可靠，必须由系统和高阶审核约束。

## 协作结论

剩余工作约七成编码和测试仍可交给低阶模型，但任务设计、状态语义、数据边界和最终验收必须由高阶模型掌握。

高阶模型下一步不是亲自重写所有代码，而是先完成 H1–H3 的窄契约和任务单，再把 L1–L3 依次交给低阶模型。
