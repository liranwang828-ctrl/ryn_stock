# Operating Console 分页信息架构设计

日期：2026-07-12  
状态：用户已选择方案 A 并确认模块归属

## 1. 取代关系

本设计取代 `2026-07-12-operating-console-simplification-design.zh.md` 中“首屏四块摘要 + 旧页面整体折叠”的布局方案。

上一版只降低了首屏可见信息，没有判断旧模块是否仍需要，造成：

- 新摘要与旧 hero / entry / workflow 重复；
- diagnostics 成为旧页面的整体收纳箱；
- 没有真正分页；
- 长期认知、日常交易、证据和工程诊断继续混杂。

## 2. 目标

每日交易 Dashboard 只服务四类任务：今天做什么、事实是否充分、复盘是否完成、系统是否健康。不同任务进入不同页面；同一事实不在多处重复解释。

认知成长继续由独立 growth dashboard 承担。

## 3. 路由方式

保持一个 `operating-console.html`，使用 hash 路由提供四个真正互斥的页面：

- `/#today`
- `/#evidence`
- `/#review`
- `/#diagnostics`

选择该方式是为了：

- 复用一次 API 数据加载；
- 避免复制 HTML、JS 和 readiness 逻辑；
- 刷新后保留当前页；
- 允许直接打开特定页面；
- 后续仍可拆成独立文件而不改变页面职责。

## 4. 顶部导航

固定导航：

1. 今日交易
2. 证据
3. 复盘
4. 系统诊断
5. 外部跳转：认知系统

旧的 Growth Demo、Intraday Demo、Latest Review、Stock Team Dashboard 等散乱 header pills 不再全部显示。仍有价值的链接移动到所属页面。

## 5. 今日交易页

只回答“现在做什么”。

直接显示：

- 一个当前主任务区：current node、current substep、status、唯一 `next_conversation_prompt`；
- DAILY-0 至 DAILY-4 紧凑时间线，仅当前节点展开；
- 今日焦点池；
- trading / observation 权限边界；
- 最高优先级 warning 或 blocker；
- 数据更新时间的简短标记。

不显示：

- coordinator action 名称；
- skill path 或 agent role；
- 文件路径；
- artifact 全量列表；
- snapshot form；
- research/evolution 内容。

## 6. 证据页

显示：

- IBKR 账户事实状态；
- Stage 0 universe、snapshot、market-context；
- Stage 0 discussion 与 focus decision；
- Stage 1 evidence；
- trading plan 与 intraday guidance 的 readiness；
- 每个 artifact 的 present / valid / confirmed / freshness；
- data source、更新时间、issues 和文件链接；
- 当前真正需要生成的产物任务。

旧 `Current Skill Task` 改为“当前产物任务”，不显示 agent/skill 工程术语。

## 7. 复盘页

显示：

- 盘中事件与待确认数量；
- DAILY-4 review 状态；
- full / quick / freeze 模式；
- 未完成收尾；
- candidate lessons；
- 最新复盘报告链接；
- 进入认知 Dashboard 查看长期晋升的入口。

在 intraday event 与 cognition bridge 尚未实现时，显示明确的“尚未接线”，不使用静态旧数据伪装完成。

## 8. 系统诊断页

显示：

- coordinator state 与 effective state；
- `state_sync_needed`；
- session、manifest 和 artifact 绝对路径；
- API / IBKR / provider 健康；
-错误日志；
-手工 snapshot fallback；
- legacy dashboard / packet 链接。

该页面只读。手工 fallback 工具必须明确标注不会授予交易权限。

## 9. 旧模块处理

| 旧模块 | 处理 |
|---|---|
| 四块首屏摘要 | 删除，合并为今日页的单一主任务 |
| Coordinator Hero | 删除原模块；必要状态并入主任务和诊断页 |
| Minimal Entry State | 删除，内容已被主任务覆盖 |
| Workflow Steps | 重写为 DAILY-0..4 时间线 |
| Current Skill Task | 移到证据页并改为业务语言 |
| Snapshot Form | 移到系统诊断页，标记为 fallback |
| Cognitive Summary | 从每日 Dashboard 删除 |
| Daily Routes | 删除，由 hash 导航替代 |
| Stock Team Packets | 移到证据页 |
| Evidence Gaps | 并入证据 readiness |
| Pending Lessons | 移到复盘页 |
| Next Actions | 删除，只保留 manifest 唯一提示 |

## 10. 数据边界

- 全站只读同一个 `daily_status`；
- 不新增第二套 readiness 判断；
- 页面切换只改变可见 panel，不重新推进流程；
- manifest 不含某页数据时，该页显示 missing/not wired；
- 今日焦点不得从旧 snapshot 静默继承；只有已确认 decision sheet 才能显示为“今日焦点”；
- growth dashboard 不修改。

## 11. 验收

- 四个 hash route 可直接访问且互斥显示；
- 今日页不存在四块重复摘要、旧 hero 和 minimal entry；
- 证据页能查看 artifact readiness；
- 复盘缺能力时诚实显示未接线；
- 诊断页保留必要排障信息但默认不进入；
- header 只保留五个稳定入口；
- source-contract tests 与 focused Dashboard tests 通过；
- Playwright 截图验证桌面与窄屏页面层级。

