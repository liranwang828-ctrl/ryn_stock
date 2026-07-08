# 最小入口数据来源映射

日期：2026-07-08
状态：第一批接线来源映射

目标字段：

- `today_mode`
- `current_step`
- `readiness`
- `missing_items`
- `next_action`

每个字段记录：

- `primary_source`
- `fallback_source`
- `owner`
- `display_rule`
- `unresolved_risk`

---

## 1. `today_mode`

- `primary_source`
  - `stock_team` 当前 session / coordinator 摘要中的 mode 或等价字段
- `fallback_source`
  - 若 session 不存在，则由 `investing-os` 按当前可见上下文推断为 `review` 或 `maintenance`
- `owner`
  - 事实来源：`stock_team`
  - 最终展示解释：`investing-os`
- `display_rule`
  - 只显示一个值：`trading / observation / review / maintenance / unknown`
- `unresolved_risk`
  - 现有 runtime 中 mode 字段命名可能不完全统一，需要在接线时做最小归一化

## 2. `current_step`

- `primary_source`
  - `stock_team` session state / coordinator state
- `fallback_source`
  - 若无 session，则根据最近 blocker 或 review required 状态显示 `unknown` 或 `REVIEW_REQUIRED`
- `owner`
  - 事实来源：`stock_team`
  - 最终展示解释：`investing-os`
- `display_rule`
  - 优先显示当前显式 state，例如 `DAY_INITIALIZED`、`STAGE0_RUNNING`、`REVIEW_REQUIRED`
- `unresolved_risk`
  - runtime state 机器名不一定适合直接暴露给用户，可能需要最小的人类可读映射

## 3. `readiness`

- `primary_source`
  - session summary / snapshot readiness / formal-ready 判断
- `fallback_source`
  - 若无明确 readiness，则由 blocker 是否存在决定：
    - 有 blocker → `blocked`
    - 无 blocker 但状态不完整 → `partial`
- `owner`
  - 事实来源：`stock_team`
  - 最终展示解释：`investing-os`
- `display_rule`
  - 只显示：`ready / partial / blocked`
- `unresolved_risk`
  - 现有系统 readiness 有多种来源，第一批只做最小归并，不先做全局统一

## 4. `missing_items`

- `primary_source`
  - active blockers
- `fallback_source`
  - runtime session summary 中已有的 `missing_items` 或等价字段
- `owner`
  - blocker 事实：`stock_team` + `investing-os` handoff
  - 最终展示解释与排序：`investing-os`
- `display_rule`
  - 最多显示 5 条
  - 优先显示最近已经确认过的真实 blocker，不显示泛化占位文案
- `unresolved_risk`
  - blocker 现在部分在 handoff 文档里、部分在 runtime 状态里，第一批需要最小桥接

## 5. `next_action`

- `primary_source`
  - session summary / coordinator next action
- `fallback_source`
  - 若无显式 next action，则由 `investing-os` 根据 blocker 优先级生成最小引导动作
- `owner`
  - 事实建议来源：`stock_team`
  - 用户-facing 引导解释：`investing-os`
- `display_rule`
  - 只显示一个最主要动作
- `unresolved_risk`
  - 现有 next action 可能更偏 runtime 术语，需要压缩成用户能执行的下一步描述

---

## 6. 第一批来源优先级

统一优先级：

1. 现有 runtime/session/coordinator 状态
2. 现有 snapshot / evidence / readiness 状态
3. 最近已确认的 blocker 文档
4. `investing-os` 最小解释层 fallback

补充的最终优先级约定：

- `missing_items`
  - `primary_source`: active blockers
  - `fallback_source`: runtime session summary `missing_items`
  - `owner`: `investing-os` 对 `stock_team` runtime 事实做最小解释

---

## 7. 设计边界

第一批不做：

- 全局 state machine 术语统一
- 所有 packet / schema 的最终回写
- growth dashboard 数据链完整接通

第一批只做：

- 让入口能真实显示今天怎么继续
- 同时为后续 contract 回写保留来源追溯
