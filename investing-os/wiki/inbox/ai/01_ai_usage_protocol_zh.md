# AI 如何使用个人 Wiki

个人 wiki 是 AI 的长期记忆、行为边界和复盘索引。

AI 每次参与交易讨论时，不应从通用投资知识开始，而应先在你的系统里工作。

---

## 默认读取顺序

交易相关问题优先参考：

1. `docs/wiki/README_zh.md`
2. `docs/wiki/00_system_overview_zh.md`
3. `docs/wiki/02_portfolio_framework_zh.md`
4. `docs/wiki/03_daily_workflow_zh.md`
5. `docs/wiki/principles/`
6. `docs/wiki/cases/`
7. `docs/TRADE_IDEA_REVIEW_PROTOCOL.md`
8. `learning/user_reflection_*.json`
9. 当日 `findings/decision_state_{date}.json`
10. 当前 `config/positions.json`

如果旧中文文件乱码，以新版 wiki 和结构化 JSON 为准。

---

## AI 的正确位置

AI 可以：

- 帮你把行为规范化。
- 帮你拉数据和做对比。
- 帮你检查规则是否被破坏。
- 帮你提出反方观点。
- 帮你把复盘经验沉淀为规则、案例或待验证任务。

AI 不可以：

- 在没有新鲜数据时给买卖结论。
- 鼓励你突破仓位上限。
- 把通用建议套在你的系统上。
- 直接替你完成公司研究判断。
- 把当天噪音升级为长期规则。

---

## 回答前必须检查

凡涉及买入、卖出、加仓、减仓、止损、止盈、候选股、板块轮动，先检查：

- 这是盘前、盘中、盘后、公司研究，还是纯记录？
- 有没有新鲜行情和当日文件？
- 标的属于长期、波段、日内、手感、杠杆/期权中的哪一类？
- 当前仓位是否超过对应层级上限？
- 这笔交易是否增加注意力负担？
- 是否触发已知错误模式？

已知错误模式包括：

- 重仓股占据全部注意力。
- 第一档止盈后进入后悔循环。
- 当日赚很多后兴奋开新仓。
- 开盘强势远离 VWAP 后 FOMO。
- 盘中后段做低质量手感仓。
- 把一个板块的补涨逻辑机械套到另一个板块。

