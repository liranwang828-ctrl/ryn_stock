# Stage0 运行时就绪闸门设计

日期：2026-07-11  
状态：待用户复核

## 目标

让最小运行入口明确区分两种状态：

- `partial`：可以查看已有市场事实，但五项脑侧前置条件或正式行情快照尚未齐全；
- `ready`：正式行情快照有效，且五项脑侧前置条件结构完整，可以继续正式 Stage 0。

本批次不改变协调器状态机，不阻止用户查看部分数据，也不扩展到 Stage 1–4。

## 方案比较与选择

1. 只看正式行情快照：改动最小，但会继续把“行情可用”误当成“Stage 0 正式可继续”。
2. 正式行情快照与五项脑侧前置条件共同决定就绪：语义完整，且可在现有 `entry_state` 上小范围接线。采用此方案。
3. 新增独立持久化 readiness 状态机：追溯性更强，但会与当前协调器状态形成第二套状态机，现阶段过重。

## 就绪规则

运行时读取当日 `pre-market-universe` 产物，并检查：

- `source_inputs.positions`
- `source_inputs.prior_review`
- `source_inputs.cognition_state`
- `permission_state_before_open`
- `forbidden_actions`

“结构完整”指字段存在且类型符合 canonical 模板；本批次不判断投资内容是否正确，也不让 `stock_team` 改写这些脑侧判断。

最终规则：

```text
stage0_formal_ready = formal_provider_snapshot AND all_brain_preconditions_present
```

缺少任一条件时，`entry_state.readiness` 保持 `partial`，并在 `missing_items` 中给出稳定、可读的缺失项。工具失败仍优先显示 `blocked`。

## 接线边界

- `dashboard_server.py`：增加纯计算 helper；聚合 snapshot 与 universe 的结果，生成统一 `entry_state`。
- `operating-console.html`：继续只消费 `entry_state`，展示 `ready`、`partial` 或 `blocked` 及缺失项，不自行重复业务判断。
- Stage 0 动作选择：只有完整就绪时默认使用 `start_stage0_from_snapshot`；否则保留 `start_stage0`，允许补齐或刷新输入。
- `investing-os` 继续拥有五项前置条件的定义与最终判断；`stock_team` 只做结构检查和流程呈现。

## 错误处理

- universe 文件不存在、JSON 损坏或字段类型错误：按缺失项处理，不崩溃。
- snapshot 不正式：报告正式行情快照缺失。
- `FAILED_TOOL`：readiness 为 `blocked`，并保留工具失败原因；脑侧缺失项可继续出现在明细中。

## 测试

测试先行覆盖：

1. 正式 snapshot + 五项完整 → `ready`，默认动作是 `start_stage0_from_snapshot`；
2. 正式 snapshot + 任一脑侧字段缺失 → `partial`，列出缺失项，默认动作是 `start_stage0`；
3. 非正式 snapshot + 五项完整 → `partial`，报告 snapshot 缺失；
4. universe 缺失或损坏 → 不崩溃并报告五项缺口；
5. `FAILED_TOOL` → `blocked` 优先级不变；
6. operating console 只读取统一 `entry_state`，不增加第二套 readiness 判定。

## 完成标准

- 用户从 Dashboard 能一眼看到当前是“部分数据可看”还是“Stage 0 正式可继续”；
- 缺失条件可定位；
- 原有部分数据路径仍可运行；
- 相关单元测试和 DAILY E2E 回归通过；
- 实现状态写回 `WORKFLOW-STATUS.zh.md`。
