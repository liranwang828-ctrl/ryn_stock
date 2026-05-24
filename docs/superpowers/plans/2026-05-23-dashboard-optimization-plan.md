# Dashboard 优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 stock_team 本地 dashboard 的 8 个问题：内容完整性（API + 数据链 + 流程）、可维护性（模板拆分）、交互（状态标签 + 批量操作）。

**Architecture:** 后端在 dashboard_server.py 新增/增强 4 个 API，dashboard_writer.py 新增上下文字段；前端将 3838 行单体 Jinja2 模板拆为 9 个子模板，各 tab 增量改内容。

**Tech Stack:** Python stdlib HTTP server, Jinja2 templates, yfinance, Chart.js CDN

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `agents/dashboard_server.py` | 修改 | API 端点：refresh-portfolio、增强 premarket、generate-focus-reports、修复 SOP |
| `agents/dashboard_writer.py` | 修改 | 新增 report_status、macro_nodes 上下文字段 |
| `templates/base.html.j2` | **新建** | HTML 骨架 + CSS + tab bar |
| `templates/overview.html.j2` | **新建** | 总览 tab |
| `templates/intraday.html.j2` | **新建** | 盘中详情 + LLM 事件 |
| `templates/command_hub.html.j2` | **新建** | 控制中心 |
| `templates/paper_trading.html.j2` | **新建** | 模拟账户 |
| `templates/research.html.j2` | **新建** | 研报中心 |
| `templates/postmarket.html.j2` | **新建** | 盘后复盘 |
| `templates/modals.html.j2` | **新建** | 模态框 |
| `templates/scripts.js.j2` | **新建** | 全部 JS |
| `templates/daily_dashboard.html.j2` | 重写 | 改为 `{% extends 'base.html.j2' %}` 兼容入口 |

---

### Task 1: dashboard_server.py — 新增 `/api/refresh-portfolio`

**Files:**
- Modify: `agents/dashboard_server.py`

- [ ] **Step 1: 在 do_GET 路由中添加 refresh-portfolio 路径**

找到 `do_GET` 方法中 `# ── 6.5 API: 新增/关注股票到自选股` 之前，插入新路由：

```python
        # ── 6.4 API: 刷新组合快照 ────────────────────────────────
        elif path == "/api/refresh-portfolio":
            self.handle_api_refresh_portfolio()
            return
```

- [ ] **Step 2: 添加 handle_api_refresh_portfolio 方法**

在 `handle_api_stop` 方法之后添加（约第 555 行之后）：

```python
    def handle_api_refresh_portfolio(self):
        """重建当日 portfolio_snapshot"""
        try:
            from agents.portfolio_snapshot import (
                build_portfolio_snapshot, write_portfolio_snapshot
            )
            date_str = _date.today().strftime("%Y-%m-%d")
            data = build_portfolio_snapshot(date_str, trigger="on_demand", base_dir=BASE)
            if not data or not data.get("totals", {}).get("total_value", 0.0):
                self._set_headers("application/json; charset=utf-8", 500)
                self.wfile.write(json.dumps({
                    "error": "portfolio_snapshot 构建失败：无持仓数据"
                }, ensure_ascii=False).encode("utf-8"))
                return
            path = write_portfolio_snapshot(date_str, data, base_dir=BASE)
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({
                "status": "ok",
                "snapshot_path": path,
                "total_value": data["totals"]["total_value"]
            }, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self._set_headers("application/json; charset=utf-8", 500)
            self.wfile.write(json.dumps({
                "error": f"刷新失败: {str(e)}"
            }, ensure_ascii=False).encode("utf-8"))
```

- [ ] **Step 3: 验证**

启动 dashboard_server，访问 `http://localhost:8080/api/refresh-portfolio`，确认返回 `{"status":"ok",...}`。

---

### Task 2: dashboard_server.py — 修复 `/api/status` SOP 状态检测

**Files:**
- Modify: `agents/dashboard_server.py:311-349`

- [ ] **Step 1: 替换 sop_status 计算逻辑**

找到 `handle_api_status` 方法中 `# 6. 计算每日操作 SOP 的实时状态` 区块（约第 311-349 行），替换为：

```python
        # 6. 计算每日操作 SOP 的实时状态
        date_str = _date.today().strftime("%Y-%m-%d")

        # Step 1: 扫描选股
        candidates_path = os.path.join(BASE, f"candidates_{date_str}.json")
        has_candidates = os.path.exists(candidates_path)
        candidates_count = 0
        if has_candidates:
            try:
                with open(candidates_path, encoding="utf-8") as f:
                    candidates_count = len(json.load(f).get("candidates", []))
            except Exception:
                pass

        # Step 2: 确认关注列表
        focus_path = os.path.join(CFG_DIR, "daily_focus.json")
        focus_stocks = []
        if os.path.exists(focus_path):
            try:
                with open(focus_path, encoding="utf-8") as f:
                    focus_stocks = json.load(f).get("focus_stocks", [])
            except Exception:
                pass
        has_focus = len(focus_stocks) > 0

        # Step 3: 盘前决策汇总（检查 premarket_summary 产出）
        premarket_summary_count = 0
        if os.path.exists(FIND_DIR):
            for f in os.listdir(FIND_DIR):
                if f.startswith(f"premarket_summary_{date_str}_") and f.endswith(".json"):
                    premarket_summary_count += 1
        has_premarket_summary = premarket_summary_count > 0

        # Step 4: 盘中轮询
        with tasks_lock:
            poll_running = (
                "poll" in ACTIVE_TASKS
                and ACTIVE_TASKS["poll"].poll() is None
            )

        # Step 5: 收盘复盘
        has_postmarket = os.path.exists(
            os.path.join(FIND_DIR, f"postmarket_summary_{date_str}.json")
        )

        status_data["sop_status"] = {
            "step1_scan": {
                "done": has_candidates,
                "label": "扫描选股",
                "detail": f"{candidates_count} 只候选" if has_candidates else "待运行"
            },
            "step2_focus": {
                "done": has_focus,
                "label": "确认关注列表",
                "detail": f"{len(focus_stocks)} 只: {', '.join(focus_stocks[:5])}" if has_focus else "待确认"
            },
            "step3_premarket": {
                "done": has_premarket_summary,
                "label": "盘前决策汇总",
                "detail": f"{premarket_summary_count} 只已完成" if has_premarket_summary else "待运行"
            },
            "step4_poll": {
                "done": poll_running,
                "label": "盘中高频轮询",
                "detail": "运行中" if poll_running else "待启动"
            },
            "step5_postmarket": {
                "done": has_postmarket,
                "label": "盘后复盘",
                "detail": "已完成" if has_postmarket else "待运行"
            }
        }
```

