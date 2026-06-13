# 个人投资 OS (investing-os) 与多智能体量化系统 (stock_team) 融合重构计划 (安全迁移版)

本计划旨在打破量化系统 `stock_team` 的扁平化文件结构与强文件依赖，将属于“认知、规则与记忆”的部分以“渐进式迁移 (Phased Migration)”的方式安全移入个人投资操作系统 `investing-os`。

根据 Codex 的 Review 意见，本方案抛弃了激进的即时删除，改用 **盘点 -> 复制/暂存 -> 规范化吸收 -> 运行时快照导出 -> 引擎重构 -> 授权归档与清理** 的安全路径，并强化了运行时解耦与代码级 AI 越权控制。

---

## User Review Required

> [!IMPORTANT]
> **资产零即时删除 (P0)**：严禁在迁移初期删除 `stock_team` 中的任何资产（包含原则、案例、研报及脚本）。所有历史资产均属于认知足迹，必须先复制到 `investing-os` 暂存，经过规范化重写与验证后，方可在用户明确输入“**同意清理**”后进行归档或删除。

> [!WARNING]
> **运行时物理去耦 (P1)**：`stock_team` 的 Python 运行时绝不直接依赖/读取 `investing-os` 的原始 Wiki 文件。我们将采用**“快照导出 (Snapshot Export)”**机制：`investing-os` 拥有原则与纪律的治理权，仅在规则变更时向 `stock_team` 导出经过 Schema 校验的只读 JSON 运行快照（如 `tactical_rules.json`），实现完全去耦。

> [!NOTE]
> **纪律定性与参数定量分离 (P1)**：原则文件（如止盈冷却）在 `investing-os` 中保留纯定性的纪律意图；而其对应的具体数字（如冷却 15 分钟）作为运行参数隔离在 JSON 快照中，并在适用时通过回测系统进行科学的扫频论证，严禁盲目硬编码。

> [!CAUTION]
> **无计划时 Fail-Safe 降级 (P1)**：当用户因时间不固定而缺失今日盘前计划或 checklist 时，`stock_team` 必须进入**“只读监控与风险告警”**的降级模式，此时系统**禁止产生或推荐任何新的主动交易订单**，防止“无计划盲目交易”的 Fail-Open 风险。

> [!IMPORTANT]
> **代码级 AI 边界防御 (P2)**：大模型的行动边界隔离不仅依赖 Markdown 政策约束，还必须在 `stock_team` 的代码层进行强制防御：默认只读模式、所有落盘写入均通过 CLI 命令层进行 Schema 校验、状态机转换增加底层代码校验（防止幻觉通过）。

---

## Proposed Changes

### Phase 0: 资产盘点 (Inventory Only)
*   **目标**：在不移动或删除任何文件的前提下，理清两套系统的物理边界与全部文件资产。
*   **行动**：
    1.  定位当前活跃的 `stock_team` 目录与 `investing-os` 目录。
    2.  对 `stock_team` 目录下的所有原则、案例、行业研报、用户反思、辅助脚本和配置文件生成一份完整的 `inventory_manifest.json` 资产清单。
    3.  将清单中的文件分类为：定性认知、CIO 研究、交易反思、运行配置、执行代码、临时数据。

