# DAILY 剩余修复高阶纲领

日期：2026-07-01
适用范围：`DAILY` 主链剩余修复
依据：
- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- `investing-os/handoff/reviews/2026-07-01-daily-implementation-review.md`
- `investing-os/handoff/decisions/2026-07-01-daily-q1-q3-approval.md`
- `investing-os/handoff/DAILY-REMAINING-WORK-ALLOCATION.zh.md`

## 1. 目的

本纲领只解决三件必须由高阶模型先定清的事：

1. `H1` 跨日恢复状态语义
2. `H2` 归档契约
3. `H3` observation 公共动作契约

它不是代码实现说明，也不是完整 DAILY 终版设计。低阶模型后续只能在本纲领约束下完成 `L1/L2/L3`，不得再自行发明状态语义、归档范围或公开动作名。

## 2. 范围外

以下内容不在本轮定义范围内：

- `H4` DAILY-4 复盘对话问题与结构化产物细节
- IBKR streaming 真接线
- 最终公开入口 E2E 验收结论
- RESEARCH / REVIEW / LEARNING / VALIDATION / SYSTEM 工作流扩展

## 3. H1 跨日恢复状态语义

### 3.1 基本原则

- 恢复逻辑先处理“旧会话”，再决定是否允许创建“今日日会话”。
- `full_review` 在旧会话完成完整 DAILY-4 之前，不得创建今日日会话。
- `quick_review` 和 `freeze` 都是“收掉旧会话”的路径，但保留不同强度的复盘债务记录。
- 遇到多旧会话或损坏会话时，不得静默跳过；必须阻断并要求显式处理。

### 3.2 旧会话识别优先级

当 `init-day` 或等价公开入口启动时，按以下顺序检查：

1. 找出所有非 `DAY_ARCHIVED` 的旧会话
2. 若存在损坏或无法校验的会话文件，先阻断
3. 若存在多个未关闭旧会话，先阻断
4. 若存在单个未关闭旧会话，进入恢复选择
5. 若无未关闭旧会话，允许正常创建今日日会话

### 3.3 阻断条件

以下情况必须阻断，不得自动继续：

- `SessionStore.list_sessions()` 发现无法解析、schema 不合法或关键字段缺失的会话文件
- 同时存在多个非 `DAY_ARCHIVED` 旧会话
- 旧会话处于 `REVIEW_REQUIRED` 且用户未完成 `full_review`
- 用户选择 `full_review` 但旧会话未进入 `DAY_ARCHIVED`

### 3.4 恢复选项语义

| 恢复选项 | 允许进入条件 | 对旧会话的要求 | 旧会话结束状态 | 是否允许立即创建今日日会话 |
|---|---|---|---|---|
| `freeze` | 旧会话已到或视作到 `MARKET_CLOSED`；用户明确接受欠账 | 创建复盘欠账记录；不做正式复盘完成判断 | `CLOSED_UNREVIEWED`，随后 `DAY_ARCHIVED` | 是 |
| `quick_review` | 用户只做最小风险检查；无需完整复盘对话 | 至少检查持仓异常、风险偏离、待处理警告，并生成最小记录 | `QUICK_REVIEWED`，随后 `DAY_ARCHIVED` | 是 |
| `full_review` | 用户准备完成完整 DAILY-4 | 必须完成正式复盘事实包、用户对话确认、归档 | `DAY_ARCHIVED` | 否，直到旧会话归档完成 |

### 3.5 旧状态到恢复路径矩阵

| 旧状态 | `freeze` | `quick_review` | `full_review` |
|---|---|---|---|
| `DAY_INITIALIZED` | 允许。视为盘前中断，记录“未进入 DAILY-1 完整链” | 允许。最小检查后归档 | 允许。补做完整复盘后归档 |
| `FOCUS_CONFIRMED` | 允许。视为 observation 或 trading 盘前中断 | 允许 | 允许 |
| `PLAN_APPROVED` | 允许。视为已过盘前但未完成盘中/盘后 | 允许 | 允许 |
| `OBSERVATION_ACTIVE` | 允许。按观察模式收尾，不生成交易权限 | 允许 | 允许 |
| `INTRADAY_ACTIVE` | 允许。必须标注为盘中中断收尾 | 允许 | 允许 |
| `MARKET_CLOSED` | 允许 | 允许 | 允许，且这是最自然路径 |
| `REVIEW_REQUIRED` | 不允许 | 不允许 | 只允许继续完整复盘 |
| `FAILED_TOOL` | 不允许静默恢复；需先判断是否属于旧会话损坏 | 不允许静默恢复 | 不允许静默恢复 |

### 3.6 `quick_review` 最小检查合同

`quick_review` 至少要落地以下固定字段：

- `session_id`
- `trading_date`
- `review_mode = "quick_review"`
- `position_anomalies`
- `risk_drift_summary`
- `pending_warnings`
- `user_confirmation`
- `archived_at`