- [ ] **Step 2: 验证**

启动 dashboard_server，访问 `http://localhost:8080/api/status`，确认 `sop_status` 包含 5 个步骤各有 `done`/`label`/`detail` 字段。

---

### Task 3: dashboard_server.py — 增强 `/api/run?task=premarket` 为智能管道

**Files:**
- Modify: `agents/dashboard_server.py:382-384`

- [ ] **Step 1: 替换 premarket 任务逻辑**

找到 `elif task_name == "premarket":` 行（约第 383 行），将 `cmd = [python_exe, os.path.join(BASE, "agents", "premarket_summary.py")]` 替换为：

```python
        elif task_name == "premarket":
            # 智能管道：读取关注列表 → 补 CIO/memo → macro_strategy → premarket_summary
            focus_path = os.path.join(CFG_DIR, "daily_focus.json")
            focus_stocks = []
            if os.path.exists(focus_path):
                try:
                    with open(focus_path, encoding="utf-8") as f:
                        focus_stocks = json.load(f).get("focus_stocks", [])
                except Exception:
                    pass
            if not focus_stocks:
                # fallback: 从 positions + candidates 构建
                pos_path = os.path.join(CFG_DIR, "positions.json")
                pos_syms = []
                if os.path.exists(pos_path):
                    pdata = json.load(open(pos_path, encoding="utf-8"))
                    pos_syms = list(pdata.get("positions", {}).keys())
                cand_path = os.path.join(BASE, f"candidates_{date_str}.json")
                cand_syms = []
                if os.path.exists(cand_path):
                    cdata = json.load(open(cand_path, encoding="utf-8"))
                    cand_syms = [c["sym"] for c in cdata.get("candidates", [])[:5]]
                focus_stocks = list(dict.fromkeys(pos_syms + cand_syms))

            # 构建顺序命令列表
            cmds = []

            # 步骤 A: 对缺失 strategic_memo 的标的跑 CIO
            for sym in focus_stocks:
                sym_upper = sym.upper()
                memo_path = os.path.join(BASE, f"strategic_memo_{sym_upper}.json")
                if not os.path.exists(memo_path):
                    cio_script = os.path.join(AGENTS_DIR, "cio.py")
                    memo_script = os.path.join(AGENTS_DIR, "strategic_memo_writer.py")
                    cmds.append([python_exe, cio_script, sym_upper, "--phases", "0123"])
                    cmds.append([python_exe, memo_script, sym_upper])

            # 步骤 B: 对所有标的跑 macro_strategy
            macro_script = os.path.join(AGENTS_DIR, "macro_strategy.py")
            for sym in focus_stocks:
                sym_upper = sym.upper()
                cmds.append([python_exe, macro_script, sym_upper])

            # 步骤 C: 跑 premarket_summary
            premarket_script = os.path.join(AGENTS_DIR, "premarket_summary.py")
            cmds.append([python_exe, premarket_script] + focus_stocks)

            cmd = cmds if cmds else [
                [python_exe, os.path.join(AGENTS_DIR, "premarket_summary.py")]
            ]
```

- [ ] **Step 2: 验证**

在 `daily_focus.json` 中设置关注标的，启动 dashboard_server，点击控制中心 Step 3「▶ 运行」，检查终端日志输出是否按顺序执行 CIO → macro_strategy → premarket_summary。

---

### Task 4: dashboard_server.py — 新增 `/api/generate-focus-reports`

**Files:**
- Modify: `agents/dashboard_server.py`

- [ ] **Step 1: 在 do_GET 路由中添加路径**

在 `/api/refresh-portfolio` 路由之后添加：

```python
        # ── 6.5 API: 批量生成关注标的报告 ────────────────────────
        elif path == "/api/generate-focus-reports":
            self.handle_api_generate_focus_reports()
            return
```

- [ ] **Step 2: 添加处理方法**

在 `handle_api_refresh_portfolio` 方法之后添加：

