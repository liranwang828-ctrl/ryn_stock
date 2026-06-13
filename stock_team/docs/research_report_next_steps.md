# 研究报告后续优化备忘

**上次会话结束时间**: 2026-05-20

## 核心设计原则（用户明确提出）

### 研究报告 ≠ 个人持仓报告
研究报告应该是**客观分析**，不应以用户成本价来定价格目标。
- ❌ 错误："目标价 $275（较成本 +50%）"
- ✅ 正确："目标价 $275（当前价 $224，上行 22.7%；基于分析师共识/DCF/EV/EBITDA）"

报告架构应分两层：
1. **客观研究层**（任何人读都有意义）：分析师目标价、技术支撑位、估值锚
2. **持仓叠加层**（仅有仓位时显示）：你的成本、止损、GTC状态

### 持仓策略优化方向
当前问题：T2条件用 "cost × 0.92"，这是以个人成本为参考，不客观。

应改为基于：
- **技术层面**：近期支撑位（MA50/MA200/近期低点）而非成本价
- **基本面层面**：合理估值区间（分析师目标价 × 0.75~0.85）
- **仓位逻辑**：论点型 = 论点完整时才加仓，不看成本位置
- **Flex 加仓**：来自 premarket_summary.exit.flex_add_level（已有）

### 出场逻辑优化
应以**当前价**为基准，不是成本：
- 目标达成出场：分析师目标价 $275（当前 $224，+22.7%）
- 不是："较成本 +50%"

---

## 待完成工作

### A. 研究报告层（当前进行中）
1. **成本价 → 当前价** 重构：所有价格目标改为基于当前价的百分比
2. **持仓策略**：T2/Flex 加仓条件改为基于技术位（MA50/近期低点），不是成本
3. **支撑论据**：替换 [Tech] key_points 为 company_profile.competitive_moat 描述
4. **当前价/浮盈**：position_snapshot.cur_price=None，需要在生成 memo 时注入实时价格

### B. 公司画像（其他标的）
- MRVU → 需要 MRVL 的公司画像（MRVU 是 2x ETF，yfinance 数据空）
- IAU → 黄金 ETF，需要黄金宏观逻辑（央行购金/通胀/美元）
- LITX → 需要 LITE 的公司画像

### C. dashboard 链接整合
- 报告链接已加入 dashboard（`📊 CIO` 链接）
- `🔬研究报告` 链接改为指向新版 research HTML

---

## 关键文件路径
- 研究报告: `agents/report_viewer.py` + `agents/strategic_memo_writer.py`
- 公司画像: `agents/company_profile_fetcher.py` → `findings/company_profile_{sym}.json`
- CIO 主流程: `agents/cio.py` (phases 0123)
- 大师论点: `agents/persona_engine.py` + `agents/debate_engine.py`
- dashboard: `templates/daily_dashboard.html.j2` + `agents/dashboard_writer.py`

## 数据依赖链
```
quick_fundamentals.py → fundamentals_{sym}.json
       ↓
company_profile_fetcher.py → company_profile_{sym}.json (web_enhanced=True 时有研报数据)
       ↓
cio.py (phases 0123) → cio_signals + narrative_{sym}.json + TechAgent_{sym}.json 等
       ↓
strategic_memo_writer.py → strategic_memo_{sym}.json (含推导证伪/出场逻辑)
       ↓
report_viewer.py → research_{sym}_{date}.html
```

## 下次 compact 后恢复时说
"继续研究报告优化，从持仓策略改为基于技术位而非成本价开始"
