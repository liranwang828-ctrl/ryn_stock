# 对话驱动 DAILY 每日交易流程设计

日期：2026-07-11  
状态：已完成对话确认，待文件复核  
适用范围：DAILY-0 至 DAILY-4、每日交易 Dashboard、既有 investing-os 认知 Dashboard 的连接边界

## 1. 目标

让用户与高阶模型在当前对话中共同走完一个交易日。Dashboard 负责展示事实、步骤、缺口和对话产物状态，但不替代讨论、确认或认知判断。

第一阶段优先让现有 `stock_team + investing-os` 真正运行起来，不先深入设计 investing-os 如何调用长期认知参与每一个每日判断。该复杂问题保留稳定接口，后续专题设计。

## 2. 已选择的总体方案

采用“对话驱动、canonical 文件作为事实、Dashboard 读取统一 manifest”的方案。

未采用：

- coordinator 状态机主导认知流程：自动化更强，但容易让代码状态压过真实讨论；
- Dashboard 表单或按钮主导流程：操作直观，但会把投资判断压缩成界面动作；
- 单一合并 Dashboard：会破坏用户已经满意的 investing-os 认知 Dashboard。

总体数据流：

```text
用户 + 高阶模型对话
  -> 讨论、解释、盘中思考和明确确认
  -> 写入 canonical 文件
  -> DAILY 轻量检查器校验文件并生成 daily-status manifest
  -> 每日交易 Dashboard 只读取 manifest 与事实产物

DAILY-4 经验候选
  -> cognition_updates / promotion_queue
  -> 既有 investing-os 认知 Dashboard
```

## 3. 职责边界

### 3.1 用户与高阶模型

- 是每日流程的主控制器；
- 完成活动模式、环境解释、焦点池、计划、权限、例外和复盘确认；
- 将确认结果写入固定 schema；
- 盘中可随时提出信号、思考、疑问和需要确认的动作。

### 3.2 investing-os

- 拥有计划、权限、风险边界、复盘、经验候选和长期认知；
- 第一阶段提供三个稳定接口，但暂不深入实现其内部推理：
  - `context_inputs`：每日流程可读取的既有认知；
  - `cognition_updates`：当日产生的认知变化候选；
  - `promotion_queue`：等待周期复核的候选。

### 3.3 stock_team

- 提供 IBKR 账户、持仓、订单和成交事实；
- 获取市场行情并生成 Stage 0/1 证据；
- 生成盘中快照和盘后事实包；
- 不决定焦点池、交易权限、计划或经验结论。

### 3.4 DAILY 轻量检查器

- 校验 canonical 文件的结构、日期、数据来源、引用和确认字段；
- 从文件推导当前步骤、缺口、数据新鲜度和下一句建议；
- 在对话写入后自动运行；Dashboard 刷新时也可重新运行；
- 不编造内容，不承担投资判断。

### 3.5 Dashboard 与 coordinator

- 每日交易 Dashboard 只展示 manifest 和事实产物，不生成认知文件，不提供推进步骤按钮；
- coordinator 调用工具、记录执行结果并支持恢复，不凌驾于 canonical 文件事实；
- 文件合格并含确认标记后自动显示下一步骤，无需额外点击“完成”。

## 4. DAILY 主链与用户交互

### 4.1 DAILY-0 晨间准备

顺序：

1. 恢复前一交易日状态，处理未完成复盘；
2. 获取 IBKR 账户、持仓和未完成订单事实；
3. 确认今日模式：交易、观察、研究、复盘或休息；
4. 确认需要进入盘前判断的持仓和候选对象；
5. 确认初始风险边界。

正常日由系统先给出摘要，用户只确认或修改异常项。账户异常、跨日欠账或风险状态变化时，切换为逐项确认。

正式入口产物为 `daily-start.json` 或经现有文件映射后确定的等价 canonical 文件。

### 4.2 DAILY-1 盘前决策

固定顺序：

```text
stock_team 获取市场环境事实
-> 用户与高阶模型讨论环境、风险和优先级
-> 用户确认焦点池
-> stock_team 只为焦点池生成标的证据
-> 用户与高阶模型讨论计划、允许动作和禁止动作
-> 用户确认当日计划
```

两个确认点不得自动跨越：

1. 焦点池确认决定“研究谁”；
2. 计划确认决定“今天允许做什么”。

环境不适合交易时，仍可生成少量焦点证据用于观察和学习，但权限必须固定为 `observe_only`，不得由证据自动升级为交易权限。

### 4.3 DAILY-2 开盘观察

- stock_team 获取开盘后的价格、量能、指数和焦点标的事实；
- 检查器对照盘前假设与已确认计划；
- 正常情况只展示，不要求用户确认，不改写盘前计划；
- 计划失效、风险边界触发或准备交易时，必须回到当前对话；
- 用户也可主动提出观察、疑问和需要确认的动作。

### 4.4 DAILY-3 盘中管理

盘中形成双向事件流：系统关键偏差与用户主动观察都进入当前对话。对话产出结构化事件卡片，至少包含：

- 时间与相关标的；
- 观察到的事实；
- 用户初步解释或疑问；
- 高阶模型回应；
- 是否影响当前计划；
- 是否需要确认；
- `pending_review` 复盘状态；
- 原始对话引用。

权限规则：

- 普通观察与心得不改写计划；
- 计划内首次建仓和加仓仍需在对话中确认；
- 计划内止损退出按已批准规则执行或提示，不要求临场重新批准；
- 计划外动作必须形成带理由、风险变化和失效条件的计划变更候选；
- 用户明确确认后生成新版本计划，旧版本和修改历史永久保留。