```python
    def handle_api_generate_focus_reports(self):
        """一键对关注列表中缺失报告的标的批量生成 CIO+memo+macro_strategy"""
        date_str = _date.today().strftime("%Y-%m-%d")
        focus_path = os.path.join(CFG_DIR, "daily_focus.json")
        focus_stocks = []
        if os.path.exists(focus_path):
            try:
                with open(focus_path, encoding="utf-8") as f:
                    focus_stocks = json.load(f).get("focus_stocks", [])
            except Exception:
                pass

        python_exe = get_python_executable()
        started = []
        skipped = []

        for sym in focus_stocks:
            sym_upper = sym.upper()
            memo_path = os.path.join(BASE, f"strategic_memo_{sym_upper}.json")
            if os.path.exists(memo_path):
                skipped.append(sym_upper)
                continue

            task_name = f"cio_{sym_upper}"
            if task_name in ACTIVE_TASKS and ACTIVE_TASKS[task_name].poll() is None:
                skipped.append(f"{sym_upper}(运行中)")
                continue

            # 启动 CIO 管道
            cio_script = os.path.join(AGENTS_DIR, "cio.py")
            memo_script = os.path.join(AGENTS_DIR, "strategic_memo_writer.py")
            macro_script = os.path.join(AGENTS_DIR, "macro_strategy.py")
            cmds = [
                [python_exe, cio_script, sym_upper, "--phases", "0123"],
                [python_exe, memo_script, sym_upper],
                [python_exe, macro_script, sym_upper],
            ]
            log_file_path = os.path.join(LOG_DIR, f"task_{task_name}.log")
            TASK_LOG_FILES[task_name] = log_file_path
            with open(log_file_path, "w", encoding="utf-8") as lf:
                lf.write(f"=== 批量生成 {sym_upper} 于 {datetime.now().isoformat()} ===\n")

            started.append(sym_upper)
            self._start_task_thread(task_name, cmds, log_file_path)

        self._set_headers("application/json; charset=utf-8")
        self.wfile.write(json.dumps({
            "status": "ok",
            "started": started,
            "skipped": skipped
        }, ensure_ascii=False).encode("utf-8"))
```

- [ ] **Step 3: 提取线程启动为 _start_task_thread 辅助方法**

在 `handle_api_run` 方法后添加（将 run_proc_thread 逻辑提取）：

```python
    def _start_task_thread(self, task_name, cmd, log_file_path):
        """启动后台任务线程"""
        def run_proc_thread():
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            cmds = cmd if (cmd and isinstance(cmd[0], list)) else [cmd]
            try:
                log_file = open(log_file_path, "a", encoding="utf-8", buffering=1)
                for idx, single_cmd in enumerate(cmds):
                    log_file.write(f"\n[顺序执行 {idx+1}/{len(cmds)}] {' '.join(single_cmd)}\n")
                    proc = subprocess.Popen(
                        single_cmd, cwd=BASE,
                        stdout=log_file, stderr=log_file,
                        env=env, text=True
                    )
                    with tasks_lock:
                        ACTIVE_TASKS[task_name] = proc
                    returncode = proc.wait()
                    log_file.write(f"\n[步骤 {idx+1}] 返回码: {returncode}\n")
                    if returncode != 0:
                        log_file.write(f"⚠️ 步骤 {idx+1} 失败，终止后续命令。\n")
                        break
                log_file.write(f"\n=== 任务 {task_name} 结束 ===\n")
                log_file.close()
            except Exception as thread_err:
                try:
                    with open(log_file_path, "a", encoding="utf-8") as err_f:
                        err_f.write(f"\n进程异常: {str(thread_err)}\n")
                except Exception:
                    pass

        t = threading.Thread(target=run_proc_thread, name=f"TaskRunner_{task_name}")
        t.daemon = True
        t.start()
        time.sleep(0.3)
```

然后重构 `handle_api_run` 中的线程启动部分（约第 466-514 行），改为调用 `self._start_task_thread(task_name, cmd, log_file_path)`。

- [ ] **Step 4: 验证**

启动 dashboard_server，访问 `http://localhost:8080/api/generate-focus-reports`，确认返回 JSON 含 `started`/`skipped` 列表。

---

### Task 5: dashboard_server.py — 重构 handle_api_run 使用 _start_task_thread

**Files:**
- Modify: `agents/dashboard_server.py:447-514`

- [ ] **Step 1: 替换线程启动代码**

找到 `handle_api_run` 方法中约第 447-514 行（从 `# 启动后台任务线程` 到 `self.wfile.write(...)`），替换为：

```python
        # 启动后台任务线程
        log_file_path = os.path.join(LOG_DIR, f"task_{task_name}.log")
        TASK_LOG_FILES[task_name] = log_file_path

        try:
            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write(f"=== 任务 {task_name} 于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 启动 ===\n")
                if cmd and isinstance(cmd[0], list):
                    cmd_desc = "\n  - " + "\n  - ".join(" ".join(c) for c in cmd)
                else:
                    cmd_desc = " ".join(cmd)
                f.write(f"计划执行命令行: {cmd_desc}\n\n")
        except Exception as e:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": f"无法初始化日志文件: {str(e)}"}).encode("utf-8"))
            return

        self._start_task_thread(task_name, cmd, log_file_path)

        self._set_headers("application/json; charset=utf-8")
        self.wfile.write(json.dumps({
            "status": "started",
            "task": task_name,
            "log_file": log_file_path
        }, ensure_ascii=False).encode("utf-8"))
```

- [ ] **Step 2: 确认无语法错误**

```bash
python -c "import py_compile; py_compile.compile('d:/gemini/lianghua/stock_team/agents/dashboard_server.py', doraise=True)"
```

