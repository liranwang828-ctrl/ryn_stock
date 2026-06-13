# LLM 主控纪律层设计

> 日期：2026-06-01
> 范围：为 Decision State Hub 增加可审计、可测试、可复盘的 LLM 主控纪律契约
> 状态：方向已确认，待实施计划

## 中文摘要

本阶段的目标不是让 LLM 直接下交易结论，也不是改交易规则，而是先给 LLM 主控加一层硬纪律：它必须知道哪些证据支持、哪些证据反对、哪些结论禁止说、哪些动作被允许、哪些情况必须降级或要求人工复核。

当前系统已经有两层地基：

- `findings/evidence_credibility_report.json`：把因子、回测、参数稳定性和盘中精确点位层分级。
- `findings/decision_state_{date}.json`：把个股 thesis、因子证据、回测证据、执行状态和 controller 汇总到每日每股状态。

但现在 `controller` 仍偏向“给出结论”：`act / wait / monitor / avoid`、置信度、阻断原因和 dashboard 摘要。它还缺一个更严格的审计契约，用来约束未来的真实 LLM 主控，防止 LLM 用叙事覆盖证据缺口。

本轮推荐落地 **方案 A：主控纪律契约优先**。也就是在 `decision_state_{date}.json` 的 `controller` 中增加结构化审计字段：

- `evidence_for`
- `evidence_against`
- `downgrade_reasons`
- `allowed_actions`
- `forbidden_claims`
- `llm_output_contract`

同时保留现有 `controller_verdict`、`controller_confidence`、`evidence_alignment`、`required_human_check`、`blocked_by` 和 `summary_for_dashboard`，避免破坏 dashboard 或现有测试。

## 最终优化方向

完整系统的最终目标是 **方案 C：真实 LLM 主控 agent**。

未来的 LLM 主控 agent 应读取完整 Decision State、证据可信度、个股 thesis、执行状态和盘中更新，输出结构化裁决与解释。但它必须受纪律层约束：

- 不能把 `caution` 回测说成 `validated`。
- 不能把样本不足因子说成强信号。
- 不能用 narrative-only upgrade 绕过因子、回测、风控或数据新鲜度问题。
- 不能在 `allowed_actions` 不包含 `act` 时建议入场。
- 必须列出反证、缺失输入、降级原因和人工复核项。

本轮不直接接真实 LLM，是为了先把“机器可测的纪律边界”做好。后续接入真实 LLM 时，prompt 和 schema 只能消费这层契约，而不能自由发明更乐观的结论。

## 本阶段目标

本阶段要把 controller 从“结论摘要”升级为“结论 + 审计轨迹 + LLM 行为边界”。

具体目标：

1. 明确哪些证据支持当前动作。
2. 明确哪些证据反对或要求谨慎。
3. 明确为什么置信度被降级。
4. 明确 LLM 被允许输出哪些动作。
5. 明确 LLM 禁止声称哪些东西。
6. 为后续 LLM prompt/schema 留稳定字段。
7. 为 dashboard 后续展示“为什么不是可入场”提供结构化数据。

## 非目标

本阶段不做：

- 不改交易规则。
- 不自动下单。
- 不接真实 LLM 调用。
- 不重写回测引擎。
- 不重跑完整回测。
- 不修改 `agents/backtest_*` 或 `scripts/weekly_*`。
- 不重新设计 dashboard UI。
- 不把探索性或样本不足证据升级成强证据。

如果实施过程中发现回测引擎、交易规则或 LLM prompt 的问题，只记录 TODO，除非后续单独确认进入对应阶段。

## 设计方案

### 方案 A：主控纪律契约优先（本轮推荐）

在现有 `agents/decision_state_hub.py` 的 `_controller()` 输出中增加审计字段。字段完全由已有结构化证据推导，不调用 LLM。

优点：

- 稳定、可测试、可复盘。
- 不依赖 prompt 自觉。
- 不改变现有交易规则。
- 后续 dashboard 和真实 LLM agent 都能直接消费。

代价：

- 本轮还不会生成真正的 LLM 主控自然语言裁决。
- 字段第一版会偏保守，后续需要随着回测/因子系统增强继续细化。

### 方案 B：增加 LLM 输出协议但不接调用（接口预留）

在方案 A 基础上，定义 `llm_output_contract` 字段，说明未来 LLM 输出必须遵守的 schema 和行为边界。

优点：

- 后续接真实 LLM agent 更顺。
- prompt 设计不会另起炉灶。

代价：

- 第一版只能提供契约，不验证真实 LLM 输出质量。

### 方案 C：真实 LLM 主控 agent（最终优化目标）

新增或改造 agent，让它实际读取 Decision State 并调用 LLM 输出主控裁决。

优点：

- 最接近完整系统目标。
- 能把个股分析、因子、回测和执行约束真正汇成主控意见。

代价：

- 依赖 LLM client、prompt、失败回退、schema 校验和复盘闭环。
- 如果纪律层还不硬，LLM 可能重新把系统变成不可复现的叙事黑箱。

因此本轮只实施方案 A，并为方案 B 留字段；方案 C 作为完整系统后续目标记录。

## 输出契约

`controller` 第一版建议扩展为：

