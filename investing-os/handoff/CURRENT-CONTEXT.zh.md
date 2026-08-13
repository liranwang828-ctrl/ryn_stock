# 当前唯一上下文

更新时间：2026-08-13

本文件是新任务和协作者的默认恢复入口。不要重新扫描整个仓库，也不要把聊天记录、文件名或历史测试自动解释为当前可运行状态。

开始工作前按顺序读取：

1. [`../SYSTEM-OVERVIEW-AND-STATUS.zh.md`](../SYSTEM-OVERVIEW-AND-STATUS.zh.md)：系统全貌、流程图、当前成熟度和恢复路线；
2. [`../PROJECT-CHARTER.zh.md`](../PROJECT-CHARTER.zh.md)：项目目标、边界、统一术语与行动原则；
3. [`../system/workflows/WORKFLOW-STATUS.zh.md`](../system/workflows/WORKFLOW-STATUS.zh.md)：细粒度实现状态和证据；
4. 当前任务明确引用的专项契约、计划或任务包。

用户与模型形成、会影响后续工作的结论必须写入仓库文件并 commit、push。未落盘的聊天内容不是项目事实。

## 一句话目标

把 `investing-os` 的认知与决策能力和 `stock_team` 的数据、计算与报告能力，连接成一个可日常使用、可中断恢复、可核验事实、由用户最终决策的投资操作系统。

## 当前系统判断

- 系统不是从零开始；旧系统和本轮开发均已有大量可复用资产。
- `investing-os` 是认知与决策主脑；`stock_team` 是数据与计算肌肉。
- Operating Console 是 DAILY 状态和产物导航；Growth Dashboard 是独立认知系统界面。
- DAILY 已完成 2026-08-13 两轮盘前隔离回归和一次跨日 freeze runtime 复核：真实交易日期、当日盘前观察价格、canonical runtime 与 Dashboard 回读已验证；`daily0_confirmation`、`prepare-stage0-universe` 和 `DAY_INITIALIZED` freeze 恢复缺口均已用 TDD 补通。主链已到 DAILY-1B，跨日 freeze 能归档旧日并创建今日会话；开盘时段实时价格以及 quick/full runtime 场景尚未完成，因此状态仍保持 `partial`。
- Research Database V3 Alpha 已有 Question、Evidence、Hypothesis、Observation、Decision 模板，三大 Alpha Questions、Dashboard summary 和多份公司阅读报告。
- 当前最大研究缺口不是报告数量，而是高质量 Evidence 的自动生产、更新与验证闭环。

## 系统硬边界

- 用户负责问题、意义、权限、计划批准、最终交易判断和长期经验吸收。
- `investing-os` 负责认知、研究问题、Hypothesis、决策边界、计划、复盘和知识谱系。
- `stock_team` 负责行情、账户、成交、计算、Evidence Packet、监控和事实报告。
- Dashboard 只展示状态、缺失、产物和导航，不拥有第二套状态机或交易判断逻辑。
- IBKR 是账户、持仓和成交的唯一正式来源；缓存只能只读展示并明确标注未验证。
- 盘前和实时价格必须包含可验证时间戳、来源和市场时段；昨日收盘不得冒充盘前或实时价格。
- 美股交易日期按交易所日历和纽约时区确定，不能直接使用北京时间自然日。
- 研究、观察、休息、无操作和跳过某日都是合法路径，但不得偷偷改变 DAILY 主链状态。

## DAILY 主链

```text
DAILY-0 晨间准备
-> DAILY-1 盘前决策
-> DAILY-2 开盘观察
-> DAILY-3 盘中管理
-> DAILY-4 盘后复盘
-> 归档并供次日恢复
```

`DAILY-1` 内部顺序固定为：

```text
市场环境证据包
-> 用户与 investing-os 讨论市场环境
-> 用户确认焦点池
-> 焦点标的证据包
-> investing-os 形成权限与计划
-> 用户批准计划版本
```

## Research Database V3 Alpha

正式研究顺序：

