# Stage 0 Universe Canonical 入口设计

日期：2026-08-13
状态：用户已选择方案 B，待书面规格复核

## 1. 背景

2026-08-13 隔离 DAILY observation 试跑证明：

- 当日 `pre-market-snapshot` 与 `stage0-market-context` 能生成并被 Dashboard 正确读取；
- `confirm-daily0` 已补齐 DAILY-0 用户确认的正式写入入口；
- Dashboard 随后停在 DAILY-1A，因为 canonical `stage0_universe` 不存在。

既有资产审计已经确认 `stage0_universe` 的生成逻辑存在于 `dashboard_server.py::_build_stage0_universe_document()`。问题不是缺少算法，而是该逻辑被放在 Dashboard 私有函数内：只读 Dashboard 不调用写操作，当前对话和 coordinator CLI 也没有正式入口。真实试跑绕过 Dashboard 后，universe 因而缺失。

## 2. 设计决策

采用方案 B：

> 将既有 Stage 0 universe 生成逻辑提取为单一、可测试的模块；Dashboard 与新的 CLI 入口共同调用该模块。

不采用：

- CLI 直接导入 Dashboard 私有函数：会继续强化 UI 与业务产物生成的耦合；
- `confirm-daily0` 隐式生成 universe：会混淆“生成输入草稿”和“用户确认”，破坏该命令只写确认事实的边界；
- 在 observation 行情 adapter 中生成 universe：universe 是 brain-side precondition，stock_team 行情生产器只能消费，不能替代 investing-os 判断。

## 3. 目标流程

```text
init-day
→ prepare-stage0-universe
→ 当前对话检查活动模式、账户事实、分析范围和风险边界
→ confirm-daily0（analysis_scope_ref 指向已生成 universe）
→ start_stage0_observation / start_stage0 / start_stage0_from_snapshot
→ daily-status 检查 snapshot + market context + universe
→ DAILY-1B
```

允许系统在无交易权限下预取观察行情，但 DAILY 节点仍由 canonical 文件和用户确认共同决定。

## 4. 组件边界

### 4.1 单一 universe builder

从 `dashboard_server.py` 提取既有生成逻辑到独立模块。模块负责：

- 接收 workspace/runtime、交易日期和 session id；
- 读取既有 positions、当日 snapshot focus、最新 journal；
- 生成现有 `pre_market_universe` 结构；
- 原子写入 `{runtime}/inputs/{session_id}-stage0-universe.json`；
- 返回 universe 路径和已引用 journal 路径。

本轮不改变已有字段、默认值、来源标签、权限文字或 forbidden actions；语义调整留给后续独立设计。

### 4.2 CLI 入口

新增：

```text
python -m stock_team.coordinator_cli prepare-stage0-universe
  --session-id <id>
  --runtime-dir <sessions-dir>
```

CLI 从 session 读取交易日期和 session 类型，通过共享 builder 生成 canonical universe，并输出结构化 JSON 摘要。它不推进 coordinator state、不运行行情 provider、不写 DAILY-0 确认。

CLI 必须保证 universe 写在与该 session 同一 canonical runtime 的 `inputs` 目录，而不是依赖主仓库默认路径。

### 4.3 Dashboard

`_default_stage0_action()` 继续具有原行为，但改为调用共享 builder。Operating Console 保持只读，不增加按钮、判断或第二套状态机。

### 4.4 `confirm-daily0`

保持现有单一职责。若传入非空 `analysis_scope_ref`，本轮不新增隐式生成或自动修复行为；调用方负责先生成并检查 universe。

## 5. 错误处理

- session 不存在或损坏：CLI 返回非零，不创建 universe；
- runtime 路径无法确定：CLI 返回非零，不回退到主仓库 runtime；
- builder 写入失败：不得留下半写文件；
- 重复执行：覆盖同一 session/date 的 canonical universe，路径保持稳定；
- CLI 成功不得改变 session state、state version、权限或确认字段。

## 6. 测试与验收

测试先行，至少覆盖：

1. `prepare-stage0-universe` 在隔离 runtime 生成正确 canonical 路径；
2. 生成文件包含现有五类脑侧前置结构：positions、prior review、cognition state、permission state、forbidden actions；
3. CLI 不改变 session state/version，且不写 `daily0_confirmation`；
4. Dashboard `_default_stage0_action()` 仍使用同一 builder 和同一路径；
5. 同一个隔离试跑完成 prepare、confirm 和已有 Stage 0 后，daily-status 从 DAILY-1A 进入 DAILY-1B；
6. 既有 orchestration、Dashboard 和 DAILY E2E 回归通过。

## 7. 非目标

本轮不做：

- 重新定义 universe schema；
- 自动选择焦点池或交易标的；
- 修改 permission / forbidden actions 的业务语义；
- 接入 IBKR 正式账户同步；
- 增加 Dashboard 操作按钮；
- 开始 DAILY-1B、DAILY-2/3 或 Evidence 自动化。

## 8. 完成定义

只有在同一隔离 canonical runtime 中证明以下链路，才可关闭本阻塞：

```text
session
+ canonical stage0_universe
+ daily0_confirmation
+ fresh observation snapshot
+ fresh stage0 market context
→ Dashboard DAILY-1B / waiting_user
```

结果必须写入 8 月试跑记录和工作流状态台账，并以独立 commit 推送。
