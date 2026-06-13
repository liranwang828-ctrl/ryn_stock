# 统一投资操作系统架构

日期：2026-06-13

状态：设计已确认，等待书面规格审阅

英文原版：[2026-06-13-unified-investing-operating-system-architecture.md](2026-06-13-unified-investing-operating-system-architecture.md)

## 1. 目的

在不重写 `investing-os` 和 `stock_team` 的前提下，将两个现有系统组合成一个个人投资产品。

系统首先优化认知进化。收益、回撤与风险结果用于检验决策质量，但不能成为工具或模型取代用户判断的理由。

用户面对一个系统，内部保留两个受约束的内核：

- `investing-os`：认知、意义、治理、计划、复盘与学习。
- `stock_team`：证据采集、计算、回测与事实输出。

两个内核位于同一仓库，共同开发和测试，同时通过明确的职责与数据契约保持边界。

## 2. 设计原则

1. 一个产品、一个用户入口，内部职责模块化。
2. 复用已有命令、Packet、工作流、Dashboard 和测试。
3. 新增薄协调器，不再实现第二套业务逻辑。
4. 严格约束阶段依赖，但不强迫用户每天走完整交易流程。
5. 自动化数据与计算工作；涉及意义、权限、例外和教训吸收时必须停下来确认。
6. 实盘数据默认失败关闭。降级证据只允许用于研究、演练或用户确认后的观察模式。
7. 保存重要状态变化与决策谱系。

## 3. 必须保留的现有能力

### 3.1 Investing OS

保留：

- 认知记录与个人模式
- 决策规则、风险预算、战术状态与计划
- 盘前、盘中、盘后及研究工作流
- Packet 模板与 brain-muscle 边界契约
- promotion queue、lesson lineage 与 traceability 索引
- `dashboards/operating-console.html`
- `dashboards/growth-dashboard-draft.html`

Operating Console 继续作为认知系统首页。Growth Dashboard 继续展示认知结构、经验谱系、能力变化和报告。每日工作流界面不能替代它们。

### 3.2 Stock Team

以下现有命令通过协调器复用：

- `market-context`
- `premarket`
- `intraday-snapshot`
- `intraday-dashboard`
- `trade-evidence`
- `company-packet`
- `industry-packet`
- `stage-context-backtest`
- `tactic-backtest`

底层数据适配器、指标计算、缓存、回测引擎、Packet 渲染器和现有 CLI 测试同样保留。

### 3.3 现有契约

继续使用：

- brain-muscle handshake protocol
- Stock Team CLI contract 与 Evidence Packet header
- 已批准规则使用的 runtime snapshot contract
- degraded-mode schema
- traceability schema 与索引

协调器只新增工作流状态，不替代上述契约。

## 4. 目标架构

```text
用户
  |
  +-- Operating Console / Daily Workspace / Growth Dashboard
  +-- 对话
  |
Session Router + Workflow Coordinator
  |
  +-- Investing OS 认知与治理内核
  +-- Stock Team 证据与计算内核
  |
Packets + Runtime Snapshots + Traceability + Dashboard Manifest
```

### 4.1 交互层

混合入口由两部分组成：

- Dashboard：展示状态、数据健康、阻塞、欠账、产物和合法动作。
- 对话：负责解释、异议、焦点选择、权限、计划批准、复盘与教训批准。

Dashboard 按钮与自然语言请求必须转换为相同的协调器动作契约。

### 4.2 Session Router

路由器在创建状态前识别活动类型：

- `trading`
- `observation`
- `research`
- `review`
- `maintenance`

没有活动的日期无需生成文件。研究或讨论不能自动创建交易会话，除非用户明确准备进入交易流程。

### 4.3 Workflow Coordinator

协调器是唯一的工作流控制者，负责：

- 状态转换和前置条件检查
- 调用现有 Stock Team CLI
- 工具超时、重试和错误分类
- 人工确认闸门
- 产物登记与哈希
- 跨日恢复
- 生成只读 Dashboard manifest