```text
Question
-> Evidence
-> Hypothesis
-> Reality Validation
-> Consensus / Price / Behavior / Odds
-> Investment Decision
-> Review
-> Learning Candidate
-> 用户批准后进入长期认知
```

当前只维护三个主问题：

1. AI 利润最终沉淀在哪里？
2. Hyperscaler CapEx 是否真正开始放缓？
3. Inference 是否会创造第二轮 Hardware Demand？

公司和新闻是这些问题下的 Evidence，不再作为孤立研究起点。

## Git 与工作区事实

- 顶层仓库：`C:\Users\rriww\Documents\STOCK`；两个子目录不是独立仓库。
- 当前分支：`codex/repository-cleanup-20260630`。
- 远端 `origin` 已配置为 GitHub 仓库。
- 2026-08-13 恢复开始前，本地相对远端领先 55 个提交；连同恢复文档共 59 个提交已完成路径、敏感信息和对象检查并推送，推送后 ahead/behind 为 `0/0`。
- 未推送提交主要包括 Research Database、Dashboard、公司研究报告、关键价格和少量行情/观察链修复。
- 工作区仍存在用户未提交的认知方法论、索引修改和运行时观察文件。不得清理、覆盖或顺手提交。
- 运行时账户、成交、会话和真实观察文件默认保持本地，不得推送。

## 2026 年 8 月恢复任务

按以下顺序推进，不并行扩张范围：

1. 更新本文件、系统总览和工作流状态台账，建立恢复基线；
2. 核验全部未推送提交的路径、敏感信息、提交完整性和远端差异；
3. 安全后推送当前分支，避免成果继续只留在本机；
4. 已在隔离 canonical runtime 中运行最小 DAILY observation；
5. 已验证真实交易日期、盘前价格时间戳/来源和 Dashboard 同源回读；跨日 freeze 已完成隔离 runtime 复核，quick/full 仍待 runtime 复核；
6. 首个真实阻塞已定位为 `daily0_confirmation` 只有 schema 和读取方、没有正式写入入口，并已按 TDD 增加 `confirm-daily0`；
7. 第二个阻塞 `stage0_universe` 生成器只藏在 Dashboard 私有函数，现已提取为共享 builder 并增加 `prepare-stage0-universe`；隔离链已推进到 DAILY-1B，state sync 为 false；
8. DAILY 稳定后，选择一个 Alpha Question 做 Evidence 自动生产的端到端最小切片。

## 当前完成定义

本轮不能因为文档更新或历史测试通过就宣布 DAILY 稳定。至少需要同一次隔离运行证明：

- session 使用正确的纽约交易日期；
- 旧归档日不会错误阻塞今天，未完成或损坏会话按契约处理；
- 盘前/实时价格不是昨日收盘，且来源、新鲜度、市场时段明确；
- Operating Console 读取同一 session 和 artifact ledger，缺失时显示缺失；
- 首个阻塞的回归测试在修复前失败、修复后通过；
- 运行证据和状态变化已写入 Git 文件。

## 模型协作与 Git 纪律

- 高阶模型负责架构、边界、优先级、状态机、数据真实性和高风险审核。
- 低阶模型只执行边界明确的任务包，不自行决定交易语义、核心 schema 或长期认知吸收。
- 每个任务使用独立可审查 commit，不混入其他脏改动或运行日志。
- 每次完成必须报告验证命令、结果、commit SHA 和 push 结果。
- 不得运行 `git clean`、hard reset 或递归删除来获得“干净工作区”。

## 默认启动方式

新任务只需说：

> 读取 `investing-os/handoff/CURRENT-CONTEXT.zh.md`，从 2026 年 8 月恢复任务的下一项继续。不要重新扫描整个仓库，不要触碰未归属的脏文件。

本轮真实运行记录：[`2026-08-13-daily-minimal-regression.zh.md`](2026-08-13-daily-minimal-regression.zh.md)。

当前唯一下一动作：进入开盘时段验证盘中实时价格、时间戳、来源与 Dashboard；不要提前扩展到 Evidence 自动化。quick/full 跨日 runtime 场景保留为后续验证项。
