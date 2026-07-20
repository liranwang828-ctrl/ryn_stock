# BE Verification Layer 研究报告设计

## 背景

用户希望把 Bloom Energy（BE）纳入当前 Investing-OS 研究体系，形成一份可以直接阅读、讨论、并支撑后续投资观察的正式研究包。现有框架已经把 BE 放在 AI 利润迁移验证地图的 `Verification Layer`，因此本次设计不改变层级定义，而是在该层级内把 BE 的 AI power optionality 讲清楚。

当前关键问题不是“BE 是不是好公司”，而是：

- 它在当前 AI 生态中承担什么观察职责；
- 它最近的价格行为应被解释为 Reality、Consensus、Price 还是 Behavior 变化；
- 哪些价格位置对实际投资有操作意义。

## 目标

产出一套最小但正式的 BE 研究包，包括：

- 公司研究底稿；
- 关键价格计算说明；
- 可阅读的 HTML 报告。

这套产物需要满足：

- 与现有 `Verification Layer` 框架一致；
- 使用 `Reality / Price / Behavior / Odds` 四维拆分；
- 明确给出可执行的关键价格锚点；
- 避免把股价高低直接误写成公司强弱。

## 不做的事

本轮不做以下扩展：

- 不重定义 BE 的层级，不把它升级为 Reality Layer；
- 不建立完整行业 power dashboard；
- 不引入难以稳定获取的复杂期权墙数据源；
- 不对全市场同类公司做横向全覆盖。

## 设计方案

### 方案选择

采用“标签保持 A，正文吸收 B”的方式：

- 报告标签：`Verification Layer`
- 正文定位：`AI power optionality inside verification layer`

这样可以同时满足两点：

- 保持与现有认知系统一致；
- 不丢掉 BE 和 AI 电力/快速供电叙事之间的真实关联。

### 报告结构

正式 HTML 报告按以下结构组织：

1. Hero summary
   - 一句话定位 BE；
   - 说明它为什么属于 `Verification Layer`；
   - 提示当前最大争议在于验证而非定性。

2. 市场在交易什么
   - AI data center power bottleneck；
   - Brookfield 扩大合作；
   - 快速供电与 AI 基建叙事。

3. 四维拆解
   - Reality：已确认的经营与合作事实；
   - Price：此前是否过度透支、当前是否压缩；
   - Behavior：为何在修复日中相对弱；
   - Odds：哪些区间才算“重新值得评估”。

4. 关键价格与操作锚点
   - 当前价格背景；
   - 观察区；
   - 试探区；
   - 升级区；
   - 降级区；
   - 近端期权 open interest 密集位。

5. 时间线
   - Q1 2026 record results；
   - 2026-06-30 Brookfield 扩容至 250 亿美元；
   - 最近市场质疑/修复失败节点；
   - 下一次硬验证节点：2026-07-28 财报。

6. 当前结论
   - 不直接判 Reality 破坏；
   - 先把今天的异常归类为 Behavior/Consensus 问号；
   - 等下一次官方验证。

### 底稿结构

配套公司底稿 `BE.zh.md` 采用更适合长期维护的结构：

- 公司定位；
- 在 AI 价值链中的职责；
- 当前核心 thesis；
- Evidence / Counter Evidence；
- 未来验证节点；
- 当前研究状态。

### 关键价格文档结构

价格文档单独记录计算逻辑与数值来源，包括：

- 均线；
- recent low / recent high；
- anchored VWAP；
- 近端期权 OI 密集位；
- 这些价格分别支持的是 `位置判断`，而不是“公司更强/更弱”的结论。

## 数据与证据要求

优先使用：

- 公司官方 IR、财报、公告；
- 稳定行情数据；
- 可复现的本地价格计算。

允许作为补充背景，但不得直接当作 Reality 结论：

- 新闻媒体对市场异动的解释；
- 市场质疑、做空报告、社交讨论。

## 语言约束

本报告必须通过现有研究可靠性约束：

- 不用“强/弱”偷换主语；
- 不把高点写成 Reality 变差；
- 不把回落写成公司更强；
- 只在 Reality 未恶化时，讨论 Odds 可能改善；
- 明确区分 `Reality / Price / Behavior / Odds`。

## 文件计划

本轮将新增：

- `investing-os/wiki/companies/BE.zh.md`
- `investing-os/handoff/2026-07-20-be-key-price-calculation.zh.md`
- `investing-os/dashboards/reports/BE-verification-layer-report.html`

并保持不修改其他无关脏文件。

## 验证方式

完成后进行：

- 文件内容自检；
- 编码与可读性检查；
- 关键价格数值与来源一致性检查；
- HTML 本地可打开性检查；
- 与可靠性 checklist 的对照检查。

## 成功标准

如果以下条件同时满足，则视为本轮设计成功：

- 用户能直接阅读 BE 报告；
- 报告里有具体价格，而不是只有观点；
- 结论没有混淆 Reality 与 Price/Behavior；
- 文件已经落入 git 仓库，便于后续扩展到更多公司。