没有上述字段，不得把 `quick_review` 视为已完成。

## 4. H2 归档契约

### 4.1 基本原则

- 归档只复制“会话 artifact ledger 中已登记”的文件。
- 归档必须保留相对路径，不允许把递归文件拍平到同一目录。
- 归档结果必须生成 manifest，且 `archive_day` 只有在 manifest 成功写入后才算完成。
- 会话未归档完成前，不得声称 DAILY-4 完成。

### 4.2 归档输入

归档器只接受：

- `session_id`
- `session_file`
- `artifact_ledger`
- `archive_root`

其中 `artifact_ledger` 是唯一白名单。未登记文件一律不复制。

### 4.3 归档输出

归档完成后必须产生：

- `archive_manifest.json`
- 已复制的归档文件树
- 会话状态中的 `archive_manifest_path`

### 4.4 canonical archive 路径

统一使用：

`investing-os/system/runtime/archive/{trading_date}/{session_id}/`

manifest 路径：

`investing-os/system/runtime/archive/{trading_date}/{session_id}/archive_manifest.json`

### 4.5 manifest 最小 schema

manifest 至少包含：

```json
{
  "session_id": "string",
  "trading_date": "YYYY-MM-DD",
  "archived_at": "ISO-8601",
  "source_session_path": "string",
  "files": [
    {
      "logical_name": "string",
      "source_path": "string",
      "archive_path": "string",
      "sha256": "string",
      "size_bytes": 123,
      "status": "archived | missing | hash_mismatch | rejected"
    }
  ],
  "missing_files": ["string"],
  "rejected_files": ["string"]
}
```

### 4.6 缺失与拒绝规则

- ledger 中列出但源文件不存在：记为 `missing`，归档失败
- 文件路径越出 session/runtime 合法范围：记为 `rejected`，归档失败
- 同一 `archive_path` 发生冲突：归档失败，不得覆盖
- manifest 写入失败：归档失败

### 4.7 `archive_day` 完成条件

只有同时满足以下条件，`archive_day` 才算成功：

1. manifest 已写入
2. ledger 中必须归档的文件全部成功复制
3. 会话状态更新为 `DAY_ARCHIVED`
4. 会话状态登记 `archive_manifest_path`

## 5. H3 observation 公共动作契约

### 5.1 基本原则

- observation 是独立只读路径，不得借壳 trading。
- Dashboard、CLI、coordinator、adapter 必须使用同一套公共动作名。
- 公共动作名描述“用户能请求什么”，不是底层 helper 或 CLI 子命令名。

### 5.2 observation 允许状态

- `DAY_INITIALIZED`
- `FOCUS_CONFIRMED`
- `OBSERVATION_ACTIVE`
- `MARKET_CLOSED`

### 5.3 公共动作列表

| 公共动作 | 允许状态 | 含义 | 禁止结果 |
|---|---|---|---|
| `start_observation` | `DAY_INITIALIZED` | 从 DAILY-1 完成的关注池进入开盘观察 | 不授予交易权限 |
| `refresh_market_observation` | `OBSERVATION_ACTIVE` | 刷新盘中事实快照与状态展示 | 不生成交易计划，不改变风险模式 |
| `record_observation_exception` | `OBSERVATION_ACTIVE` | 记录观察到的异常或备注 | 不升级为交易动作 |
| `close_observation_day` | `OBSERVATION_ACTIVE` | 结束观察日并进入 `MARKET_CLOSED` | 不写入交易执行结论 |
| `archive_day` | `MARKET_CLOSED` | 归档观察日 | 不绕过 manifest |

### 5.4 映射原则

- `ACTION_INTENTS` 使用上表公共动作名
- `BEGIN_TRANSITIONS` 和状态机使用同名动作
- adapter 层可再映射到底层实现，例如单次快照 helper，但该映射不对外暴露
- `allowed_actions` 只展示 coordinator 真能执行的公共动作

### 5.5 observation 明确禁止

在任何 observation 状态下都禁止：

- 生成或修改 trading plan
- 修改 `risk_mode`
- 暴露 buy / sell / scale-in / scale-out 等交易动作
- 通过 `refresh_market_observation` 间接写入交易权限

## 6. 对低阶模型的边界要求

低阶模型在 `L1/L2/L3` 中：

- 可以实现本纲领已定清的状态和 schema
- 可以补测试、接 coordinator、adapter、CLI、dashboard
- 不可以改动本纲领中的状态语义、归档白名单原则、manifest 最小 schema、公共动作名
- 若发现现有代码与本纲领冲突，必须停在“冲突说明 + 建议修正点”，不能自行改语义

## 7. 本纲领后的执行顺序

```text
L1 observation 动作一致性
-> L2 白名单归档接线
-> L3 跨日恢复实现
-> 高阶复核
```

只有 `L1/L2/L3` 全部通过高阶复核后，才进入 `H4` 和后续 E2E 验收。
