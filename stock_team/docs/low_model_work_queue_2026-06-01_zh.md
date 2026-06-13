# 低阶模型工作队列

日期：2026-06-01

说明：本文件列出适合低阶模型执行的低风险任务。低阶模型只能按委托单工作，不能修改交易规则、核心代码、真实持仓、API key、回测核心或运行产物。

## P0

### 1. 盘前流程命令清单整理

任务等级：C

目标：从盘前 runbook 中提取纯命令清单，方便下次盘前逐条执行。

输入文件：
- `docs/premarket_planning_runbook_2026-06-01_zh.md`

允许修改：
- `docs/premarket_command_checklist_zh.md`

禁止触碰：
- `agents/`
- `scripts/`
- `config/`
- `findings/`
- `learning/`
- `.env`

输出格式：中文优先；按执行顺序列命令、产物、验收条件。

验收标准：不得新增交易判断；不得改交易规则；只整理已有流程。

不确定时：写“待高阶模型确认”。

### 2. 盘前流程硬门槛摘要

任务等级：C

目标：把“什么时候不能给交易规划”整理成一页中文检查表。

输入文件：
- `docs/premarket_planning_runbook_2026-06-01_zh.md`
- `docs/premarket_workflow_todo_2026-06-01_zh.md`

允许修改：
- `docs/premarket_hard_gates_zh.md`

禁止触碰：
- `agents/`
- `config/`
- `findings/`
- 任何交易运行 JSON

输出格式：中文 checklist。

验收标准：必须包含 stale summary、missing entry decision、price source 未刷新、summary 生成失败这几类阻断；不能给买卖建议。

不确定时：写“待高阶模型确认”。

## P1

### 3. TODO 中文优先整理

任务等级：B

目标：阅读 `docs/TODO.md`，整理出一份更易读的中文索引，不直接改原 TODO。

输入文件：
- `docs/TODO.md`
- `docs/premarket_workflow_todo_2026-06-01_zh.md`

允许修改：
- `docs/todo_index_zh.md`

禁止触碰：
- `docs/TODO.md`
- `agents/`
- `scripts/`
- `config/`

输出格式：按 P0/P1/P2 分类；每项最多 3 行。

验收标准：只做索引，不删改原 TODO；遇到乱码或含义不明处标“待高阶模型确认”。

不确定时：写“待高阶模型确认”。

### 4. Dashboard 字段说明草稿

任务等级：B

目标：从 `decision_state` 相关文档中整理 dashboard 后续可视化字段说明。

输入文件：
- `docs/TODO.md`
- `docs/superpowers/specs/2026-06-01-llm-controller-discipline-design.md`
- `docs/premarket_planning_runbook_2026-06-01_zh.md`

允许修改：
- `docs/dashboard_decision_state_fields_zh.md`

禁止触碰：
- `agents/dashboard_writer.py`
- `templates/`
- `findings/`
- 任何 UI 实现代码

输出格式：字段名 / 来源 / 含义 / 可视化用途 / 风险提示。

验收标准：只整理字段，不设计交易逻辑，不实现 dashboard。

不确定时：写“待高阶模型确认”。

## P2

### 5. 文档中文覆盖检查

任务等级：C

目标：列出 `docs/` 下哪些重要文档缺中文摘要，给高阶模型后续补文档用。

输入文件：
- `docs/`

允许修改：
- `docs/chinese_doc_coverage_report_zh.md`

禁止触碰：
- 除输出文件外的任何文件

输出格式：表格，列出文档路径、是否中文优先、建议动作。

验收标准：只读检查，不改原文档。

不确定时：写“待高阶模型确认”。

### 6. 运行产物字段索引

任务等级：B

目标：整理今天盘前运行产物中常用字段索引，帮助后续沟通更快定位文件。

输入文件：
- `docs/premarket_planning_runbook_2026-06-01_zh.md`

允许修改：
- `docs/premarket_artifact_field_index_zh.md`

禁止触碰：
- `findings/`
- `premarket_analysis_*.json`
- `daily_checklist_*.json`
- 任何运行产物

输出格式：文件名 / 关键字段 / 用途 / 谁消费。

验收标准：只根据文档整理，不读取或修改实时交易 JSON。

不确定时：写“待高阶模型确认”。
