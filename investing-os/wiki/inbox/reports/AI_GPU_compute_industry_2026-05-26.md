# AI GPU 算力行业 + 三杰深度调研存档

**首次创建**: 2026-05-26 | **版本**: v1.0 | **可持续扩充**

---

## 一句话定位
**AI GPU 算力是 2-3 年的黄金窗口（不是 5 年的稳态机会）。NBIS > IREN > CRWV，但都不应该是核心持仓。绝对不要碰 NBIL 2x 杠杆 ETF。**

---

## 一、行业全景

### 1.1 市场规模与增长
| 指标 | 2025 | 2028E | CAGR |
|------|------|-------|------|
| AI 基础设施总市场 | $250B | $700-900B | ~40% |
| Compute as a Service | $45B | $180B | ~58% |
| Neo-cloud 份额 | 18-22% | 25-28% (趋稳) | - |
| NVDA DGX Cloud (自营) | <$2B | - | 战略意义 > 营收 |

**关键单一项目**：Stargate (OpenAI/Oracle/SoftBank/NVDA) — 2025 启动 $100B → 2029 目标 $500B（占未来 5 年 AI 基建 20%+）

### 1.2 三层格局演变

```
                        2025       2028E      趋势
Layer A (Hyperscaler)   65%       → 75%     ↑ 自研 ASIC 25→40%
  AWS/Azure/GCP/Oracle
                                              
Layer B (Neo-cloud)     20%       → 22-25%  → 头部存活，中尾消失
  CRWV/NBIS/Lambda/Crusoe
  (NVDA 嫡系军)
                                              
Layer C (转型方)         15%       → 3-5%    ↓ 70% 矿企退出
  IREN/CRSO/DLR/EQIX
```

### 1.3 NVIDIA DGX Cloud Partner 完整生态

**官方核心 6 家**：AWS / Azure / GCP / Oracle / **CRWV** / **NBIS (2026 新增)**

**Cloud Partner Program** (~30 家广义)：Lambda / Crusoe / Vultr / 其他

**NVIDIA AI Enterprise Partner** (ISV 层)：Dell / HPE / Lenovo / VMware / Red Hat

**NVDA 战略投资完整清单（公开持仓）**：
- 13F 普通股：Intel ($9.48B) / CoreWeave ($3.66B) / Synopsys ($1.91B) / Coherent ($1.86B) / Nokia ($1.34B) / Nebius ($123M) / Generate Biomedicines ($10M)
- 2026 新增非普通股：Lumentum $2B / Marvell $2B / Nebius 追加 $2B / CRWV 加注 $2B
- 早期/其他：xAI $700M / Lambda / Mistral / Recursion / Wayve / Coherence

**"客户即股东" 循环交易争议**：Burry 等指控 NVDA 投资 neo-cloud → 它们买 NVDA 卡 → 订单回流给 NVDA。规模 ~$15-20B vs 市值 $1.5T 仍属小比例，但估值崩塌时会放大。

### 1.4 GPU 平台演进与供需
- 时间表：H100 (2023) → H200 (2024) → B200/GB200 (2024Q4) → GB300 (2025H2) → Vera Rubin (2026 GTC, 2026H2 量产) → Rubin Ultra (2027)
- 当前供给：Blackwell 2025 产能售罄，NVDA Q1 FY27 DC +95% YoY（剔除中国）
- **H100 二手价**：$35K (2024) → $22K (2025) → 2026 进一步走低
- 折旧周期：Hyperscaler 6 年 vs Neo-cloud 4 年 = 单位成本 +50%

### 1.5 真实需求结构
- 训练 vs 推理：2025 55/45 → 2027E 35/65
- 推理转向 ASIC（不是纯 GPU）— 对 Neo-cloud 长期利空
- Frontier capex：OpenAI $500B (Stargate) + Anthropic $50B (AWS Trainium) + xAI $80B
- Sovereign AI：G42/Stargate UAE 5GW / Mistral 欧洲 / 印度 IndiaAI
- 中国市场已基本切断（NVDA 中国营收 25% → <5%）

