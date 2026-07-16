# Investing-OS V2 设计：以 Daily 为入口，把 Knowledge Base 升级为 Research Database

## 元信息

- 日期：2026-07-16
- 状态：draft_for_review
- 适用范围：Investing-OS daily 工作流、daily 产物结构、轻量 Topic 挂载、dashboard 最小适配
- 不在本次范围：完整长期数据库、自动抓取产业数据、复杂可视化分析引擎、自动推理决策

## 1. 背景

当前 Investing-OS 已经具备多套上层认知框架：

- Reality Framework
- Reality → Consensus → Price
- AI 第二阶段 / 利润迁移框架

但系统的主要瓶颈已经不是“缺少框架”，而是“缺少证据化结构”。

当前很多判断仍容易走成：

```text
新闻
-> 逻辑推理
-> 观点
```

这会带来几个问题：

- 观点和证据链绑定不稳定
- daily 容易变成当天临时发挥
- 长期研究问题与当天盘前/盘中脱节
- dashboard 能显示状态，但不能清楚呈现“今天到底在验证什么”

因此，本次设计的目标，不是再增加一层新框架，而是让 Investing-OS 从“记录知识”升级为“记录问题、证据、假设与验证过程”。

## 2. 设计目标

本次设计只追求四个目标：

1. 让 daily 的核心输出从“结论笔记”升级为“研究产物”
2. 让长期 Research Topic 可以轻量挂载到 daily，而不是孤立存在
3. 让每个 daily 判断都能追到对应的 Question / Evidence / Hypothesis
4. 让 dashboard 在不承担复杂判断逻辑的前提下，展示这些研究产物是否存在、是否完整、是否可读

## 3. 非目标

以下内容明确不纳入第一版：

- 不建立完整数据库服务
- 不引入复杂标签系统或检索系统
- 不要求所有历史认知资产一次性迁移
- 不让 dashboard 负责生成研究结论
- 不把所有公司研究立即重构为 Topic-first 全量系统

第一版强调：

- 先让 daily 用起来
- 再为 Research Database 留出生长接口

## 4. 核心范式升级

### 4.1 从 Knowledge Base 到 Research Database

V1 更像：

```text
记录知识
```

V2 要升级为：

```text
记录问题
-> 记录证据
-> 记录假设
-> 记录反证
-> 记录下一验证节点
```

最终形成的研究闭环是：

```text
Question
-> Evidence
-> Hypothesis
-> Reality
-> Consensus
-> Price
-> Investment Decision
```

### 4.2 Daily 的新定位

daily 不再只是“今天怎么交易”的流程。

它应成为：

- 长期问题的日常验证入口
- 证据链的日常沉淀入口
- 近期计划与长期 Topic 的连接层

换句话说：

daily 是入口层，Research Database 是积累层。

## 5. 第一版信息架构

第一版采用：

```text
一份主报告
+ 若干卡片摘要
+ 轻量 Topic 挂载
```

### 5.1 主报告

主报告是 daily 的中心产物，负责回答：

- 今天主要在验证哪些问题？
- 今天最重要的证据是什么？
- 今天形成了哪些阶段性假设？
- 今天允许和禁止什么动作？

### 5.2 卡片

卡片是更小的研究单元，负责把观察、证据、假设、决定拆开，方便追溯与展示。

### 5.3 Topic 挂载

长期 Topic 第一版不做成重量级数据库，而是作为轻量 research topics 清单存在，并允许：

- 主报告挂 1–3 个主 Topic
- 卡片多对多挂 Topic

这样既能支持长期累积，又不阻塞 daily 落地。

## 6. 主报告设计

### 6.1 主报告角色

主报告是 daily 的正式研究记录，不是临时聊天摘要。

它必须能被未来回看，并回答：

- 当天主要研究问题是什么
- 证据链是什么
- 有哪些相互冲突的证据
- 当前假设是什么
- 下一次该怎么验证

### 6.2 主报告结构

主报告顶部固定字段：

- session_id
- trading_date（以 US/Eastern 为准）
- session_mode（observation / formal）
- primary_topics（1–3 个）
- current_structural_context
- current_allowed_actions
- current_forbidden_actions

主报告正文固定分三段：

- Pre-Market
- Intraday
- Review

每一段的标准研究字段统一为：

- Questions
- Evidence
- Counter Evidence
- Hypotheses
- Confidence
- Next Validation

### 6.3 主报告输出要求

主报告不是长篇散文，优先结构化书写：

- 每个问题都对应证据
- 每个证据都尽量标注来源、日期、用途
- 每个假设都标注当前置信度
- 每个结论都必须能指出下一次验证节点

## 7. 卡片设计

第一版只定义四类卡片。

### 7.1 Observation Card

用途：

- 记录盘前、盘中、盘后发生的关键观察

字段：

- title
- timestamp
- related_topics
- observation
- why_it_matters
- source_refs

### 7.2 Evidence Card

用途：

- 把某条正式证据结构化沉淀

字段：

- question
- evidence
- source
- source_date
- supports
- weakens
- reliability_level

### 7.3 Hypothesis Card

用途：

- 记录当前工作假设，而不是假装得出最终答案

字段：

- question
- hypothesis
- supporting_evidence_refs
- counter_evidence_refs
- confidence
- next_validation

### 7.4 Decision Card

用途：

- 记录行动约束与交易层含义

字段：

- decision_context
- allowed_actions
- forbidden_actions
- trigger_conditions
- invalidation_conditions

## 8. Research Topic 设计

### 8.1 第一版 Topic 目标

Topic 不是为了制造一套更复杂的分类系统，而是为了让 daily 不再脱离长期研究主线。

