---
session_id: daily-2026-07-17-alpha-draft
trading_date: 2026-07-17
session_mode: research
status: draft
primary_topics:
  - topic_id: ai-profit-migration
    topic_name: AI 第二阶段、利润迁移与硬件/软件重新定价
    priority: primary
  - topic_id: evidence-system-v3-alpha
    topic_name: Investing-OS V3 Alpha Evidence System
    priority: primary
alpha_questions:
  - question_id: Q1
    status: primary
  - question_id: Q2
    status: active
  - question_id: Q3
    status: active
near_term_plan_ref: investing-os/handoff/2026-07-16-near-term-operating-plan.zh.md
question_status_summary:
  Q1: supporting
  Q2: mixed
  Q3: mixed
current_structural_context: >
  当前主线仍然是“Reality 偏硬件，Consensus 开始偏软件，Price 已提前交易利润迁移”。
  今日工作重点不是新增结论，而是把近期计划、Alpha Questions、daily 主报告层正式接通。
allowed_actions:
  - observe_only
  - research_only
forbidden_actions:
  - revenge_trade
  - isolated_day_judgment
---

# Daily Report - 2026-07-17

## Alpha Questions / Research Spine

- Attached Questions:
  - Q1: AI 利润最终沉淀在哪里？
  - Q2: Hyperscaler CapEx 是否真正开始放缓？
  - Q3: Inference 是否会创造第二轮 Hardware Demand？
- Near-Term Plan Reference:
  - `investing-os/handoff/2026-07-16-near-term-operating-plan.zh.md`
- Why These Questions Matter Today:
  - 今天最重要的不是判断单日涨跌，而是把近期研究主线正式变成 daily 的上游约束。
  - Q1 负责约束我们如何理解近期“软件强、半导体承压”的结构变化。
  - Q2/Q3 负责提醒我们，不要把价格回调直接等同于硬件 Reality 转坏。
- Main Validation Target:
  - 检验今日研究和 daily 记录，是否已经不再从“今天有什么新闻”出发，而是从 active questions 出发。
- Plan Status Today:
  - 总体支持近期开盘计划中的主判断：当前更重要的是验证结构，而不是强行寻找交易动作。
  - 还没有新增高质量证据去明显上调或下调任何一个核心假设的置信度。

## Pre-Market / 盘前

- Questions:
  - 今日的研究准备是否围绕 Q1/Q2/Q3 展开，而不是围绕孤立个股和新闻展开？
  - 近期“软件相对强、硬件相对弱”的结构，是否应被理解为利润现实迁移，还是市场提前交易？
- Evidence:
  - 近期开盘计划已经明确：当前默认基线是 Reality 仍偏硬件，Consensus 开始偏软件，Price 已提前反映未来利润迁移。
  - 我们已将 AMAT、MU、COHR、NVDA 归入 Hardware / Demand 观察组，将 MSFT、NOW 归入 Commercialization 观察组。
  - 用户新增的 Knowledge Increment 进一步确认：Investing-OS 下一阶段重点不是增加框架，而是提高 Evidence Production 能力。
- Counter Evidence:
  - 目前还缺少直接来自官方财报、产业数据或替代数据的新证据，去强力证明软件利润已经现实兑现。
  - 也缺少新的高质量证据，去证明 hyperscaler CapEx 已系统性转弱，或 inference 已经形成第二轮需求兑现。
- Hypotheses:
  - H1: 当前利润仍主要沉淀于硬件层，软件上涨更多是 Consensus Expansion。
  - H2: 市场对硬件板块的定价压缩速度可能快于 Reality 的变化速度。
  - H3: Inference 可能会延长部分硬件利润周期，但目前仍待验证。
- Confidence:
  - Q1: 70% 维持不变
  - Q2: 55% 维持不变
  - Q3: 55% 维持不变
- Next Validation:
  - 下一轮财报季
  - hyperscaler 资本开支指引
  - AI software 利润率 / 现金流兑现情况
  - inference 部署与需求的后续证据
- Effect on Attached Questions:
  - Q1: 支持当前“Reality 偏硬件、Price 提前交易软件”的工作假设
  - Q2: 暂无新证据足以确认 CapEx 真正放缓，因此维持 mixed
  - Q3: 暂无新证据足以确认 inference 第二轮需求兑现，因此维持 mixed

## Intraday / 盘中

- Questions:
  - 今天是否有必要从“做什么交易”切换回“确认我们在看什么问题”？
  - daily 是否真正承担了研究主线挂载层，而不是只记录事件？
- Evidence:
  - 今天完成了 Alpha Question Attached Daily 的正式接线：daily 模板、daily workflow、workflow README、操作说明文件已经全部落地。
  - daily frontmatter 已增加 `alpha_questions`、`near_term_plan_ref`、`question_status_summary`。
  - daily 正文已增加 `Alpha Questions / Research Spine` 区块，以及三段中的 `Effect on Attached Questions`。
- Counter Evidence:
  - 当前仍未接入 dashboard 展示层，因此这套结构现在主要体现在 markdown 工作流，而不是可视化消费层。
  - 当前也还没有把 evidence card / hypothesis card 全面 question-driven 化。
