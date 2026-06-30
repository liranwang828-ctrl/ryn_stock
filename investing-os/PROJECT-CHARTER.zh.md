# 个人投资操作系统行动纲领

状态：当前项目级行动纲领
更新日期：2026-06-30

## 1. 项目为何存在

本项目不是自动交易机器人，也不是把许多分析脚本拼成一个 Dashboard。

它是：

```text
个人认知
× AI 放大器
× 纪律执行系统
```

系统首先服务于用户认知、判断和纪律的持续进化。收益、回撤和风险结果用于检验决策质量，但不能成为工具或模型取代用户判断的理由。

目标不是每天交易，而是每天让系统、认知和行动更清楚一点。

## 2. 一个产品，两个内核

用户面对一个系统，内部保留两个职责严格分离的内核。

### `investing-os`：主脑

负责：

- 用户认知、偏差和经验；
- 投资意义、研究问题与论点；
- 决策框架、风险边界和交易权限；
- 盘前计划、盘中指导与盘后复盘；
- 教训审核、规则晋升和知识谱系；
- 面向用户的主入口、对话和确认闸门。

### `stock_team`：肌肉

负责：

- 市场、账户和交易事实的获取；
- 指标、相对强度、波动、风险和规则碰撞计算；
- IBKR、行情供应商、缓存和数据质量；
- Evidence Packet、事实报告和 Dashboard 详情页；
- 回测、历史检验和研究数据整理。

`stock_team` 不得：

- 替用户决定买入、卖出或持有；
- 授予交易权限或改变风险预算；
- 采纳投资论点、心理判断或长期教训；
- 直接修改 `investing-os` 的认知和决策；
- 创建与主系统竞争的用户工作流。

## 3. 用户与 AI 的关系

用户负责：

- 提出真正关心的问题；
- 解释事实对自己的意义；
- 确认关注对象、权限、计划和例外；
- 作出最终交易判断并承担风险；
- 决定一次经验是否进入长期系统。

AI 与工具负责：

- 收集、计算、整理和核验事实；
- 暴露缺失数据、矛盾、风险和纪律偏离；
- 提供反方问题、历史对照和结构化复盘；
- 维持流程、状态、产物和可追溯性。

涉及意义、权限、计划批准、例外处理和教训吸收时，系统必须停下来等待用户确认。

## 4. 统一工作流语言

项目统一采用：

```text
工作流 → 步骤 → 产物
```

新文档和界面不再把 `Node`、`Stage`、技术形态阶段和实施 Phase 混作每日流程名称。

### 4.1 工作流目录

| 编号 | 名称 | 目的 |
|---|---|---|
| `DAILY` | 每日交易工作流 | 从晨间准备到盘后复盘 |
| `RESEARCH` | 投资研究工作流 | 公司、行业、主题、宏观和事件研究 |
| `REVIEW` | 周期复盘工作流 | 周度、月度、季度及专项复盘 |
| `LEARNING` | 经验进化工作流 | 教训审核、规则晋升和知识沉淀 |
| `VALIDATION` | 策略验证工作流 | 回测、历史类比、因子和战术验证 |
| `SYSTEM` | 系统维护工作流 | 数据、契约、运行状态和知识库维护 |

### 4.2 DAILY 每日交易工作流

| 编号 | 名称 | 旧称映射 |
|---|---|---|
| `DAILY-0` | 晨间准备 | `stock_team` Node 0 |
| `DAILY-1` | 盘前决策 | Node 1；内部使用原 Evidence Stage 0/1 产物 |
| `DAILY-2` | 开盘观察 | Node 2 |
| `DAILY-3` | 盘中管理 | Node 3 |
| `DAILY-4` | 盘后复盘 | Node 6 |

旧代码和历史文档中的名称暂时保留兼容。任何代码级重命名必须另立任务，不得在文档统一时顺手修改。

### 4.3 RESEARCH 投资研究工作流

- `RESEARCH-COMPANY`：公司研究
- `RESEARCH-INDUSTRY`：行业研究
- `RESEARCH-THEME`：主题研究
- `RESEARCH-MACRO`：宏观研究
- `RESEARCH-EVENT`：事件研究

### 4.4 REVIEW 周期复盘工作流

- `REVIEW-WEEKLY`：周度复盘
- `REVIEW-MONTHLY`：月度复盘
- `REVIEW-QUARTERLY`：季度复盘
- `REVIEW-PORTFOLIO`：组合复盘
- `REVIEW-THESIS`：投资论点复盘
- `REVIEW-TACTIC`：战术复盘

### 4.5 LEARNING 经验进化工作流

