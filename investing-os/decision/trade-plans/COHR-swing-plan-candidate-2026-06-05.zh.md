# COHR 条件式波段计划候选

## 基本信息

```yaml
date: 2026-06-05
ticker: COHR
direction: long
time_horizon: swing
status: plan_candidate_pending_user_review
trade_permission: no
source_dossier: wiki/companies/COHR.zh.md
valuation_temperature: wiki/companies/COHR-valuation-temperature.zh.md
```

## 角色

COHR 在本系统中不是最高 beta 进攻工具。

它的角色是：

```yaml
cohr_role_in_system: mainline_carrier_plus_resilient_swing
```

也就是：

- AI 光学主线承接仓
- 相对抗波动的波段仓
- 不默认核心仓
- 不追求比 AAOI 更爆发
- 必须相对 LITE / AAOI / SOXX 不掉队

## Thesis

显性 thesis：

```text
AI 数据中心扩张推动高速光互联需求。
COHR 具备平台级光子能力，可以参与光模块、光器件、InP/EML、CPO、光交换等多个瓶颈。
但 COHR 只有在市场奖励平台宽度，并且它不相对 LITE / AAOI / SOXX 掉队时，才是合格波段表达。
```

为什么是 COHR，而不是其他光学表达：

- 相比 AAOI：COHR beta 可能更低，财务质量和平台宽度更好。
- 相比 LITE：COHR 平台更宽，但 LITE 当前增长和毛利率更干净。
- 所以 COHR 的优势不是最大弹性，而是主线参与 + 相对抗波动。

今日/近期 thesis 失效条件：

- AI 光学主线退潮。
- COHR 相对 LITE / AAOI / SOXX 明显掉队。
- COHR 价格无法在关键位承接。
- 上涨缺乏成交量确认。

## 估值温度

当前温度：

```yaml
valuation_temperature: orange
entry_permission: no_chase
preferred_entry: pullback_or_reclaim
trade_permission: no
```

含义：

- 不允许在接近高位时无条件追高。
- 允许写条件式计划。
- 只有回调承接或重新确认后，才允许考虑试探。
- 初始仓位不能直接使用 30% 波段仓上限。

## Entry Condition

只允许两类入口。

### A. 回调承接入口

允许条件：

1. COHR 从高位回调到可观察支撑区。
2. 价格出现承接，而不是自由下跌。
3. LITE / AAOI / SOXX 没有同步破坏主线。
4. QQQ / SOXX 不处于明显风险释放状态。
5. 成交量或价格结构显示卖压减弱。

候选观察区：

- 400 附近整数位 / gamma 区域
- 380-390 一带是否形成承接
- 20 日线附近
- 前一轮突破 / 启动区

注意：

这些不是自动买点。

必须看到承接。

### B. 重新确认入口

允许条件：

1. COHR 重新站回关键位。
2. 光学 peer basket 同步强。
3. COHR 不明显落后 LITE / AAOI / SOXX。
4. 上涨有成交量确认。
5. 不是连续加速后的情绪末端追高。

适用场景：

- 市场没有给深回调，但 COHR 在板块确认后重新走强。

## 禁止入口

禁止：

- 因为之前卖早了而重进。
- 因为 COHR 又涨了而追。
- COHR 跑输 LITE / AAOI / SOXX 时买入。
- QQQ / SOXX 明显走弱时强行买入。
- 仅凭“AI 光学逻辑很强”买入。
- 没有止损位置时买入。

## Position Size

用户候选上限：

```yaml
max_position_candidate: 30% of swing sleeve
```

当前 Orange 温度下：

```yaml
initial_starter_if_triggered: 10% to 15% of swing sleeve
add_to_30pct_allowed_only_if: confirmation_after_entry
full_size_limit: 30% of swing sleeve
portfolio_equivalent_if_swing_sleeve_60pct: about 18% total portfolio
status: pending_user_confirmation
```

解释：

- 30% 波段仓不是初始仓位。
- 只有当入口触发、peer 确认、价格承接后，才可逐步接近上限。
- 如果波段仓总预算是组合 60%，那么满仓 COHR 等于总组合约 18%，这个数值偏高，需要你最终确认。

