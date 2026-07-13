# 2026-07-13 DAILY-1 盘前计划

```yaml
session_id: observation-2026-07-13
mode: observation
status: pending_user_confirmation
generated_at_et: 2026-07-13T08:51:00-04:00
account_facts: stale_unverified
permission: Yellow / no automatic trading permission
```

## 一句话计划

今天先处理半导体风险暴露，不在 CPI、PPI 与 TSM 财报连续事件窗口前抢建完整新仓；开盘第一段只验证“行业去风险是否继续”，不把低开直接当成 Reality 恶化或入场机会。

## 盘前事实

| 对象 | 盘前变化 | 解释状态 |
|---|---:|---|
| NQ=F / ES=F | -0.05% / +0.08% | 指数期货接近平盘 |
| QQQ / SPY | -1.04% / -0.33% | QQQ 明显更弱；与期货参考基准存在冲突 |
| SMH / SOXX | -2.21% / -2.98% | 风险集中在半导体 |
| VIX | +9.78% | 风险溢价上升，但读数为 aging |
| WTI / 美元 / 10Y Note future | +0.09% / -0.19% / -0.03% | 当前 Tape 未显示新的同步宏观冲击扩张 |
| BTC | +0.39% | 数据 stale_unverified，不进入正式判断 |

外部事件：7 月 14 日 08:30 ET 发布 CPI，7 月 15 日 08:30 ET 发布 PPI，TSM Q2 财报在 7 月 16 日 02:00 ET。AMD Q2 财报日期为 8 月 4 日盘后，不属于本周立即事件。

## Investing-OS 解释

### Reality

盘前价格没有提供 AMAT、TSM、MU 或 COHR 公司 Reality 恶化的新证据。AI capex、HBM、先进制程和光网络的产业判断暂不因低开而改写。

### Consensus

市场正在降低高预期半导体暴露，并提高事件与地缘风险折价。MU、AMAT、COHR 跌幅显著大于 TSM，说明 Consensus 对高波动、高预期或兑现速度更敏感。

### Price

Price 已先行压缩，但尚未形成止跌确认。今天需要判断这是短期 PE 压缩，还是将进一步传播为行业趋势破坏；不能从“跌得多”直接推出“价格尚未反映 Reality”。

## 标的行动矩阵

| 标的 | 盘前约值 | 当前状态 | 开盘后升级条件 | 失效或风险条件 |
|---|---:|---|---|---|
| TSM | 434.50 / +0.09% | `relative_strength_watch / event_wait` | 持续强于 SMH/SOXX；回踩后守住 428 并收回，或财报后站稳 441–452 | 跌破约 409 且无法快速收回；财报 Reality 破坏 |
| AMAT | 576.79 / -4.27% | `zone_touched / no_entry` | 550–580 内停止扩大跌幅、波动收缩并恢复相对 SMH 强度 | 跌破约 528 且不能收回；TSM capex 证据恶化 |
| AMD | 544.21 / -2.45% | `continue_wait` | 回到 510–535 后仍保持相对行业强度，或重新建立趋势确认 | 跌势与行业同步扩大；把 8 月 4 日财报误当成今天必须抢跑的理由 |
| MU | 926.23 / -5.42% | `hold_no_add / risk_watch` | 收回 950 后稳定，再讨论是否完成第一层修复 | 跌破 891–900 且不能收回；杠杆工具需单独降低路径风险 |
| COHR | 311.39 / -4.04% | `risk_review / no_add` | 守住 304 并先收回 330；368–370 才是更完整修复 | 跌破 304 且不能快速收回；反弹无相对强度只视为风险处理窗口 |

认知差观察池：SNPS 与 MSFT 盘前分别约 +1.12%、+0.73%，继续作为软件/商业化相对强度对照；CIEN、LITE 与光通信风险同步走弱。今天不把观察池升级为买入池。

## 开盘观察顺序

### 09:30–09:45 ET：只观察

1. 不交易第一跳，不用低开修复亏损。
2. 看 QQQ 相对 SPY、SMH/SOXX 相对 QQQ 是否继续恶化。
3. 看 TSM 是否继续显著强于行业。
4. 看 MU 的 900–950 区域与 COHR 的 304 是否出现快速失守。
5. 看 VIX 是否继续上冲，以及油价/利率是否重新加入风险传播链。

### 09:45–10:15 ET：分类，不自动下单

- `stabilizing`：半导体跌幅收窄，TSM保持强势，AMAT/MU/COHR不再创新低；
- `sector_risk_continues`：SMH/SOXX继续弱于QQQ，MU或COHR跌破风险线；
- `broad_risk_off`：QQQ、SPY、期货同步恶化，VIX和宏观链继续扩张。

只有形成分类后，才在对话中讨论下一动作。Dashboard 只检查 Tape、计划和后续记录是否存在，不替代用户确认。

## 今日组合约束

- TSM、AMAT、MU、COHR、AMD 属于高度相关的 AI/半导体风险桶；
- 在账户仓位和工具类型未确认时，不输出数量化订单；
- TSM 与 AMAT 不同时建立完整新仓；
- MU/COHR 的风险处理优先于新增 AMAT/TSM 风险；
- CPI 前不因怕踏空提高总风险，不使用摊低成本修复近期亏损。

## 待用户一次性确认

确认本日焦点顺序为：`MU/COHR 风险处理 -> TSM 相对强度 -> AMAT 观察区 -> AMD 等待 -> SNPS/MSFT 对照`。确认后进入开盘观察，不再重复询问同一组选择。

## 来源

- Premarket Tape：`investing-os/system/runtime/inputs/observation-2026-07-13-premarket-tape.json`
- BLS CPI：https://www.bls.gov/cpi/
- BLS PPI：https://www.bls.gov/ppi/
- TSM Q2 2026：https://investor.tsmc.com/english/quarterly-results/2026/q2
- AMD Q2 2026：https://ir.amd.com/news-events/press-releases/detail/1289/amd-to-report-fiscal-second-quarter-2026-financial-results
- AP 7 月 13 日市场报道：https://apnews.com/article/2d6744b09c68b5473d0bc8584b89e60e