- `LEARNING-LESSON`：教训审核
- `LEARNING-RULE`：规则晋升
- `LEARNING-CASE`：案例沉淀
- `LEARNING-COGNITION`：认知模式更新

### 4.6 VALIDATION 策略验证工作流

- `VALIDATION-BACKTEST`：回测验证
- `VALIDATION-HISTORY`：历史类比
- `VALIDATION-FACTOR`：因子验证
- `VALIDATION-TACTIC`：战术验证

### 4.7 SYSTEM 系统维护工作流

- `SYSTEM-DATA`：数据健康检查
- `SYSTEM-CONTRACT`：契约检查
- `SYSTEM-RUNTIME`：运行状态维护
- `SYSTEM-KNOWLEDGE`：知识库维护

## 5. 产物名称

证据产物使用业务名称，不再用 Stage 编号作为对外名称：

- `市场环境证据包`：原 Evidence Stage 0；
- `焦点标的证据包`：原 Evidence Stage 1；
- `盘中事实包`；
- `交易复盘证据包`；
- `公司研究证据包`；
- `行业研究证据包`；
- `回测或验证记录`。

证据包是 `stock_team` 生成的事实与计算，不是最终决策。解释、权限和计划属于 `investing-os`，最终确认属于用户。

## 6. DAILY 的产品节奏

DAILY 是当前第一实施重点。它不是要求用户每天交易，而是提供一个可开始、可跳过、可观察、可中断恢复、可正常收尾的日常节奏。

### `DAILY-0 晨间准备`

目的：恢复上下文，确认今天是否进入交易、观察或其他活动。

系统准备：

- 交易日与时间窗口；
- IBKR 可用的账户、持仓、近期成交和暴露事实；
- 前一日未完成状态与复盘欠账；
- 当前认知约束、风险快照和已有研究候选；
- 数据源健康与缺失项。

用户交互：

- 确认今天的活动类型；
- 对前日欠账选择快速复盘、冻结收尾或完整复盘；
- 确认需要进入盘前判断的持仓、观察对象和问题。

### `DAILY-1 盘前决策`

目的：从市场事实走到用户批准的当日计划。

内部顺序：

```text
investing-os 定义市场范围和事实请求
→ stock_team 生成市场环境证据包
→ 用户与 investing-os 解释环境、讨论权限和优先级
→ 用户确认焦点池
→ stock_team 仅为焦点池生成焦点标的证据包
→ investing-os 形成权限、风险、允许事项和禁止事项
→ 用户批准具体计划版本
```

市场环境证据包和焦点标的证据包沿用旧 Stage 0/1 的依赖关系，但不再作为 DAILY 步骤名称。

### `DAILY-2 开盘观察`

目的：观察真实开盘如何验证或否定盘前假设。

系统只更新事实、条件状态和数据健康。用户决定是否维持观察、启用已批准条件或保持不行动。没有已批准计划时，只能观察。

### `DAILY-3 盘中管理`

目的：按已批准计划管理注意力、风险和已有持仓，而不是持续制造新观点。

`stock_team` 更新 IBKR、价格、VWAP、关键位置、账户暴露和警告等事实；`investing-os` 对照计划显示允许、禁止和需要重新确认的事项。任何计划外扩张都必须回到用户确认。

### `DAILY-4 盘后复盘`

目的：重建事实、评价判断与执行，并形成候选经验。

`stock_team` 生成交易复盘证据；`investing-os` 区分判断、执行、仓位、情绪和数据问题；用户决定是否结束当日，以及哪些内容只属于当天噪音、哪些进入 `LEARNING` 候选。

复盘草稿或候选教训不能自动修改长期认知和规则。

## 7. 其他工作流的共同握手

DAILY 之外的工作流遵循同一基本边界：

```text
用户或 investing-os 定义问题、意义和证伪条件
→ stock_team 收集事实、计算或回测
→ investing-os 解释证据、检查冲突
→ 用户确认结论、状态或下一步
→ 需要长期变化时进入 LEARNING 审核
```

研究和复盘是合法旁路，可以随时使用，但不得暗中改变当日交易状态或已批准计划。

## 8. 交互界面

- Operating Console 是产品首页，展示当前活动、状态、阻塞、下一合法动作、欠账和产物入口。
- Daily Workspace 服务 DAILY，不替代认知 Dashboard。
- Growth Dashboard 展示认知、经验谱系和能力变化，不控制交易状态。
- Stock Team Evidence View 展示事实详情，不作决策。
- 对话负责解释、异议、选择、权限、计划批准、复盘和经验批准。

Dashboard 按钮和对话请求必须转换为同一种协调器动作契约。

