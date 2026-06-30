# DAILY-AUDIT-1 盘前决策事实审计

## 审计元数据

- Base commit: c1024c3b67a213eea0419cccd486eef84907e673
- Branch: codex/repository-cleanup-20260630
- Allowed scope respected: yes

## 握手链

| 顺序 | 统一名称 | 旧代码名称 | 用户是否必须交互 | 输入 | 输出 | 证据等级 |
|---:|---|---|---|---|---|---|
| 1 | 市场范围与事实请求 | `start_stage0` / Node 1 Stage 0 | 否（investing-os 必须预先构建 universe 文档） | `--universe`（脑端 universe JSON，含 source_inputs.positions / prior_review / cognition_state / permission_state_before_open / forbidden_actions）、`--date`、`--as-of`（ISO timestamp with timezone，对应的 snapshot JSON） | `pre-market-snapshot` JSON + `pre_market_environment_packet` Markdown | test-covered |
| 2 | 市场环境证据包 | Evidence Stage 0 产出 | 否（stock_team 仅生成事实包，不涉及决策） | 步骤 1 产出的 snapshot JSON + universe JSON | `pre_market_environment_packet` .md（含 QQQ/SPY/IWM/VIXY 行情、sector heat、universe relevance map、catalysts、missing_data） | test-covered |
| 3 | 环境解释与焦点池确认 | `record_focus_confirmation` | 是（`requires_confirmation` 为 true，必须 `user_confirmation` 字段为真） | 步骤 2 产出的 market context packet + 用户对话中的关注标的/排除标的/risk mode 声明 | `trading-YYYY-MM-DD-stage0-discussion-notes.md` + `trading-YYYY-MM-DD-stage1-decision-sheet.json`（含 focus_symbols / excluded_symbols / risk_mode / allowed_tactics / forbidden_actions / user_confirmed） | code-only |
| 4 | 焦点标的证据包 | `start_stage1` / Evidence Stage 1 | 否（stock_team 仅为已确认焦点池计算事实与规则碰撞） | `--context-packet`（步骤 2 产出路径）+ `--decision-sheet`（步骤 3 产出路径） | `plan_evidence_packet` .md（含 brain decision echo、symbol factor calculations、requested formula outputs、rule collision results、missing_data、warnings） | test-covered |
| 5 | 权限与风险计划 | `record_plan_approval`（计划撰写阶段） | 是（`requires_confirmation` 为 true） | 步骤 4 产出的 plan evidence packet + 当前 permission state + 用户确认 | `trading-YYYY-MM-DD-trading-plan.json` + `trading-YYYY-MM-DD-intraday-guidance.json`（含 risk_mode / allowed_actions by symbol / forbidden_actions / invalidation conditions / intraday checks） | code-only |
| 6 | 计划版本批准 | `record_plan_approval`（批准确认阶段） | 是（与步骤 5 共享同一 intent，`user_confirmation` 必须为 true） | 步骤 5 产出的 trading-plan.json + 用户最终批准 | 状态跃迁至 `PLAN_APPROVED` + 产物哈希存入 session artifact ledger | code-only |

## 数据真实性检查

