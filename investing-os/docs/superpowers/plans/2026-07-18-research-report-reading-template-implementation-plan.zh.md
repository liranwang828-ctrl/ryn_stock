# Research Report Reading Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable reading-layer template for company + industry hybrid research reports and produce the first HTML reading example for the NBIS verification-layer report.

**Architecture:** Keep markdown company/industry reports as the source of truth. Add a standalone HTML reading template under `investing-os/dashboards/` that is purpose-built for research reports, not daily reports. Create one first rendered example for NBIS by manually structuring the reading-layer sections around the existing markdown source, while keeping the lower section linked back to the original research body.

**Tech Stack:** HTML, CSS, Markdown source reports, investing-os dashboard folder

---

## File Structure

- Create: `investing-os/dashboards/research-report-template.html`
  - Reusable visual template for readable company + industry research reports.
- Create: `investing-os/dashboards/reports/NBIS-verification-layer-report.html`
  - First rendered example using the new reading design.
- Verify against:
  - `investing-os/wiki/companies/NBIS.zh.md`
  - `investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md`
  - `investing-os/docs/superpowers/specs/2026-07-18-research-report-reading-template-design.zh.md`
- Verify with:
  - `powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path <source>`
  - `Get-Content -Raw <html file>`
  - browser opening through the existing localhost static viewer when needed
  - `git status --short`

### Task 1: Create the reusable research report reading template

**Files:**
- Create: `investing-os/dashboards/research-report-template.html`

- [ ] **Step 1: Inspect current report-reading assets for style reuse**

Run:

```powershell
Get-Content -Raw 'investing-os/tools/generate-report-html.ps1'
Get-Content -Raw 'stock_team/templates/report.html.j2'
```

Expected:

- The current daily/report readers are readable but not structured for company + industry research reading.
- We confirm we should create a dedicated research-reading template instead of forcing the daily-report renderer.

- [ ] **Step 2: Create the standalone template file**