协调器不负责行情计算、认知、策略意义或交易执行，也不得下单或输出最终买入、卖出、持有指令。

## 5. 会话模型

### 5.1 交易会话

完整交易会话可经过：

```text
IDLE
-> DAY_INITIALIZED
-> STAGE0_READY
-> DISCUSSION_REQUIRED
-> FOCUS_CONFIRMED
-> STAGE1_READY
-> PLAN_CONFIRMATION
-> INTRADAY_ACTIVE
-> MARKET_CLOSED
-> REVIEW_REQUIRED
-> DAY_ARCHIVED
```

这是依赖关系图，不是每天必须完成的清单。

规则：

- 实盘 Stage 1 必须基于同日有效 Stage 0 和用户确认的焦点池。
- 没有已批准计划时，盘中只能进入观察模式。
- 盘中刷新只能更新运行事实，不能重新生成 Stage 0、Stage 1 或已批准计划锚点。
- 无交易日可以用简短的无交易记录结束，不制造虚假交易复盘。

### 5.2 其他会话类型

- Observation：可以刷新市场事实，但不存在新增交易授权。
- Research：独立于当日交易的公司、行业、因子或战术研究。
- Review：复盘过去的交易、阶段、行为模式或历史案例。
- Maintenance：数据修复、契约检查、回测和系统维护。

### 5.3 横向状态

- `BLOCKED_DATA`：实盘必需证据无效或缺失。
- `WAITING_USER`：正在等待人工确认。
- `DEGRADED_OBSERVE`：用户批准使用降级证据进行观察。
- `FAILED_TOOL`：工具失败，恢复信息已记录。

这些状态保留上一个有效阶段，不能静默推进。

## 6. 每日交易流程

### 6.1 初始化

输入：

- 市场日期与交易日历
- 可用的当前持仓和暴露事实
- 活跃观察池与已研究候选
- 当前权限与风险快照

输出：交易会话状态及 brain-owned universe request。

### 6.2 Stage 0

复用 `python -m stock_team.cli market-context`。

Packet 必须明确包含 as-of 时间、时区、市场窗口、来源、时效、缺失数据和警告。实盘流程要求证据来自该交易日美东时间 09:30 前。

无效、开盘后、陈旧或缺失的实盘数据进入 `BLOCKED_DATA`。用户可以明确选择降级观察，但降级证据不能授权风险。

### 6.3 认知讨论

用户与 Investing OS 解释 Stage 0，讨论权限和优先级，并确认焦点池。讨论记录必须区分事实、假设、分析和用户判断。

输出：有版本的焦点决策与 Stage 1 decision sheet。

### 6.4 Stage 1

复用 `python -m stock_team.cli premarket`。

命令读取同日 canonical Stage 0 产物和已确认 decision sheet，计算证据与规则碰撞，但不能授予权限。

输出：`plan-evidence-packet.md` 及对应产物登记。

### 6.5 计划确认

Investing OS 生成包含权限、风险预算、允许与禁止事项、例外以及预授权条件的计划。用户批准具体版本后，会话才能进入活动状态。

### 6.6 盘中

复用 `intraday-snapshot` 和 `intraday-dashboard`。

只刷新价格、VWAP 或关键位置、条件状态、数据健康、持仓、账户暴露、警告及时效等事实。盘中循环不得运行回测，也不得生成 Stage 0/1。

### 6.7 盘后

复用 `trade-evidence` 和现有盘后工作流。系统准备事实、复盘草稿、开放问题与候选教训。用户决定结果的意义以及是否吸收教训。

## 7. 跨日恢复

未完成的前一日不能把用户困在过期会话中。

当新交易日开始，而昨日仍为 `INTRADAY_ACTIVE` 或 `REVIEW_REQUIRED` 时，协调器可以预取今日 Stage 0，但未经用户确认不能冻结昨日。

Dashboard 提供三个选择：

1. 快速复盘后开始今天（推荐）。
2. 确认冻结昨日，稍后完整复盘。
3. 先完成完整复盘，再开始今天。

快速复盘至少检查：

