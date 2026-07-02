# Stage0 真实试跑阻断修复纲领

日期：2026-07-03  
范围：仅处理 `Stage0 from snapshot` 在真实隔离试跑中暴露的两个阻断  
状态：design-only，未授权扩展实现

## 1. 本轮发现的真实阻断

基于 2026-07-03 的隔离 runtime 试跑，当前 `Stage0 from snapshot` 仍未真实走通。暴露出两个阻断：

### B1. `38a4dc9` 未真正落在当前工作分支

表现：

- 当前分支 `HEAD` 为 `b79ce9c`
- `git log` 显示存在 `6500238 -> aa17a22 -> b79ce9c`
- 但不包含 `38a4dc9`
- 因此 `stock_team/orchestration/models.py` 中 `new_trading_session()` 仍然写着：
  - `allowed_actions = ["start_stage0"]`
- 真实 `init-day` 产出的 session 也只暴露 `start_stage0`

结论：

- 这不是逻辑 bug，而是提交链未闭合
- 必须先把 `38a4dc9` 的修补真实带入当前工作分支

### B2. `market-context` 真实 CLI 调用链无法正确吃进 `--as-of`

表现：

- 隔离试跑中，`_default_stage0_action()` 已生成 `start_stage0_from_snapshot`
- coordinator 执行后进入 `FAILED_TOOL`
- 继续单独执行 adapter 目标命令：
  - `python -m stock_team.cli market-context ... --as-of 2026-07-03T09:20:00-04:00 ...`
- 原始错误为：
  - `[ERROR] --as-of is required for live Stage 0 market-context packets`
- 即使改成 Python `subprocess.run([...])` 直接传 list 参数，仍然同样报错

结论：

- 这不是 PowerShell quoting 偶发问题
- 也不是 snapshot formal 判定问题
- 是 `market-context` 真实集成链上的参数接收/构造阻断

## 2. 本轮目标

本轮只做两件事：

1. 让当前工作分支真实包含 `38a4dc9` 的 `allowed_actions` 修补
2. 找到并修复 `market-context`/`--as-of` 的真实集成阻断，使隔离 runtime 中的 `start_stage0_from_snapshot` 能推进到 `STAGE0_READY`

不在本轮内：

- 扩展 DAILY 其他阶段
- 改 observation / intraday / review 逻辑
- 顺手重构 `stock_team.cli`
- 解决 dashboard manifest freshness 旧失败

## 3. 修复顺序

固定顺序如下：

### H5-1 提交链修补

先把 `38a4dc9` 的内容真实并入当前分支，确认：

- `new_trading_session().allowed_actions`
  包含：
  - `start_stage0`
  - `start_stage0_from_snapshot`

以及：

- `init-day` 在真实隔离 runtime 中产出的 session JSON 也反映这点

### H5-2 CLI 集成阻断修补

再修 `start_stage0_from_snapshot -> market-context` 的真实调用链，要求：

- adapter 侧传给 `market-context` 的 `as_of` 能被 CLI 正常消费
- 不是只在 FakeAdapter / 单元测试里通过
- 必须在隔离 runtime 的真实命令执行里通过

## 4. 验收标准

本轮完成的最低标准：

1. 当前工作分支包含 `38a4dc9` 的等价修补
2. `python -m stock_team.coordinator_cli init-day ...` 生成的 session 中，`allowed_actions` 含 `start_stage0_from_snapshot`
3. 在隔离 runtime 中，formal snapshot 路径执行 `start_stage0_from_snapshot` 后，session 从 `DAY_INITIALIZED` 推进到 `STAGE0_READY`
4. 产生 Stage 0 packet artifact
5. 原 `start_stage0` 回归仍保持通过

## 5. 对低阶模型的边界

低阶模型可以做：

- 补提交流失的等价修补
- 修 adapter / CLI 调用链
- 补最小测试与隔离验证

低阶模型不能做：

- 改 Stage 0 contract 本身
- 发明新的 snapshot 来源类别
- 顺手改 dashboard freshness 旧问题
- 扩大到 Stage 1/2/3/4

## 6. 当前结论

这轮不是“测试没过”，而是“测试过了，但真实集成没闭环”。

所以本轮修复必须以真实隔离试跑为最终裁判，而不是只以 unit / integration 测试绿灯为准。
