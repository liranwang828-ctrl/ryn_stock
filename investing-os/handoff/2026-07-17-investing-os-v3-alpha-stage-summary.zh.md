# Investing-OS 阶段总结（V3 Alpha）

## 状态

- Date: 2026-07-17
- Status: active_stage_summary
- Scope: Research Operating System / Evidence System / Hypothesis System
- Relation:
  - builds on `2026-07-16-evidence-system-and-research-infrastructure.zh.md`
  - constrains next-stage Evidence Card / Hypothesis Card / Alpha Questions implementation

## 一、当前最大的认知更新

Investing-OS 当前最大的瓶颈，已经不是：

- 缺少框架
- 缺少观点
- 缺少分析

而是：

> 缺少持续产生高质量 Evidence（证据）的能力。

未来竞争优势不会来自知道更多新闻，而会来自：

- 更好的问题
- 更高质量的证据
- 更快的反证
- 更持续的置信度更新

因此，系统的下一阶段重点不是继续叠加框架，而是正式建设：

- Evidence System
- Hypothesis System
- Question-Driven Research System

## 二、Research 目标已经改变

过去更容易走成：

```text
新闻
-> 观点
-> 交易
```

现在正式改为：

```text
Question
-> Evidence
-> Hypothesis
-> Reality Validation
-> Investment Decision
```

以后不再因为新闻本身改变观点。

而是因为：

- 新 Evidence 进入
- Counter Evidence 出现
- Confidence 被上调或下调

才修改当前 Hypothesis。

## 三、V3 Alpha 的最小研究范围

V3 Alpha 第一阶段只维护三个长期问题。

### Question 1（最高优先级）

AI 利润最终沉淀在哪里？

这是未来几年整个 AI 投资最重要的问题。

以后：

- 公司不是研究中心
- 公司只是这个问题下的 Evidence

### Question 2

Hyperscaler CapEx 是否真正开始放缓？

这个问题决定：

- AI Hardware 的长期景气度
- CapEx 链的持续性
- 设备、代工、内存、网络、电力的中期预期

### Question 3

Inference 是否会创造第二轮 Hardware Demand？

这个问题决定：

- GPU
- HBM
- Networking
- Power

是否仍然拥有第二轮中长期成长空间。

## 四、Evidence 来源重新定义

不同平台以后不是信息流入口，而是承担不同研究职责。

### Official

负责验证：

- Reality

包括：

- 财报
- Earnings Call
- Investor Day
- 官方数据
- 官方披露

权重最高。

### GitHub

负责验证：

- Technology Reality

重点不是看代码细节本身，而是看：

- Release 节奏
- Contributors
- Enterprise Adoption
- Inference / Agent / MCP / Framework 演进

### Reddit

负责验证：

- User Reality

重点不是看市场情绪，而是看：

- 企业部署
- 开发者反馈
- 推理成本
- 使用痛点
- Adoption 真伪

### X

负责：

- 发现新的 Hypothesis

权重最低。

它可以触发研究，但不能直接作为最终 Reality 证据。

## 五、Research Source 不再是信息流

以后不是每天刷平台。

而是：

> Question → Source

例如，“AI 利润最终沉淀在哪里”这个问题，就由：

- Official
- GitHub
- Reddit

共同回答。

不是平台驱动研究，而是问题驱动研究。

## 六、Evidence Card 的定位

以后 Evidence 必须从聊天内容升级为可持续更新的结构化对象。

统一字段应收敛为：

- Question
- Evidence
- Evidence Grade
- 支持 / 反对
- 影响公司
- Confidence Change
- Next Validation

Evidence 不再是一次性讨论片段。

它应成为：

- 可追踪
- 可回看
- 可更新
- 可反证

的数据单元。

## 七、Hypothesis 管理正式成为核心层

以后维护的是：

- Hypothesis

不是：

- 观点

例如：

- Hardware 利润仍领先
- Software 开始商业化
- Inference 创造第二轮需求

每个 Hypothesis 需要长期维护：

- Evidence
- Counter Evidence
- Confidence
- Last Update
- Next Validation

系统要做的不是“证明自己是对的”，而是尽快识别：

- 什么时候该下调置信度
- 什么时候该切换假设
- 什么时候原有叙事已经失效

## 八、Codex 的定位

Codex 不负责预测股价。

Codex 负责：

- 自动收集 Evidence
- 更新 Dashboard
- 维护数据库
- 更新 Hypothesis
- 追踪 Confidence 的变化

因此 AI 的角色不是：

- Fund Manager

而是：

- Research Analyst

## 九、长期原则

以后：

- 不收集 Information，只收集 Evidence
- 不讨论 Opinion，只讨论 Hypothesis
- 不更新新闻，只更新 Confidence

这意味着系统的目标从“更快反应市场”，转向“更快发现自己什么时候错了”。

## 十、当前阶段最重要的一句话

> Research 的目标不是证明自己是对的，而是尽可能快地发现自己什么时候错了。

Investing-OS 最终目标不是建立一个新闻系统，而是建立一个能够持续验证、修正和进化认知的：

> Research Operating System

## 十一、对当前系统的直接约束

从这份阶段总结开始，后续实现应优先满足：

1. daily 必须围绕 Question / Hypothesis 组织，而不是围绕新闻组织
2. Evidence Card 必须成为正式对象，而不是聊天附属物
3. Hypothesis 必须能被持续更新置信度
4. Source 必须按问题分工，而不是按平台堆积
5. Dashboard 负责呈现研究状态，不负责生成观点

## 十二、下一步最自然的实现方向

V3 Alpha 之后，最顺的下一步应是：

1. 升级 Evidence Card 模板与字段
2. 增加 Hypothesis Card / Hypothesis Ledger
3. 为三个 Alpha Questions 建立正式索引文件
4. 让 daily 盘前 / 盘中 / 复盘开始围绕这三个问题运行

