# Exchange Trading Date and Session Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 DAILY 和 operating console 以美股交易所交易日而非北京时间自然日选择会话，并阻止旧产物冒充当日就绪产物。

**Architecture:** 扩展现有 `stock_team.utils.market_clock`，使其成为唯一交易日上下文提供者；`daily_status` 只根据选定 session 和产物声明日期计算 validity/freshness；Dashboard server 只负责选择会话并传递上下文，HTML 只展示返回结果。交易所日历不可用时显式降级为 `calendar_unverified`，不创建正式会话。

**Tech Stack:** Python 3、`zoneinfo`、`exchange-calendars`、pytest、现有原生 HTML/JavaScript operating console

---

## 文件职责

- Modify: `stock_team/requirements.txt` — 声明交易所日历依赖。
- Modify: `stock_team/utils/market_clock.py` — 统一生成 ET/CN 时间和当前、最近、下一交易日上下文。
- Modify: `stock_team/tests/unit/core/test_market_clock.py` — 覆盖北京时间跨日、周末、节假日和日历不可用。
- Modify: `stock_team/orchestration/daily_status.py` — 分离产物 validity 与 freshness。
- Modify: `stock_team/tests/unit/orchestration/test_daily_status.py` — 覆盖旧日期、缺日期及当前日期产物。
- Modify: `stock_team/server/dashboard_server.py` — 使用交易日上下文选择当前、待恢复或历史 session。
- Modify: `stock_team/tests/unit/core/test_dashboard_refresh_prices.py` — 覆盖会话选择和 API payload。
- Modify: `investing-os/dashboards/operating-console.html` — 显示 ET 交易日、北京时间和会话性质。
- Modify: `stock_team/tests/integration/test_daily_e2e.py` — 隔离验证 DAILY-0/1 不复用旧日期证据。
- Create: `investing-os/handoff/2026-07-12-exchange-trading-date-isolated-trial.zh.md` — 记录隔离试跑事实与剩余缺口。

### Task 1: 统一交易日上下文

- [ ] **Step 1: 写失败测试**

在 `test_market_clock.py` 增加：北京时间已跨日而美东仍为前一交易日、NYSE 休市日、周末、日历 provider 抛错四类测试。期望返回字段：

```python
assert context["trading_date"] == "2026-07-10"
assert context["now_cn"].startswith("2026-07-11T03:00:00")
assert context["session_kind"] == "current"
assert context["calendar_status"] == "verified"
```

日历异常时：

```python
assert context["calendar_status"] == "unverified"
assert context["formal_session_allowed"] is False
```

- [ ] **Step 2: 验证 RED**

Run: `python -m pytest stock_team/tests/unit/core/test_market_clock.py -q`

Expected: FAIL，因为当前 payload 没有 `trading_date`、`calendar_status` 和 `formal_session_allowed`。

- [ ] **Step 3: 最小实现**

在 `requirements.txt` 添加 `exchange-calendars>=4.5`。在 `market_clock.py` 保留现有 `get_market_clock()` 公共入口，新增可注入的 calendar provider，并返回：

```python
{
    "trading_date": "YYYY-MM-DD" or None,
    "last_trading_date": "YYYY-MM-DD" or None,
    "next_trading_date": "YYYY-MM-DD" or None,
    "now_et": "...",
    "now_cn": "...",
    "calendar_status": "verified" | "unverified",
    "formal_session_allowed": bool,
    "session_kind": "current" | "non_trading_day",
}
```

日历 import 或查询失败时不得退回工作日猜测；返回 `unverified`。

- [ ] **Step 4: 验证 GREEN**

Run: `python -m pytest stock_team/tests/unit/core/test_market_clock.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```powershell
git add stock_team/requirements.txt stock_team/utils/market_clock.py stock_team/tests/unit/core/test_market_clock.py
git commit -m "feat: centralize exchange trading date context"
```

### Task 2: 分离产物有效性与新鲜度

- [ ] **Step 1: 写失败测试**

在 `test_daily_status.py` 创建三个 session-scoped 产物：日期匹配、日期较旧、无日期。断言：

```python
assert current["valid"] is True
assert current["freshness"] == "fresh"
assert old["valid"] is True
assert old["freshness"] == "stale"
assert undated["freshness"] == "unverified"
```

并断言只有 `fresh` 的必需产物能推进 readiness。

- [ ] **Step 2: 验证 RED**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_daily_status.py -q`

Expected: FAIL，因为当前实现把所有 valid 产物标为 fresh。

- [ ] **Step 3: 最小实现**

让 `_artifact()` 独立计算 `valid` 和 `freshness`。JSON 优先读取 `trading_date`，兼容现有 `date`；Markdown 从 session-scoped 文件名归属当前 session，但旧 session 只能在其自身历史 manifest 中有效。流程闸门同时要求 `valid` 且 `freshness == "fresh"`。

- [ ] **Step 4: 验证 GREEN 与回归**