### 1.6 Neo-cloud Unit Economics
- 8×H100 SXM 服务器 capex ~$280K；8×B200 ~$400K
- 月租 H100 ~$2.5-3/GPU-hr → $15-18K/月
- 折旧 4 年：年成本 $70-100K + 电力/网络/人工 $30K
- 毛利率 35-50%（CRWV 实际 40-45%，但**净亏 $1.2B** 因利息+折旧+SBC）
- Payback 2.5-3 年，但需 4 年合约锁定才能融资
- 负债结构：CRWV 总债 ~$20B（11-15% 利率），利息覆盖率 <1.5x（脆弱）

### 1.7 关键风险（按权重）
1. **DeepSeek 类效率突破**：V3 训练 $5.6M vs GPT-4 $100M = **18x 效率**，推理需求被压缩 30-40%
2. **Hyperscaler 自研 ASIC**：Trainium 3 + Maia 2 + TPU v8 → 2027 抢走 25% 训练市场
3. **NVDA 升级周期**：每年迭代，旧 GPU 加速过时
4. **电力瓶颈**：Texas ERCOT 2026 增量 8GW 已被预订；Virginia 排队到 2028
5. **客户集中**：训练市场 90% 来自 5 家 frontier labs
6. **资产负债脆弱**：CRWV 利息覆盖率 <1.5x
7. **监管**：FTC 反垄断 + 出口管制

### 1.8 中国/欧洲/中东/印度
- **中国**：阿里云 + 腾讯云 + 火山 ~30%，字节自建 20%，华为 Ascend 910C 2025 出货 200K → 2026 目标 500K
- **欧洲**：Mistral (NBIS 主供) + Aleph Alpha + EuroHPC
- **中东**：G42 / Stargate UAE 5GW + Saudi HUMAIN $40B
- **印度**：Reliance Jio + Tata 100MW
- **NBIS 战略区**：欧洲 + 中东 sovereign AI

### 1.9 行业整合预期
- Oracle / Microsoft 收购 CRWV/NBIS 概率：30%（2027-2028 窗口）
- BTC 矿企整合不可避免
- 估值天花板：类比成熟期 SaaS 5-10x P/S；当前估值需 2026-2027 营收 100%+ YoY 才能消化

---

## 二、三杰公司画像

### 2.1 CoreWeave (CRWV) — NVDA 亲儿子，但隐患重

