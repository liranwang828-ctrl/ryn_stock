# DAILY Status Manifest 设计

日期：2026-07-11  
状态：用户已逐段确认

## 1. 目标

建立一个独立、只读的 manifest builder，从现有 DAILY canonical 文件推导当前步骤、缺口、数据新鲜度和下一句对话建议。每日交易 Dashboard 只渲染 manifest，不承担业务判断或流程推进。

状态来源优先级：

1. canonical 文件内容与用户确认字段；
2. 文件的数据来源、日期和新鲜度；
3. coordinator session 作为执行历史与恢复参考；
4. Dashboard 缓存只作降级展示，不能决定完成状态。

canonical 文件与 coordinator 冲突时，以文件显示真实进度，同时报告 `state_sync_needed`。第一版不自动修改 coordinator。

## 2. 架构选择

采用独立只读 manifest builder。

不采用：

- 把更多检查逻辑塞进 `dashboard_server.py`；
- 让 coordinator state 成为 manifest 的唯一事实；
- 让 Dashboard 直接解析多个业务文件。

数据流：

```text
canonical DAILY files + coordinator session
-> independent manifest builder
-> daily-status.json
-> operating console read-only render
```

## 3. 顶层 schema

```json
{
  "schema_version": "1.0",
  "trading_date": "YYYY-MM-DD",
  "generated_at": "ISO-8601",
  "current_node": "DAILY-1",
  "current_step": "DAILY-1B",
  "overall_status": "waiting_user",
  "observation_available": true,
  "next_conversation_prompt": "请在当前对话确认进入 Stage 1 的标的。",
  "nodes": [],
  "artifacts": [],
  "missing_items": [],
  "warnings": [],
  "state_sync": {
    "needed": true,
    "canonical_step": "DAILY-1B",
    "coordinator_state": "STAGE0_READY",
    "suggested_action": "review_state_sync_in_conversation"
  },
  "cognition_links": {
    "context_inputs": [],
    "cognition_updates": [],
    "promotion_queue": ""
  }
}
```

主进度只显示 DAILY-0 至 DAILY-4。仅当前节点展开子步骤。DAILY-1 使用：

- DAILY-1A 市场环境；
- DAILY-1B 焦点确认；
- DAILY-1C 标的证据；
- DAILY-1D 计划确认。

## 4. 状态词与优先级

只使用：

- `not_started`
- `waiting_data`
- `waiting_user`
- `active`
- `blocked`
- `complete`

优先级：`blocked` > `waiting_user` > `waiting_data` > `active` > `complete` > `not_started`。

同时缺数据和等待用户时，只有现有数据足以支持有效讨论才显示 `waiting_user`；否则先显示 `waiting_data`。

正式数据不足但可只读观察时，使用 `waiting_data` 并设置 `observation_available: true`。

## 5. 检查边界

每个产物只检查三层：

1. `present`：文件存在；
2. `valid`：结构、日期、来源和必填字段符合 contract；
3. `confirmed`：需要用户确认的文件含明确确认字段。

检查器不得判断市场解释是否正确、焦点标的是否值得交易、风险模式是否合理、经验候选是否应晋升。

文件结构与确认有效但引用数据过期时，保留 `valid/confirmed`，步骤状态为 `waiting_data`，直到事实刷新。新鲜度标准由各产物 contract 定义，manifest 只执行规则。

## 6. artifact、node 与 missing item

Artifact：

```json
{
  "role": "stage1_decision_sheet",
  "path": "...",
  "present": true,
  "valid": true,
  "confirmed": true,
  "freshness": "fresh",
  "source": "investing-os",
  "updated_at": "...",
  "issues": []
}
```

Dashboard 默认隐藏绝对路径；展开详情后显示路径、来源、时间和问题。

Node：

```json
{
  "node": "DAILY-1",
  "label": "盘前决策",
  "status": "waiting_user",
  "current_substep": "DAILY-1B",
  "substeps": [
    {
      "step": "DAILY-1A",
      "label": "市场环境",
      "status": "complete",
      "artifact_roles": [
        "stage0_universe",
        "premarket_snapshot",
        "stage0_market_context"
      ]
    }
  ]
}
```

Missing item：

```json
{
  "code": "focus_confirmation_missing",
  "severity": "waiting_user",
  "artifact_role": "stage1_decision_sheet",
  "field": "user_confirmed",
  "message": "焦点池尚未由用户确认。",
  "conversation_prompt": "请在当前对话确认进入 Stage 1 的标的。"
}
```

同时存在多个缺口时，Dashboard 只显示最高优先级的一句 `next_conversation_prompt`，其余保留在清单中。提示语来自固定映射，不由 Dashboard 自由生成。

## 7. DAILY-0 判定

### 7.1 Session 扩展

在现有 session JSON 增加：