## Risk Limit

风险限制：

- 单次试探亏损必须可接受。
- 如果不能接受隔夜波动，必须降低仓位。
- 如果持仓影响睡眠，说明仓位过大。
- 如果 COHR 消耗过多注意力，必须降风险。

候选风险边界：

```yaml
max_loss_per_attempt: to_be_confirmed
max_total_loss_for_plan: to_be_confirmed
sleep_risk_allowed: only_if_position_size_small_or_plan_explicit
attention_budget: limited
```

## Falsification

计划失效条件：

1. COHR 跑输 LITE / AAOI / SOXX。
2. COHR 跌破计划内承接区且不能快速收回。
3. 光学板块退潮。
4. SOXX / QQQ 进入明显风险释放。
5. COHR 上涨无量、下跌放量。
6. 交易理由从“主线承接”变成“我不想错过”。
7. 交易理由从“承接确认”变成“摊低成本”。

## Add Rule

是否允许加仓：

```yaml
adding_allowed: yes_but_only_after_confirmation
```

允许加仓条件：

- 初始入场后价格按预期走强。
- COHR 相对 LITE / AAOI / SOXX 不掉队。
- 光学板块继续强。
- QQQ / SOXX 没有同步恶化。
- 加仓后总仓位仍不超过计划上限。

禁止加仓条件：

- 只是为了摊低成本。
- COHR 已经跌破承接区。
- 你已经看见走弱但希望它反弹。
- LITE / AAOI / SOXX 更强而 COHR 掉队。
- 已接近睡觉时间且无法监控风险。

## Re-Entry Rule

是否允许止盈后重进：

```yaml
reentry_allowed: conditional
```

允许重进条件：

- 有新的触发。
- peer basket 重新确认。
- COHR 未掉队。
- 不是因为“刚才卖少了”或“想再赚一段”。

禁止重进条件：

- 卖出后后悔。
- 想复刻上一笔利润。
- 价格已经进入情绪加速。
- 没有新的 invalidation。

## Exit Condition

分三类退出。

### 1. 风险退出

触发：

- 跌破承接区。
- peer basket 破坏。
- QQQ / SOXX 风险释放。
- COHR 跌幅明显大于同行。

行动：

- 减仓或退出。
- 不等待“奇迹反弹”。

### 2. Thesis 降级退出

触发：

- 财报 / 指引 / 管理层表述不再支持 AI datacenter demand。
- LITE / AAOI 明显夺取领导力，而 COHR 长时间掉队。
- 市场不再奖励平台宽度。

行动：

- 降级为 research_only 或 no_trade。

### 3. 止盈退出

候选规则：

- 第一档止盈：20%-30% 仓位。
- 第一档止盈后冷却 15-30 分钟，不因后悔立刻重进。
- 剩余仓位用趋势 / 移动止盈 / peer strength 管理。

注意：

这是为了避免重复 COHR 止盈后悔循环。

## Attention Budget

COHR 不是日内短线仓。

注意力规则：

- 不连续盯盘超过 30 分钟。
- 盘中只看关键节点。
- 如果开始频繁刷新价格，说明仓位或计划有问题。
- 如果影响睡眠，必须减仓或明确隔夜风险。

## Emotional Check

入场前必须回答：

- 我是在追高吗？
- 我是在修复之前卖早的后悔吗？
- 我是不是因为 AAOI / LITE 涨了而焦虑？
- COHR 是否真的符合自己的角色：主线承接 + 相对抗波动？
- 如果 COHR 今天不涨，我是否仍认可这笔计划？
- 如果买入后立刻跌破承接区，我是否能执行？

## Final Human Decision

```yaml
human_decision_required: true
current_decision: not_approved_for_trade
next_step: user_review_plan_candidate
```

## 当前结论

COHR 可以进入条件式波段计划候选。

但当前不是直接买入状态。

最合理的下一步是：

```text
等待回调承接或重新确认
|
检查 LITE / AAOI / SOXX
|
确认 QQQ / SOXX 风险环境
|
小仓试探
|
确认后才考虑加到上限
```