---

### Task 6: dashboard_writer.py — 新增上下文字段

**Files:**
- Modify: `agents/dashboard_writer.py:350-379`

- [ ] **Step 1: 在 build_dashboard_context 返回 dict 前添加新字段**

找到 `return {` 语句（约第 350 行），在 `"date": date,` 之前插入：

```python
    # 10. 构建每只标的的三态报告状态
    report_status = {}
    macro_nodes_all = {}
    for s in symbols:
        sym_upper = s.upper()
        memo_path = os.path.join(base_dir, f"strategic_memo_{sym_upper}.json")
        macro_path = os.path.join(base_dir, f"macro_strategy_{sym_upper}.json")
        prem_path = os.path.join(find_dir, f"premarket_summary_{date}_{sym_upper}.json")
        cio_rpt = os.path.join(rpt_dir, f"{date}_{sym_upper}.html") if os.path.exists(os.path.join(base_dir, "reports")) else None

        status = {
            "has_cio": os.path.exists(cio_rpt) if cio_rpt else False,
            "has_memo": os.path.exists(memo_path),
            "has_macro_nodes": os.path.exists(macro_path),
            "has_premarket_summary": os.path.exists(prem_path),
        }
        report_status[sym_upper] = status

        # 加载 macro_strategy 节点（供 Intraday 盘前展示）
        if os.path.exists(macro_path):
            try:
                with open(macro_path, encoding="utf-8") as f:
                    ms = json.load(f)
                    macro_nodes_all[sym_upper] = ms.get("nodes", {})
            except Exception:
                pass

    # 11. 加载 premarket_summary 数据（供 Intraday 盘前展示）
    premarket_details = {}
    for s in symbols:
        sym_upper = s.upper()
        prem_path = os.path.join(find_dir, f"premarket_summary_{date}_{sym_upper}.json")
        if os.path.exists(prem_path):
            try:
                with open(prem_path, encoding="utf-8") as f:
                    premarket_details[sym_upper] = json.load(f)
            except Exception:
                pass
```

并在 return dict 中添加新字段：

```python
        "report_status":          report_status,
        "macro_nodes":            macro_nodes_all,
        "premarket_details":      premarket_details,
```

- [ ] **Step 2: 验证**

```bash
python -c "import sys; sys.path.insert(0,'d:/gemini/lianghua/stock_team'); from agents.dashboard_writer import build_dashboard_context; ctx = build_dashboard_context('2026-05-23'); print('report_status' in ctx, 'macro_nodes' in ctx, 'premarket_details' in ctx)"
```

---

### Task 7: 模板拆分 — 从单体提取 base + CSS + tab bar

**Files:**
- Create: `templates/base.html.j2`
- Create: `templates/scripts.js.j2`
- Modify: `templates/daily_dashboard.html.j2`

- [ ] **Step 1: 提取 CSS 和 HTML 骨架到 base.html.j2**

从 `daily_dashboard.html.j2` 提取：
- `<!DOCTYPE html>` 到 `<body>` 之前的所有内容（含 `<style>` 块中全部 CSS）→ `base.html.j2` 头部
- Tab bar（`<!-- ── Tab Bar ── -->` 区块）→ `base.html.j2` 中 `<body>` 之后的固定结构
- `<footer>` → `base.html.j2` 底部
- `</body></html>` → `base.html.j2` 收尾

在各 tab 占位处使用 Jinja2 block：

```jinja2
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trading Dashboard {{ date }}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    /* 从 daily_dashboard.html.j2 复制全部 <style> 内容 */
    {% include 'styles.css.j2' %}
  </style>
</head>
<body>
  <div>
    <h1>📊 Trading Dashboard</h1>
    <div class="meta">
      <span>日期: <b style="color:#fff;">{{ date }}</b></span>
      <span>生成时间: <b style="color:#fff;">{{ generated_at }}</b></span>
      <span>每 30 秒自动刷新</span>
      {% if daily_plan and daily_plan.get('market_context') %}
        <span>环境: <b style="color:#fff;">{{ daily_plan.market_context.get('env','—') }}</b></span>
      {% endif %}
    </div>
  </div>

  {% if data_health and data_health.status != 'stable' %}
  <div class="card" style="border-color: rgba(245,158,11,0.2); background: rgba(245,158,11,0.03);">
    <!-- data_health 警告块 -->
  </div>
  {% endif %}

  <!-- ── Tab Bar ── -->
  <div class="tab-bar">
    <button class="tab-btn active" onclick="showTab('overview', this)">📋 总览 Overview</button>
    <button class="tab-btn" onclick="showTab('intraday', this)">📈 盘中详情 Intraday</button>
    <button class="tab-btn" onclick="showTab('paper-trading', this)">📊 模拟账户 Paper Trading</button>
    <button class="tab-btn" onclick="showTab('postmarket', this)">🌙 盘后复盘 Postmarket</button>
    <button class="tab-btn" onclick="showTab('research', this)">🔬 研报中心 Research</button>
    <button class="tab-btn" onclick="showTab('command', this)" id="btn-command">🎛️ 控制中心 Command Hub</button>
  </div>

  <!-- ═══════════════ TAB: 总览 ═══════════════ -->
  <div id="tab-overview" class="tab-pane active">
    {% include 'overview.html.j2' %}
  </div>

  <!-- ═══════════════ TAB: 盘中详情 ═══════════════ -->
  <div id="tab-intraday" class="tab-pane">
    {% include 'intraday.html.j2' %}
  </div>

  <!-- ═══════════════ TAB: 模拟账户 ═══════════════ -->
  <div id="tab-paper-trading" class="tab-pane">
    {% include 'paper_trading.html.j2' %}
  </div>

  <!-- ═══════════════ TAB: 盘后复盘 ═══════════════ -->
  <div id="tab-postmarket" class="tab-pane">
    {% include 'postmarket.html.j2' %}
  </div>

  <!-- ═══════════════ TAB: 研报中心 ═══════════════ -->
  <div id="tab-research" class="tab-pane">
    {% include 'research.html.j2' %}
  </div>

  <!-- ═══════════════ TAB: 控制中心 ═══════════════ -->
  <div id="tab-command" class="tab-pane">
    {% include 'command_hub.html.j2' %}
  </div>

  {% include 'modals.html.j2' %}

  <footer>ANTIGRAVITY TRADING INTEL DASHBOARD · SECURE MULTI-AGENT EXECUTION HUB</footer>

  <script>
    {% include 'scripts.js.j2' %}
  </script>
</body>
</html>
```

