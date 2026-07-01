# DAILY L1-L3 低阶任务包

日期：2026-07-01
前置约束：`investing-os/handoff/2026-07-01-daily-h1-h3-repair-charter.zh.md`
适用对象：低阶模型

## 总规则

- 只能按任务包施工，不得改任务语义。
- 每个任务单独 commit。
- 不得并行修改同一组 coordinator 文件。
- 交付日志必须写明：修改文件、验证命令、未解决问题、建议高阶复核点。

## L1 observation 动作一致性

### 目标

让 observation 路径暴露的公共动作，与 coordinator 可执行动作完全一致，不再出现 UI 可见但 coordinator 拒绝执行的动作。

### 允许读取

- `investing-os/handoff/2026-07-01-daily-h1-h3-repair-charter.zh.md`
- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- `stock_team` 下现有 coordinator / adapter / dashboard 相关代码与测试

### 允许修改

- observation 动作 schema、models、transitions、adapter、dashboard manifest 相关文件
- 相关单元测试和集成测试

### 禁止修改

- 交易计划语义
- `H1/H2` 定义的状态语义和归档契约
- DAILY-4 复盘问题与经验判断

### 输入契约

- 公共动作名必须使用：
  - `start_observation`
  - `refresh_market_observation`
  - `record_observation_exception`
  - `close_observation_day`
  - `archive_day`

### 输出契约

- `allowed_actions` 只展示 coordinator 真能执行的 observation 公共动作
- `ACTION_INTENTS`、状态机、adapter 映射一致
- observation 下绝不暴露交易权限动作

### 验收命令

```text
python -m pytest -q stock_team/tests/unit/orchestration stock_team/tests/unit/core/test_cli.py
```

### 完成定义

- 所有 observation 公共动作都能从公开入口到达 coordinator
- 不存在“展示可点但执行失败”的 observation 动作
- 测试覆盖至少包含：允许动作、禁止交易动作、状态跳转

## L2 白名单归档接线

### 目标

让 `archive_day` 真实走白名单归档链，输出 manifest，而不是只改状态或只在测试里直接调 helper。

### 允许读取

- `investing-os/handoff/2026-07-01-daily-h1-h3-repair-charter.zh.md`
- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- 现有 archiver、coordinator、session store、runtime artifact 相关代码

### 允许修改

- archiver
- coordinator 的 `archive_day` 接线
- artifact ledger / manifest 相关 schema 或测试

### 禁止修改

- 归档最小 schema
- archive 路径规则
- 未登记文件自动纳入归档

### 输入契约

- 归档器只吃 `session_id`、`session_file`、`artifact_ledger`、`archive_root`
- `artifact_ledger` 是唯一白名单

### 输出契约

- `archive_day` 成功时必须写出 `archive_manifest.json`
- 会话状态登记 `archive_manifest_path`
- 同名冲突、缺失文件、越界路径必须失败

### 验收命令

```text
python -m pytest -q stock_team/tests/unit/orchestration stock_team/tests/integration/test_daily_e2e.py
```

### 完成定义

- 生产路径能触发归档器
- manifest 至少覆盖成功、缺失、拒绝三类结果
- 测试不再通过直接调用 archiver helper 冒充生产归档完成

## L3 跨日恢复实现

### 目标

按高阶状态矩阵实现 `freeze / quick_review / full_review`，并把旧会话阻断、恢复、归档与今日日会话创建顺序接通。

### 允许读取

- `investing-os/handoff/2026-07-01-daily-h1-h3-repair-charter.zh.md`
- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- 现有 session store、coordinator、CLI、recovery 测试

### 允许修改

- session listing / validation
- recovery router
- CLI / coordinator 相关恢复入口
- 恢复测试

### 禁止修改

- 自行新增第四种恢复模式
- 允许损坏会话静默跳过
- `full_review` 未归档就创建今日日会话

### 输入契约

- 恢复模式只允许：
  - `freeze`
  - `quick_review`
  - `full_review`

### 输出契约

- 损坏会话显式阻断
- 多旧会话显式阻断
- `REVIEW_REQUIRED` 只能继续 `full_review`
- `full_review` 只有在旧会话 `DAY_ARCHIVED` 后才允许开今日日会话

### 验收命令

```text
python -m pytest -q stock_team/tests/unit/orchestration stock_team/tests/unit/core/test_cli.py stock_team/tests/integration/test_daily_e2e.py
```

### 完成定义

- 至少覆盖：`INTRADAY_ACTIVE`、`OBSERVATION_ACTIVE`、`MARKET_CLOSED`、`REVIEW_REQUIRED`、盘前中断、损坏会话、多旧会话
- `freeze`、`quick_review`、`full_review` 行为与高阶状态矩阵一致
- 测试从公开入口验证恢复结果
