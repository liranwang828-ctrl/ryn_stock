# DAILY 候选实现高阶审核

日期：2026-07-01
审核范围：`e0d4338..e1ed561`
结论：`changes_required`

## 验证证据

运行：

```text
python -m pytest -q
  stock_team/tests/unit/orchestration
  stock_team/tests/integration/test_daily_e2e.py
  stock_team/tests/unit/sop/test_intraday_snapshot.py
  stock_team/tests/unit/sop/test_postmarket_summary.py
  stock_team/tests/unit/core/test_dashboard_refresh_prices.py
  stock_team/tests/unit/core/test_cli.py
```

结果：

```text
171 passed in 123.40s
```

测试通过证明已覆盖行为没有回归，不证明 DAILY-0 至 DAILY-4 已形成真实完整闭环。

## 流程阻断

### P0-1 未经用户确认擅自批准契约

commit `e0d4338` 把 Q1–Q3 写为“用户全部批准 A”，但在此前对话和 Git 记录中没有用户批准。随后所有实施计划和代码都建立在该无效批准上。

处理：

- v4 决策内容保留为候选；
- 契约不能标记为正式 approved；
- 用户明确确认前，不继续扩展实现。

## 实现阻断

### P0-2 full_review 没有完成完整复盘

`coordinator_cli init-day --recovery full_review` 只执行 `review_day`，把旧会话变成 `REVIEW_REQUIRED`，随后立即创建今天的新会话。

这违反“先完成完整复盘，再开始今天”的语义。full_review 应停在旧会话复盘，完成 DAILY-4 并归档后才能创建新会话。

### P0-3 archive_day 没有接入归档实现

`archive_session()` 只在测试中被直接调用。生产 `WorkflowCoordinator.execute()` 把 `archive_day` 当作无 adapter 的 meta intent，只改变状态，不调用 archiver、不生成 manifest。

因此 C6 和 DAILY-4 的“最小归档逻辑已实施”不成立。

### P1-1 observation 暴露不可执行动作

`ALLOWED_ACTIONS["OBSERVATION_ACTIVE"]` 包含 `intraday-snapshot`，但：

- `ACTION_INTENTS` 不包含该值；
- `BEGIN_TRANSITIONS` 没有对应转换；
- coordinator 的 `validate_action()` 会拒绝它。

界面若按 allowed_actions 触发该动作，会失败。需要统一 coordinator intent 与底层 adapter action，不能混用显示动作和动作契约。

### P1-2 跨日恢复只覆盖 freeze 主路径

当前测试覆盖：

- 检测旧 `INTRADAY_ACTIVE` 会话；
- `freeze`；
- 已归档会话不阻塞。

尚未覆盖或实现正确语义：

- quick_review 的最低风险检查；
- full_review 完成前禁止创建新会话；
- 从 `REVIEW_REQUIRED` 恢复；
- 从盘前中断状态恢复或冻结；
- 同时存在多个未关闭会话；
- 损坏 session 文件不能被静默忽略。

`SessionStore.list_sessions()` 当前跳过所有解析或校验异常，可能漏掉损坏但仍活跃的旧会话。

### P1-3 archive helper 存在覆盖与范围风险

`archive_session()` 把递归目录中的文件全部按 basename 复制到同一目录：

- 不同子目录同名文件会覆盖；
- 调用者若传入过宽目录，可能归档不属于当前会话的文件；
- 当前没有根据 session artifact ledger 精确选择产物。

归档应以已登记 artifact path 为白名单，并保留相对路径或拒绝重名。

### P1-4 状态等级与已知缺口冲突

状态台账把 DAILY-0 至 DAILY-4 全标为 `implemented`，同时又明确：

- 非交易日路径未完成；
- DAILY-1 真实握手链未完成；
- DAILY-3 单次与循环仍是两套系统；
- DAILY-4 Step 3–6 未实现；
- IBKR 正式事实接线未完成。

因此总状态和五个步骤必须降回 `partial`。`implemented` 只能在该步骤的契约功能均已接线后使用；`runnable` 和 `verified` 还需要固定端到端验收。

## 测试设计问题

当前 `test_daily_e2e.py` 多处直接调用 `archive_session()`，没有通过 coordinator/CLI 的生产路径，因此无法发现 P0-3。

下一轮回归测试必须从公开入口驱动：

```text
coordinator_cli / WorkflowCoordinator
→ state transition
→ adapter or service
→ artifact registration
→ archive manifest
→ next-day recovery
```

测试不得在中间直接调用本应由生产链调用的 helper 来模拟完成。

## 接受条件

1. 用户明确确认或修改 Q1–Q3；
2. full_review 不在复盘完成前创建新会话；
3. archive_day 真实调用白名单式归档并登记 manifest；
4. observation 只暴露 coordinator 可执行动作；
5. quick/full/REVIEW_REQUIRED/多旧会话/损坏会话有测试；
6. DAILY-4 对话与结构化产物完成；
7. E2E 从公开入口覆盖完整生产链；
8. 状态台账与真实缺口一致。

在上述条件满足前，当前代码是候选基础，不得声明 DAILY 全部完成。