```json
{
  "controller_verdict": "wait",
  "controller_confidence": 55,
  "evidence_alignment": "mixed",
  "required_human_check": ["Style-OOS alpha 为负"],
  "blocked_by": [],
  "summary_for_dashboard": "证据存在分歧，需带 caution 执行或人工复核",
  "audit": {
    "evidence_for": [
      {
        "source": "thesis",
        "status": "supportive",
        "detail": "个股 thesis 可用"
      },
      {
        "source": "factor",
        "status": "usable",
        "detail": "存在可用因子证据"
      }
    ],
    "evidence_against": [
      {
        "source": "backtest",
        "status": "caution",
        "detail": "style-OOS alpha 为负"
      }
    ],
    "downgrade_reasons": [
      "回测证据为 caution，不能声称完全验证"
    ],
    "allowed_actions": ["wait", "monitor", "avoid"],
    "forbidden_claims": [
      "不能声称证据完全对齐",
      "不能把 caution 回测称为 fully validated",
      "不能建议立即入场"
    ],
    "llm_output_contract": {
      "must_include": [
        "final_action",
        "confidence",
        "supporting_evidence",
        "opposing_evidence",
        "downgrade_reasons",
        "human_review_items"
      ],
      "final_action_must_be_one_of": ["wait", "monitor", "avoid"],
      "confidence_ceiling": 55,
      "narrative_only_upgrade_allowed": false
    }
  }
}
```

### 字段说明

`evidence_for`：记录支持当前方向的证据，例如 thesis 可用、因子为 usable/robust、time-OOS 为正。

`evidence_against`：记录反向或谨慎证据，例如 stale source、样本不足、style-OOS 为负、盘中点位层仍探索性。

`downgrade_reasons`：记录为什么不能更乐观，例如缺失 thesis、因子 weak、回测 caution、输入过期。

`allowed_actions`：约束未来 LLM 主控能给出的动作集合。若存在 `blocked_by`，不能包含 `act`。若证据为 mixed/caution，通常只允许 `wait / monitor / avoid`，除非后续交易规则明确允许带 caution 执行。

`forbidden_claims`：约束 LLM 禁止说出的结论。它是防止 narrative-only upgrade 的核心字段。

`llm_output_contract`：为未来真实 LLM agent 准备的结构化协议。本轮只生成契约，不调用 LLM。

## 纪律规则

### 数据新鲜度

如果 `premarket_summary` 或 `entry_decision` 为 `missing / stale / parse_error / invalid`：

- `blocked_by` 必须包含对应原因。
- `allowed_actions` 不能包含 `act`。
- `forbidden_claims` 必须禁止“可按计划执行”或“证据完整”。
- `required_human_check` 必须要求刷新或修复输入。

### Thesis 证据

如果 thesis 缺失或不可解析：

- `evidence_against` 记录 `missing_thesis`。
- `downgrade_reasons` 说明缺少个股主线。
- LLM 只能输出 `wait / monitor / avoid`。

### 因子证据

如果因子质量为 `unavailable / weak / insufficient / exploratory`：

- 不允许声称因子支持强 conviction。
- 如果 `Sentiment Catalyst` 或其他因子样本不足，必须进入 `evidence_against` 或 `required_human_check`。
- 因子只能作为排序或辅助证据，不能单独生成交易结论。

如果因子质量为 `usable / robust`：

- 可以进入 `evidence_for`。
- 仍不能绕过 thesis、回测或执行层门控。

### 回测证据

如果回测为 `unavailable / reject`：

- 必须阻断 `act`。
- LLM 不能声称历史验证支持。

如果回测为 `caution`：

- `evidence_alignment` 应为 `mixed`，除非后续规则明确更细分。
- `allowed_actions` 默认不包含 `act`。
- `forbidden_claims` 必须禁止 `fully validated`、`证据完全对齐`、`强样本外支持` 等表达。
- `required_human_check` 保留 style-OOS 或其他 caution 原因。

如果回测为 `supportive`：

- 可作为 `evidence_for`。
- 仍需要检查其他证据层是否缺失或冲突。

### 执行状态

如果 `entry_decision` 给出 `可入场`，但纪律层发现阻断或混合证据：

- `execution.action_state` 可以保留原始执行建议。
- `controller.controller_verdict` 必须降级为 `wait` 或 `monitor`。
- `audit.allowed_actions` 必须以 controller verdict 为准。

## Dashboard 预留

本轮不改 dashboard UI，但输出字段要方便后续可视化优化 agent 使用。

后续 dashboard 可以围绕这些模块设计：

- 主控动作条：显示 `controller_verdict` 和 `allowed_actions`。
- 证据天平：左侧 `evidence_for`，右侧 `evidence_against`。
- 禁止声称区：展示 `forbidden_claims`，提醒用户不要被乐观叙事带偏。
- 人工复核队列：展示 `required_human_check` 和 `downgrade_reasons`。
- LLM 合规检查：对照 `llm_output_contract` 检查真实 LLM 输出是否越界。

这些字段应该继续从 `decision_state_{date}.json` 读取，而不是让 dashboard 直接拼原始因子、回测和盘前 JSON。

## 测试要求

实施时需要覆盖：

1. 完整证据且全部支持时，`allowed_actions` 可包含 `act`，`forbidden_claims` 不应禁止入场。
2. 回测 `caution` 时，`allowed_actions` 不包含 `act`，并禁止声称证据完全对齐。
3. 因子样本不足时，`evidence_against` 或 `downgrade_reasons` 必须记录样本不足。
4. premarket stale 时，`blocked_by`、`downgrade_reasons`、`forbidden_claims` 和 `required_human_check` 都必须体现刷新要求。
5. `entry_decision` 为可入场但证据缺失时，controller 必须降级，且 `allowed_actions` 以降级后的 verdict 为准。
6. `llm_output_contract.final_action_must_be_one_of` 必须与 `allowed_actions` 一致。

## 交接备注

本设计是 Decision State Hub 的下一层增强。实现时优先修改：

- `agents/decision_state_hub.py`
- `tests/test_decision_state_hub.py`

不需要新增独立脚本。第一版应保持向后兼容：现有 controller 字段不删除，只新增 `audit`。

如果实施中发现需要改变交易规则、真实 LLM prompt 或 dashboard UI，应先记录 TODO，并另开设计。