| 项目 | 实现位置 | 测试位置 | 当前证据 | 缺口 |
|---|---|---|---|---|
| as-of 与时区 | `stock_team/cli.py` `_validate_stage0_as_of()` L118-128；`_parse_stage0_as_of()` L101-116 | `test_cli_market_context_rejects_post_open_as_of` | 强制 `--as-of` 包含时区偏移、转换为 `America/New_York`、日期必须等于 `--date`、时间必须早于 09:30 ET | 时区回退到 UTC 的 fallback 分支（L115）未测试：when `zoneinfo.ZoneInfo` 不可用时，系统回退到 UTC 而非报错 |
| 盘前窗口 | `_validate_stage0_as_of()` L126-127；`_is_premarket_stage0_row()` L130-142；`_fetch_polygon_premarket_bars()` L302-303 | `test_cli_market_context_rejects_post_open_as_of` | 窗口定义为 04:00-09:29:59 ET；`window` 字段必须为 `pre_market_before_09_30_ET`；拒绝 09:30:00 及之后的时间戳 | 盘前窗口开始时间（04:00 ET）为硬编码，未在协议文档中显式约定 |
| provider/source | Handshake Protocol `brain-muscle-handshake-protocol.md` L55-73；`_fetch_paid_premarket_row()` L347-415；`_history_context()` L682-763 | 无独立 provider 优先级测试 | 优先级链：Polygon 1m aggregates → Polygon snapshot → Polygon daily aggs → Polygon cache (fresh <1hr) → yfinance → stale cache；每个产出必须声明 `data_sources` 和 `fallback` | protocol 文档声明 IBKR 为第二优先级，但盘前 snapshot / market-context 路径中未见 IBKR 调用；`premarket` 命令（Stage 1）硬编码 yfinance 为 intraday snapshot 的数据源（L1825），未见 Polygon 调用 |
| degraded/stale/missing | `_history_context()` L682-763；`handle_market_context()` missing 列表；`handle_premarket()` warnings 列表 | 无独立 degraded 路径测试 | 存在三级降级链（Polygon → yfinance → stale cache），每级均向 missing/warnings 追加条目；handshake protocol 要求 `stale:` 字段在 `data_sources` 中揭露 | protocol 要求 `missing_data` 解释为何首选源不可用，但代码中缺失时仅写入符号级标签（如 `MU_polygon_failed`），未解释根因 |
| 焦点池限制 | Handshake Protocol L204-209；`_brain_precondition_state_quality()` L615-646 | 无独立焦点池限制测试 | 脑端必须提供由 positions/watchlist/researched names 构成的 universe；market-context 未限制 universe 条目数量上限；Stage 1 仅处理决策单中的 focus symbols | 无显式最大焦点池数量限制；`handle_premarket()` 在 decision sheet 不存在时回退到 watchlist 全量（L1159），可能绕过焦点池确认步骤 |

## 固定产物与 schema

| 产物 | 当前路径 | schema/模板 | 生产者 | 验证方式 |
|---|---|---|---|---|
| Pre-Market Snapshot JSON | 由 `--out` 参数指定（adapters.py 推断为 `pre_market_snapshot.json`） | `_generate_premarket_snapshot_payload()` 定义：{as_of_et, window, markets, themes, focus_symbols, catalysts, notes, missing_data} | `premarket-snapshot` CLI 命令 | CLI 命令成功返回 + 文件存在性检查 |
| 市场环境证据包 | 协议指定：`C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`；代码中 `handle_premarket()` 备选搜索 `stock_team/findings/pre_market_environment_packet.md` | `print_yaml_header()` L47-82 定义 front matter；包体含 6 节（market context、sector heat、universe quality、universe relevance map、catalysts、missing data） | `market-context` CLI 命令 | Adapter 检查文件存在性；无 schema 校验 |
| Stage 0 讨论笔记 | 代理文档指定：`system/runtime/inputs/trading-YYYY-MM-DD-stage0-discussion-notes.md` | 未找到已实现模板 | `record_focus_confirmation` intent（仅记录路径，不由 CLI 生成） | 无自动验证；由 investing-os 负责写入 |
| Stage 1 决策单 | 代理文档指定：`system/runtime/inputs/trading-YYYY-MM-DD-stage1-decision-sheet.json` | 代理文档定义最小 shape：{date, source_stage0_packet, focus_symbols, excluded_symbols, risk_mode, allowed_tactics, forbidden_actions, user_confirmed, notes} | `record_focus_confirmation` intent（仅记录路径，不由 CLI 生成） | 无自动 schema 校验 |
| 焦点标的证据包 | `--out` 参数指定（默认由 adapter 传入） | `handle_premarket()` L1521-1675 定义：YAML front matter + 7 节（input summary、market context echo、brain decision echo、factor calculations、formula outputs、rule collisions、missing/warnings/forbidden check） | `premarket` CLI 命令 | Adapter 检查文件存在性；无 schema 校验 |
| 交易计划 | 代理文档指定：`system/runtime/inputs/trading-YYYY-MM-DD-trading-plan.json` | Risk Boundary Agent 文档定义：{risk_mode, allowed_actions by symbol, forbidden_actions, invalidation_conditions, intraday_checks} | `record_plan_approval` intent（仅记录路径，不由 CLI 生成） | 无自动验证 |
| 盘中指导 | 代理文档指定：`system/runtime/inputs/trading-YYYY-MM-DD-intraday-guidance.json` | 未在代码中找到 schema 定义；`handle_intraday_dashboard()` 期望 guidance JSON 含 symbols / derived_from / date | `record_plan_approval` intent（仅记录路径） + `intraday-dashboard` CLI 消费 | `handle_intraday_dashboard()` 在 guidance 文件不存在时退化为硬编码路径 |

