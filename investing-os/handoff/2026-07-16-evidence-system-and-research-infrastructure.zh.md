# Knowledge Increment（Pending）

## Topic

Investing-OS V2.1 —— Evidence System 与 Research Infrastructure

## 状态

- Status: pending_absorption_completed
- Source: 2026-07-16 任务讨论
- Intended destination:
  - `docs/superpowers/specs/2026-07-16-investing-os-research-database-daily-design.zh.md`
  - `handoff/2026-07-16-ai-profit-migration-validation-map.zh.md`
  - future research topics / evidence / MVD files

## 一、这次增量真正推进了什么

这次增量不是简单补充“证据要更重要”，而是把系统的下一阶段重点从：

- 证据结构

推进到：

- 证据生产能力
- 数据源优先级
- 长期研究基础设施

也就是说，问题已经不只是“怎么记录证据”，而是：

> 如何持续生产高质量证据，并把它们组织进研究系统。

## 二、核心转向

系统以后不追求：

- 拥有最多信息

而追求：

- 拥有最高质量的 Evidence

真正优势来自：

- Evidence Quality

而不是：

- Information Quantity

## 三、正式研究流程

以后研究正式统一为：

```text
Question
-> Evidence
-> Hypothesis
-> Reality Validation
-> Investment Decision
```

任何投资结论，都必须能追溯到：

- Question
- Evidence
- Hypothesis

## 四、Evidence 四层体系

### Layer 1：Official Evidence

最高优先级，用于建立 Reality。

包括：

- 财报
- Earnings Call Transcript
- Investor Presentation
- Investor Day
- SEC 文件
- 官方 Blog / 公告

原则：

- 任何新闻都不能替代官方数据

### Layer 2：Industry Evidence

用于验证产业 Reality。

重点领域：

- HBM
- GPU
- CoWoS
- 先进封装
- Data Center
- AI CapEx
- Power
- Networking

### Layer 3：Alternative Evidence

用于领先发现 Reality。

例如：

- GPU Lead Time
- GPU Rental Price
- HBM ASP
- 数据中心出租率
- 电力审批
- 招聘数据

### Layer 4：Expert View

用于产生新的 Hypothesis。

包括：

- 行业专家
- 产业分析
- 开发者社区
- X
- Reddit
- GitHub

原则：

- 不能直接作为 Reality

## 五、预算有限下的高 ROI 研究路径

默认优先级：

1. 官方财报 / Earnings Call / Investor Day
2. Reuters / 免费 Bloomberg 产业与宏观新闻
3. X 上的长期研究者、工程师、分析师
4. Reddit 技术社区
5. GitHub 开源生态

重点不是信息覆盖最广，而是长期研究回报率最高。

## 六、未来付费数据源策略

若增加预算，建议优先级：

1. SemiAnalysis
2. TrendForce
3. TechInsights

Bloomberg 不应作为当前第一优先，因为对 AI Reality 研究的专项性价比不够高。

## 七、MVD：最小可行数据集

系统长期不应维护庞大指标池，而应持续维护少量真正影响 Reality 的核心变量。

示例：

- HBM ASP
- GPU Lead Time
- Hyperscaler CapEx
- TSMC CapEx
- AMAT Orders
- VRT Orders
- Copilot Adoption
- Oracle OCI Growth
- GPU Rental Price
- Data Center Power

## 八、研究对象升级

以后不再默认以 Company 为中心，而以 Question 为中心。

例如：

- 不是研究 MU
- 而是研究 HBM

MU、三星、SK Hynix 都只是 HBM Question 下的 Evidence。

例如：

- 不是研究 Microsoft
- 而是研究 AI Monetization

Microsoft、Oracle、Meta、ServiceNow 都只是该 Question 下的 Evidence。

## 九、AI / Codex 的正式职责

AI 在这套系统中的职责不是预测股价，而是：

- 读取财报
- 提取指标
- 更新 Dashboard
- 更新 Evidence
- 维护 Hypothesis
- 生成验证节点

也就是：

> 成为 Research Analyst，而不是预测器。

## 十、长期目标

Investing-OS 的长期目标，不只是：

- Knowledge Base

也不只是：

- Research Database

而是：

- Research Operating System

最终积累的核心资产是：

- Evidence Chain

而不是：

- 新闻流
- 观点堆积

## 十一、这次增量对当前实现的含义

第一版系统应至少预留：

- evidence layer 字段
- high ROI source 策略
- MVD 占位结构
- future evidence production 流程挂载点

这样后续成长时，才不会重新推翻 daily 与 dashboard 结构。
