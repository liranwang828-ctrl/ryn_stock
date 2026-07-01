# DAILY H4 盘后复盘高阶契约

日期：2026-07-01
适用范围：`DAILY-4 盘后复盘`
依据：
- `investing-os/system/workflows/DAILY-CONTRACT.zh.md`
- `investing-os/handoff/2026-07-01-daily-h1-h3-repair-charter.zh.md`
- `investing-os/handoff/decisions/2026-07-01-daily-q1-q3-approval.md`

## 1. 目的

本契约定义 DAILY-4 中必须由高阶模型先定清的部分：

1. 复盘对话问题顺序
2. 用户必须确认的判断点
3. 结构化产物的事实层、判断层、候选层边界
4. `stock_team` 与 `investing-os` 的职责边界

本契约不直接定义代码实现，也不授权低阶模型自行修改复盘语义。

## 2. 基本原则

- 先事实，后判断，最后才允许形成经验候选。
- `stock_team` 只输出复盘事实，不输出心理归因、永久教训或 thesis 级结论。
- `investing-os` 可以基于事实和用户对话形成“判断记录”和“经验候选草稿”，但不能自动批准进入 `LEARNING`。
- 用户必须显式确认哪些内容只是当日噪声，哪些内容进入候选经验。
- 若 IBKR 正式成交事实不可得，允许只读展示缓存，但不得完成正式复盘闭环。

## 3. DAILY-4 六步合同

### Step 1 事实收集

`stock_team` 负责生成复盘事实包，至少覆盖：

- 当日成交记录
- 当日持仓变化
- 盘前计划关键锚点
- 盘中快照摘要
- 执行偏差事实
- 信号准确性事实
- 风险使用事实

### Step 2 事实呈现

`investing-os` 负责把事实包按“可讨论顺序”呈现给用户，不新增推断结论。

### Step 3 复盘对话

用户与 `investing-os` 完成结构化对话，按固定问题顺序进行。

### Step 4 判断记录

`investing-os` 把对话结果写成“判断记录”，但这些判断仍分层，不自动升级为经验。

### Step 5 候选筛选

用户明确区分：

- 当日噪声
- 需要后续观察的候选经验
- 可以进入 `LEARNING` 候选队列的候选

### Step 6 归档收尾

只有事实包、判断记录、用户确认结果都已生成且归档成功，才能进入 `DAY_ARCHIVED`。

## 4. 固定对话问题

DAILY-4 对话必须按以下 6 组问题进行，允许压缩措辞，但不允许跳层：

### Q1 事实核对

问题目的：确认当天发生了什么，而不是先解释为什么。

至少覆盖：

- 今天实际做了哪些交易或观察动作
- 哪些标的与盘前计划一致，哪些不一致
- 是否存在明显的数据缺口或事实不确定性

### Q2 判断与计划偏差

问题目的：识别盘前判断是否偏了。

至少覆盖：

- 哪些盘前判断被市场验证
- 哪些盘前判断被市场否定
- 偏差更像是判断问题还是信息不足

### Q3 执行质量

问题目的：识别执行层是否偏离。

至少覆盖：

- 进出场是否按计划执行
- 是否存在临场加减仓、追单、拖延、犹豫
- 是否出现计划外动作

### Q4 仓位与风险

问题目的：识别风险使用是否得当。

至少覆盖：

- 仓位大小是否与计划一致
- 风险暴露是否超过原本授权
- 是否存在止损、容忍区间、例外使用不当

### Q5 情绪与行为

问题目的：记录用户自述，而不是系统替用户做心理诊断。

至少覆盖：

- 当时是否有情绪干扰
- 是否因焦虑、贪婪、报复、怕错过而改变动作
- 用户自己如何描述当时的主观状态

### Q6 经验候选

问题目的：从已确认事实与用户自述里提炼候选，而不是直接定论。

至少覆盖：

- 哪些结论只是今天有效的噪声
- 哪些值得继续观察
- 哪些可以进入 `LEARNING` 候选

## 5. 用户必须确认的判断点

以下 4 类点必须由用户显式确认：

1. 偏差分类
2. 情绪/行为自述是否保留
3. 当日结论中哪些是噪声
4. 哪些候选可以进入 `LEARNING`

没有用户确认，不得把这些内容标记为最终复盘结论。