- 成交与日终持仓是否一致
- 是否明显偏离已批准计划
- 是否存在未解决的账户、杠杆或风险问题

选择 1 后，昨日状态变为 `QUICK_REVIEWED`；选择 2 后变为 `CLOSED_UNREVIEWED`，并创建带日期的欠账任务；选择 3 进入完整复盘。在用户选择前，昨日保持 `REVIEW_PENDING`。

普通复盘欠账不阻塞今日 Stage 0。未解决的持仓、账户、杠杆或严重规则风险，会成为今日计划批准前必须完成的风险检查。

## 8. 研究与学习旁路

研究可随时进行，并与活动交易计划隔离：

```text
主脑定义问题与证伪条件
-> Stock Team 生成证据或回测
-> 认知讨论与冲突检查
-> 候选队列
-> 用户批准
-> Investing OS 吸收并更新谱系
```

现有入口映射：

| 用途 | 现有命令 | Investing OS 落点 |
|---|---|---|
| 公司研究 | `company-packet` | dossier / thesis candidate |
| 行业研究 | `industry-packet` | industry dossier / sector map |
| 宏观或阶段验证 | `stage-context-backtest` | factor / gate evidence |
| 盘中战术验证 | `tactic-backtest` | tactic validation record |
| 交易复盘 | `trade-evidence` | journal / case / lesson candidate |

所有结果默认为 `candidate_only`。批准后的规则最早从下一次新交易会话开始生效，并记录版本与来源谱系。研究可以提醒用户重新审视活动计划，但不能修改计划。

## 9. Dashboard 架构

### 9.1 Operating Console

保留 `investing-os/dashboards/operating-console.html` 作为产品首页。

保留权限、下一步、证据缺口、路由、Packet 和待处理教训，并新增：

- 当前会话类型与状态
- 主要及备选合法动作
- 当前阻塞与恢复动作
- 跨日复盘欠账
- Daily Workspace 与近期产物链接

其数据应从手工维护逐步迁移到统一 manifest。

### 9.2 Growth Dashboard

保留 `growth-dashboard-draft.html` 的认知地图、经验谱系、能力雷达、报告归档和当前任务。在 traceability 索引支持时，增加候选审查状态。该页面不控制交易流程。

### 9.3 Daily Workspace

新增专注于 Stage 0、讨论准备、Stage 1、计划状态、盘中证据、跨日恢复和复盘入口的每日工作台。

### 9.4 Evidence View

Stock Team 证据 Dashboard 作为详情页复用。它不是另一个产品首页，也不能做决策。

第一阶段继续使用现有静态 HTML/JavaScript，通过生成 JSON manifest 增强。大型前端重写不在范围内。

## 10. 数据契约

### 10.1 Session State

新增交易与活动会话 schema。交易状态至少包括：

```json
{
  "session_id": "trading-2026-06-15",
  "session_type": "trading",
  "market_date": "2026-06-15",
  "state": "STAGE0_READY",
  "state_version": 7,
  "artifacts": [
    {"role": "stage0", "path": "...", "sha256": "..."}
  ],
  "data_quality": {"status": "production_ready", "warnings": []},
  "pending_confirmations": [],
  "allowed_actions": [],
  "backlog_links": [],
  "last_error": null,
  "updated_at": "..."
}
```

运行状态存放于 `investing-os/system/runtime/`，与已批准规则及 Evidence Packet 分离。

### 10.2 Coordinator Action

Dashboard 与对话使用同一种动作格式：

```json
{
  "intent": "start_stage0",
  "session_id": "trading-2026-06-15",
  "expected_state": "DAY_INITIALIZED",
  "user_confirmation": false,
  "parameters": {},
  "idempotency_key": "..."
}
```

协调器拒绝过期的 `expected_state` 和未经授权的状态转换。

### 10.3 Dashboard Manifest

只读 manifest 投影会话状态、证据健康、当前权限快照、合法动作、欠账和产物链接。它不含凭据，也不能成为第二个状态权威来源。

## 11. 鲁棒性与错误处理