- [ ] **Step 2: 提取 CSS 到 styles.css.j2**

将 `daily_dashboard.html.j2` 中 `<style>` 标签内的全部 CSS（约第 9-800 行）复制到新文件 `templates/styles.css.j2`。

- [ ] **Step 3: 重写 daily_dashboard.html.j2 为兼容入口**

```jinja2
{% extends 'base.html.j2' %}
```

（如果测试发现 `{% extends %}` 不兼容 `{% include %}` 的用法，则改为 `{% include 'base.html.j2' %}` 并让 base 直接渲染。）

- [ ] **Step 4: 验证渲染不变**

启动 dashboard_server，打开 `http://localhost:8080/`，确认页面与原版完全一致。检查所有 tab 切换正常。

---

### Task 8: 模板拆分 — 提取各 tab 子模板

**Files:**
- Create: `templates/overview.html.j2`
- Create: `templates/intraday.html.j2`
- Create: `templates/command_hub.html.j2`
- Create: `templates/paper_trading.html.j2`
- Create: `templates/research.html.j2`
- Create: `templates/postmarket.html.j2`
- Create: `templates/modals.html.j2`

- [ ] **Step 1: 逐 tab 提取**

从 `daily_dashboard.html.j2` 中将每个 `<!-- ═══════════════ TAB: XXX ═══════════════ -->` 注释对应的 `<div id="tab-xxx" class="tab-pane">...</div>` 内容完整复制到对应的子模板文件。

具体行号参考（以当前 3838 行文件为准）：

| 子模板 | 大致行范围 |
|--------|-----------|
| `overview.html.j2` | 925 → 1177 |
| `intraday.html.j2` | 1179 → 1478 |
| `paper_trading.html.j2` | 1480 → 1935 |
| `postmarket.html.j2` | 1937 → 2068 |
| `research.html.j2` | 2070 → 2180 |
| `command_hub.html.j2` | 2182 → 2351 |
| `modals.html.j2` | 2358 → 2675 |

- [ ] **Step 2: 提取 JS 到 scripts.js.j2**

从 `daily_dashboard.html.j2` 的 `<script>` 块（约第 2677 行到 `</script>` 之前，约第 3830 行）复制到 `templates/scripts.js.j2`。保留 Jinja2 模板变量引用（`{{ date }}`、`{{ symbol }}` 等）。

- [ ] **Step 3: 验证渲染一致**

启动 dashboard_server，确认所有 tab 内容与原版一致。

---

### Task 9: Overview tab — 刷新按钮 + 报告状态标签

**Files:**
- Modify: `templates/overview.html.j2`

- [ ] **Step 1: 组合风险卡添加刷新按钮**

找到组合风险卡片的 `.card-title`（当前含 `📊 组合风险与度量` 文本），在标题右侧添加：

```jinja2
<div class="card-title">
  <div class="title-left">
    <span>📊 组合风险与度量</span>
  </div>
  <button class="action-btn" onclick="refreshPortfolio()" title="根据最新持仓和实时价格重建组合快照">
    🔄 刷新组合
  </button>
</div>
```

- [ ] **Step 2: 今日关注列表 — 替换操作列**

找到 `{% for sym in focus_list %}` 循环中的操作列（`<td>` 含 `操作 Options` 标题，约第 1100-1120 行），替换为：

```jinja2
                  <td>
                    <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                      {% set rs = report_status.get(sym, {}) %}
                      {# CIO 报告状态 #}
                      {% if rs.get('has_cio') %}
                        <a class="json-link" href="../reports/{{ date }}_{{ sym }}.html"
                           style="border-color:var(--green); color:#6ee7b7;" target="_blank"
                           title="CIO 深度辩论报告">✅CIO</a>
                      {% else %}
                        <span class="json-link" style="border-color:var(--yellow); color:var(--yellow); cursor:pointer"
                              title="生成 CIO 深度辩论报告 + 策略备忘录"
                              onclick="generateReportForFocus('{{ sym }}')">⚠️待生成</span>
                      {% endif %}
                      {# 研报状态 #}
                      {% if sym in research_reports %}
                        <a class="json-link" href="../reports/research_{{ sym }}.html"
                           style="border-color:var(--blue); color:#93c5fd;" target="_blank">✅研报</a>
                      {% else %}
                        <span class="json-link" style="border-color:var(--gray-border); color:var(--text-muted); cursor:default">—</span>
                      {% endif %}
                      {# 策略节点状态 #}
                      {% if rs.get('has_macro_nodes') %}
                        <span class="json-link" style="border-color:var(--green-border); color:var(--green); cursor:default">✅节点</span>
                      {% else %}
                        <span class="json-link" style="border-color:var(--gray-border); color:var(--text-muted); cursor:default">—</span>
                      {% endif %}
                      {# 移出按钮 #}
                      <span class="btn-watch-active" style="background:rgba(244,63,94,0.15); color:var(--red); border:1px solid rgba(244,63,94,0.3); padding:2px 6px; cursor:pointer;"
                            onclick="removeFromFocus('{{ sym }}')">❌</span>
                    </div>
                  </td>
```

