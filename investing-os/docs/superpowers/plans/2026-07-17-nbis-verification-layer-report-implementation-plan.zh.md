# NBIS Verification Layer Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the first reusable company + industry hybrid research example for NBIS, including a readable report and a structured research card, using the investing-os framework and existing dossier templates.

**Architecture:** Reuse existing `investing-os/wiki/companies/` and `investing-os/wiki/industries/` structures rather than inventing a new report system. Create one company-level NBIS report as the main readable artifact, optionally add a compact industry-layer note for the AI commercialization / verification layer, and append a structured research card to the company report so the example can later plug into the research database direction.

**Tech Stack:** Markdown, investing-os research templates, Git

---

## File Structure

- Create: `investing-os/wiki/companies/NBIS.zh.md`
  - Main readable hybrid research report for NBIS.
- Create: `investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md`
  - Compact industry-layer framing note that explains the verification layer and where NBIS sits inside it.
- Verify against:
  - `investing-os/wiki/companies/company-dossier-template.md`
  - `investing-os/wiki/industries/industry-dossier-template.md`
  - `investing-os/templates/company-research.md`
  - `investing-os/templates/industry-research.md`
- Verify with:
  - `powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path <file>`
  - `git diff --stat`
  - `git status --short`

### Task 1: Create the compact industry-layer framing note

**Files:**
- Create: `investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md`

- [ ] **Step 1: Re-read the existing industry template**

Run:

```powershell
Get-Content -Raw 'investing-os/wiki/industries/industry-dossier-template.md'
```

Expected:

- The template includes worldview, first-principles, value capture, key companies, risks, and monitoring sections.

- [ ] **Step 2: Write the compact industry note**

Create `investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md` with these sections:

```md
# AI 商业化验证层

## Metadata

```yaml
industry: AI commercialization verification layer
status: active_theme
created_at: 2026-07-17
updated_at: 2026-07-17
review_due: 2026-10-31
source_packets:
related_companies:
  - NBIS
  - NOW
  - ORCL
  - MSFT
related_principles:
  - Reality before narrative
  - Question -> Evidence -> Hypothesis
```

## Worldview Link

这一层研究的核心问题不是“AI 是否有前景”，而是“哪些公司真正把 AI 需求转化为可验证的商业模式、利润率与现金流”。

## First-Principles Analysis

AI 商业化验证层位于：

- 硬件 Reality 指标层之后
- 软件成熟商业化领导者之前

它的特点是：

- 叙事很强
- 价格弹性很高
- Reality 尚未完全确认

## Value Capture

这一层真正要验证的不是收入故事，而是：

- 用户需求是否稳定
- 收费模式是否成立
- 毛利率和经营杠杆是否能改善
- 业务是否能跨过“概念被交易”进入“利润被验证”

## Key Companies By Role

- NBIS: 验证层高弹性标的
- NOW: 较成熟商业化观察对象
- ORCL: 基础设施与商业化交界层
- MSFT: 商业化领导层对照组

## Risks And Counter-Thesis

- 市场可能提前交易过多未来利润
- 商业模式验证速度可能慢于估值扩张速度
- 高弹性票的价格修复不等于 Reality 修复

## Monitoring Plan

- 财报中的收入质量
- 利润率改善
- 新客户与续费质量
- 与 AI 相关业务占比是否真实提升

## Open Questions

- 哪些公司会从验证层升级为已验证商业化层？
- 哪些只是高弹性叙事承载体，而不具备长期价值捕获能力？
```

- [ ] **Step 3: Read the file back through the UTF-8 helper**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\industries\ai-commercialization-verification-layer.zh.md'
```

Expected:

- Chinese content renders correctly.
- The note explains the verification layer clearly and mentions NBIS as one member of that layer.

- [ ] **Step 4: Commit the industry note**

Run:

```powershell
git add -- 'investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md'
git commit -m "docs: add AI commercialization verification layer note"
```

Expected:

- One commit is created for the industry note.

### Task 2: Create the NBIS hybrid company report

**Files:**
- Create: `investing-os/wiki/companies/NBIS.zh.md`

- [ ] **Step 1: Re-read the existing company template**

Run:

```powershell
Get-Content -Raw 'investing-os/templates/company-research.md'
```

Expected:

- The template includes business model, industry context, narrative, valuation, risks, falsification, and next actions.

- [ ] **Step 2: Write the main NBIS report**

Create `investing-os/wiki/companies/NBIS.zh.md` with this structure:

```md
# NBIS 研究报告（验证层示例）

## Company

- Name: NBIS
- Ticker: NBIS
- Date: 2026-07-17
- Researcher: Codex + User

## 一句话定位

NBIS 不是 AI 产业中的已验证核心资产，而是位于“AI 商业化验证层”的高弹性观察对象：市场愿意提前给它未来空间，但 Reality 仍需未来 1–2 个季度继续验证。

## 它在 AI 生态中的角色

NBIS 更适合放在“Verification Layer”而不是“Reality Indicator”或“Commercialization Leader”。

这意味着：

- 它承载的是未来商业模式验证的预期
- 它的价格弹性可以很强
- 但它还不能被当成已经验证完成的核心资产

## 为什么它属于验证层

对 NBIS 来说，市场现在最关心的不是“有没有故事”，而是：

- 需求是否真实可持续
- 商业模式是否跑通
- 收入是否能向利润和现金流转化
- 它是否能从叙事资产升级为已验证资产

## 市场当前在交易什么

市场当前更像是在交易以下预期：