- 动作必须幂等，重复点击或重试不能重复生成产物或状态变化。
- 状态更新使用 `state_version` 乐观锁。
- 每个会话同时只能有一个写状态任务。
- 文件先写临时路径，验证通过后再原子替换。
- 所有工具调用都有超时与重试策略。
- 网络或临时供应商错误可以重试；契约错误和人工闸门不能自动重试。
- 错误状态记录命令、输入版本、错误类别、是否可重试以及最后有效状态。
- 页面刷新、模型切换或进程重启后，从状态文件恢复并验证已登记产物哈希。

数据质量等级：

- `production_ready`
- `degraded`
- `stale`
- `missing`

只有 `production_ready` 可以在无需额外用户动作时推进实盘依赖。

## 12. 安全与所有权

- 协调器与 Stock Team 都不能下单。
- Stock Team 可以写证据和运行输出，但不能写 cognition 或 decision 文件。
- 只有用户批准的 adoption 动作可以把候选教训或规则写入长期认知和决策文件。
- 凭据、原始账户导出和敏感 broker 状态保留在本地并排除出 Git。
- 每次状态变化记录触发动作、输入版本、产物哈希、时间及必要的确认记录。
- 低阶模型可以实施范围明确的任务并提交候选项，但不能重新解释系统边界，也不能批准交易或学习状态。

## 13. 验收场景

1. 生产数据通过现有命令完成 Stage 0 到复盘闭环。
2. Stage 0 数据缺失时阻断实盘，并提供降级观察选项。
3. 只讨论公司时创建研究活动，不创建交易会话。
4. 无交易日可以正常关闭，不制造交易复盘。
5. 昨日未复盘时提供三个选择，不能自动冻结。
6. 等待昨日选择期间，可以预取今日 Stage 0。
7. 未解决的重大风险阻塞今日计划批准，但不阻塞 Stage 0。
8. 工具超时可见、可重试，且不重复产物。
9. 重复 UI 动作只产生一次状态变化。
10. 页面或模型重启后恢复相同状态与产物。
11. 回测结果进入候选队列，但不改变今日计划。
12. 用户批准教训后更新目标文件、谱系索引和 Growth Dashboard 数据。
13. 现有 Operating Console 与 Growth Dashboard 内容继续可用。
14. 协调器接入后，现有 CLI contract tests 继续通过。

## 14. 实施阶段

该架构必须拆成可独立审查的计划和变更，不能一次性整体实施。

### Phase 1：协调器基础

- session 与 action schema
- 状态存储与转换验证
- coordinator CLI
- 现有 Stock Team 命令适配器
- 幂等、原子写入和针对性测试

### Phase 2：统一交互

- Dashboard manifest
- Operating Console 接入
- Daily Workspace
- 跨日恢复选项
- 重启与重试行为

### Phase 3：实盘主链

- 生产级 Stage 0 collector
- 生产数据质量闸门
- Stage 0 到盘后的端到端验证
- 在验证通过前保留原始源目录，不进行删除

### Phase 4：研究与学习集成

- activity session
- 候选队列适配器
- 批准与吸收动作
- traceability 与 Growth Dashboard 刷新

### Phase 5：运行强化

- 在有价值的场景增加后台调度
- IBKR 运行时集成
- 数据供应商韧性与可观测性
- 更广泛的集成和恢复测试

## 15. 不在范围内

- 自动下单
- 自动决定交易权限
- 自动吸收教训
- 替换现有 CLI 业务逻辑
- 大型前端框架重写
- 在盘中实时刷新循环里运行回测或优化
- 在运行闭环稳定前进行全面因子优化

## 16. 低阶模型实施约束

每个实施任务必须明确：

- 要复用的具体文件与命令
- 允许修改的具体文件
- 输入与输出契约
- 禁止行为与所有权边界
- 要新增或运行的测试
- 覆盖的验收场景

实施模型不得重新设计架构、重命名既有契约或擅自合并阶段。遇到歧义或契约冲突时，必须交回高阶模型审查，不能自行发明解决方案。
