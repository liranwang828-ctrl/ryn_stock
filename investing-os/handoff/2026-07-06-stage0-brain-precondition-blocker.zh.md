# Stage0 Brain Preconditions 真实阻断说明

日期：2026-07-06  
来源：`R2` 真实命令复核后的新最前置阻断  
状态：design-only，未授权扩展实现

## 1. 当前结论

`--as-of` 不再是当前最前面的真实阻断。

在真实执行：

```text
python -m stock_team.cli market-context --date 2026-07-06 --as-of 2026-07-06T09:20:00-04:00 ...
```

时，当前最前面的失败变成：

```text
[ERROR] missing_brain_precondition_state:
Stage 0 requires brain-side positions, prior_review, cognition_state,
permission_state_before_open, and forbidden_actions before market evidence
collection; missing=permission_state_before_open,forbidden_actions
```

因此当前真实主链的最前置阻断，已经从“CLI 参数传递”前移到“Stage 0 brain-side 输入契约不完整”。

## 2. 问题边界

本轮只处理一个问题：

- `market-context` 对 brain-side precondition 的最小输入契约，到底应该由谁生成、以什么最小 schema 提供、如何在真实隔离试跑中满足

不在本轮内：

- Stage 1 / intraday / review
- dashboard freshness 旧失败
- paid provider 逻辑
- snapshot source_kind 扩展
- 大范围重构 universe document

## 3. 当前已知事实

### 3.1 CLI 现有要求

`stock_team.cli handle_market_context()` 在 live Stage 0 路径中要求 brain-side preconditions 完整。

当前错误信息明确提到至少需要：

- `positions`
- `prior_review`
- `cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

### 3.2 我们的真实隔离输入未满足

在高阶复核的真实命令中，我构造了最小 universe/snapshot 输入，但仍触发：

- `permission_state_before_open` 缺失
- `forbidden_actions` 缺失

这说明：

- 目前“formal snapshot 路径”虽然动作语义已成立
- 但并没有一个稳定、被真实命令接受的最小 brain-side universe 生成契约

### 3.3 这不是 FakeAdapter 能发现的问题

现有单测多数只证明：

- action intent 对不对
- adapter command 构造对不对
- coordinator state transition 对不对

但并不证明：

- 真实 `market-context` 命令吃得下真实隔离 universe 文档

## 4. 下一轮目标

下一轮只要做到：

1. 定义并实现一个“真实 `market-context` 可接受”的最小 brain-side universe 文档
2. 在隔离 runtime 中用它重新跑 `start_stage0_from_snapshot`
3. 让 session 真正推进到 `STAGE0_READY`

## 5. 推荐修复顺序

### P1 — 先确认最小 universe 契约

找出 `market-context` 真正接受的最小字段集合，不靠猜。

重点：

- `permission_state_before_open` 的最小合法值
- `forbidden_actions` 的最小合法值
- `positions` / `prior_review` / `cognition_state` 是否允许空对象或空数组

### P2 — 再修默认 universe 生成器

如果当前 `_build_stage0_universe_document()` 或相关生成路径没满足这个契约，就补到最小可运行。

### P3 — 最后做真实隔离试跑

必须以真实命令为准：

- `python -m stock_team.cli market-context ...`
- 或 `python -m stock_team.coordinator_cli run --action ...`

测试通过但真实命令不过，不算完成。

## 6. 验收标准

本阻断被解决的最低标准：

1. 真实 `market-context` 不再报 `missing_brain_precondition_state`
2. formal snapshot 路径的 `start_stage0_from_snapshot` 可推进到 `STAGE0_READY`
3. 产出 Stage 0 packet artifact
4. 原 `start_stage0` 回归不被破坏

## 7. 协作约束

低阶模型可以：

- 读 `stock_team.cli`
- 读/改 Stage 0 universe 生成相关代码
- 补最小单测和真实命令验证

低阶模型不能：

- 扩大到 Stage 1+
- 改 daily contract 语义
- 顺手清理无关 stock_team 历史结构

## 8. 一句话总结

`Stage0 from snapshot` 现在离真实走通只差最后一类前置输入问题：

- 不是动作语义
- 不是 adapter 命令构造
- 而是 brain-side universe/precondition 文档没有稳定满足真实 CLI 契约