| 维度 | 数据 |
|------|------|
| 现价 / 市值 | $105.49 / $57.6B |
| Q1 营收 / 增速 | $2.08B / +112% YoY |
| Q1 净亏 | -$740M |
| 累计债务 | $20B (Magnetar/Blackstone/Apollo, 11-15% 利率) |
| Backlog | $88B (OpenAI $12B + MSFT/Meta/Anthropic) |
| 客户集中 | MSFT 60%+ (2024)，前三 >80% |
| NVDA 关系 | $3.66B (13F #2) + 2026-01 加 $2B + $1.6B 历史首单 |
| 距 52w 高 | -43.6% (IPO 后大跌) |
| YTD | +47% |
| P/S | ~9x (最便宜) |
| 12M 目标 | $138.9 (+32%) |

**起源**：2017 年 4 个交易员（Atlantic Crypto）做以太坊矿，2019 转型 AI GPU 云。Mike Intrator (CEO) 是交易员出身，解释了高杠杆打法。

**优势**：NVDA 优先供货 + 部署速度 + OpenAI $12B 锁单
**劣势**：MSFT 单点依赖 + 高息债 + GPU 4 年折旧 + 护城河本质是"NVDA 关系" 非技术

**"NVDA 涨 1，CRWV 涨 2，但 NVDA 见顶日就是 CRWV 减仓日"**

### 2.2 Nebius (NBIS) — 真增长 + 真叙事 + 真烧钱

| 维度 | 数据 |
|------|------|
| 现价 / 市值 | $214.77 / $54.5B |
| Q1 2026 营收 | **$399M, YoY +684%** (真实数字，非基数) |
| TTM 营收 | $878M |
| 毛利率 | **83.88%** (行业最高) |
| FCF | -$3.16B (重资本扩张期) |
| 现金 / 净债务 | $9.3B / -$198M (基本净现金) |
| Capex 指引 | **$20-25B** (超 CRWV 50%) |
| NVDA 关系 | 2024-12 $700M (0.5%) + 2026-03 追加 $2B |
| 距 52w 高 | -8.1% (贴顶) |
| YTD | +157% / 1Y +468% |
| P/S | ~62x (最贵) |
| 12M 目标 | $230.77 (+7%, 已贴顶) |

**起源**：前身 Yandex (俄罗斯 Google) 国际业务。2024-07 剥离俄罗斯本土业务，更名 Nebius。CEO Arkady Volozh (Yandex 联合创始人)。

**业务**：Nebius AI Cloud (核心) + Avride (自驾) + TripleTen (教育) + Toloka (数据标注)
**地理优势**：芬兰 / 法国 / 美国 (Alabama AI Factory)，欧洲 GDPR + 数据主权
**重要合作**：Meta 大单 / Bloom Energy / 收购 Eigen AI + Tavily ($400M)

**支撑"真机会"的硬证据**：
1. Q1 +684% 是 $399M 实数
2. NVDA 两次重仓
3. Volozh 是真正建过百亿美金 CEO
4. 净现金 + 83% 毛利证明商业模型成立
5. 欧洲数据主权 CRWV 无法复制

**风险**：P/S 62x 比 CRWV 贵；D.A. Davidson 已降 Neutral；Capex $20-25B 隐含再融资稀释

### 2.3 IREN (Iris Energy) — 唯一 GAAP 盈利的转型新星

| 维度 | 数据 |
|------|------|
| 现价 / 市值 | $56.83 / $20.3B |
| TTM 营收 | $757M (+104% YoY) |
| **净利润 (TTM)** | **+$158M GAAP 盈利** (三家唯一) |
| 毛利率 | 68.4% |
| FCF | -$2.3B (扩张期) |
| 算力 | 运营 810MW / 在建 2,100MW / 在研 1,600MW / 锁电 >4.5GW |
| 数据中心 | Childress TX (750MW) + Sweetwater (2GW 在建) + Oklahoma + BC |
| NVDA 关系 | **$3.4B 多年客户合同** (客户级，非股权) |
| 距 52w 高 | -26.1% |
| YTD / 1Y | +50% / **+512%** |
| Beta | **4.18** (最高) |
| P/S | ~27x (中等) |

**转型路径**：2018-2019 创立 (BC 水电 + Texas 风电 BTC 矿)，2024-11 更名 IREN，2025-2026 大规模 GPU 部署。

**业务**：AI Cloud + Colocation + Build-to-Suit (三条线)

**独特护城河**：100% 可再生能源 + 自有 4.5GW 电力 (CRWV/NBIS 没有的资产)

**唯一 GAAP 盈利** = 与 MARA/RIOT/CIFR 等"PPT 转型矿企" 本质区别

**风险**：估值已假设 Sweetwater 满产；FCF -$2.3B 依赖资本市场；BTC 减半 + 价格回调；AI 算力价格战

---

## 三、NBIL (2x 杠杆 ETF) 评估

| 维度 | 数据 |
|------|------|
| 全名 | GraniteShares 2x Long NBIS Daily ETF |
| 现价 | $37.95 |
| 成立 | 2026-02-23 (仅 3 个月) |
| 52w 范围 | $6.37 - $46.11 |
| 距 52w 高 | -17.7% |
| 1M 实际杠杆 | 1.80x (验证 ~ 2x 关系) |
| AUM | 极小 (Direxion 类竞品对照) |

**判断**：**明确避开**

理由：
1. 仅成立 3 个月，AUM 小，流动性差
2. NBIS 已贴顶 -8%，杠杆品种在贴顶时最危险
3. 与 MRVU 教训完全一样：研究告诉你"长期看好但短期透支"，杠杆品种把这个矛盾放大 2x
4. 杠杆 ETF 长期持有必输于复利衰减

---

## 四、横向对比 + 行业角度

### 4.1 三家在 AI 价值链的位置

| 维度 | CRWV | NBIS | IREN |
|------|------|------|------|
| DGX Cloud Partner | ✅ 核心 6 家之一 | ✅ 2026 新增 | ❌ |
| NVDA 普通股投资 | ✅ $3.66B (13F #2) | $123M (13F #6) | ❌ |
| NVDA 2026 加注 | ✅ $2B (1月) | ✅ $2B (3月) | ❌ |
| NVDA 客户合同 | $1.6B 首单 | 未披露 | ✅ $3.4B 多年 |
| 行业层级 | Layer B 头部 | Layer B 头部 (欧洲) | Layer C 头部 (转型) |
| 致命短板 | MSFT 60% + $20B 高息债 | P/S 62x 估值贴顶 | Beta 4.18 + BTC 周期 |
| 独有护城河 | NVDA 优先供货 | 欧洲主权 + 净现金 | 自有 4.5GW 电力 |

### 4.2 投资优先级判断

| 角色 | 选择 | 理由 |
|------|------|------|
| 长期核心 (12-24M) | **NBIS** | 资产负债表最干净 + 毛利最高 + NVDA 二次加注 + 欧洲主权 |
| 短线博弈 (1-3M) | **IREN** | NVDA $3.4B 合同 + 唯一盈利 + 弹性最大 |
| 卫星投机 | **CRWV** | 估值最便宜 + 12M 目标 +32% + NVDA 最深绑定 |
| 规避 | **CRWV 短期** | 客户集中 + 高债务 + IPO 解禁 |
| 绝对避开 | **NBIL** | 贴顶 + 杠杆 + 流动性差 |

### 4.3 建仓时机

```
NBIS  现价 $214 (距高 -8%) — 等回调
       目标 $170-180 分批入
       止损 $155 (前低密集区)
       目标仓位 3-6% 总账户

IREN  现价 $57 (距高 -26%) — 等回调
       目标 $45-50 分批入
       目标仓位 1-3% 总账户

CRWV  现价 $105 (距高 -44%) — 已大幅回调但不入
       理由：GOOG TPU 利空 + 解禁压力未消化
       
NBIL  绝对不碰
```

---

## 五、持续观察清单

### 5.1 行业层面（季度跟踪）
- [ ] OpenAI / Anthropic / xAI Capex 指引变化
- [ ] DeepSeek / Llama 类效率突破事件
- [ ] Trainium / Maia / TPU 量产爬坡（自研 ASIC 渗透率）
- [ ] H100 / H200 二手价格走势
- [ ] NVDA 季度财报中 DC 增速（90%+ 守住 vs 跌破 50%）

### 5.2 公司层面（财报跟踪）
- **CRWV**：
  - [ ] MSFT 客户占比变化 (50% → ?)
  - [ ] 利息覆盖率
  - [ ] OpenAI $12B 单兑现节奏
- **NBIS**：
  - [ ] Capex $20-25B 融资计划
  - [ ] Meta 合同细节披露
  - [ ] DGX Cloud Partner 新增其他公司
- **IREN**：
  - [ ] Sweetwater 投产里程碑
  - [ ] 第二个 hyperscaler anchor tenant
  - [ ] BTC 业务占比下降

### 5.3 关键事件触发警报
- ⚠️ MSFT 公告自研 Maia 3 量产 → CRWV 减仓
- ⚠️ DeepSeek 3.0 类突破再现 → 全板块减半
- ⚠️ NVDA 季度财报指引下修 → 全板块清仓
- ✅ NVDA 进一步加注任何一家 → 加仓信号

---

## 六、可扩充板块（待补充）

### 6.1 其他 AI 算力公司（待加入）
- Lambda Labs（私有）
- Crusoe Energy（Stargate Abilene 主建造方）
- Vultr
- Applied Digital (APLD)
- Cipher Mining (CIFR)
- WULF (TeraWulf)
- CleanSpark (CLSK)
- Bitdeer (BTDR)

### 6.2 上游受益方
- 光通信：COHR (已研究) / LITE (已研究) / AAOI (已研究)
- 网络芯片：MRVL (已研究)
- 电力 / 数据中心 REIT：DLR / EQIX / VRT
- 电力建设：CEG / VST / NRG

### 6.3 后续研究方向
- [ ] OpenAI 上市的可能性和影响
- [ ] Anthropic / Mistral / xAI 估值演变
- [ ] Stargate 项目对整个产业链的影响
- [ ] 量子计算与传统 GPU 算力的竞争（IONQ / RGTI 等）

---

## 七、决策记录

- **2026-05-26 v1.0**：完成三家公司画像 + 行业全景。判断 NBIS > IREN > CRWV，但都不进入核心持仓。NBIL 明确避开。
- 下次更新建议：财报季后（CRWV Q2 8月 / NBIS Q2 8月 / IREN Q3 8月）