- Hypotheses:
  - H4: 只要 daily 被稳定挂到 active questions 上，系统就会明显减少“每天孤立判断”的倾向。
  - H5: 先约束 daily 主报告层，比先重做 dashboard 更能帮助系统真正用起来。
- Confidence:
  - H4: 75%
  - H5: 80%
- Next Validation:
  - 用真实的下一次盘前分析继续沿用这份结构
  - 观察这种写法是否比旧 daily 更自然、更能约束思考
- Effect on Attached Questions:
  - Q1/Q2/Q3: 今日没有新增市场证据，但新增了系统层证据生产能力的约束，有助于以后围绕三大问题持续积累证据

## Review / 复盘

- Questions:
  - 今天的产出是否真的推进了 V3 Alpha，而不是只新增了一份文档？
  - 这份 daily 是否已经开始体现“Question → Evidence → Hypothesis → Validation”？
  - 今天这次反弹，究竟是趋势反转，还是恐慌后的结构性修复？
- Evidence:
  - V3 Alpha 阶段总结、Alpha Questions Ledger、Daily Design、Implementation Plan、以及正式 workflow 接线都已写入 git。
  - 今日 daily 已显式绑定 Q1/Q2/Q3，并显式引用 active near-term plan。
  - 这让以后每天都必须回答：今天的 evidence 是支持、削弱，还是与主问题无关。
  - 指数层面出现了明显盘中修复，但更像“先杀再拉”，不是全面重新转强：SPY、QQQ 都从盘中低位明显反弹，SOXX/SMH 修复更强。
  - 板块层面，半导体和 AI 链条的修复强于软件对照组，说明市场没有继续单边强化“软件强、硬件弱”的旧结构。
  - 个股分层已经比较清楚：
    - MU：最像高质量硬件修复
    - COHR / NBIS / BE：高弹性风险偏好修复明显
    - AMAT / VRT：核心资产稳住并修复，但还不是最强进攻者
    - NVDA：更像止跌稳锚，不像重新带队
    - MSFT / NOW：今天没有证明软件重新全面接管
- Counter Evidence:
  - 这次反弹的主要性质仍然更接近超跌修复，还不能据此确认半导体链重新进入趋势性主升。
  - 还没有结合 dashboard、evidence cards、hypothesis cards 做端到端体验验证。
  - 核心锚点 NVDA / AMAT / VRT 并没有全部表现出那种“明确重新领涨”的状态，因此今天更适合理解为修复确认，而不是趋势确认。
- Hypotheses:
  - H6: Investing-OS 从 Knowledge Base 向 Research Operating System 升级的第一步，不是更多内容，而是更稳定的问题挂载和证据沉淀。
  - H7: 当前市场更像在快速修正 Price，而不是快速修正 Reality；因此硬件链条的波动速度仍明显快于基本面变化速度。
  - H8: 如果下一个交易日高质量修复票（MU、AMAT、VRT）能够延续，而软件对照组没有重新夺回相对强势，则“半导体被过度压缩”的判断会得到进一步支持。
- Confidence:
  - H6: 80%
  - H7: 75%
  - H8: 60%
- Next Validation:
  - 下一个交易日重点观察：
    - 核心锚：NVDA / AMAT / VRT 能否继续稳住
    - 高质量修复：MU 能否延续
    - 高弹性票：COHR / NBIS / BE 是延续还是只是一日脉冲
    - 对照组：MSFT / NOW 是否重新夺回相对强势
  - 下一次真实盘前分析直接复用此结构
  - 再决定是否把 dashboard 也做最小接线
- Effect on Attached Questions:
  - Q1: 今天的价格表现更支持“市场在重定价利润迁移路径”，而不是“软件利润 Reality 已经完全压过硬件”
  - Q2: 今天没有新证据证明 hyperscaler CapEx 真正系统性放缓，反而更像市场先过度压缩了硬件链估值
  - Q3: NBIS / COHR / BE 这类高弹性修复说明风险偏好回流到 AI 链，但仍不足以单独证明 inference 第二轮需求已经被现实验证

## Post-Market Summary / 盘后总结

- 大盘结论：
  - 今天是一次不错的修复日，但更像“先杀再拉后的盘中修复”，不是已经确认的新一轮全面转强。
- 结构结论：
  - 半导体 / AI 链的修复强于软件对照组，说明旧的“软件单边占优”结构今天没有继续强化。
- 个股结论：
  - MU 最像高质量修复；
  - COHR / NBIS / BE 最像高弹性风险偏好修复；
  - AMAT / VRT 是核心资产稳住；
  - NVDA 更像稳锚；
  - MSFT / NOW 今天不是主角。
- 操作结论：
  - 今天没有必要为了“反弹不错”强行新增动作；
  - 更合理的做法是保存体力，等待下一个交易日确认这次修复是否有延续性。

## Trade Log

Use this section only if there were trades.

无。

## Research Links

- Evidence Cards:
  - 待后续按 question-driven card 补齐
- Observation Cards:
  - 待后续真实盘前 / 盘中 session 接入
- Hypothesis Cards:
  - 待后续正式建立 Q1/Q2/Q3 假设台账
- Decision Cards:
  - 暂无
- Metrics Updated:
  - daily 主报告层已升级为 Alpha Question attached structure
