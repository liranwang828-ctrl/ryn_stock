# COHR 波段估值温度计

## 元数据

```yaml
symbol: COHR
date: 2026-06-05
status: valuation_candidate_pending_user_review
methodology: wiki/methodologies/ai-swing-valuation-temperature.zh.md
trade_permission: no
```

## 角色前提

COHR 在系统中的角色不是最高 beta 进攻工具。

它是：

```yaml
cohr_role_in_system: mainline_carrier_plus_resilient_swing
```

也就是：

- AI 光学主线承接仓
- 相对抗波动的波段仓
- 不默认核心仓
- 不追求比 AAOI 更爆发
- 必须相对 LITE / AAOI / SOXX 不掉队

## 1. Narrative Temperature

判断：

AI 光学处于热状态，接近过热。

理由：

- AI 数据中心光互联需求被市场持续关注。
- COHR、LITE、AAOI 近期都有强表现。
- COHR Q3 FY2026 财报确认 datacenter / communications demand 强。
- AAOI 近期更高 beta，说明资金愿意追逐光学弹性。

结论：

```yaml
narrative_temperature: hot_to_overheated
entry_implication: no_chase
```

## 2. Growth Confirmation

判断：

COHR 基本面有确认，但不是最高质量同行。

事实：

- COHR Q3 FY2026 收入 $1.81B，同比 +21%，pro forma 同比 +27%。
- Non-GAAP 毛利率 39.6%。
- Non-GAAP EPS $1.41。
- 管理层确认 datacenter / communications demand 强，并正在扩产。

同行：

- LITE Q3 FY2026 收入同比 +90%，Non-GAAP 毛利率 47.9%。
- AAOI 增长弹性强，但仍 GAAP 亏损。

结论：

```yaml
growth_confirmation: strong_but_not_cleanest_peer
entry_implication: needs_peer_confirmation
```

## 3. Peer Valuation And Quality

判断：

COHR 是中等 beta + 平台宽度表达。

不是：

- 最高 beta：AAOI 更像
- 最干净利润率：LITE 更像

COHR 的优势：

- 平台宽
- 规模大
- 多技术路线覆盖
- 相对可能更抗波动

COHR 的约束：

- 不能掉队
- 不能因为平台逻辑忽略市场偏好
- 如果市场只奖励纯弹性，COHR 可能不是最优

结论：

```yaml
peer_positioning: resilient_mainline_expression
entry_implication: allowed_only_if_not_lagging_peer_basket
peer_basket: [LITE, AAOI, SOXX]
```

## 4. Price Location

判断：

当前位置偏高，不适合无条件追高。

事实：

- 2026-06-04 COHR 收盘 421.90。
- 2026-06-04 盘中高点 432.51。
- 2026-06-03 区间高点附近为 440。
- 2026-05-20 至 2026-06-04，COHR 10D +17.68%。

结论：

```yaml
price_location: elevated_near_recent_high
entry_implication: pullback_or_reclaim_only
```

允许的买点类型：

- 回调后承接
- 重新站回关键位
- 板块强而 COHR 不掉队
- 不能在连续加速后无计划追高

## 5. Downside If Narrative Cools

判断：

如果 AI 光学情绪降温，COHR 回撤风险不小。

潜在回撤观察位：

- 最近突破 / 承接区
- 20 日线附近
- 400 附近整数位 / gamma 区域
- 前一轮启动区
- 380-390 一带是否成为承接区

结论：

```yaml
downside_if_narrative_cools: meaningful
entry_implication: position_size_must_depend_on_entry_location
```

## 6. Swing Risk / Reward

判断：

当前不能直接假设有足够 2:1 赔率。

原因：

- 价格接近近期高位。
- AI 光学叙事偏热。
- COHR 估值不便宜。
- 同行中 AAOI 更强，LITE 财务更干净。

结论：

```yaml
risk_reward_now: not_enough_for_full_size_chase
entry_implication: wait_for_better_location_or_stronger_confirmation
```

## 总体估值温度

```yaml
valuation_temperature: orange
entry_permission: no_chase
allowed_action:
  - monitor
  - wait_for_pullback
  - write_conditional_swing_plan
forbidden_action:
  - full_size_entry_now
  - regret_reentry
  - add_while_lagging_peers
```

## 仓位映射

用户提出：

```yaml
max_position_candidate: 30% of swing sleeve
```

系统解释：

如果波段仓总预算是组合 60%，那么 COHR 占波段仓 30% 等于总组合约 18%。

这对 COHR 来说偏高，只有在 Green 状态下才可考虑。

当前 Orange 状态下：

```yaml
max_allowed_now: 0% unless a valid conditional plan triggers
starter_if_triggered: 10% to 15% of swing sleeve
full_size_limit: 30% of swing sleeve only after confirmation
portfolio_equivalent_if_full: about 18% total portfolio
status: pending_user_confirmation
```

## COHR 当前结论

```yaml
cohr_valuation_status: orange
trade_permission: no
next_step: conditional_swing_plan_candidate
preferred_entry: pullback_or_reclaim
not_allowed: chase_near_high
```

一句话：

COHR 作为 AI 光学主线承接仓可以继续研究，但当前位置更像“等回调/等确认”，不是“直接满仓重进”。

## 下一步

如果用户认可这个估值温度计，则下一步写 COHR 条件式 swing plan：

- 什么价格/结构允许试探
- 什么条件允许加到 30% swing sleeve
- 什么条件必须放弃
- 如何分批止盈
- 如果 LITE / AAOI 领先而 COHR 掉队，如何处理