## 状态与动作映射

| state/action | 业务含义 | 是否需要用户确认 | 测试证据 | 冲突 |
|---|---|---|---|---|
| `DAY_INITIALIZED` → `start_stage0` | 初始化交易日，请求 stock_team 收集市场环境事实 | 否 | `test_transitions.py` 覆盖 | 无 |
| `STAGE0_RUNNING` → (success) → `STAGE0_READY` | stock_team 生成市场环境证据包完成 | 否 | `test_transitions.py` 覆盖 SUCCESS_TRANSITIONS | 无 |
| `STAGE0_READY` → `record_focus_confirmation` | 用户与 investing-os 解释环境、确认或调整焦点池 | 是（`CONFIRMATION_ACTIONS`） | `test_transitions.py` 覆盖 CONFIRMATION_ACTIONS 常量 | agent 文档 `pre-market-planning-agent.md` 要求 `user_confirmed: true` 才可写决策单；`transitions.py` 强制执行 `requires_confirmation`，但 adapter 的 `record_focus_confirmation` 分支（L141-144）不执行任何 CLI 命令，仅记录 artifact 路径，未校验 decision sheet 内容 |
| `FOCUS_CONFIRMED` → `start_stage1` | stock_team 仅为已确认焦点池生成标的级证据包 | 否 | `test_transitions.py` 覆盖 | 无 |
| `STAGE1_RUNNING` → (success) → `STAGE1_READY` | 焦点标的证据包生成完成 | 否 | `test_transitions.py` 覆盖 | 无 |
| `STAGE1_READY` → `record_plan_approval` | investing-os 撰写交易计划与盘中指导，用户批准 | 是（`CONFIRMATION_ACTIONS`） | `test_transitions.py` 覆盖 | agent 文档要求 `risk_mode: "observe_only"` 当证据缺失时；`transitions.py` 和 `coordinator.py` 未在状态机层面强制此约束 |
| `FAILED_TOOL` → `retry_last_action` | 适配器执行失败时恢复上一意图 | 否 | `test_coordinator.py` 覆盖 | 无 |

## 测试结果

- Command: `python -m pytest stock_team/tests/unit/orchestration/test_adapters.py stock_team/tests/unit/orchestration/test_coordinator.py stock_team/tests/unit/orchestration/test_transitions.py -q`
- Result: 13 passed, 0 failed
- Command: `python -m pytest -q "stock_team/tests/unit/core/test_cli.py::test_cli_market_context_requires_brain_universe" "stock_team/tests/unit/core/test_cli.py::test_cli_market_context_rejects_post_open_as_of" "stock_team/tests/unit/core/test_cli.py::test_cli_premarket_generation"`
- Result: 3 passed, 0 failed
- Failures: none

## 只陈述事实的结论