- [ ] **Step 3: 表头上方添加批量生成按钮**

在 `<table>` 之前，`.card-title` 之后插入：

```jinja2
          <div style="margin-bottom:0.8rem; display:flex; gap:8px; align-items:center;">
            <button class="action-btn" onclick="generateAllFocusReports()"
                    style="background:rgba(99,102,241,0.1); border-color:rgba(99,102,241,0.3); color:#a5b4fc;">
              ⚡ 一键生成全部缺失报告
            </button>
            <span style="font-size:0.75rem; color:var(--text-muted);">
              将自动补全 CIO 辩论 + 策略备忘录 + 宏观节点
            </span>
          </div>
```

- [ ] **Step 4: 验证**

启动 dashboard_server，确认 Overview tab：
- 组合风险卡有「🔄 刷新组合」按钮
- 关注列表每行显示三态标签
- 批量生成按钮存在

---

### Task 10: 前端 JS — 新增 refreshPortfolio / generateAllFocusReports

**Files:**
- Modify: `templates/scripts.js.j2`

- [ ] **Step 1: 添加 refreshPortfolio 函数**

在 `scripts.js.j2` 末尾添加：

```javascript
    function refreshPortfolio() {
      try {
        const terminal = document.getElementById('terminal-body');
        fetch('/api/refresh-portfolio')
          .then(res => res.json())
          .then(data => {
            if (data.error) {
              alert('刷新失败: ' + data.error);
            } else {
              alert('组合快照已刷新（NAV: $' + Number(data.total_value).toLocaleString() + '），页面将在 2 秒后自动重载');
              setTimeout(() => { location.reload(); }, 2000);
            }
          })
          .catch(err => {
            alert('刷新请求失败: ' + err);
          });
      } catch (err) {
        console.error('Error in refreshPortfolio:', err);
      }
    }

    function generateAllFocusReports() {
      try {
        if (!confirm('将自动为所有缺失报告的关注标的生成 CIO 辩论 + 策略备忘录 + 宏观节点。\n\n已有报告的标的将跳过。继续？')) {
          return;
        }
        showTab('command', document.getElementById('btn-command'));
        fetch('/api/generate-focus-reports')
          .then(res => res.json())
          .then(data => {
            const terminal = document.getElementById('terminal-body');
            if (terminal) {
              terminal.innerText = '[批量生成] 已启动: ' + JSON.stringify(data.started) + '\n';
              if (data.skipped && data.skipped.length > 0) {
                terminal.innerText += '[跳过] 已有报告: ' + JSON.stringify(data.skipped) + '\n';
              }
              terminal.innerText += '\n任务在后台执行中，可在日志控制台查看进度。完成后刷新 Overview 页面查看状态更新。\n';
            }
            // 切换到控制中心查看进度
            const badge = document.getElementById('current-task-badge');
            if (badge) {
              badge.innerText = "BATCH";
              badge.className = "badge badge-blue";
            }
          })
          .catch(err => {
            console.error('Error in generateAllFocusReports:', err);
          });
      } catch (err) {
        console.error('Error in generateAllFocusReports:', err);
      }
    }
```

- [ ] **Step 2: 验证**

刷新 dashboard 页面，点击 Overview 的刷新按钮和批量生成按钮，确认功能正常。

---

### Task 11: Command Hub — Pipeline 流程重排

**Files:**
- Modify: `templates/command_hub.html.j2`

- [ ] **Step 1: 移除旧 Step 3 (CIO 深度辩论)**

在 command_hub.html.j2 中，找到 `<!-- Step 3: CIO 决策报告 -->` 对应的 `<div class="pipeline-step">` 块，整块删除。

但仍保留右侧控制台的手动 CIO 触发功能（`runCIOTask()` + 下拉框），将其放在终端控制台上方作为独立卡片：

```jinja2
      <!-- 手动 CIO 触发（独立卡片） -->
      <div class="card" style="margin-bottom:1.5rem;">
        <div class="card-title"><span>🧠 手动 CIO 深度辩论</span></div>
        <div style="display:flex; gap:8px; align-items:center;">
          <select id="cio-symbol-select" class="btn btn-secondary"
                  style="padding:0.35rem 0.8rem; font-weight:700;"
                  onchange="if(this.value==='__custom__'){document.getElementById('cio-custom-input').style.display='inline-block';document.getElementById('cio-custom-input').focus();}else{document.getElementById('cio-custom-input').style.display='none';}">
            {% for sym in symbols %}
              <option value="{{ sym }}">{{ sym }}</option>
            {% endfor %}
            <option value="__custom__">+ 手动输入...</option>
          </select>
          <input type="text" id="cio-custom-input" placeholder="代码 (如 AAPL)"
                 class="btn btn-secondary"
                 style="display:none; padding:0.35rem 0.8rem; width:150px; text-transform:uppercase;" />
          <button class="btn btn-primary" onclick="runCIOTask()">▶ 运行</button>
        </div>
      </div>
```

