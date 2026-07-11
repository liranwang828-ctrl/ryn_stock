# Operating Console 首屏精简设计

日期：2026-07-12  
状态：用户已确认方向，待文件复核

## 目标

把每日交易 Dashboard 从工程控制台收缩为日常交易入口。用户打开首屏后，应在一个视口内看清：现在在哪一步、事实是否就绪、需要在当前对话确认什么、今天关注什么风险。

## 方案选择

采用“首屏四块 + 诊断折叠”的方案。

未采用：

- 删除工程信息：会失去排障能力；
- 保持现状只调整样式：不能解决信息层级混乱；
- 重做新 Dashboard：违背复用现有 operating console 的方向。

## 首屏结构

首屏只保留四块：

1. 今日步骤：DAILY-0 至 DAILY-4 与当前子步骤；
2. 事实就绪：账户、盘前、焦点证据和计划的状态摘要；
3. 当前对话：唯一的 `next_conversation_prompt`；
4. 今日关注：焦点标的、最高优先级警告和 observation/trading 边界。

首屏不得显示：

- 绝对文件路径；
- coordinator state/version；
- skill path、agent role、内部 action 名称；
- 大段 artifact 输入输出列表；
- Init/Confirm/Start 等流程按钮。

## 诊断详情

以下内容移动到默认折叠的 `<details>` 区域：

- coordinator 与 state sync；
- artifacts、路径、来源、新鲜度和 issues；
- current skill task、输入输出和内部说明；
- snapshot form；
- legacy routes 与工程入口。

诊断详情只读，不推进状态。

## 认知 Dashboard

首屏只保留一个明确的“打开认知系统”跳转，指向现有 `growth-dashboard-draft.html`。不在每日 Dashboard 展开 lineage、能力雷达、经验晋升或长期研究内容。

## 数据与行为边界

- 继续只读 `daily_status` manifest；
- 不新增第二套 readiness 计算；
- manifest 缺失时显示一个清晰的“等待状态检查”卡片；
- `FAILED_TOOL` 或 blocked 时，最高优先级警告进入首屏，其余细节折叠；
- 页面刷新不调用 coordinator action；
- 不修改 growth dashboard、manifest schema 或 DAILY 状态机。

## 验收

- 首屏存在四个稳定区域：`dailyStepSummary`、`factReadinessSummary`、`conversationPromptSummary`、`todayFocusSummary`；
- 工程详情位于默认折叠的 `diagnosticDetails`；
- 首屏没有 workflow action buttons；
- operating console 仍能展示 daily_status 缺口并跳转认知 Dashboard；
- focused Dashboard tests 通过；
- 浏览器人工检查首屏信息密度明显降低。
