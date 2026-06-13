# Dashboard 优化设计文档

> 日期：2026-05-23 | 状态：已确认 | 目标：内容完整性 → 可维护性 → 交互

---

## 一、背景与问题诊断

当前 `stock_team` 的本地 dashboard（`dashboard_server.py` + `dashboard_writer.py` + `daily_dashboard.html.j2`）存在 8 个问题：

| # | 问题 | 根因 | 严重度 |
|---|------|------|--------|
| 1 | 更新持仓后组合风险无刷新按钮 | 无 `/api/refresh-portfolio` 端点 | 高 |
| 2 | 净值历史曲线不随持仓变化更新 | 同 #1，数据源不重建 | 高 |
| 3 | 关注列表「📊生成」按钮含义不明 | 只判断有无 CIO 报告，无整体状态标签 | 中 |
| 4 | 流程引导断裂：扫描→盘前决策之间缺确认步骤 | Pipeline 设计不完整 | 高 |
| 5 | 盘前决策汇总后流程卡在「待计划」 | SOP 状态检测用错误文件（daily_plan 而非 premarket_summary） | 高 |
| 6 | 盘中详情 tab 完全无内容 | 仅依赖 poll.py 的 intraday_snapshot，盘前无数据 | 高 |
| 7 | CIO 脑暴不应阻塞主流程 | Pipeline 中将 CIO 设为独立顺序步骤 | 中 |
| 8 | 盘中监测（poll）无法启动 | 待排查（Python 路径/依赖/poll.py 逻辑） | 待确认 |

此外，`daily_dashboard.html.j2` 已膨胀至 3838 行，`scratch/` 目录中 30+ 个探测脚本反映了维护困难。

---

## 二、数据依赖链分析

盘前决策汇总的完整数据链：

```
cio.py (多智能体辩论)
  ↓
strategic_memo_writer.py
  ↓ 产出
strategic_memo_{SYM}.json          ← 被 macro_strategy.py 读取
  ↓
macro_strategy.py                   ← 无 memo 则跳过
  ↓ 产出
macro_strategy_{SYM}.json          ← 被 premarket_summary.py 读取（止损/TP/节点）
  ↓
premarket_summary.py                ← 无 memo → lite_mode；无 macro_strategy → auto_atr 回退
  ↓ 产出
premarket_summary_{date}_{SYM}.json
```

**结论**：CIO 不是可选项 — `strategic_memo` 缺失会导致整个链条降级。正确的做法是将 CIO 集成进盘前决策流程，但对已有 memo 的标的自动跳过。

---

## 三、解决方案

### 3.1 新增/增强 API 端点（dashboard_server.py）

#### `/api/refresh-portfolio` (GET, 新增)
- 功能：重建当日 `portfolio_snapshot_{date}.json`
- 实现：调用 `portfolio_snapshot.build_portfolio_snapshot()` + `write_portfolio_snapshot()`
- 触发：Overview 组合卡片的「🔄 刷新组合」按钮
- 响应：`{"status": "ok", "snapshot_path": "..."}`

#### `/api/run?task=premarket` (GET, 增强)
- 当前：直接调用 `premarket_summary.py`
- 增强为智能管道：
  1. 读取 `daily_focus.json` 获取今日关注列表
  2. 对每只标的检查 `strategic_memo_{SYM}.json` 是否存在
  3. 缺失的 → 后台执行 `cio.py SYM --phases 0123` + `strategic_memo_writer.py SYM`
  4. 全部有 memo → 执行 `macro_strategy.py SYM`（每只）
  5. 执行 `premarket_summary.py SYM1 SYM2 ...`
  6. 进度输出到 `logs/task_premarket.log`
- 如已在运行中返回 409

#### `/api/generate-focus-reports` (GET, 新增)
- 功能：一键对关注列表中所有缺失报告的标的批量生成
- 流程：同 premarket 管道的步骤 3-5
- 区别：不等待全部完成，逐个异步启动

#### `/api/status` (GET, 修改)
- 修复 SOP 状态检测：
  - Step 1 (扫描): 检查 `candidates_{date}.json` 存在 → 不变
  - Step 2 (确认关注): 检查 `daily_focus.json` 中 `focus_stocks` 非空
  - Step 3 (盘前决策): 检查 `findings/premarket_summary_{date}_{SYM}.json` 存在 ≥1
  - Step 4 (轮询): 检查 `ACTIVE_TASKS` 中 poll 是否运行中
  - Step 5 (复盘): 检查 `findings/postmarket_summary_{date}.json` 存在 → 不变

### 3.2 上下文字段增强（dashboard_writer.py）

`build_dashboard_context()` 新增字段：

