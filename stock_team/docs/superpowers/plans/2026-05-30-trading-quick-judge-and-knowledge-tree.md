# Trading Quick Judge And Knowledge Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two Chinese trading-knowledge documents: one fast intraday quick-judge card and one durable knowledge tree for review and learning.

**Architecture:** Keep the implementation intentionally light: create two focused markdown files under `knowledge/`, one optimized for live decision speed and one optimized for deeper explanation and future lesson accumulation. Reuse existing repo language and recent case studies so the artifacts match the user's actual trading workflow instead of inventing a new framework.

**Tech Stack:** Markdown, existing repo knowledge files, existing session notes, manual review via shell commands.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `D:\gemini\lianghua\stock_team\knowledge\trading_playbook_quick_judge.md` | Create | A compact Chinese intraday checklist for environment, VWAP, strong/weak pattern, and execution mapping. |
| `D:\gemini\lianghua\stock_team\knowledge\trading_knowledge_tree.md` | Create | A deeper Chinese knowledge tree that explains the logic behind the quick-judge rules and stores canonical case studies. |
| `D:\gemini\lianghua\stock_team\knowledge\session_2026-05-28.md` | Reference only | Source for recent lessons and case-study phrasing. |
| `D:\gemini\lianghua\stock_team\docs\superpowers\specs\2026-05-30-trading-quick-judge-and-knowledge-tree-design.md` | Reference only | Approved design source. |

---

### Task 1: Create the quick intraday judge card

**Files:**
- Create: `D:\gemini\lianghua\stock_team\knowledge\trading_playbook_quick_judge.md`
- Reference: `D:\gemini\lianghua\stock_team\docs\superpowers\specs\2026-05-30-trading-quick-judge-and-knowledge-tree-design.md`
- Reference: `D:\gemini\lianghua\stock_team\knowledge\session_2026-05-28.md`

- [ ] **Step 1: Draft the file with five sections**

Write a markdown document with these exact sections:

```md
# 盘中速判卡

## 1. 先看环境
## 2. 强弱模板
## 3. VWAP 判断
## 4. 动作映射
## 5. 周期纪律
```

- [ ] **Step 2: Fill the environment and strong/weak sections**

Include concrete rules for:

```md
- QQQ 稳 / VIX 不恶化 / BTC 不继续跳水 = 偏进攻
- QQQ 走弱 / VIX 上冲 / 高 beta 普遍失守 = 偏防守
- 强票回踩：到价、没崩、有承接
- 弱票失守：跌破关键位、收不回、反抽无力
- 复杂票：不能只靠“AI 总会轮回来”判断
```

- [ ] **Step 3: Fill the VWAP, action, and timeframe sections**

Include these execution rules in Chinese:

```md
- VWAP reclaim -> 站稳 3-5 分钟 -> 再扩张 = 可执行小仓试错信号
- 跌破后弱拉锯 = 允许 3-10 分钟过滤，不必一秒钟卖在最差价
- 真失控破位 = 立即执行
- 日内单不自动升级成长拿
- 只有盘后重新确认 thesis，才能把日内单升级为波段单
```

- [ ] **Step 4: Review the quick card for speed**

Run:

```powershell
Get-Content -Path 'D:\gemini\lianghua\stock_team\knowledge\trading_playbook_quick_judge.md'
```

Expected: the whole file can be scanned top-to-bottom quickly, with short bullets and no long essay paragraphs.

- [ ] **Step 5: Commit**

```bash
git add D:/gemini/lianghua/stock_team/knowledge/trading_playbook_quick_judge.md
git commit -m "docs: add intraday quick judge playbook"
```

### Task 2: Create the deeper knowledge tree

**Files:**
- Create: `D:\gemini\lianghua\stock_team\knowledge\trading_knowledge_tree.md`
- Reference: `D:\gemini\lianghua\stock_team\docs\superpowers\specs\2026-05-30-trading-quick-judge-and-knowledge-tree-design.md`
- Reference: `D:\gemini\lianghua\stock_team\knowledge\session_2026-05-28.md`

- [ ] **Step 1: Draft the knowledge-tree skeleton**

Write a markdown document with these exact branches:

```md
# 交易知识树

## 1. 环境层
## 2. 板块资金流层
## 3. 个股类型层
## 4. 执行模板层
## 5. 持仓周期纪律层
## 6. 案例库
```

- [ ] **Step 2: Fill the environment, sector-flow, and stock-type branches**

Include rules for:

```md
- 进攻日 vs 防守日
- 月末/养老金再平衡作为顺风偏置，而不是单独信号
- AI 内部轮动：软件/安全 vs 光/存储/电力
- 纯暴露票、复杂平台票、弱破位票、高 beta 事件票
```

- [ ] **Step 3: Fill the execution, timeframe, and case-study branches**

Use the recent concrete cases:

```md
- BABA / SYM：方向对，但卖太急
- SNOW / NBIS / ARM：错过 VWAP reclaim -> 站稳 -> 再扩张
- IOT：短线成功，不等于长期 thesis 翻案
- COHR vs LITE：复杂性折价 vs 更干净暴露
```

- [ ] **Step 4: Review the knowledge tree for reuse**

Run:

```powershell
Get-Content -Path 'D:\gemini\lianghua\stock_team\knowledge\trading_knowledge_tree.md'
```

Expected: every branch has reusable language that can accept new lessons later without rewriting the whole file.

- [ ] **Step 5: Commit**

```bash
git add D:/gemini/lianghua/stock_team/knowledge/trading_knowledge_tree.md
git commit -m "docs: add trading knowledge tree"
```

### Task 3: Final consistency pass

**Files:**
- Modify: `D:\gemini\lianghua\stock_team\knowledge\trading_playbook_quick_judge.md`
- Modify: `D:\gemini\lianghua\stock_team\knowledge\trading_knowledge_tree.md`

- [ ] **Step 1: Cross-check terminology**

Verify these terms are used consistently in both files:

```text
进攻日 / 防守日
VWAP reclaim
站稳
再扩张
弱拉锯
真失控破位
日内单 / 波段单 / 长期 thesis
```

- [ ] **Step 2: Verify the quick card and tree agree with each other**

Run:

```powershell
Get-Content 'D:\gemini\lianghua\stock_team\knowledge\trading_playbook_quick_judge.md'
Get-Content 'D:\gemini\lianghua\stock_team\knowledge\trading_knowledge_tree.md'
```

Expected: the quick card is shorter and more operational, while the tree explains the same rules in more depth without contradiction.

- [ ] **Step 3: Commit**

```bash
git add D:/gemini/lianghua/stock_team/knowledge/trading_playbook_quick_judge.md D:/gemini/lianghua/stock_team/knowledge/trading_knowledge_tree.md
git commit -m "docs: align quick judge card with knowledge tree"
```
