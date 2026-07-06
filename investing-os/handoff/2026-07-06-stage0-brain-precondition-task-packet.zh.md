# Stage0 Brain Preconditions 低阶任务包

日期：2026-07-06  
前置文件：[`2026-07-06-stage0-brain-precondition-blocker.zh.md`](./2026-07-06-stage0-brain-precondition-blocker.zh.md)

## 本轮只做

- 找清 `market-context` 最小 brain-side precondition 契约
- 让默认 Stage 0 universe 生成路径满足它
- 用真实隔离命令证明 `start_stage0_from_snapshot` 不再卡在 `missing_brain_precondition_state`

## 允许读取

- `stock_team/cli.py`
- `stock_team/server/dashboard_server.py`
- `stock_team/tests/unit/core/test_cli.py`
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`
- `stock_team/tests/unit/orchestration/test_adapters.py`

## 允许修改

- `stock_team/server/dashboard_server.py`
- `stock_team/cli.py`
- `stock_team/tests/unit/core/test_cli.py`
- `stock_team/tests/unit/core/test_dashboard_refresh_prices.py`

## 禁止修改

- `stock_team/orchestration/models.py`
- `stock_team/orchestration/transitions.py`
- `stock_team/tests/integration/test_daily_e2e.py`
- Stage 1/2/3/4、archive、review 相关文件
- 不要顺手改 freshness 旧失败

## 目标

1. 确认真实 `market-context` 接受的最小 brain-side字段
2. 修补默认 Stage 0 universe 生成路径，使其满足真实 CLI 要求
3. 给出真实隔离命令证据，证明不再报：
   - `missing_brain_precondition_state`

## 必须交付的证据

### 测试证据

- `python -m pytest stock_team/tests/unit/core/test_cli.py -q`
- `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q`

### 真实命令证据

必须附一段真实运行摘要，至少包含：

- 使用的隔离 runtime 路径
- 生成的 universe 文档路径
- 运行的 `python -m stock_team.cli market-context ...` 命令
- 返回码
- stdout / stderr 关键行
- Stage 0 packet 是否生成

## 完成定义

- 真实 `market-context` 不再报 `missing_brain_precondition_state`
- formal snapshot 场景下可生成 Stage 0 packet
- 不扩大 scope

## 交付格式

```text
本轮只审：
- Stage0 brain precondition 最小契约
- 默认 universe 生成路径是否满足真实 market-context
- 真实命令是否不再报 missing_brain_precondition_state

提交：
- <commit sha>

低阶摘要：
- 改动文件：
- 关键行为：
- 新增/修改测试：
- 验收命令与结果：
- 真实命令结果：
- 未确认风险：

需要高阶复核：
- 静态 review
- 跑上述 pytest
- 看真实 market-context 命令输出
```