### 8.2 第一版 Topic 结构

每个 Topic 至少包含：

- topic_id
- title
- question
- current_hypothesis
- current_confidence
- key_evidence_refs
- next_validation
- status

### 8.3 Daily 中的挂载方式

第一版采用双层挂载：

- 主报告顶部关联 1–3 个 primary_topics
- 卡片可多对多关联 related_topics

这允许：

- 今天的研究有主线
- 具体观察又不被硬塞进单一分类

## 9. Evidence 结构

用户已明确要求第一版直接采用完整结构，而不是轻量简写。

因此标准 Evidence 结构固定为：

- Question
- Evidence
- Counter Evidence
- Hypothesis
- Confidence
- Next Validation

并补充两个执行层字段：

- Source
- Use In Decision

### 9.1 Source 分层

为避免“观点冒充证据”，证据来源分五层：

1. Official Data
2. Industry Data
3. Value Chain
4. Alternative Data
5. Expert View

### 9.2 第一版处理原则

第一版允许先以人工填写为主，不做自动抓取，但输出格式必须预留这些来源层级。

## 10. Workflow 设计

### 10.1 Pre-Market

盘前不是单独看新闻，而是先从 active topics 与近期行动纲领进入。

盘前要回答：

- 今天优先验证哪个长期问题
- 今天新增的盘前事实支持还是削弱当前假设
- 今天 focus pool 中的标的分别属于哪个研究角色

盘前主报告至少应生成：

- primary_topics
- pre-market questions
- pre-market evidence
- current hypotheses
- allowed / forbidden actions

### 10.2 Intraday

盘中不再只是“看涨跌”，而是记录：

- 哪些价格动作只是 Price 层变化
- 哪些观察真正推动了 Reality / Consensus 判断
- 哪些已有假设被强化或削弱

### 10.3 Review

复盘不再只是总结操作，而是回答：

- 今天到底验证了什么
- 哪些结论仍不能成立
- 哪些 Topic 的置信度该调整
- 下一次验证节点是什么

## 11. Dashboard 最小适配

第一版 dashboard 不新增复杂推理。

只做最小可读与就绪检查。

### 11.1 要展示的内容

- 今日主报告是否存在
- primary_topics
- 今日核心 questions
- 今日核心 hypotheses
- 卡片列表
- 每张卡片的 type / topic / status
- 缺失字段提醒
- next_validation 摘要

### 11.2 明确不做的事

- 不在 dashboard 里自动生成研究结论
- 不在 dashboard 里做复杂 Topic 评分
- 不把 dashboard 变成新的研究引擎

dashboard 的职责只是：

- 看得到
- 看得懂
- 知道哪里缺

## 12. 文件与产物建议

第一版建议新增或调整以下产物层：

- daily 主报告模板
- card 模板
- research topics 索引文件
- dashboard 读取这些结构化文件的最小适配逻辑

建议采用：

- 主报告：单文件
- 卡片：可单独文件或内嵌数组结构
- Topic：索引文件

第一版优先保证可读和可维护，不追求过早规范化。

## 13. 数据流

第一版数据流建议为：

```text
active_topic_selection
-> daily main report creation
-> cards creation / update
-> dashboard reads report + cards + topic links
-> review updates hypothesis confidence and next validation
```

关键点：

- Topic 驱动 daily
- daily 反向更新 Topic
- dashboard 只读取，不决策

## 14. 错误处理与失败模式

第一版优先考虑以下失败模式：

### 14.1 daily 重新退回观点笔记

防护方式：

- 模板必须要求 Question / Evidence / Hypothesis 完整字段

### 14.2 Topic 挂载形式化但无实际作用

防护方式：

- 每日主报告顶部必须显式写 primary_topics

### 14.3 dashboard 内容太多但引导性差

防护方式：

- 第一版只显示摘要和缺失项，不叠加太多逻辑

### 14.4 证据和观点继续混淆

防护方式：

- Source 分层必须显式存在
- Expert View 不得直接当作 Reality

## 15. 测试与验收

第一版验收不以“研究结论是否正确”为标准，而以“结构是否被系统稳定产出和展示”为标准。

最小验收项：

1. daily 能生成带完整研究字段的主报告
2. 主报告能关联 1–3 个 primary_topics
3. 卡片能挂载 related_topics
4. dashboard 能显示主报告摘要、卡片摘要、缺失项、next_validation
5. workflow 文档与模板能明确要求 Question / Evidence / Hypothesis 结构

## 16. 分阶段实施建议

### Phase 1

- 写清 daily 主报告结构
- 写清 card 结构
- 写清 topic 索引结构
- 调整 workflow 文档

### Phase 2

- dashboard 最小适配
- 缺失字段展示
- 主 Topic / 卡片 Topic 显示

### Phase 3

- 把近期已有认知与 AI 第二阶段框架逐步挂到 Topic 层
- 开始形成跨日验证链

## 17. 本设计的取舍

本设计刻意选择：

- 不追求一步到位数据库化
- 不追求 dashboard 智能化
- 不追求全量历史迁移

而是优先保证：

- daily 真正变成研究入口
- Topic 有轻量但真实的挂载
- Evidence 结构可长期累积

## 18. 结论

本次设计的核心，不是再创造一个新框架。

而是把已有框架真正变成日常研究生产系统。

第一版最重要的成果应当是：

- daily 不再只是结论记录
- Topic 不再只是长期想法
- dashboard 不再只显示状态

而三者开始形成：

```text
Question
-> Evidence
-> Hypothesis
-> Daily Validation
-> Topic Update
```

这就是 Investing-OS 从 Knowledge Base 升级为 Research Database 的最小可用起点。