- [ ] **Step 2: 在 Step 1 和 Step 2 之间插入 Step 1.5**

在 `<!-- Step 1: 扫描选股 -->` 的 `</div>` 之后、`<!-- Step 2: 盘前计划 -->` 之前插入：

```jinja2
          <!-- Step 1.5: 确认关注列表 -->
          <div class="pipeline-step" style="background:rgba(99,102,241,0.02); border-color:rgba(99,102,241,0.1);">
            <div class="step-info">
              <div class="step-number" style="background:rgba(59,130,246,0.1); border-color:rgba(59,130,246,0.3); color:#93c5fd;">1.5</div>
              <div>
                <div class="step-name">确认今日关注列表 (Confirm Focus List)</div>
                <div class="step-desc">
                  前往 <a href="javascript:showTab('overview', document.querySelector('.tab-btn'))" style="color:var(--primary);">📋 总览 Overview</a> 添加/移除关注标的。
                  {% if focus_list %}
                  <br>当前关注: <strong style="color:#fff;">{{ focus_list|join(', ') }}</strong>
                  {% else %}
                  <br><span style="color:var(--yellow);">⚠️ 关注列表为空，请先添加标的</span>
                  {% endif %}
                </div>
              </div>
            </div>
            <span class="badge badge-blue" style="cursor:pointer;" onclick="showTab('overview', document.querySelector('.tab-btn'))">前往 Overview →</span>
          </div>
```

- [ ] **Step 3: 更新步骤编号**

将 `Step 2: 盘前决策汇总` 改为 `Step 2`，`Step 4: 盘中高频轮询` 改为 `Step 3`，`Step 5: 盘后复盘` 改为 `Step 4`。

步骤编号的 `.step-number` 改为对应的 2/3/4。

- [ ] **Step 4: 更新 SOP 状态绑定**

Pipeline 步骤的 `.step-status` 改为读取 `/api/status` 返回的新 `sop_status` 结构：

```javascript
// 在 scripts.js.j2 的 syncStatus() 函数中更新：
const sop = data.sop_status || {};
// Step 1: sop.step1_scan.done
// Step 1.5: sop.step2_focus.done
// Step 2: sop.step3_premarket.done
// Step 3: sop.step4_poll.done
// Step 4: sop.step5_postmarket.done
```

- [ ] **Step 5: 验证**

启动 dashboard_server，确认 Command Hub：
- 只有 5 个步骤（含 1.5）
- Step 1.5 显示当前关注列表或空提示
- Step 2 的「▶ 运行」按钮触发智能管道
- 手动 CIO 触发卡片在右侧

---

### Task 12: Intraday tab — 盘前策略节点展示

**Files:**
- Modify: `templates/intraday.html.j2`

- [ ] **Step 1: 添加盘前策略节点卡片**

在 `intraday.html.j2` 开头（LLM 事件列表之前）添加：

```jinja2
    <!-- 盘前策略节点（Pre-market Strategy Nodes） -->
    <div class="card">
      <div class="card-title">
        <div class="title-left">
          <span>🎯 盘前策略节点 (Premarket Strategy Nodes)</span>
        </div>
        <span class="badge badge-blue">Macro Strategy</span>
      </div>
      {% if macro_nodes %}
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>标的</th>
              <th>动态止损</th>
              <th>目标价 TP1</th>
              <th>Flex 加仓</th>
              <th>Flex 减仓</th>
              <th>情景降级</th>
              <th>论点状态</th>
            </tr>
          </thead>
          <tbody>
            {% for sym in focus_list %}
            {% set nodes = macro_nodes.get(sym, {}) %}
            {% set pm = premarket_details.get(sym, {}) %}
            {% set exit_sect = pm.get('exit', {}) if pm else {} %}
            <tr>
              <td style="font-family:'Outfit',sans-serif; font-weight:700; color:#fff;">{{ sym }}</td>
              <td style="font-family:'JetBrains Mono',monospace;">
                {{ '$%.2f'|format(nodes.get('dynamic_stop', {}).get('price', 0)) if nodes.get('dynamic_stop', {}).get('price') else '—' }}
              </td>
              <td style="font-family:'JetBrains Mono',monospace; color:var(--green);">
                {{ '$%.2f'|format(nodes.get('tp1', {}).get('price', 0)) if nodes.get('tp1', {}).get('price') else '—' }}
              </td>
              <td style="font-family:'JetBrains Mono',monospace; color:var(--blue);">
                {{ '$%.2f'|format(nodes.get('add1', {}).get('price', 0)) if nodes.get('add1', {}).get('price') else '—' }}
              </td>
              <td style="font-family:'JetBrains Mono',monospace; color:var(--yellow);">
                {{ exit_sect.get('flex_reduce_level', '—') }}
              </td>
              <td>
                {% set sd = nodes.get('scenario_downgrade', {}) %}
                {% if sd.get('price') %}
                <span class="badge badge-yellow">{{ '$%.2f'|format(sd.price) }}</span>
                {% else %}—{% endif %}
              </td>
              <td>
                {% set ts = pm.get('exit', {}).get('thesis_status', '—') if pm else '—' %}
                {% if ts == 'intact' %}<span class="badge badge-green">✅ intact</span>
                {% elif ts == 'weakening' %}<span class="badge badge-yellow">⚠️ weakening</span>
                {% elif ts == 'broken' %}<span class="badge badge-red">❌ broken</span>
                {% else %}<span class="badge badge-gray">{{ ts }}</span>{% endif %}
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div style="text-align:center; padding:2rem; color:var(--text-muted);">
        尚未生成策略节点。请在控制中心运行「盘前决策汇总」以自动生成。
      </div>
      {% endif %}
    </div>

    <!-- 盘中实时快照（Poll 运行时动态更新） -->
    <div class="card">
      <div class="card-title">
        <span>📡 盘中实时快照 (Intraday Snapshots)</span>
        <span class="badge {% if sop_status and sop_status.step4_poll and sop_status.step4_poll.done %}badge-green{% else %}badge-gray{% endif %}">
          {{ '运行中' if sop_status and sop_status.step4_poll and sop_status.step4_poll.done else '待启动' }}
        </span>
      </div>
      {# 保留原有 intraday 数据展示逻辑 #}
      {% if intraday %}
        {% for sym in focus_list %}
          {% set it = intraday.get(sym, {}) %}
          {% if it %}
          <div style="padding:0.5rem 0; border-bottom:1px solid rgba(255,255,255,0.03);">
            <strong style="color:#fff;">{{ sym }}</strong>
            <span style="font-family:'JetBrains Mono',monospace; margin-left:1rem;">
              现价: {{ '$%.2f'|format(it.get('price_now', {}).get('price', 0)) if it.get('price_now', {}).get('price') else '—' }}
            </span>
          </div>
          {% endif %}
        {% endfor %}
      {% else %}
      <div style="text-align:center; padding:1.5rem; color:var(--text-muted);">
        盘中快照将在轮询启动后自动填充。
      </div>
      {% endif %}
    </div>
```

