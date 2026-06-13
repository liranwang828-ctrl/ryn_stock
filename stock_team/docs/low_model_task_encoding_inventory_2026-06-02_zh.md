# 低级模型任务单：编码污染盘点

任务日期：2026-06-02

## 任务目标

盘点仓库中可能导致系统读写不稳定的编码问题，为后续高级模型迁移到“机器层英文 ASCII、展示层中文”的规范做准备。

本任务只做盘点，不做修复。

## 输入范围

允许只读扫描：

- `docs/`
- `config/`
- `knowledge/`
- `learning/`
- `findings/`
- `agents/`
- `scripts/`

禁止读取或输出：

- `.env`
- API key
- 任何凭证文件

## 允许输出

只能新增一个文件：

- `docs/encoding_inventory_2026-06-02_zh.md`

## 禁止修改

低级模型不得修改以下任何路径：

- `agents/`
- `scripts/`
- `config/`
- `knowledge/`
- `learning/`
- `findings/`
- `reports/`
- `*.json`
- `*.jsonl`
- `.env`

## 盘点要求

请列出以下类型问题：

- 非 ASCII 字符。
- emoji。
- 明显乱码，例如 `锛`、`绛`、`鐩`、`鈥` 等 mojibake 特征。
- JSON/JSONL 中作为机器事实源存在的中文长文本。
- 机器枚举值中出现中文，例如 `考虑减仓`、`不入场` 等。
- 混合中英文状态字段。

## 输出格式

在 `docs/encoding_inventory_2026-06-02_zh.md` 中按表格输出：

| priority | file | layer | issue_type | example | recommendation |
|---|---|---|---|---|---|

字段说明：

- `priority`: P0 / P1 / P2
- `file`: 文件路径
- `layer`: machine / presentation / docs / unknown
- `issue_type`: mojibake / emoji / chinese_text / chinese_enum / mixed_encoding / unknown
- `example`: 最短示例，不要长段复制
- `recommendation`: keep / migrate / archive / high_model_review

## 判断标准

P0：

- 会被交易流程直接读取的机器文件。
- 会影响盘前、盘中、盘后决策的 JSON/JSONL。

P1：

- agent 输出、报告数据源、dashboard 数据源。

P2：

- 文档、历史报告、纯展示内容。

## 验收标准

- 不修改任何已有文件。
- 不做交易判断。
- 不提出买卖建议。
- 不输出 API key。
- 遇到不确定内容，写 `high_model_review`。