```json
{
  "daily0_confirmation": {
    "confirmed_at": "ISO-8601",
    "activity_mode": "trading | observation | research | review | maintenance",
    "account_fact_status": "verified | stale_unverified | missing",
    "account_snapshot_ref": "...",
    "analysis_scope_ref": "...",
    "user_confirmed": true
  }
}
```

不新增平行 `daily0-confirmation.json`。

### 7.2 完成条件

- session 日期、类型和状态有效；
- 跨日欠账已处理或明确进入 recovery；
- `daily0_confirmation.user_confirmed == true`；
- trading 正式路径要求 `account_fact_status == verified`；
- stale/missing 时可进入只读观察，但不得授予新交易权限。

## 8. DAILY-1 判定

| 子步骤 | 现有文件 | 完成条件 |
|---|---|---|
| DAILY-1A 前置范围 | `{session_id}-stage0-universe.json` | 五项脑侧结构、日期和来源有效 |
| DAILY-1A 盘前事实 | `{session_id}-pre-market-snapshot.json`、`{session_id}-stage0-market-context.md` | 当日真实盘前数据；as-of 合格；引用一致 |
| DAILY-1B 环境讨论 | `{session_id}-stage0-discussion-notes.md` | 引用有效 Stage 0；包含环境、风险、优先级和排除项 |
| DAILY-1B 焦点确认 | `{session_id}-stage1-decision-sheet.json` | 日期一致；focus symbols 存在；`user_confirmed=true` |
| DAILY-1C 标的证据 | `{session_id}-stage1-plan-evidence.md` | 只覆盖确认焦点池；引用同日 Stage 0/decision sheet |
| DAILY-1D 计划确认 | `{session_id}-trading-plan.json`、`{session_id}-intraday-guidance.json` | 风险、允许/禁止动作、失效条件和引用完整；计划版本经用户确认 |

Trading plan 增加计划版本确认字段：

```json
{
  "user_confirmation": {
    "confirmed": true,
    "confirmed_at": "ISO-8601",
    "confirmed_version": "..."
  }
}
```

现有 universe builder 中的缓存 positions、硬编码 cognition 和 Yellow permission 只能作为草稿或降级输入，不满足正式 DAILY-0/1 完成条件。

## 9. DAILY-2/3

DAILY-2 读取 intraday snapshot、已确认 plan 和 guidance。正常刷新只更新事实。计划失效、风险触发或准备首次建仓时，将最高优先级提示切回当前对话。

新增 canonical 文件：

`runtime/inputs/{session_id}-intraday-events.jsonl`

事件 schema：

```json
{
  "event_id": "evt-...",
  "observed_at": "ISO-8601",
  "symbols": ["NVDA"],
  "source": "user | system",
  "fact_summary": "",
  "user_thought": "",
  "model_response_summary": "",
  "conversation_ref": "",
  "plan_impact": "none | condition_check | invalidation | change_candidate",
  "confirmation_required": false,
  "confirmation_status": "not_required | pending | confirmed | rejected",
  "review_status": "pending_review | reviewed | archived"
}
```

普通观察只追加事件；`change_candidate` 不得直接改写计划；首次建仓、加仓和计划外动作必须确认。session 的 `intraday_exceptions` 继续记录已批准例外。

第一实施批次只完成 DAILY-0/1，不实现 intraday event runtime。

## 10. DAILY-4 与 cognition

DAILY-4 读取 IBKR 成交事实、plan versions、intraday events、Stage 0/1 证据和 daily4 review。完成要求：

- IBKR fact status 满足 review mode；
- 高价值、异常和矛盾事件已处理；
- candidate lessons 已形成；
-规定用户确认完成；
- archive manifest 已生成。

经验候选进入既有 promotion queue/traceability 链，不直接晋升长期认知。

## 11. 双 Dashboard

每日交易 Dashboard：

- 读取 manifest；
- 显示 DAILY-0..4、当前子步骤、最高优先级提示、产物、缺口、新鲜度和盘中事件；
- 不推进步骤，不自动同步 coordinator；
- Dashboard 刷新只重建 manifest。

认知 Dashboard：

- 保持现有 growth dashboard 与 indexes 生成链；
- 接收 DAILY-4 cognition updates、promotion queue 和 lineage 更新；
- 第一实施批次不修改。

## 12. 恢复规则

- 每次从 canonical 文件重建，不依赖旧 manifest；
- manifest 是派生视图，可以覆盖写；
- 损坏文件保留路径和错误，不猜测内容；
- canonical 文件领先时报告 `state_sync_needed`；
- 第一版只报告，不自动同步；
- Dashboard 不可用时，对话与 canonical 文件仍可继续。

## 13. 第一实施批次

1. manifest JSON schema 与路径 contract；
2. DAILY-0/1 artifact validators；
3. read-only manifest builder；
4. session `daily0_confirmation` 与 trading plan confirmation schema；
5. operating console 只读接线；
6. offline fixture 隔离试跑 DAILY-0/1；
7. 真实盘前数据试跑另行安排，不在离线验收中伪造成功。