- [ ] **Step 2: 合并 LLM 事件到此 tab**

将原来 Events tab 的 LLM 事件列表移到策略节点卡片和盘中快照卡片之后。

- [ ] **Step 3: 移除独立 Events tab**

在 `base.html.j2` 的 tab bar 中移除 `LLM 事件 Events` 按钮，intraday tab 包含全部盘中内容。

- [ ] **Step 4: 验证**

启动 dashboard_server，确认 Intraday tab：
- 盘前策略节点表格（如有 macro_strategy 数据）
- 无数据时显示提示文字
- LLM 事件列表在下方

---

### Task 13: 排查 poll 启动问题

**Files:**
- Inspect: `agents/poll.py`

- [ ] **Step 1: 检查 poll.py 的依赖和入口**

```bash
cd d:\gemini\lianghua\stock_team
python -c "import sys; sys.path.insert(0,'.'); from agents.poll import snap; print('poll import OK')"
```

- [ ] **Step 2: 手动试跑 poll.py**

```bash
cd d:\gemini\lianghua\stock_team
python agents/poll.py BABA --once 2>&1 | head -20
```

检查是否有 ImportError、yfinance 连接错误、文件路径问题。

- [ ] **Step 3: 通过 dashboard API 启动**

确认 `watchlist.json` 中有自选股，然后访问 `http://localhost:8080/api/run?task=poll`，检查返回和日志文件 `logs/task_poll.log`。

- [ ] **Step 4: 修复发现的问题**

常见问题及修复：
- **Python 路径**: 确保 `get_python_executable()` 返回正确的 `sys.executable`
- **yfinance 限流**: 添加重试逻辑或降低频率
- **编码问题**: 确保 `PYTHONIOENCODING=utf-8`

- [ ] **Step 5: 验证**

确认 poll 启动后，`logs/task_poll.log` 有持续输出，`/api/status` 显示 Step 4 为 running。

---

### Task 14: 端到端验证 + 提交

- [ ] **Step 1: 运行所有现有测试**

```bash
cd d:\gemini\lianghua\stock_team
python -m pytest tests/ -x --timeout=60 -q 2>&1 | tail -20
```

确认无新增失败。

- [ ] **Step 2: 冒烟测试 dashboard 全流程**

1. 启动 dashboard_server: `python agents/dashboard_server.py`
2. 打开 `http://localhost:8080`
3. 点击「刷新组合」→ 确认弹窗
4. 确认关注列表三态标签显示
5. Command Hub 步骤 5 个，Step 1.5 正确
6. 点击 Step 2「▶ 运行」→ 终端有日志
7. 切换到 Intraday tab → 盘前节点表格
8. 模拟账户 tab 正常
9. 研报中心 tab 正常

- [ ] **Step 3: Git commit**

```bash
cd d:\gemini\lianghua\stock_team
git add agents/dashboard_server.py agents/dashboard_writer.py templates/
git commit -m "feat(dashboard): 内容完整性修复 + 模板模块化拆分

- 新增 /api/refresh-portfolio、/api/generate-focus-reports
- 增强 /api/run?task=premarket 为智能管道（CIO→macro_strategy→premarket_summary）
- 修复 /api/status SOP 状态检测（5步骤各有 done/label/detail）
- 新增 report_status/macro_nodes/premarket_details 上下文字段
- 3838行单体模板拆分为 9 个子模板（Jinja2 include）
- Overview: 刷新组合按钮 + 报告三态标签 + 一键批量生成
- Command Hub: 新增 Step 1.5 确认关注 + CIO移出主流程
- Intraday: 盘前策略节点展示"
```
