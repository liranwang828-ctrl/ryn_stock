# DAILY H4 低阶任务包

日期：2026-07-01
前置约束：`investing-os/handoff/2026-07-01-daily-h4-review-contract.zh.md`
适用对象：低阶模型

## 总规则

- 只能按本任务包施工，不得修改 H4 语义。
- 每个任务单独 commit。
- 不得自行新增复盘问题组、候选层级或脑-肌边界。

## H4-L1 结构化产物骨架

### 目标

实现 DAILY-4 结构化复盘文件的 schema、路径、校验与最小持久化。

### 允许修改

- review schema / models / validators
- runtime path registration
- 相关单元测试

### 禁止修改

- 6 组对话问题
- 用户确认点
- `stock_team` 输出边界

### 输出契约

- 生成 `.../{session_id}-daily4-review.json`
- schema 至少覆盖 `fact_packet_refs`、`review_judgments`、`candidate_lessons`、`user_confirmations`、`archive_closure`

### 验收命令

```text
python -m pytest -q stock_team/tests/unit/orchestration stock_team/tests/unit/core/test_cli.py
```

## H4-L2 `quick_review` / `freeze` 最小记录

### 目标

把 `quick_review` 和 `freeze` 的最小记录接到 H4 结构里，但不假装成完整 `full_review`。

### 允许修改

- coordinator / transitions / serializers
- 相关测试

### 禁止修改

- 把 `freeze` 伪装成完整复盘
- 在 `quick_review` 中自动生成完整 `candidate_lessons`

### 输出契约

- `quick_review` 只写最小风险检查记录
- `freeze` 只写欠账记录

### 验收命令

```text
python -m pytest -q stock_team/tests/unit/orchestration stock_team/tests/integration/test_daily_e2e.py
```

## H4-L3 `full_review` 接线与测试

### 目标

把 `full_review` 从公开入口接到 H4 结构化产物，并验证用户确认门与归档门。

### 允许修改

- coordinator / CLI / review persistence / tests

### 禁止修改

- 没有用户确认就落最终 judgment
- `ibkr_fact_status != verified` 时标记正式完整复盘完成

### 输出契约

- `full_review` 能写出完整 DAILY-4 review artifact
- user confirmations 缺失时阻断最终完成
- archive success 前不得宣称完成

### 验收命令

```text
python -m pytest -q stock_team/tests/unit/orchestration stock_team/tests/unit/core/test_cli.py stock_team/tests/integration/test_daily_e2e.py
```
