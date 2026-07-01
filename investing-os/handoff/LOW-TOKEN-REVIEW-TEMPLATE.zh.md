# 低 Token Review 交接模板

日期：2026-07-01
适用场景：高阶模型对低阶模型交付做增量审查

## 目的

减少高阶复核时的上下文重复读取，避免每轮都重扫 DAILY 全链路与大文档。

## 使用规则

- 默认只做增量 review，不做全量项目回顾。
- 默认只读取本模板里明确列出的文件和提交。
- 除非本轮明确涉及契约变更，否则不重读整份 `DAILY-CONTRACT.zh.md`。
- 若要求“静态 review”，高阶模型不主动做额外复现。
- 若要求“验证 + review”，只跑指定测试，不扩展测试范围。

## 交接模板

```text
本轮只审：
- <问题 1>
- <问题 2>
- <问题 3>

提交：
- <commit sha 1>
- <commit sha 2>

前置文件：
- <任务包文件>
- <高阶契约文件>
- <必要时的单个决策文件>

允许高阶读取：
- <代码文件 1>
- <代码文件 2>
- <测试文件 1>

低阶摘要：
- 改动文件：
- 关键行为：
- 新增测试：
- 未确认风险：

高阶要求：
- 静态 review
或
- 静态 review + 跑以下测试：
  - <pytest 命令>
```

## 推荐约束

### 推荐 1

“本轮只审”不要超过 3 个点。

### 推荐 2

“允许高阶读取”尽量限制在 2 到 6 个文件。

### 推荐 3

如果本轮只是实现任务包，不要附带整个 DAILY 历史总结。

### 推荐 4

若高阶发现问题，下一轮继续沿用本模板，只更新：

- 新提交
- 新问题点
- 新测试命令

## 不推荐写法

以下写法会显著增加 token 消耗：

- “请全面复核这轮实现”
- “请结合之前所有 DAILY 文档一起判断”
- “请重新确认整个系统现在是否可用”
- 附上大段重复的历史背景

## 推荐写法示例

```text
本轮只审：
- full_review 在 review 文件缺失时是否阻断
- daily4 review 文件是否进入 artifact ledger

提交：
- abc1234

前置文件：
- investing-os/handoff/2026-07-01-daily-h4-task-packets.zh.md
- investing-os/handoff/2026-07-01-daily-h4-review-contract.zh.md

允许高阶读取：
- stock_team/orchestration/coordinator.py
- stock_team/orchestration/models.py
- stock_team/tests/unit/orchestration/test_coordinator.py

低阶摘要：
- 改动文件：coordinator.py, test_coordinator.py
- 关键行为：补 full_review 缺失 review 文件阻断；补 daily4 review artifact 登记
- 新增测试：2 个
- 未确认风险：未跑 integration

高阶要求：
- 静态 review + 跑以下测试：
  - python -m pytest -q stock_team/tests/unit/orchestration/test_coordinator.py
```