- 已有：
  1. `transitions.py` 定义了 7 个状态和 4 个可执行意图的状态机，含 2 个需用户确认的意图（`record_focus_confirmation`、`record_plan_approval`）。所有状态跃迁均通过单元测试。
  2. `adapters.py` 支持 5 个 intent 到 CLI 命令的映射（`start_stage0`、`start_stage1`、`record_focus_confirmation`、`record_plan_approval`、`start_intraday`），其中 `start_stage0` 执行两个顺序命令（snapshot + market-context）。
  3. `coordinator.py` 实现幂等性（idempotency_key 去重）、乐观锁（expected_version 校验）、失败回退（FAILED_TOOL → retry_last_action 含 resume_from_state）。
  4. `cli.py` 中 `_validate_stage0_as_of()` 强制盘前时间窗口（< 09:30 ET）和时区一致性；`_brain_precondition_state_quality()` 校验 universe 文档的必要前置字段。
  5. 数据降级链在 `_history_context()` 中实现为 Polygon → yfinance → stale cache，每一级在 missing/warnings 列表中标记。

- 缺失：
  1. `record_focus_confirmation` 和 `record_plan_approval` 在 adapter 层仅记录文件路径，不执行 CLI 命令，不校验产物内容或 schema。产物由 investing-os 手动写入，不在当前代码库中自动生成或验证。
  2. handshake protocol 声明的 IBKR 数据源优先级（第 2 位）在盘前 `market-context` 和 `premarket` 路径中未见实际调用。Stage 1 `premarket` 命令的 intraday 部分硬编码 yfinance（L1825）。
  3. `handle_premarket()` 在 decision sheet 不存在时回退到 watchlist 全量符号（L1159），无保护机制防止绕过焦点池确认步骤。
  4. 盘前窗口开始时间 04:00 ET 为硬编码，未在协议文档中出现。
  5. Stage 1 证据包对 decision sheet 的解析逻辑（L1164-1196）尝试多种 JSON 形状（`user_confirmed_focus_pool`、`symbols` list、字典型 key），存在形状歧义。
  6. `as-of` 时区回退到 UTC 的分支（L115）未经过测试，zoneinfo 不可用时系统不报错。
  7. 无端到端集成测试覆盖完整的 6 步握手链。

- 冲突：
  1. agent 文档路径约定（`system/runtime/packets/`、`system/runtime/inputs/`）与代码中实际使用的路径不一致。协议文档指定 Stage 0 产出路径为 `C:\Users\rriww\Documents\investing-os\system\data\packets\pre-market-context-packet.md`，但 `handle_premarket()` 备选搜索 `stock_team/findings/pre_market_environment_packet.md`。
  2. `pre-market-planning-agent.md` 要求 6 个讨论问题 + 2 个产出文件；`pre-market.md` 工作流文档列出 11 个步骤；`transitions.py` 将步骤 3-6 压缩为 2 个 confirmation intent。三者描述的粒度不同，无文档解释压缩映射。
  3. `transitions.py` 中 `record_plan_approval` 成功后的 complete_transition 落在 default 分支返回原状态（L44-50），意味着该 intent 完成后状态不自动跃迁——这与 handshake protocol 描述的 "Plan Approval → Intraday Active" 链条不一致。需在 `SUCCESS_TRANSITIONS` 中显式添加映射。

- 需要高阶模型决定：
  1. `record_focus_confirmation` 和 `record_plan_approval` 的产物生成是否应由 CLI 命令自动化，还是保持手动写入模式。
  2. IBKR 数据源在盘前路径中的集成优先级与实现范围。
  3. agent 文档路径约定与代码实际路径的分歧以哪一方为准。
  4. `transitions.py` L44-50 的 complete_transition 对 `record_focus_confirmation` 和 `record_plan_approval` 的回退行为是有意设计还是遗漏。
  5. 焦点池最大数量是否需要显式约束。
