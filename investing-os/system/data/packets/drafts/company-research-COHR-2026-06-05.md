# Company Research Packet: COHR

## Packet Header

```yaml
packet_type: company_research
status: reviewed_absorbed_to_dossier
created_at: 2026-06-05
source_system: investing-os + stock_team + public sources
source_files:
  - D:/gemini/lianghua/stock_team/findings/company_profile_COHR.json
  - D:/gemini/lianghua/stock_team/config/sector_registry.json
  - D:/gemini/lianghua/stock_team/docs/full_candidate_review_2026-06-02_zh.md
  - D:/gemini/lianghua/stock_team/docs/wiki/cases/2026-06-02_cohr_profit_taking_zh.md
  - D:/gemini/lianghua/stock_team/knowledge/trading_knowledge_tree.md
  - wiki/journals/2026-06-04-cohr-orcl-intc-exit-review.md
symbol: COHR
company_name: Coherent Corp.
research_date: 2026-06-05
review_owner: user
```

## 1. Research Question

Primary question:

Is COHR currently a good swing expression of the AI optical infrastructure theme, or is it a complex platform stock that should only be monitored unless it proves leadership versus cleaner optical peers?

Sub-questions:

1. What exactly does COHR sell into the AI datacenter chain?
2. Is the bottleneck optical bandwidth, power, capacity, or customer qualification?
3. Where does COHR capture value versus LITE / AAOI / broader semiconductors?
4. Is COHR's complexity an advantage or a discount for swing trading?
5. What would falsify the swing thesis?

## 2. Facts

### Company Identity

COHR is a photonics, materials, optical components, and laser company.

Local company profile describes three segments:

- Networking: transceivers, systems, subsystems, modules, components, optics, and semiconductor devices for datacenter and communications applications.
- Materials: engineered materials, laser optics, thermoelectric components, ceramics, metal-matrix composites, VCSELs, edge-emitting lasers, pump lasers, and related products.
- Lasers: excimer lasers, solid-state lasers, CO2 lasers, and laser systems for industrial and semiconductor applications.

Source:

- `stock_team/findings/company_profile_COHR.json`

### Recent Financial Facts

Company-reported Q3 FY2026 facts:

- Revenue: $1.81B.
- Revenue growth: up 21% year over year, up 27% year over year on a pro forma basis.
- GAAP gross margin: 37.7%.
- Non-GAAP gross margin: 39.6%.
- GAAP EPS: $0.97.
- Non-GAAP EPS: $1.41.
- Management attributed performance to strong datacenter and communications demand.
- Management said it is expanding capacity to meet AI datacenter demand.

Source:

- [Coherent Q3 FY2026 results](https://www.coherent.com/news/press-releases/third-quarter-fiscal-year-2026-results)

### Industry / Product Facts

Coherent announced or demonstrated AI datacenter optical products around OFC 2026, including:

- 1.6T-FR4 OSFP transceiver using 200G/lane EML and InP DFB technology.
- 3.2T co-packaged optics transmit and receive optical engines.
- a 1.6T optical circuit switch for AI datacenters.

Sources:

- [Coherent 1.6T-FR4 transceiver announcement](https://www.coherent.com/news/press-releases/coherent-revolutionizes-transceiver-technology)
- [Coherent 3.2T CPO optical engines announcement](https://www.coherent.com/news/press-releases/coherent-announces-3.2t-cpo-transmit-receive-optical-engines)
- [Coherent 1.6T optical circuit switch announcement](https://www.coherent.com/news/press-releases/coherent-demonstrates-1.6t-optical-circuit-switch-ai-datacenters-ofc-2026)

### Local Investing-OS / Stock-Team Facts

`stock_team` prior optical-sector map framed optical transceivers and optical components as a core physical interconnect layer for AI compute clusters.

Local sector map suggested:

- AI cluster scaling drives high-bandwidth optical interconnect demand.
- 1.6T era may accelerate VCSEL, EML, silicon photonics, and TFLN technology.
- COHR has broader platform exposure than narrower peers, including InP, EML, silicon photonics, TFLN, and SiC-related optionality.
- LITE may have cleaner short-term exposure and capital efficiency.
- AAOI may be higher beta and more sentiment-sensitive.

Source:

- `stock_team/config/sector_registry.json`

### Recent Market / Relative Strength Facts

Read-only Polygon daily aggregates for 2026-05-20 to 2026-06-04:

| Symbol | Close 2026-06-04 | 1D | 5D | 10D | RS 5D vs QQQ | RS 10D vs QQQ |
|---|---:|---:|---:|---:|---:|---:|
| COHR | 421.90 | +1.07% | +11.92% | +17.68% | +11.24% | +13.83% |
| LITE | 945.08 | +0.75% | +9.81% | +8.87% | +9.13% | +5.02% |
| AAOI | 202.89 | +10.22% | +20.04% | +22.77% | +19.36% | +18.92% |
| SOXX | 602.72 | -2.10% | +5.84% | +15.84% | +5.16% | +11.99% |
| QQQ | 740.61 | -0.48% | +0.68% | +3.85% | 0.00% | 0.00% |

Interpretation:

- COHR showed strong 5D and 10D relative strength versus QQQ.
- AAOI was the stronger high-beta optical peer into 2026-06-04.
- COHR was stronger than LITE over 5D and 10D in this measured window, but prior `stock_team` notes warned that COHR had lagged optical peers during a previous snapshot.
- For swing use, peer leadership should be checked at the time of entry, not assumed from one static window.

Source:

- read-only Polygon daily aggregates using `stock_team/.env` API key.

### Supplemental Peer / Valuation Data

Current market snapshot from finance lookup on 2026-06-05 UTC:

| Symbol | Price | Market Cap | P/E | EPS |
|---|---:|---:|---:|---:|
| COHR | 421.90 | $82.54B | 199.95x | 2.11 |
| LITE | 945.08 | $90.92B | 170.59x | 5.54 |
| AAOI | 202.89 | $15.42B | negative | -0.65 |

Peer operating evidence:

- LITE Q3 FY2026 revenue was $808.4M, up 90% year over year, with GAAP gross margin of 44.2% and non-GAAP gross margin of 47.9%.
- AAOI Q1 2026 revenue was $151.1M, with datacenter revenue of $81.4M, but GAAP net loss remained negative.

Sources:

- [Lumentum Q3 FY2026 results](https://investor.lumentum.com/financial-news-releases/news-details/2026/Lumentum-Announces-Third-Quarter-of-Fiscal-Year-2026-Financial-Results/default.aspx)
- [Applied Optoelectronics Q1 2026 results](https://www.nasdaq.com/press-release/applied-optoelectronics-reports-first-quarter-2026-results-2026-05-07)

Interpretation:

- COHR has scale and platform breadth.
- LITE currently appears cleaner on margin profile and year-over-year growth.
- AAOI appears higher beta and more explosive, but still lower quality financially.
- Therefore COHR is not automatically the best optical trade. Its swing case depends on peer confirmation and price discipline.

## 3. Thesis Candidate

Draft thesis:

COHR can be a swing candidate when AI optical infrastructure is in favor and COHR is confirming peer leadership. The company has a plausible structural role in AI datacenter scaling because larger AI clusters require higher bandwidth, lower power, and better optical interconnect. COHR's platform breadth can capture value across transceivers, lasers, InP/EML devices, optical engines, and optical switching.

One-sentence version:

COHR is a swing expression of AI datacenter optical bandwidth demand, valid only when its price action and peer leadership confirm that the market is rewarding the platform rather than discounting its complexity.

This is not yet an active thesis.

Current lifecycle state:

```yaml
lifecycle_state: thesis_candidate_draft
role: swing
trade_permission: no
requires_user_review: yes
```

## 4. Value Capture

### First Principle

AI clusters are constrained not only by GPU supply.

As clusters grow, the system bottleneck shifts toward:

- bandwidth
- latency
- power efficiency
- network scale
- optical component supply
- qualification and reliability

If GPUs become more powerful and cluster sizes increase, interconnect density and optical bandwidth requirements can rise faster than generic datacenter growth.

### Bottleneck Analysis

Potential bottlenecks:

| Bottleneck | Why It Matters | COHR Exposure |
|---|---|---|
| 800G / 1.6T transceiver supply | AI clusters need higher throughput | Networking segment |
| 200G/lane EML and InP | Enables higher-speed links | InP / EML capabilities |
| CPO / optical engines | Future packaging architecture | 3.2T CPO optical engines |
| Optical switching | AI datacenter network optimization | 1.6T optical circuit switch |
| Power efficiency | Datacenter power is scarce | optical efficiency advantage |
| Reliability / qualification | hyperscale customers avoid weak suppliers | scale and portfolio breadth |

### Supply Chain Mapping

Simplified chain:

```text
hyperscaler AI capex
|
GPU clusters and networking systems
|
switches / optical interconnect / transceiver demand
|
optical components, lasers, InP/EML, SiPho, CPO, OCS
|
COHR / LITE / AAOI / other suppliers
```

COHR can participate at multiple levels:

- optical components
- transceivers
- lasers
- InP / EML
- optical engines
- materials and adjacent photonics

This breadth is the main advantage and the main trading risk.

### Why This Company Rather Than Peers

Possible advantages:

- broader photonics platform
- InP / EML / silicon photonics optionality
- exposure to both near-term transceiver demand and longer-term optical architecture shifts
- datacenter and communications demand already visible in revenue growth

Possible disadvantages:

- less pure than a cleaner optical momentum name
- complexity discount
- more moving parts outside the AI optical story
- may lag high-beta peers when the market wants simpler exposure

Current working rule:

COHR is acceptable for a swing only if it is not lagging the peer basket.

Peer basket:

- LITE
- AAOI
- SOXX
- optionally FN / CIEN if broader optical network confirmation is needed

## 5. Valuation Frame

This packet does not build a full DCF.

Current valuation frame:

- COHR should be valued as a cyclical growth / AI infrastructure supplier, not as a stable software compounder.
- The important variables are revenue growth, gross margin, operating leverage, capex / capacity execution, and whether AI optical demand remains durable.
- A high multiple can be justified only if datacenter / communications growth and margin expansion continue.
- A lower multiple is appropriate if COHR is treated as a complex hardware supplier with volatile demand.

Local `stock_team` profile from 2026-05-26 showed:

- forward P/E around 46.6x
- TTM P/E around 178.9x
- PEG around 0.92
- analyst target around $380.62 at that time

Important caveat:

- This profile is stale relative to the 2026-06-04 close of $421.90.
- It should not be used as a current valuation conclusion without refresh.

Scenario frame:

| Scenario | Required Assumptions | What To Watch |
|---|---|---|
| Bull | AI datacenter optical demand accelerates, COHR expands capacity, margins improve | revenue growth, gross margin, peer leadership |
| Base | demand remains good but valuation already reflects much of it | pullbacks hold, growth continues, no margin shock |
| Bear | optical demand slows, peers win share, complexity discount widens | peer lag, margin miss, guidance cut |

## 6. Falsification

### Business Falsification

The thesis weakens if:

- datacenter / communications demand decelerates materially
- management stops emphasizing AI datacenter capacity expansion
- COHR loses major hyperscale or networking opportunities to peers
- new architectures reduce COHR value capture

### Financial Falsification

The thesis weakens if:

- revenue growth remains strong but gross margin fails to improve
- capacity expansion creates cost pressure without revenue conversion
- cash-flow quality deteriorates
- debt or capex burden becomes the dominant story

### Market-Structure Falsification

The swing thesis weakens if:

- COHR lags LITE, AAOI, and SOXX during optical-led rallies
- COHR cannot reclaim key moving averages after sector strength
- the stock repeatedly fails near prior high zones while peers break out
- volume does not confirm upward moves

### Timing / Catalyst Failure

The swing thesis weakens if:

- AI optical narrative remains strong but COHR fails to react
- OFC / product announcements do not translate into investor demand
- earnings or guidance fail to confirm the demand story

## 7. Risk

### Thesis Risk

AI optical demand can be real while COHR is still not the best stock expression.

This is the central risk.

### Position Risk

COHR is high volatility.

Local profile previously noted beta around 2.1x.

The 2026-06-04 regular session showed large intraday movement:

- open: 398.70
- high: 432.51
- low: 380.20
- close: 421.90

### Peer / Complexity Risk

If the market wants pure exposure, AAOI or LITE may move faster.

If the market wants durable platform breadth, COHR may deserve a premium.

The swing plan must decide which regime is active.

### Valuation Risk

The stock can be right on theme but wrong on price.

If forward estimates already price in acceleration, any margin or guidance disappointment can hurt.

### Emotional / Attention Risk

COHR has already appeared in:

- 2026-06-02 profit-taking regret case
- 2026-06-04 mixed-quality exit review

Therefore COHR requires:

- prewritten exit rule
- partial profit-taking rule
- no regret-driven re-entry
- attention budget

## 8. Action Boundary

Allowed outputs from this packet:

- keep COHR in `plan_required`
- update company dossier after review
- create thesis candidate
- create peer-leadership checklist
- create swing trade plan draft after user review

Forbidden outputs:

- direct buy / sell command
- automatic position sizing
- treating COHR as core holding
- re-entry only because the prior sale feels early
- adding while COHR lags LITE / AAOI / SOXX

## 9. Absorption Decision

```yaml
absorb_to_wiki: yes
absorb_to_template: no
absorb_to_principle: no
absorb_to_watchlist: yes
next_review_date: 2026-06-12
reason: user directed review, modification, supplemental data, and absorption; packet supports thesis-candidate company dossier but not trade permission
```

## Working Conclusion

COHR deserves thesis-candidate status as a swing candidate, not automatic re-entry.

The best version of the thesis is:

```text
AI datacenter optical bandwidth demand is real.
COHR has platform-level exposure.
But for swing trading, COHR must prove market leadership versus cleaner optical peers.
```

Next step:

Absorb reviewed conclusions into `wiki/companies/COHR.md` as a `thesis_candidate`.