### Phase 1: 制定导入契约 (Define Import Contracts)
*   **目标**：在 `investing-os` 中建立规范的准入机制，防止低质量文档堆积。
*   **行动**：
    1.  创建临时暂存目录 `wiki/inbox/` 及其 [README.md](file:///C:/Users/rriww/Documents/investing-os/wiki/inbox/README.md)，规定未经重构的源资产一律先存放在此。
    2.  在 [wiki/principles/README.md](file:///C:/Users/rriww/Documents/investing-os/wiki/principles/README.md) 中制定 `PRIN-[编号]-[英文短命名].md` 原则模板，要求包含：唯一标识、核心断言、触发条件、执行约束及偏离审计条件（去阈值化）。
    3.  在 [wiki/historical-cases/README.md](file:///C:/Users/rriww/Documents/investing-os/wiki/historical-cases/README.md) 中制定 `CASE-[编号]-[事件简述].md` 案例模板，包含：基本数据、事实经过、主观心理剖析、客观量化审计及关联原则链接。

### Phase 2: 复制暂存入收件箱 (Copy Into Inbox)
*   **目标**：保留原始文件的时间戳和完整性，将资产安全复制到 `investing-os`。
*   **行动**：
    1.  将 `stock_team/docs/wiki/principles/` 目录下的所有中文原则文件，**复制**到 `investing-os/wiki/inbox/principles/` 下。
    2.  将 `stock_team/docs/wiki/cases/` 下的所有中文案例，**复制**到 `investing-os/wiki/inbox/cases/` 下。
    3.  将 `stock_team/findings/` 下的所有行业与个股研究报告，**复制**到 `investing-os/wiki/inbox/reports/` 下。
    4.  **注意**：此阶段严禁修改或删除 `stock_team` 下的源文件。

### Phase 3: 标准化结构吸收 (Structure and Absorb)
*   **目标**：将收件箱（inbox）中的原始文件标准化，转化为 `investing-os` 的永久认知资产。
*   **行动**：
    1.  **吸收原则**：将暂存原则重写并定性化，剔除未验证的硬编码数字，保存为永久文件：
        *   `PRIN-001-leveraged-tool-discipline.md` (杠杆产品强制 OCO 规则)
        *   `PRIN-002-hand-feel-trade-limit.md` (手感仓时间窗口与限额规则)
        *   `PRIN-003-profit-taking-cooling-period.md` (止盈冷却防后悔规则)
        *   `PRIN-004-sector-sympathy-rules.md` (板块 sympathy 补涨辨析规则)
        *   `PRIN-005-vwap-volume-rules.md` (VWAP 与量能确认规则)
    2.  **吸收案例**：将暂存案例重写为 `CASE-001`、`CASE-002`、`CASE-003` 等规范文档，并与定性原则建立双向 Markdown 链接。
    3.  **吸收研报与反思**：重写研报为长期公司笔记，归档入 `wiki/companies/` 和 `wiki/industries/`，反思归入 `wiki/journals/`。

### Phase 4: 运行时快照导出 (Export Runtime Snapshots)
*   **目标**：通过数据快照，建立两套系统间的单向、松耦合直连协议。
*   **行动**：
    1.  在 `investing-os/system/data/` 下定义运行快照的 JSON Schema 契约（定义 `tactical_rules.json` 格式，区分定性意图与定量阈值参数）。
    2.  将原则中的定量数值参数（如偏离度阈值、冷却时间值）提取到快照中。
    3.  建立手动/脚本触发机制，将经过校验的快照导出并复制到 `stock_team/config/` 下，供引擎读取。

### Phase 5: 重构量化执行器 (Refactor stock_team)
*   **目标**：使 `stock_team` 降级为无状态计算与执行器，强化 Fail-Safe 机制与 AI 防御。
*   **行动**：
    1.  **参数解耦**：重构 `poll.py` 和 `session_manager.py`，禁止读取任何 `investing-os` 原生 Wiki，强制仅载入 `config/tactical_rules.json` 快照。
    2.  **无状态与降级**：实现降级监控逻辑。若检测到今日 `daily_plan.json` 缺失，系统禁止报错，自动切换为只读告警模式，**禁止任何 discretionary 交易单 drafting**。
    3.  **AI 代码隔离**：在 `session_manager.py` 和底层命令中实现：
        *   对大模型修改 State 的请求实行强 Schema 校验，且必须通过物理 CLI（如 `entry_guard.py`）调用写入。
        *   状态机跳转必须由代码进行前置校验。
    4.  **测试分层重构**：将平铺的测试文件收纳到 `tests/unit/core/`、`tests/unit/agents/`、`tests/unit/sop/` 和 `tests/integration/`。
    5.  **脚本收纳**：建立 `scripts/legacy/`，将不活跃的遗留脚本收纳。

### Phase 6: 备份归档与用户审批清理 (Archive/Delete After Approval)
*   **目标**：在系统稳定运行后，安全清理历史冗余资产。
*   **行动**：
    1.  对已迁移的 `stock_team` 原 Wiki 进行压缩备份，移入 `stock_team/archive/`。
    2.  进行重构后的自动化测试验证与场景降级人工测试。
    3.  **向用户提交迁移与测试报告，在获得用户“同意清理”指令后，再物理删除 stock_team 下的冗余 Wiki 文件和 legacy 脚本。**

---

## Verification Plan

### Automated Tests
*   **单元测试**：`python -m pytest tests/unit/core/ -q` (验证数据源与数学因子)
*   **原则载入测试**：`python -m pytest tests/unit/agents/ -q` (验证快照参数成功载入，且原则定性校验无误)
*   **状态机控制测试**：`python -m pytest tests/unit/sop/ -q` (验证缺少规划文件时的降级保护机制)

### Manual Verification
1.  **无盘前规划降级测试**：临时隐藏 `daily_plan_*.json` 运行 `python agents/poll.py`，验证系统是否转为 Read-Only 降级监控模式，并确保没有产生任何 discretionary 订单。
2.  **大模型越权拦截测试**：在 Brainstorm 模式下模拟向大模型发出修改持仓 JSON 的指令，验证底层代码防御是否硬性拦截该写入操作并报错。