```python
# 每只标的的三态报告状态
report_status = {}  # {sym: {"has_cio": bool, "has_memo": bool, "has_macro_nodes": bool, "has_premarket_summary": bool}}

# macro_strategy 节点数据（供 Intraday tab 盘前展示）
macro_nodes = {}    # {sym: {nodes: {...}}}

# 关注列表（从 daily_focus.json 读取，与 focus_list 合并）
```

### 3.3 模板拆分

| 文件 | 内容 | 估算行数 |
|------|------|----------|
| `templates/base.html.j2` | HTML 骨架、CSS 变量、通用样式、tab bar 框架 | ~600 |
| `templates/overview.html.j2` | 总览 tab | ~500 |
| `templates/intraday.html.j2` | 盘中详情 tab（合并 events） | ~400 |
| `templates/command_hub.html.j2` | 控制中心 tab | ~500 |
| `templates/paper_trading.html.j2` | 模拟账户 tab | ~300 |
| `templates/research.html.j2` | 研报中心 tab | ~200 |
| `templates/postmarket.html.j2` | 盘后复盘 tab | ~200 |
| `templates/scripts.js.j2` | 全部 JavaScript | ~600 |
| `templates/modals.html.j2` | 交易记录弹窗等模态框 | ~200 |

`base.html.j2` 通过 `{% include %}` 引入子模板，原有 `daily_dashboard.html.j2` 保留为兼容入口（`{% extends 'base.html.j2' %}`）。

### 3.4 各 Tab 内容变更

#### Overview 总览
- 组合风险卡：标题右侧新增「🔄 刷新组合」按钮
- 净值走势图：刷新后 30 秒自动重载
- 今日关注列表：
  - 操作列改为状态标签组：`✅CIO` / `⚠️待生成` | `✅研报` / `—` | `✅节点` / `—`
  - 表头上方新增「⚡ 一键生成全部缺失报告」按钮
  - 单只「生成」按钮改名为「生成报告」并保留

#### Intraday 盘中详情
- 盘前阶段：展示 premarket_summary 中的关键价位（dynamic_stop / tp1 / add1 / flex_reduce / scenario_downgrade / thesis_status）
- 盘中阶段：poll.py 启动后按标的实时叠加快照
- LLM 事件列表并入此 tab

#### Command Hub 控制中心
- 新增 Step 1.5：「确认关注列表」— 静态提示，显示当前 focus_list
- Step 2→3：「盘前决策汇总」— 增强的「▶ 运行」按钮
- 移除旧 Step 3：「CIO 深度辩论」— 功能移至研报中心 tab
- 保留右侧控制台的手动 CIO 触发（下拉框）
- SOP 状态实时反映

### 3.5 新增前端 JS 函数

```javascript
refreshPortfolio()      // 调用 /api/refresh-portfolio → 30秒后 reload
generateAllReports()    // 批量生成缺失报告 → 轮询日志
getReportStatus(sym)    // 渲染三态标签
```

---

## 四、实施顺序

1. **dashboard_server.py** — 后端改动（新增 API + 增强 premarket + SOP 修复）
2. **dashboard_writer.py** — 新增上下文字段
3. **模板拆分** — 从现有单体模板提取 9 个子模板（不改变功能）
4. **Overview tab 内容** — 刷新按钮 + 状态标签 + 批量生成
5. **Command Hub 重排** — Step 1.5 + 增强 Step 2 + 移除 Step 3
6. **Intraday tab 内容** — 盘前节点 + 盘中快照占位
7. **排查 poll 启动** — 调试 #8
8. **交互增强** — Chart.js + 视觉优化（延后）

---

## 五、不改动的范围

- `poll.py` / `premarket.py` / `cio.py` / `macro_strategy.py` 等分析脚本本身
- `harvest_agent.py` / `candidate_scanner.py` 的逻辑
- `positions.json` 等配置文件结构
- `session_manager.py` 的 workfow 编排（dashboard 独立于 CLI 工作流）

---

## 六、测试验证点

- [ ] `/api/refresh-portfolio` 成功重建 snapshot 文件
- [ ] `/api/run?task=premarket` 管道：memo 缺失的标的自动跑 CIO → macro_strategy → premarket_summary
- [ ] `/api/run?task=premarket` 管道：memo 已存在的标的跳过 CIO
- [ ] `/api/generate-focus-reports` 批量启动多只标的
- [ ] `/api/status` 各 SOP 步骤状态正确
- [ ] Overview 刷新按钮功能正常
- [ ] Overview 关注列表三态标签正确渲染
- [ ] Intraday tab 盘前显示节点数据
- [ ] Command Hub pipeline 步骤数量 + 标签正确
- [ ] 模板拆分后页面渲染与原版一致（功能不变）
- [ ] poll 启动成功并输出日志