## 9. 当前建设策略

先走通完整 DAILY，再按真实阻塞深化，不先把某个局部做到“完整”。

每轮遵循：

1. 运行一遍最小完整 DAILY；
2. 记录事实上的断点和人工替代步骤；
3. 只选择一个最高优先级阻塞；
4. 给低阶模型边界明确的任务单；
5. 局部测试后重新运行完整 DAILY；
6. 更新工作流状态台账和证据链接。

优先级：

- P0：不能继续、结束或恢复；
- P1：账户来源、数据真实性、权限、顺序或用户确认错误；
- P2：用户不知道该做什么，或产物不可验证；
- P3：体验、覆盖率、算法增强和旧代码整理。

`stock_team` 不做全仓清理。旧能力只在 DAILY 或其他工作流实际需要时局部审计，并标记为使用、复用、参考或退役候选。

## 10. 实现状态与追溯

工作流目录和理想流程不代表已经实现。

统一状态：

- `defined`：名称、目的和边界已定义；
- `documented`：存在较完整的流程或契约文档；
- `partial`：部分代码或产物可用，但闭环未验证；
- `runnable`：可按明确步骤运行一次；
- `verified`：已通过固定验收和恢复测试；
- `blocked`：存在明确阻塞；
- `unknown`：尚未审计，不能推断。

每个状态必须附：

- 最近核验日期；
- 证据文件、测试或运行记录；
- 已知缺口；
- 下一验收动作；
- 相关 commit。

当前台账见 [`system/workflows/WORKFLOW-STATUS.zh.md`](system/workflows/WORKFLOW-STATUS.zh.md)。

## 11. 模型协作纪律

高阶模型负责架构、术语、契约、优先级、状态机、风险和审核。

低阶模型一次只处理一个任务单，并且：

- 只读取和修改允许范围；
- 先写或更新测试，再做最小实现；
- 不重新解释 DAILY、Evidence Packet 或 Brain–Muscle 边界；
- 不决定交易建议、权限、风险阈值和长期经验吸收；
- 遇到歧义停止局部工作并上报；
- 提交测试、风险、未解决问题、commit 和 push 记录。

任务完成的标准不是“代码写了”，而是契约审核通过、局部测试通过、相关工作流回归通过且状态台账已更新。

## 12. 对话必须落盘

模型记忆和聊天记录都不是项目事实的可靠来源。

凡是用户与模型讨论后形成、并会影响后续工作的结论，包括目标、术语、边界、优先级、流程、用户交互、数据来源、风险规则、任务范围和验收标准，都必须：

1. 写入对应的仓库文件；
2. 更新受影响的行动纲领、状态台账、规格、计划或任务记录；
3. 作为独立、可审查的 Git commit；
4. 推送到远端；
5. 在回复中报告文件路径、commit SHA 和 push 结果。

没有落入 Git 文件的对话结论只能视为临时讨论，不能作为下一线程或低阶模型的执行依据。

如果一次对话尚未形成确定结论，应明确记录为开放问题，而不是由模型在之后凭记忆补全。

## 13. 权威来源与冲突处理

本文件负责当前项目级名称、边界和行动方向。详细业务契约仍以对应专项文档和 schema 为准。

主要来源：

- [`docs/superpowers/specs/2026-06-13-unified-investing-operating-system-architecture.zh.md`](docs/superpowers/specs/2026-06-13-unified-investing-operating-system-architecture.zh.md)
- [`handoff/2026-06-07-system-overview-for-next-agent.md`](handoff/2026-06-07-system-overview-for-next-agent.md)
- [`system/closed-loop-operating-architecture.md`](system/closed-loop-operating-architecture.md)
- [`system/workflows/brain-muscle-handshake-protocol.md`](system/workflows/brain-muscle-handshake-protocol.md)
- [`system/workflows/trading-day.md`](system/workflows/trading-day.md)
- [`../stock_team/docs/SYSTEM_FLOWCHART.md`](../stock_team/docs/SYSTEM_FLOWCHART.md)
- [`../stock_team/docs/personal_trading_system_wiki_zh.md`](../stock_team/docs/personal_trading_system_wiki_zh.md)
- [`../stock_team/docs/brain-muscle-handshake-protocol.md`](../stock_team/docs/brain-muscle-handshake-protocol.md)

发生冲突时：

1. 用户最新明确决定优先；
2. 本行动纲领的项目级边界和统一名称优先；
3. 已批准 schema 和运行契约优先于说明文字；
4. 新文档不因日期较新就自动推翻旧业务含义；
5. 无法判定时标记冲突并交回用户和高阶模型，不由低阶模型猜测。
