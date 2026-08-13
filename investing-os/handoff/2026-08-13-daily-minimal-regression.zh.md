# 2026-08-13 DAILY 最小回归记录

日期：2026-08-13
交易日期口径：纽约时区 / 交易所日历
运行方式：隔离 runtime，`observation`，无交易权限

## 1. 本轮范围

本轮只验证恢复计划中最小 DAILY 的四个重点：

1. 真实交易日期；
2. 跨日恢复既有回归；
3. 盘前价格的时间、来源和时段；
4. Dashboard 是否读取同一 session 与 canonical artifact 路径。

遇到首个真实阻塞后停止扩展，以根因调查和 TDD 修复，不继续进入焦点池、交易计划或盘中链。

## 2. 基线验证

- `market_clock` 在 2026-08-13 08:35 ET 返回：`phase=premarket`、`trading_date=2026-08-13`、`last_trading_date=2026-08-12`、`next_trading_date=2026-08-14`、`calendar_status=verified`；
- `python -m pytest stock_team/tests/unit/orchestration stock_team/tests/integration/test_daily_e2e.py -q`：168 passed；
- 修复完成后的扩展回归：
  `python -m pytest stock_team/tests/unit/orchestration stock_team/tests/integration/test_daily_e2e.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q`：230 passed；
- 分支同步前审计未发现 runtime/account/trade-history 被纳入待推送提交，远端同步后 ahead/behind 为 `0/0`。

跨日恢复在本轮达到 `test-covered`，没有在首个阻塞修复前继续构造第二个 runtime 场景。

## 3. canonical 隔离试跑

隔离根目录：

```text
%TEMP%/investing-os-daily-canonical-20260813/investing-os
```

通过 `INVESTING_OS_HOME` 让 session、inputs、packets 和 manifests 全部指向同一棵 canonical runtime。直接给 coordinator 传任意 sessions 路径而不设置该变量，会导致 Dashboard 回读主仓库 runtime；该现象是试跑配置错误，不是生产代码路径缺陷。

会话：

```text
session_id: observation-2026-08-13
session_type: observation
permission: no_trading_permission
```

`start_stage0_observation` 成功生成：

- `inputs/observation-2026-08-13-pre-market-snapshot.json`
- `packets/observation-2026-08-13-stage0-market-context.md`
- `inputs/observation-2026-08-13-premarket-tape.json`

状态从 `DAY_INITIALIZED` 到 `STAGE0_READY`。观察产物明确标记 `evidence_level=observation_only`，没有授予交易权限。

## 4. 盘前数据真实性

在约 08:36 ET 获取到的代表性事实：

| 标的 | 价格/状态 | 对照 | 来源与时间 |
|---|---:|---:|---|
| QQQ | 约 723.75 | 前收 723.70 | `yfinance_1m_prepost`，约 08:36 ET |
| SPY | 约 773.81 | 前收 772.49 | `yfinance_1m_prepost`，约 08:36 ET |
| IWM | 约 303.35 | 前收 302.71 | `yfinance_1m_prepost`，约 08:36 ET |
| NQ=F | 29829.5，约 -0.16% | 29878 | `yfinance_1m_futures`，约 08:26 ET |
| BTC-USD | 约 63569.98，约 -0.85% | — | 盘前跨资产观察数据 |

`missing_symbols=[]`、`warnings=[]`。QQQ 因 reported volume 为零被降级为 degraded quality，但价格带有盘前时间戳，并非把 8 月 12 日收盘价冒充为盘前价。

## 5. 首个真实阻塞与根因

### 表象

Stage 0 数据已经生成，coordinator 已到 `STAGE0_READY`，但 Dashboard 仍显示 DAILY-0 等待用户确认。

### 根因

系统已有：

- `daily0_confirmation` session schema；
- daily-status 对 DAILY-0 确认的检查；
- Dashboard 的只读缺口展示。

但没有任何正式命令把当前对话中的用户确认写入 session。真实使用只能人工修改 JSON，因此 DAILY-0 无法沿正式入口完成。

只读行情预取本身不是缺陷：它可以在无交易权限下提前生成；缺陷是用户确认没有 canonical 写入入口。

## 6. 最小修复

新增：

```text
python -m stock_team.coordinator_cli confirm-daily0
```

该命令显式接收：

- session id；
- activity mode；
- account fact status；
- account snapshot reference；
- analysis scope reference。

它只写入 `daily0_confirmation`、递增 `state_version`、更新时间；不推进 coordinator 状态，不运行行情工具，不改变交易权限。Dashboard 仍然只读，不增加第二套业务逻辑。

TDD 证据：写入测试首先因 `confirm-daily0` 命令不存在而失败；模式一致性测试首先证明错误模式会被接受。最小实现后两项均通过；完整相关回归为 230 passed。

## 7. 修复后合流结果

对同一个隔离 session 执行 `confirm-daily0` 后：

- Dashboard 从 `DAILY-0 / waiting_user` 前进到 `DAILY-1A / waiting_data`；
- 当日 `premarket_snapshot`：present、valid、fresh；
- 当日 `stage0_market_context`：present、valid、fresh；
- 没有重新采集行情，也没有升级为 trading；
- coordinator 仍为 `STAGE0_READY`。

这证明 DAILY-0 正式写入入口已修通。

## 8. 下一阻塞

Dashboard 目前在 DAILY-1A 明确缺少：

```text
stage0_universe
```

观察 Stage 0 adapter 生成 snapshot、market context 和 tape，但没有生成 daily-status 要求的 canonical universe 文件。因此系统尚不能宣布 DAILY 稳定。

下一步只处理这个边界：先确认 universe 应由 DAILY-0 的 analysis scope 物化，还是由 observation Stage 0 生成；确定唯一归属后再以失败测试和最小实现修复。