Create `investing-os/dashboards/research-report-template.html` with a documented skeleton containing these named blocks:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Report Reading Template</title>
  <style>
    body { margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #f5f7fb; color: #182230; }
    .page { max-width: 1180px; margin: 0 auto; padding: 28px 20px 48px; }
    .hero, .section, .timeline-item, .card { background: #fff; border: 1px solid #d7dee8; border-radius: 14px; }
    .hero { padding: 28px; margin-bottom: 18px; }
    .hero h1 { margin: 0 0 8px; font-size: 32px; }
    .hero .meta { color: #667085; font-size: 14px; }
    .hero .summary { margin-top: 16px; font-size: 18px; line-height: 1.6; }
    .hero .chips { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
    .chip { display: inline-flex; border: 1px solid #cfd7e3; border-radius: 999px; padding: 4px 10px; font-size: 13px; background: #f8fafc; }
    .cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }
    .card { padding: 18px; }
    .card h3 { margin: 0 0 10px; font-size: 18px; }
    .card ul { margin: 0; padding-left: 18px; line-height: 1.6; }
    .coupling { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }
    .section { padding: 22px; margin-bottom: 18px; }
    .section h2 { margin: 0 0 14px; font-size: 22px; }
    .timeline { display: flex; flex-direction: column; gap: 12px; }
    .timeline-item { padding: 16px; }
    .timeline-date { font-weight: 700; color: #175cd3; margin-bottom: 6px; }
    .timeline-tag { display: inline-block; margin-top: 8px; font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #eef4ff; color: #1849a9; }
    .full-body { white-space: pre-wrap; line-height: 1.7; font-size: 15px; }
    @media (max-width: 900px) { .cards, .coupling { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>[Company] Research Report</h1>
      <div class="meta">Ticker | Layer | Date</div>
      <div class="summary">One-sentence positioning</div>
      <div class="chips">
        <span class="chip">Current stance</span>
        <span class="chip">Layer classification</span>
        <span class="chip">1–2 quarter focus</span>
      </div>
    </section>

    <section class="cards">
      <article class="card"><h3>What the market is trading</h3></article>
      <article class="card"><h3>Reality confirmed</h3></article>
      <article class="card"><h3>Reality unconfirmed</h3></article>
      <article class="card"><h3>Next 1–2 quarter validation</h3></article>
    </section>

    <section class="section">
      <h2>Event / Price / Interpretation Timeline</h2>
      <div class="timeline"></div>
    </section>

    <section class="coupling">
      <article class="section"><h2>Company Layer</h2></article>
      <article class="section"><h2>Industry Layer</h2></article>
    </section>

    <section class="section">
      <h2>Full Research Body</h2>
      <div class="full-body">Markdown-derived body or deep-reading content</div>
    </section>
  </main>
</body>
</html>
```

- [ ] **Step 3: Verify the template file**

Run:

```powershell
Get-Content -Raw 'investing-os/dashboards/research-report-template.html'
```

Expected:

- The template contains the five reading blocks from the spec.
- The layout is clearly separate from the daily report renderer.

- [ ] **Step 4: Commit the template**

Run:

```powershell
git add -- 'investing-os/dashboards/research-report-template.html'
git commit -m "docs: add research report reading template"
```

Expected:

- One commit is created for the reusable template.

### Task 2: Create the first NBIS reading-layer example

**Files:**
- Create: `investing-os/dashboards/reports/NBIS-verification-layer-report.html`

- [ ] **Step 1: Re-read the NBIS company and industry sources**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\companies\NBIS.zh.md'
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\industries\ai-commercialization-verification-layer.zh.md'
```

Expected:

- The source markdown clearly provides the content for the hero, four cards, timeline, coupling block, and full body.

- [ ] **Step 2: Create the NBIS HTML reading example**

Create `investing-os/dashboards/reports/NBIS-verification-layer-report.html` with:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NBIS 研究报告（阅读版）</title>
  <style>
    body { margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #f5f7fb; color: #182230; }
    .page { max-width: 1180px; margin: 0 auto; padding: 28px 20px 48px; }
    .hero, .section, .timeline-item, .card { background: #fff; border: 1px solid #d7dee8; border-radius: 14px; }
    .hero { padding: 28px; margin-bottom: 18px; }
    .hero h1 { margin: 0 0 8px; font-size: 32px; }
    .hero .meta { color: #667085; font-size: 14px; }
    .hero .summary { margin-top: 16px; font-size: 18px; line-height: 1.6; }
    .hero .chips { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
    .chip { display: inline-flex; border: 1px solid #cfd7e3; border-radius: 999px; padding: 4px 10px; font-size: 13px; background: #f8fafc; }
    .cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }
    .card { padding: 18px; }
    .card h3 { margin: 0 0 10px; font-size: 18px; }
    .card ul { margin: 0; padding-left: 18px; line-height: 1.6; }
    .coupling { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }
    .section { padding: 22px; margin-bottom: 18px; }
    .section h2 { margin: 0 0 14px; font-size: 22px; }
    .timeline { display: flex; flex-direction: column; gap: 12px; }
    .timeline-item { padding: 16px; }
    .timeline-date { font-weight: 700; color: #175cd3; margin-bottom: 6px; }
    .timeline-tag { display: inline-block; margin-top: 8px; font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #eef4ff; color: #1849a9; }
    .full-body { line-height: 1.8; font-size: 15px; }
    .full-body h3 { margin-top: 18px; }
    .full-body ul { padding-left: 20px; }
    code { background: #f2f4f7; padding: 2px 4px; border-radius: 4px; }
    a { color: #175cd3; text-decoration: none; }
    a:hover { text-decoration: underline; }
    @media (max-width: 900px) { .cards, .coupling { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>NBIS 研究报告（阅读版）</h1>
      <div class="meta">Nebius Group N.V. | NBIS | 2026-07-17</div>
      <div class="summary">
        NBIS 不是 AI 产业中的已验证核心资产，而是位于“AI 商业化验证层”的高弹性观察对象：市场愿意提前给它未来空间，但 Reality 仍需未来 1–2 个季度继续验证。
      </div>
      <div class="chips">
        <span class="chip">Current stance: observe</span>
        <span class="chip">Layer: Verification Layer</span>
        <span class="chip">Focus: next 1–2 quarters</span>
      </div>
    </section>

    <section class="cards">
      <article class="card">
        <h3>市场在交易什么</h3>
        <ul>
          <li>AI cloud 与 hyperscaler 相关需求继续扩张</li>
          <li>NBIS 可以承接部分高增长价值</li>
          <li>商业化验证一旦出现，估值可以被继续上修</li>
        </ul>
      </article>
      <article class="card">
        <h3>Reality Confirmed</h3>
        <ul>
          <li>AI cloud 已成为核心收入主线</li>
          <li>Q1 2026 收入增长非常强</li>
          <li>获得 NVIDIA 战略合作与新增融资支持</li>
        </ul>
      </article>
      <article class="card">
        <h3>Reality Unconfirmed</h3>
        <ul>
          <li>商业模式是否稳定成立</li>
          <li>利润率与现金流是否能支撑高估值</li>
          <li>能否从高弹性标的升级为核心资产</li>
        </ul>
      </article>
      <article class="card">
        <h3>未来 1–2 季度验证重点</h3>
        <ul>
          <li>下一轮财报收入质量</li>
          <li>利润率和经营杠杆变化</li>
          <li>管理层商业化路径与大客户兑现节奏</li>
        </ul>
      </article>
    </section>

    <section class="section">
      <h2>事件 / 股价 / 解读时间轴</h2>
      <div class="timeline">
        <div class="timeline-item">
          <div class="timeline-date">2024-10-21</div>
          <div>剥离后恢复交易，市场开始重新定价新业务结构。</div>
          <span class="timeline-tag">Narrative Reset</span>
        </div>
        <div class="timeline-item">
          <div class="timeline-date">2025-09-08</div>
          <div>Microsoft AI 基础设施协议强化“需求真实存在”叙事，但利润质量仍待验证。</div>
          <span class="timeline-tag">Mixed</span>
        </div>
        <div class="timeline-item">
          <div class="timeline-date">2026-03-11</div>
          <div>NVIDIA 战略合作与 20 亿美元投资强化技术与资本背书。</div>
          <span class="timeline-tag">Reality + Narrative</span>
        </div>
        <div class="timeline-item">
          <div class="timeline-date">2026-05-13</div>
          <div>Q1 2026 财报高增长：AI cloud 收入高速上行，市场显著重估其成长空间。</div>
          <span class="timeline-tag">Reality Support</span>
        </div>
        <div class="timeline-item">
          <div class="timeline-date">2026-07-17</div>
          <div>secured debt 融资与股价强修复，说明市场愿意继续交易扩张能力，但仍不等于商业模式完全成熟。</div>
          <span class="timeline-tag">Mixed</span>
        </div>
      </div>
    </section>

    <section class="coupling">
      <article class="section">
        <h2>Company Layer</h2>
        <ul>
          <li>AI cloud / infrastructure 平台型资产</li>
          <li>收入增长强，但盈利质量验证不足</li>
          <li>高弹性，适合观察，不适合直接视为核心资产</li>
        </ul>
      </article>
      <article class="section">
        <h2>Industry Layer</h2>
        <ul>
          <li>所属：AI 商业化验证层</li>
          <li>同层对照：NOW / ORCL / MSFT（商业化成熟度更高）</li>
          <li>研究重点：验证它能否从“概念被交易”升级为“利润被验证”</li>
        </ul>
      </article>
    </section>

    <section class="section">
      <h2>Full Research Body</h2>
      <div class="full-body">
        <h3>当前投资看法</h3>
        <p>当前更合理的定位是：正式观察、可以研究、不应直接视为已验证核心仓位。</p>
        <h3>Upgrade Trigger</h3>
        <ul>
          <li>财报继续验证收入质量、利润率或现金流改善</li>
          <li>管理层给出更可信的商业化路径</li>
          <li>市场对其定价不再只依赖高弹性情绪</li>
        </ul>
        <h3>Downgrade Trigger</h3>
        <ul>
          <li>财报与指引无法支撑当前预期</li>
          <li>商业模式验证继续拖延</li>
          <li>价格强，但 Reality 没有同步改善</li>
        </ul>
        <h3>Source Markdown</h3>
        <p><a href="../../wiki/companies/NBIS.zh.md">打开 NBIS 研究底稿</a></p>
        <p><a href="../../wiki/industries/ai-commercialization-verification-layer.zh.md">打开行业层底稿</a></p>
      </div>
    </section>
  </main>
</body>
</html>
```

- [ ] **Step 3: Read the HTML file back**

Run:

```powershell
Get-Content -Raw 'investing-os/dashboards/reports/NBIS-verification-layer-report.html'
```

Expected:

- The file contains the five reading blocks.
- The reading layer is clearly more scan-friendly than the source markdown.

- [ ] **Step 4: Commit the NBIS reading example**

Run:

```powershell
git add -- 'investing-os/dashboards/reports/NBIS-verification-layer-report.html'
git commit -m "docs: add NBIS research reading example"
```

Expected:

- One commit is created for the first reading example.

### Task 3: Final verification and handoff

**Files:**
- Verify:
  - `investing-os/dashboards/research-report-template.html`
  - `investing-os/dashboards/reports/NBIS-verification-layer-report.html`

- [ ] **Step 1: Check the final diff scope**

Run:

```powershell
git diff --stat HEAD~2..HEAD
```

Expected:

- The diff range shows only the reading template and first reading example, plus already-committed spec/plan docs for this work.

- [ ] **Step 2: Re-read the source and output relationship**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\companies\NBIS.zh.md'
Get-Content -Raw 'investing-os/dashboards/reports/NBIS-verification-layer-report.html'
```

Expected:

- The HTML reading example clearly reflects the markdown source.
- The output is easier to scan in under a minute.

- [ ] **Step 3: Check repository status**

Run:

```powershell
git status --short
```

Expected:

- No unrelated active user files were staged.
- Only the intended reading-template files were part of this implementation sequence.

## Self-Review

Spec coverage check:

- Hero summary: covered in Task 2
- Four core cards: covered in Task 2
- Timeline block: covered in Task 2
- Company × industry coupling block: covered in Task 2
- Full body deep-read layer: covered in Task 2
- Reusable template file: covered in Task 1

Placeholder scan:

- No `TODO`, `TBD`, or unresolved implementation references remain.

Type and naming consistency:

- `research-report-template.html`, `NBIS-verification-layer-report.html`, and the five reading blocks are used consistently across the plan.