Run: `python -m pytest stock_team/tests/unit/orchestration/test_daily_status.py stock_team/tests/unit/orchestration/test_models.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```powershell
git add stock_team/orchestration/daily_status.py stock_team/tests/unit/orchestration/test_daily_status.py
git commit -m "fix: separate artifact validity from trading-date freshness"
```

### Task 3: 按交易日上下文选择 Dashboard 会话

- [ ] **Step 1: 写失败测试**

在 `test_dashboard_refresh_prices.py` 覆盖：

1. 当前交易日 session 优先于修改时间较新的历史 terminal session；
2. 唯一旧 open session 返回 `recovery_required`；
3. 多个旧 open session 返回 blocked diagnostics；
4. 非交易日且无 open session 返回 `DAY_NOT_STARTED`，不得生成下一交易日 session；
5. payload 同时包含 `trading_date_context` 和 `session_kind`。

- [ ] **Step 2: 验证 RED**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q -k "coordinator or trading_date or session"`

Expected: FAIL，因为 `_load_coordinator_manifest()` 当前只按文件 mtime 选择。

- [ ] **Step 3: 最小实现**

在 `dashboard_server.py` 提取 `_select_dashboard_session(sessions, trading_context)`：

```python
selection = {
    "session": session_or_none,
    "session_kind": "current" | "recovery_required" | "history" | "not_started" | "blocked",
    "diagnostics": [],
}
```

`_load_coordinator_manifest()` 使用 SessionStore 的已验证 session 列表和 `get_market_clock()`，不再单凭 mtime。日历 `unverified` 时不得初始化会话。

- [ ] **Step 4: 验证 GREEN 与回归**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py stock_team/tests/unit/orchestration/test_store.py -q`

Expected: 除已记录的固定日期 freshness 旧测试外全部 PASS；该旧测试若受本变更影响，改为注入固定 now，不得放宽断言。

- [ ] **Step 5: Commit**

```powershell
git add stock_team/server/dashboard_server.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "fix: select dashboard session by exchange trading date"
```

### Task 4: operating console 双时区与会话性质展示

- [ ] **Step 1: 写失败测试**

在 Dashboard 单元测试读取 HTML，断言存在并消费：

```javascript
manifest.trading_date_context
manifest.session_kind
```

同时断言页面保留只读性质，不新增 workflow POST 或推进按钮。

- [ ] **Step 2: 验证 RED**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q -k "operating_console"`

Expected: FAIL，因为页面尚未展示双时区和会话性质。

- [ ] **Step 3: 最小实现**

修改 `operating-console.html` 顶部摘要：显示 `交易日 YYYY-MM-DD ET`、`北京时间 YYYY-MM-DD HH:mm` 和 `当前/待恢复/历史/非交易日`。当 `session_kind == "not_started"` 时显示“今日尚未开始”；Evidence 页不把历史 session artifacts 汇总为今日 readiness。

- [ ] **Step 4: 验证 GREEN**

Run: `python -m pytest stock_team/tests/unit/core/test_dashboard_refresh_prices.py -q -k "operating_console"`

Expected: PASS。

- [ ] **Step 5: Commit**

```powershell
git add investing-os/dashboards/operating-console.html stock_team/tests/unit/core/test_dashboard_refresh_prices.py
git commit -m "feat: show exchange date context in operating console"
```

### Task 5: 隔离 DAILY-0/1 验收与记录

- [ ] **Step 1: 写失败的集成测试**

在 `test_daily_e2e.py` 建立两个 session（旧 session 含完整有效产物，当前 session 无产物），注入北京时间跨日时刻，断言当前 session 仍 waiting_data，旧产物不参与 readiness。

- [ ] **Step 2: 验证 RED 或确认由前述任务已转 GREEN**

Run: `python -m pytest stock_team/tests/integration/test_daily_e2e.py -q -k "trading_date or old_artifact"`

Expected: 若在 Task 2/3 前运行则 FAIL；在实现后 PASS。若立即 PASS，确认测试确实通过移除 freshness 判断会失败，避免无效测试。

- [ ] **Step 3: 运行限定回归**

Run:

```powershell
python -m pytest stock_team/tests/unit/core/test_market_clock.py stock_team/tests/unit/orchestration/test_daily_status.py stock_team/tests/unit/orchestration/test_store.py stock_team/tests/unit/core/test_dashboard_refresh_prices.py stock_team/tests/integration/test_daily_e2e.py -q
```

Expected: 全部 PASS；不得依赖真实 runtime 或网络数据。

- [ ] **Step 4: 浏览器隔离检查**

以临时 runtime 启动 server，检查 `#today`、`#evidence`、`#diagnostics`：旧 session 显示待恢复/历史，Evidence 不显示为今日已就绪，双时区日期正确。

- [ ] **Step 5: 写试跑记录并 Commit**

记录固定输入、命令、结果、未覆盖风险和是否可继续 DAILY-0/1：

```powershell
git add stock_team/tests/integration/test_daily_e2e.py investing-os/handoff/2026-07-12-exchange-trading-date-isolated-trial.zh.md
git commit -m "test: verify exchange-date daily isolation"
```

### Task 6: 最终核验与推送

- [ ] **Step 1: 检查工作树和运行时派生文件**

Run: `git status --short`

Expected: 仅计划内文件；`investing-os/system/runtime/manifests/` 不得进入提交。

- [ ] **Step 2: 运行限定完整测试集**

Run: Task 5 Step 3 的 pytest 命令。

Expected: 全部 PASS。

- [ ] **Step 3: 推送当前分支**

```powershell
git push origin codex/repository-cleanup-20260630
```

- [ ] **Step 4: 交付结论**

报告 commit、测试数、浏览器检查结果，以及“可开始真实 DAILY-0/1”或具体阻断；不得把隔离测试通过表述为真实交易流程已经完成。
