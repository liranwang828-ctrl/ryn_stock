# DAILY 契约 v3 高阶审核记录

日期：2026-07-01
审核对象：commit `d69a206`
结论：`high_tier_approved_pending_user_decisions`

## v2 接受条件复核

| 条件 | 结果 |
|---|---|
| C1、C3 改为 `missing_capability` | 通过 |
| 时间窗口改为目标窗口 | 通过 |
| H4 只从当前契约和待实施清单移除，历史保留 | 通过 |
| 技术问题与用户决策分离 | 通过 |
| 只保留三项用户决策 | 通过 |
| 未修改业务代码 | 通过 |

## 高阶收口

以下技术事项由高阶模型根据行动纲领和统一架构收口，不再交给用户设计：

1. Observation 使用独立 `OBSERVATION_ACTIVE` 状态，避免与交易活动混淆。
2. `intraday-snapshot` 是盘中事实生产动作；持续循环是对同一幂等动作的调度，不保留第二套业务逻辑。
3. Dashboard 当前消费者路径与 CLI 生产路径不一致；实现时统一到 coordinator 登记的 runtime manifest，不只是在启动时创建一个可能陈旧的文件。
4. DAILY canonical runtime 位于 `investing-os/system/runtime/`：
   - `sessions/`：协调器状态；
   - `inputs/`：investing-os 与用户确认后的输入；
   - `packets/`：stock_team 生成并经协调器登记的证据包。
5. `stock_team/findings/`、`reports/` 和 `investing-os/system/data/packets/` 中的旧路径保留为历史或工具工作区，不再作为新 DAILY 产物的 canonical 路径。
6. `generate_suggestions()` 产出 lesson/thesis 类型属于已确认的 Brain–Muscle 边界冲突；实现时 `stock_team` 只保留事实输出，认知候选移至 `investing-os`。

## 用户确认项

高阶模型推荐：

- Q1：A，移除 `post_open_adj` 覆盖盘前锚点的能力；
- Q2：A，对话完成复盘，investing-os 写结构化产物；
- Q3：A，时间窗口软提示，数据真实性校验继续严格执行。

用户确认 Q1–Q3 后，契约可以标记为 `approved`，随后编写代码实施计划。
