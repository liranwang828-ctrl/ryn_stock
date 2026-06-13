# 核心待办：系统编码与内部数据语言规范化

日期：2026-06-02

## 背景

当前系统存在较明显的编码与展示混用问题：部分 `json/jsonl/md` 文件包含中文、emoji、全角符号和历史乱码；在 Windows PowerShell、Python、HTML 报告、LLM 摘要之间流转时，容易出现不可读内容，导致排查和复盘耗时增加。

核心判断：**机器读写层应统一为英文 ASCII；中文只作为展示层或用户总结层生成。**

## 优先级

P0 / 核心基础设施清理。

原因：影响盘前、盘中、盘后多个流程的可信读写，也影响 agent 交接和低级模型协作。

## 目标状态

- 所有机器读写产物使用英文 key、英文枚举、英文 reason code。
- 机器读写产物避免 emoji、中文标点、全角符号和混合编码文本。
- 人类可读中文由展示层生成，不作为核心事实源。
- 历史乱码文件先归档或只读，不暴力重写，避免损坏交易记录。

## 建议分层

### 1. Machine Layer

范围：

- `config/*.json`
- `knowledge/*.jsonl`
- `learning/*.jsonl`
- `findings/*.json`
- agent 间传递的中间 JSON
- dashboard 数据源 JSON

规范：

- ASCII-only text where practical.
- English field names and enum values.
- Use `reason_codes` instead of long free-form Chinese explanation.
- No emoji.
- No translated text as canonical data.

示例：

```json
{
  "symbol": "COHR",
  "action": "reduce",
  "reason_codes": ["price_in_loss_zone", "relative_strength_lagging"],
  "confidence": 0.62,
  "notes_en": "COHR lags AAOI/LITE and has not reclaimed soft stop."
}
```

### 2. Presentation Layer

范围：

- HTML 报告
- dashboard UI
- 用户最终总结
- 中文复盘文档

规范：

- 可以使用中文。
- 可以由英文事实源翻译生成。
- 不反向作为系统核心输入，除非经过结构化转换。

## 迁移顺序

### Phase 1：盘点，不改代码

由低级 agent 执行：

- 扫描核心热路径文件，列出中文、emoji、乱码、非 ASCII 字符出现位置。
- 输出风险等级和建议迁移顺序。
- 不修改 `agents/`、`scripts/`、`config/`、`findings/`、`knowledge/`、`learning/`。

输出文件建议：

- `docs/encoding_inventory_2026-06-02_zh.md`

### Phase 2：新增规范，不改历史

由高级模型执行：

- 新增 `docs/DATA_LANGUAGE_STANDARD.md`。
- 明确 machine layer / presentation layer 边界。
- 定义 reason code、action enum、status enum 的英文命名规范。

### Phase 3：热路径迁移

由高级模型执行，低级 agent 只做辅助盘点：

- `config/positions.json`
- `knowledge/trading_history.jsonl`
- `learning/*`
- 盘前/盘中/盘后关键 JSON 输出

原则：

- 先迁移 schema 和新写入逻辑。
- 历史文件只做只读兼容或归档。
- 所有交易含义迁移前后必须可验证一致。

### Phase 4：展示层翻译

由高级模型或可视化 agent 执行：

- dashboard/report 从英文数据源生成中文展示。
- 用户需要查看时输出中文解释。
- 中文不得覆盖英文核心事实源。

## 低级 agent 可执行任务

任务名称：编码污染盘点与迁移建议。

允许范围：

- 只读扫描仓库文件。
- 只允许新增 `docs/encoding_inventory_2026-06-02_zh.md`。

禁止范围：

- 禁止修改 `agents/`。
- 禁止修改 `scripts/`。
- 禁止修改 `config/`。
- 禁止修改 `findings/`。
- 禁止修改 `knowledge/`。
- 禁止修改 `learning/`。
- 禁止读取或输出 `.env`。
- 禁止自动替换中文或 emoji。

验收标准：

- 列出高风险文件清单。
- 标注每个文件属于 machine layer 还是 presentation layer。
- 对每个文件给出建议：keep / migrate / archive / high-model-review。
- 不做任何交易逻辑判断。

## 当前决策

本事项进入核心待办，但暂不立即大规模重写历史文件。下一步先让低级 agent 做只读盘点，再由高级模型制定迁移方案和执行热路径改造。