## 6. 结构化产物边界

DAILY-4 的结构化产物统一分成 4 层。

### Layer A `fact_packet`

只含事实，不含解释：

- trade facts
- position facts
- plan anchors
- intraday observations
- pnl facts
- risk facts
- data gaps

### Layer B `review_judgment`

允许判断，但必须标注来源：

- `judgment_type`: `thesis | execution | sizing | emotion | data_quality`
- `summary`
- `evidence_refs`
- `confidence`: `low | medium | high`
- `source`: `user_confirmed | assistant_inferred`

其中 `assistant_inferred` 只能作为待确认草稿，不能直接成为最终结论。

### Layer C `candidate_lessons`

只允许“候选经验”，不允许写成永久规则：

- `candidate_id`
- `theme`
- `statement`
- `supporting_evidence_refs`
- `requires_followup`
- `user_decision`: `noise | observe | learning_candidate`

### Layer D `archive_closure`

记录收尾状态：

- `review_mode`
- `ibkr_fact_status`
- `user_confirmed_at`
- `archive_manifest_path`

## 7. 正式 schema 最小要求

建议最终文件名：

`investing-os/system/runtime/inputs/{session_id}-daily4-review.json`

最小 schema：

```json
{
  "session_id": "string",
  "trading_date": "YYYY-MM-DD",
  "review_mode": "full_review | quick_review | freeze",
  "ibkr_fact_status": "verified | stale_unverified | missing",
  "fact_packet_refs": ["string"],
  "review_judgments": [
    {
      "judgment_type": "thesis | execution | sizing | emotion | data_quality",
      "summary": "string",
      "evidence_refs": ["string"],
      "confidence": "low | medium | high",
      "source": "user_confirmed | assistant_inferred"
    }
  ],
  "candidate_lessons": [
    {
      "candidate_id": "string",
      "theme": "string",
      "statement": "string",
      "supporting_evidence_refs": ["string"],
      "requires_followup": true,
      "user_decision": "noise | observe | learning_candidate"
    }
  ],
  "user_confirmations": {
    "bias_classification_confirmed": true,
    "emotion_notes_confirmed": true,
    "noise_vs_candidate_confirmed": true,
    "learning_candidates_confirmed": true
  },
  "archive_closure": {
    "archive_manifest_path": "string",
    "user_confirmed_at": "ISO-8601"
  }
}
```

## 8. `stock_team` 与 `investing-os` 职责边界

### `stock_team` 允许输出

- 成交、持仓、价格、计划对照、执行偏差、风险使用等事实
- 缺失数据与来源警告

### `stock_team` 禁止输出

- 用户心理归因
- “今天最大的教训”这类认知结论
- thesis 升降级建议
- 可直接进入 `LEARNING` 的经验判断

### `investing-os` 允许输出

- 基于事实包的讨论引导
- 偏差分类草稿
- 候选经验草稿
- 用户确认后的结构化复盘记录

### `investing-os` 禁止输出

- 在没有用户确认时，把推断写成最终结论
- 在 `ibkr_fact_status != verified` 时宣称正式复盘完成

## 9. 降级与阻断规则

### 9.1 `quick_review`

只允许写最小复盘记录，不生成完整 `candidate_lessons` 列表；至多记录：

- 持仓异常
- 风险偏离
- 待处理警告
- 用户是否接受快速收尾

### 9.2 `freeze`

不生成正式 `review_judgments` 和 `candidate_lessons`，只生成欠账记录。

### 9.3 IBKR 不可用

若正式成交事实不可用：

- 可展示 `stale_unverified` 缓存
- 可完成对话草稿
- 不得标记 `full_review` 完成
- 不得进入正式 `LEARNING` 候选

## 10. 对低阶模型的约束

低阶模型后续只允许实现：

- 结构化产物 schema
- 持久化路径
- 校验器
- 最小 CLI / coordinator 接线
- 对应测试

低阶模型不得自行修改：

- 6 组复盘问题
- 用户确认点
- 四层结构边界
- `stock_team` / `investing-os` 的职责边界

## 11. 本契约后的执行顺序

```text
H4 高阶契约
-> H4-L1 结构化产物骨架
-> H4-L2 quick_review / freeze 最小记录
-> H4-L3 full_review 接线与测试
-> 高阶复核
```