- AI 相关需求会继续扩张
- NBIS 有机会承接其中一部分高增长价值
- 一旦商业化验证出现，估值可以被重新上修

但价格在交易这些预期，不代表这些预期已经被 Reality 全部确认。

## Reality Confirmed

- 市场确实愿意在风险偏好回升时重新给 NBIS 定价
- NBIS 具备高弹性、可被纳入 AI 主题交易的属性
- 它已经进入我们的正式观察池，而不是完全边缘标的

## Reality Unconfirmed

- 商业模式是否已经具备稳定可验证的盈利路径
- 利润率和现金流是否足够支撑更高估值
- 未来几个季度的增长是否能证明这不是单纯叙事交易

## 行业背景：AI 商业化验证层

参考：

- `investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md`

NBIS 所在层的核心特征是：

- 价格对预期很敏感
- 叙事与 Reality 存在较大距离
- 真正重要的是未来几个季度的验证，而不是一天的反弹

## 未来 1–2 个季度最关键的验证节点

- 财报中与 AI 相关的收入质量
- 利润率和经营杠杆是否改善
- 客户需求是否稳定、可持续
- 管理层对未来业务节奏的指引

## Bull Case

- NBIS 在未来 1–2 个季度逐步证明需求与商业化路径
- 市场发现它不只是高弹性叙事票，而是可以升级的验证层资产
- 估值从“预期型”向“部分验证型”迁移

## Bear Case

- 价格修复只是风险偏好回升下的一次脉冲
- 后续财报无法证明收入质量或利润改善
- 市场重新把它归类为高波动主题票而非可升级资产

## 当前投资看法

当前更合理的定位是：

- 正式观察
- 可以研究
- 不能当作已验证核心仓位

如果后续出现更强的基本面验证，可以从“观察对象”升级为“更高优先级候选”。

## Upgrade Trigger

- 财报明确验证收入质量、利润率或现金流改善
- 管理层给出更可信的商业化路径
- 市场对其定价不再只依赖高弹性情绪

## Downgrade Trigger

- 财报与指引无法支撑当前预期
- 商业模式验证继续拖延
- 价格强但 Reality 没有同步改善

## Falsification

如果未来 1–2 个季度内，NBIS 仍无法证明自身具备持续可验证的商业模式，而价格又持续只依赖情绪与主题回流，那么“它能够从验证层升级”的假设应被下调。

## Next Actions

- 在下一轮财报前继续跟踪验证信号
- 将其与 NOW / ORCL / MSFT 做商业化层级对照
- 将其与 MU / AMAT / NVDA 做“Reality 已验证层”对照

---

## Structured Research Card

- Company: NBIS
- Industry Theme: AI commercialization verification layer
- Role in Value Chain: Verification-layer AI company
- Current Narrative: 市场在提前交易其未来商业化与增长空间
- Reality Confirmed:
  - 具备 AI 主题高弹性属性
  - 风险偏好回升时有明显价格修复能力
- Reality Unconfirmed:
  - 商业模式是否稳定成立
  - 利润率与现金流是否能验证估值
- Key Hypotheses:
  - NBIS 可能从验证层升级为部分已验证商业化标的
- Bull Case:
  - 财报与指引逐步验证商业模式
- Bear Case:
  - 只是高弹性叙事票，无法真正兑现
- Next 3 Validation Events:
  - 下一轮财报
  - 管理层业务指引
  - 收入质量 / 利润率变化
- Current Stance: observe
- Upgrade Trigger: fundamentals confirm commercialization path
- Downgrade Trigger: repeated narrative without operating proof
```

- [ ] **Step 3: Read the company report back through the UTF-8 helper**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\companies\NBIS.zh.md'
```

Expected:

- The report reads as one coherent company + industry hybrid note.
- The structured card is present at the end.

- [ ] **Step 4: Commit the company report**

Run:

```powershell
git add -- 'investing-os/wiki/companies/NBIS.zh.md'
git commit -m "docs: add NBIS verification layer report example"
```

Expected:

- One commit is created for the NBIS example report.

### Task 3: Final verification and handoff

**Files:**
- Verify:
  - `investing-os/wiki/industries/ai-commercialization-verification-layer.zh.md`
  - `investing-os/wiki/companies/NBIS.zh.md`

- [ ] **Step 1: Check the final diff scope**

Run:

```powershell
git diff --stat HEAD~2..HEAD
```

Expected:

- The diff range shows only the two new research example files, plus already committed spec/plan docs for this work.

- [ ] **Step 2: Re-read both files with the UTF-8 helper**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\industries\ai-commercialization-verification-layer.zh.md'
powershell -ExecutionPolicy Bypass -File '.\investing-os\tools\show-utf8-file.ps1' -Path '.\investing-os\wiki\companies\NBIS.zh.md'
```

Expected:

- Both files remain readable in Chinese.
- The industry note and company note fit together.

- [ ] **Step 3: Check repository status**

Run:

```powershell
git status --short
```

Expected:

- No unrelated active user files were staged.
- Only the intended example files were part of this implementation sequence.

## Self-Review

Spec coverage check:

- Company + industry hybrid structure: covered in Tasks 1 and 2
- Verification-layer framing: covered in Tasks 1 and 2
- One to two quarter validation focus: covered in Task 2
- Structured research card: covered in Task 2
- Reusable report format: covered in Tasks 1–3

Placeholder scan:

- No `TODO`, `TBD`, or unresolved references remain.

Type and naming consistency:

- `NBIS.zh.md`, `ai-commercialization-verification-layer.zh.md`, and `Structured Research Card` are used consistently across the plan.