Dashboard 显示结构化事件卡片，不直接堆叠完整原始对话。

### 4.5 DAILY-4 盘后复盘

输入包括：

- 账户、订单和成交事实；
- 盘前假设、计划与实际走势的偏差；
- 盘中对话形成的观察、疑问和心得候选。

系统先按市场判断、标的选择、入场执行、风险控制、情绪与纪律等主题聚类。用户与高阶模型逐一处理异常、矛盾和高价值记录，普通记录可批量归档。

每日只形成经验候选、待验证问题和认知变化候选，不直接修改长期规则。周期复核采用双触发：每周例行复核，高风险或重复出现的问题提前触发。

收尾必须保存次日可恢复状态。

## 5. 文件就绪与统一 manifest

实施前必须先把下列逻辑名称映射到现有文件，不得因为命名不同而创建重复产物。

| 步骤 | 逻辑产物 | 就绪条件 |
|---|---|---|
| DAILY-0 | `daily-start.json` | 当日日期、活动模式、账户事实状态、分析范围和用户确认齐全 |
| DAILY-1A | `pre-market-universe.json`、`pre-market-snapshot.json`、`stage0-market-context.md` | 来源与时间有效，五项脑侧前置结构存在 |
| DAILY-1B | `stage0-discussion-notes.md`、`stage1-decision-sheet.json` | 对话结论和用户确认焦点池存在 |
| DAILY-1C | `stage1-evidence-packet.md`、`trade-plan.json`、`intraday-guidance.json` | 证据引用完整，交易或观察权限经用户确认 |
| DAILY-2/3 | `intraday-snapshot.json`、`intraday-events.jsonl` | 快照可读，事件带时间、来源和复盘状态 |
| DAILY-4 | `daily4-review.json`、`next-day-state.json` | 当日结论、经验候选、遗留问题和归档确认齐全 |

检查器输出统一 `daily-status manifest`：

```json
{
  "trading_date": "YYYY-MM-DD",
  "current_step": "DAILY-1A",
  "status": "ready | waiting_user | waiting_data | blocked | complete",
  "ready_artifacts": [],
  "missing_items": [],
  "next_conversation_prompt": "",
  "data_freshness": {},
  "pending_intraday_events": 0,
  "pending_review_candidates": 0
}
```

Dashboard 不自行重复这些判断。

## 6. 双 Dashboard

### 6.1 每日交易 Dashboard

第一版只显示：

- 今日账户和市场事实；
- DAILY-0 至 DAILY-4 进度；
- 当前缺口和建议在这里继续的下一句话；
- 盘中事件卡片；
- 与今天有关的经验候选和认知摘要；
- 跳转到 investing-os 认知 Dashboard 的入口。

### 6.2 investing-os 认知 Dashboard

- 优先原样复用用户已经满意的既有版本；
- 独立展示公司研究、主题认知、策略经验、错误模式、候选晋升和知识演化；
- 读取 `cognition_updates` 与 `promotion_queue`；
- 提供返回每日交易 Dashboard 的清晰跳转；
- 本设计不将其嵌入或重做为每日交易 Dashboard 的子页面。

## 7. 异常与恢复

- IBKR 不可用：账户事实标记 `stale_unverified`；允许观察和研究，不授予新交易权限；
- 行情源不可用：显示缺失和降级来源，不得把昨日收盘伪装为盘前数据；
- 前日未复盘：支持冻结收尾、快速复盘或完整复盘，然后恢复今日流程；
- 无交易日：允许观察、研究、复盘或休息，不强迫进入完整交易链；
- 对话或服务中断：检查器重新读取 canonical 文件和确认标记恢复步骤；
- 文件损坏或矛盾：停留当前步骤并报告具体文件与字段，不由 Dashboard 猜测；
- Dashboard 不可用：对话与文件流程仍可独立运行。

## 8. 最小落地顺序

1. 深入读取并映射现有 DAILY 文件、检查器、盘前命令和两个 Dashboard；
2. 为文件标注 `reuse-now`、`merge-later`、`reference-only` 或 `retire-later`，为后续筛选有用与无用文件保留证据；
3. 建立统一 `daily-status manifest` 检查器；
4. 跑通 DAILY-0 与 DAILY-1，包括账户事实、盘前数据、环境讨论、焦点确认、标的证据和计划确认；
5. 让每日交易 Dashboard 只读取 manifest 和现有事实产物；
6. 隔离试跑一个交易日，记录断点；
7. 接入 DAILY-2/3 的盘中事件卡片和确认路径；
8. 接入 DAILY-4，并把经验候选连接到既有认知 Dashboard；
9. DAILY 稳定后，单独设计 investing-os 如何深度参与每日判断。

## 9. 验收标准

用户能够在当前对话中共同走完一个交易日。每日交易 Dashboard 始终正确显示：

- 当前步骤；
- 已准备的事实和产物；
- 正在等待的讨论或确认；
- 下一步将生成什么；
- 盘中对话事件及其复盘状态；
- 当日内容如何进入经验候选和长期认知。

流程必须能在 Dashboard 暂时不可用时继续，并能在恢复后从 canonical 文件重建显示状态。

## 10. 明确延后事项

- investing-os 长期认知如何选择、压缩并注入每日判断；
- 认知冲突、置信度和版本晋升的详细算法；
- 两个 Dashboard 是否未来增加统一总首页；
- 自动交易执行；
- 与 DAILY 主链无关的仓库级重构。
