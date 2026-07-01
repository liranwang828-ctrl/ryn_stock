# DAILY Q1–Q3 用户批准记录

日期：2026-07-01
决定者：用户
状态：approved

用户明确回复：“全部A没问题”。

批准内容：

1. **Q1 — `post_open_adj`：选项 A**
   - 移除其覆盖盘前锚点的能力。
   - 盘中调整锚点必须回到计划变更与用户确认流程，并保留版本和审计记录。
2. **Q2 — 复盘交互：选项 A**
   - 通过对话完成复盘判断。
   - `investing-os` 将确认结果写入结构化产物。
   - Dashboard 后续负责展示和辅助确认，不要求用户重复填写 CLI 表单。
3. **Q3 — 时间窗口：选项 A**
   - 使用软提示，不因错过目标时间窗口而硬拒绝流程。
   - 允许跨时区、迟到恢复、观察和补做。
   - as-of、市场窗口、freshness 和数据真实性校验仍严格执行。

本批准使 DAILY 契约的用户决策部分正式生效。

本批准不代表当前候选代码已经通过验收。实现仍须修复并通过：

- full_review 完整复盘闸门；
- archive_day 生产归档接线；
- observation 动作契约；
- quick/full/异常 session 的跨日恢复；
- DAILY-4 对话与结构化产物；
- 从公开入口驱动的完整 E2E。

实现审核见：

`investing-os/handoff/reviews/2026-07-01-daily-implementation-review.md`
