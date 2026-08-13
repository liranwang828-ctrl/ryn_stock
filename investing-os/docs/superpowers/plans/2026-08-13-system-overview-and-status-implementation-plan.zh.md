# Investing-OS / Stock Team 系统总览与状态文档实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份可在十分钟内解释交易系统、认知系统、Dashboard、当前实现状态和 2026 年 8 月恢复路线的权威总览。

**Architecture:** 新文档只承担导航和状态摘要，不复制专项契约。结构、流程和握手关系由 Mermaid 表达；实现状态全部来自现有权威文档、Git 与定向测试证据，并明确区分历史验证和 8 月重新验证。

**Tech Stack:** Markdown、Mermaid、Git、PowerShell、pytest（仅用于读取后续恢复验证结果，不在本计划伪造运行结论）

---

### Task 1: 固定 2026 年 8 月事实基线

**Files:**
- Read: `investing-os/PROJECT-CHARTER.zh.md`
- Read: `investing-os/system/workflows/WORKFLOW-STATUS.zh.md`
- Read: `investing-os/handoff/CURRENT-CONTEXT.zh.md`
- Read: `investing-os/handoff/2026-07-17-v3-alpha-questions-ledger.zh.md`
- Read: `investing-os/handoff/2026-07-16-evidence-system-and-research-infrastructure.zh.md`
- Read: `investing-os/handoff/2026-07-22-ai-repair-day-followthrough.zh.md`

- [ ] **Step 1: 重新核验 Git 基线**

Run:

```powershell
git status --short --branch
git rev-list --count origin/codex/repository-cleanup-20260630..HEAD
git log -1 --date=short --pretty=format:'%h %ad %s'
git remote -v
```

Expected: 输出当前分支、相对远端提交数、最近提交和远端；只把实际值写入总览。

- [ ] **Step 2: 核验权威来源存在**

Run:

```powershell
@(
  'investing-os/PROJECT-CHARTER.zh.md',
  'investing-os/system/workflows/DAILY-CONTRACT.zh.md',
  'investing-os/system/workflows/WORKFLOW-STATUS.zh.md',
  'investing-os/handoff/CURRENT-CONTEXT.zh.md'
) | ForEach-Object { "$_ = $(Test-Path -LiteralPath $_)" }
```

Expected: 四项均为 `True`。

### Task 2: 编写权威总览和四张核心流程图

**Files:**
- Create: `investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md`

- [ ] **Step 1: 写入文档头部、定位和成熟度摘要**

文档头部必须包含：

```markdown
# Investing-OS / Stock Team 系统总览与当前状态

状态：2026 年 8 月恢复基线
最近核验：2026-08-13
```

摘要必须明确：系统已有较丰富资产和可试跑原型，但 DAILY 尚未在 8 月重新验证，Evidence 自动生产尚未闭环。

- [ ] **Step 2: 写入总体架构 Mermaid 图**

图中必须包含：用户、Investing-OS、Stock Team、外部事实源、Dashboard，并用边说明讨论确认、Evidence Request、Evidence Packet 和只读展示关系。

- [ ] **Step 3: 写入 DAILY Mermaid 图**

图中必须包含 `DAILY-0` 至 `DAILY-4`、市场环境证据包、用户确认焦点池、焦点标的证据包、计划批准、开盘观察、盘中管理、复盘与归档，以及研究/观察合法旁路。

- [ ] **Step 4: 写入认知闭环 Mermaid 图**

图中必须完整显示：

```text
Question -> Evidence -> Hypothesis -> Reality Validation
-> Consensus / Price / Behavior / Odds -> Investment Decision
-> Review -> Learning Candidate -> User Approval -> Durable Knowledge
```

- [ ] **Step 5: 写入脑—肌握手 Mermaid 图**

分别表达研究和交易共用的四段握手：定义问题、生成事实、解释证据、用户批准。

### Task 3: 写入状态矩阵、Dashboard 地图和恢复路线

**Files:**
- Modify: `investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md`

- [ ] **Step 1: 写入工作流状态矩阵**

矩阵至少覆盖：`DAILY`、`RESEARCH`、`REVIEW`、`LEARNING`、`VALIDATION`、`SYSTEM`。每行包含状态、历史证据、当前缺口、下一验收动作；不得把历史测试写成 8 月已验证。

- [ ] **Step 2: 写入 DAILY 分步状态**

分别记录 `DAILY-0` 至 `DAILY-4` 的现有能力和待重新验证项，重点标明真实交易日期、跨日恢复、盘前/实时价格、Dashboard 展示。

- [ ] **Step 3: 写入 Dashboard 职责地图**

覆盖 Operating Console、Growth Dashboard、Evidence / Report 页面，明确页面可打开不等于数据和流程已验证。

- [ ] **Step 4: 写入 8 月恢复路线**

固定顺序：基线 → 同步提交 → 隔离 DAILY 回归 → 修首个阻塞 → Evidence 自动化下一切片。

### Task 4: 验证文档、自检并提交

**Files:**
- Verify: `investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md`

- [ ] **Step 1: 检查禁用占位词和术语**

Run:

```powershell
rg -n 'TBD|TODO|待补充|待定' investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md
rg -n 'DAILY-[0-4]|Evidence|Question|Hypothesis|Reality|Dashboard' investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md
```

Expected: 第一条无输出；第二条能定位所有核心概念。

- [ ] **Step 2: 检查 Mermaid 围栏成对**

Run:

```powershell
$content = Get-Content -Raw -Encoding UTF8 investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md
$open = ([regex]::Matches($content, '```mermaid')).Count
$all = ([regex]::Matches($content, '```')).Count
"mermaid=$open fences=$all"
```

Expected: `mermaid` 至少为 4，代码围栏总数为偶数。

- [ ] **Step 3: 检查相对链接目标**

手动提取文档中的仓库相对链接，并逐个用 `Test-Path` 验证；不得出现 `file:///` 或 `/C:/abs/path/`。

- [ ] **Step 4: 检查 diff**

Run:

```powershell
git diff --check -- investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md
git diff --stat -- investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md
```

Expected: `diff --check` 无输出，diff 只包含总览文档。

- [ ] **Step 5: 提交**

Run:

```powershell
git add -- investing-os/SYSTEM-OVERVIEW-AND-STATUS.zh.md
git diff --cached --check
git commit -m "docs: add investing system overview and status map"
```

Expected: 新提交只包含总览文档。
