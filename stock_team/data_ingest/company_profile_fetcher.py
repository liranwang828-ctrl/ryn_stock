"""
公司深度画像生成模块 — company_profile_fetcher.py
整合 yfinance 数据 + LLM 分析，生成结构化公司研究画像。

输出: findings/company_profile_{sym}.json

用法:
  python3.12 agents/company_profile_fetcher.py NVDA
  python3.12 agents/company_profile_fetcher.py NVDA MRVU LITX
"""
import json, os, sys
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from datetime import datetime, timezone, date as _date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
FIND_DIR = os.path.join(BASE, "findings")

# ── 竞争对手固定映射（补充 yfinance 没有的信息）─────────────────────────
COMPETITOR_MAP = {
    "NVDA": [
        {"sym": "AMD",  "name": "AMD", "angle": "GPU/AI加速器，ROCm追赶CUDA"},
        {"sym": "INTC", "name": "Intel", "angle": "Gaudi 3 AI加速器，以太网AI网络"},
        {"sym": "GOOGL","name": "Google TPU", "angle": "内部ASIC，推理优化，不对外销售"},
        {"sym": "AMZN", "name": "AWS Trainium/Inferentia", "angle": "自研训练/推理ASIC，成本优势~20-30%"},
    ],
    "MRVL": [
        {"sym": "AVGO", "name": "Broadcom", "angle": "定制ASIC王者，Google TPU/Meta MTIA供应商"},
        {"sym": "NVDA", "name": "NVIDIA", "angle": "通用GPU竞争推理市场"},
        {"sym": "QCOM", "name": "Qualcomm", "angle": "边缘AI芯片竞争"},
    ],
    "MSFT": [
        {"sym": "GOOGL","name": "Google/Alphabet", "angle": "搜索/云/AI全面竞争"},
        {"sym": "AMZN", "name": "Amazon AWS", "angle": "云计算市场领导者"},
        {"sym": "AAPL", "name": "Apple", "angle": "消费端OS+生产力软件"},
    ],
    "BABA": [
        {"sym": "JD",   "name": "京东", "angle": "B2C电商直接竞争"},
        {"sym": "PDD",  "name": "拼多多", "angle": "下沉市场+价格战"},
        {"sym": "AMZN", "name": "Amazon", "angle": "全球电商对标"},
    ],
    "IAU": [
        {"sym": "GLD",  "name": "SPDR Gold ETF", "angle": "最大黄金ETF，费率0.40% vs IAU 0.25%"},
        {"sym": "SGOL", "name": "Aberdeen Gold ETF", "angle": "实物黄金存储在瑞士"},
        {"sym": "GDX",  "name": "VanEck Gold Miners", "angle": "黄金矿业股ETF，杠杆效应更强"},
    ],
    "LITE": [
        {"sym": "COHR", "name": "Coherent (II-VI)", "angle": "最大光模块竞争对手，收购II-VI后规模第一"},
        {"sym": "IINN", "name": "Innolight", "angle": "中国光模块厂商，价格竞争激烈"},
        {"sym": "FNSR", "name": "Finisar/II-VI", "angle": "高速光学器件竞争"},
    ],
}

# ── 特定公司 bull/bear case 知识库 ─────────────────────────────────────
BULL_BEAR_MAP = {
    "NVDA": {
        "bull": [
            "Blackwell 供不应求：GB200 NVLink 系统交货期排到2026年底，CSP Capex 持续创新高",
            "推理市场崛起：ChatGPT/Copilot商业化后推理需求季节性更低、持续性更强",
            "CUDA 生态护城河：数百万研究员代码基于 CUDA，迁移成本极高，AMD ROCm落后3年+",
        ],
        "bear": [
            "估值透支：PE(fwd)=19x 看似合理，但依赖CSP Capex不减速——任何宏观收紧将重创",
            "出口管制黑天鹅：美国进一步限制H20/B20出口将削减中国市场$10B+营收",
        ],
    },
    "BABA": {
        "bull": [
            "估值极度低估：PE=14x，阿里云以AWS估值折扣80%以上，资产折价空间巨大",
            "AI 变现加速：通义千问+阿里云AI产品商业化提速，云业务增速有望重回20%+",
        ],
        "bear": [
            "拼多多/抖音持续蚕食：核心电商市场份额从70%降至50%以下，GMV增速承压",
            "VIE/退市风险：中美关系恶化时中概股结构性风险定价，流动性折价长期存在",
        ],
    },
    "MSFT": {
        "bull": [
            "Copilot 货币化进行时：M365 Copilot $30/月加价覆盖4亿企业用户，潜在TAM超$100B",
            "Azure OpenAI 独家优势：80%+ OpenAI API 流量走 Azure，AI云收入季度环比加速",
        ],
        "bear": [
            "估值消化期：PE(fwd)=31x，需要3-4年高增速才能支撑，任何AI变现低于预期将调整",
            "OpenAI 依赖风险：独家协议到期或竞争对手（Google Gemini）突破将削弱护城河",
        ],
    },
    "IAU": {
        "bull": [
            "央行去美元化趋势：全球央行持续净购金，中国/印度/波兰等增持黄金已是结构性趋势",
            "降息周期受益：美联储降息→实际利率下行→黄金持有成本降低，历史上黄金大涨",
            "地缘风险长期化：中东/俄乌冲突推升避险溢价，黄金替代美债成为全球避险资产",
        ],
        "bear": [
            "高利率延续：美联储鹰派超预期时实际利率上升，黄金无息资产承压",
            "美元指数走强：美元走强时黄金价格通常承压，二者负相关性约-0.6",
        ],
    },
    "MRVL": {
        "bull": [
            "定制ASIC爆发：Google/Amazon/Microsoft三大客户AI芯片定制需求加速，MRVL是核心供应商",
            "以太网AI网络：AI集群扩大推动800G以太网取代InfiniBand，MRVL市场份额领先",
        ],
        "bear": [
            "分析师目标价过时：当前目标价$148低于现价$187，市场已涨过分析师最乐观预期",
            "客户自研风险：Google/Amazon同时是最大客户和自研AI芯片竞争者，随时可能减少外采",
        ],
    },
    "LITE": {
        "bull": [
            "AI光互联核心受益：GPU集群规模化推动800G/1.6T光模块需求指数增长，LITE份额前三",
            "高毛利率+垂直整合：全栈自研降低成本，毛利率有望持续提升",
        ],
        "bear": [
            "竞争加剧：Coherent整合II-VI后规模更大，中国厂商价格战压缩利润空间",
            "客户集中度高：少数云厂商贡献大部分营收，单一客户订单波动影响股价剧烈",
        ],
    },
}

# ── 护城河关键词映射（从财务指标推导）─────────────────────────────────
def _derive_moat(fund: dict) -> list[str]:
    moat = []
    gm   = fund.get("gross_margin") or 0
    roe  = fund.get("roe") or 0
    beta = fund.get("beta") or 1
    rev_g= fund.get("rev_growth_pct") or 0
    n_emp= fund.get("employees") or 0
    sector = fund.get("sector","")

    if gm > 60:
        moat.append(f"超高毛利率（{gm:.0f}%），具备强定价权和差异化竞争优势")
    elif gm > 40:
        moat.append(f"较高毛利率（{gm:.0f}%），具备一定定价能力")

    if roe > 50:
        moat.append(f"ROE={roe:.0f}%，资本效率极高，护城河已转化为超强盈利")
    elif roe > 20:
        moat.append(f"ROE={roe:.0f}%，资本回报率良好，具备竞争优势")

    if rev_g > 50:
        moat.append(f"营收增速+{rev_g:.0f}%，大幅高于行业平均，增长护城河显著")

    if "Technology" in sector or "Semiconductor" in sector:
        moat.append("科技/半导体行业：技术迭代快，研发投入和专利积累构成壁垒")
    elif "Financial" in sector or "Bank" in sector:
        moat.append("金融行业：监管牌照、客户粘性和规模效应构成进入壁垒")
    elif "Consumer" in sector:
        moat.append("消费品行业：品牌认知度和渠道网络构成护城河")

    return moat[:3]


def _derive_growth_drivers(fund: dict, description: str) -> list[str]:
    drivers = []
    rev_g   = fund.get("rev_growth_pct") or 0
    earn_g  = fund.get("earn_growth_pct") or 0
    pe_fwd  = fund.get("pe_fwd") or 0
    sector  = fund.get("sector","")

    if rev_g > 30:
        drivers.append(f"强劲营收增速（+{rev_g:.0f}% YoY），市场对高增长给予溢价估值")
    if earn_g > 30:
        drivers.append(f"盈利增速+{earn_g:.0f}%，经营杠杆释放推动利润增速快于营收")

    # 从描述中提取行业特定驱动
    desc_lower = description.lower()
    if "artificial intelligence" in desc_lower or "ai" in desc_lower:
        drivers.append("AI基础设施需求爆发，超大规模云厂商Capex持续创新高")
    if "data center" in desc_lower:
        drivers.append("数据中心扩张驱动算力需求，云计算/AI训练/推理需求三轮驱动")
    if "automotive" in desc_lower or "vehicle" in desc_lower:
        drivers.append("智能汽车/自动驾驶渗透率提升，汽车芯片需求长期增长")
    if "cloud" in desc_lower or "saas" in desc_lower:
        drivers.append("企业数字化转型持续，SaaS/云订阅收入具备可预期性")
    if "gold" in desc_lower or "precious" in desc_lower:
        drivers.append("通胀/地缘风险环境下黄金避险需求，央行持续增储")

    return drivers[:4]


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_agent_insights(sym: str) -> dict:
    """从 per-sym agent 文件和 narrative 提取 bull/bear case 及补充护城河/增长点"""
    today = _date.today().strftime("%Y-%m-%d")
    bull, bear, moat_extra, growth_extra = [], [], [], []

    # 从各 agent key_points 提取（bullish→bull_case, bearish→bear_case）
    for agent_file in [f"TechAgent_{sym}_{today}.json",
                       f"FundAgent_{sym}_{today}.json",
                       f"SentimentAgent_{sym}_{today}.json",
                       f"MacroAgent_{sym}_{today}.json",
                       f"RiskAgent_{sym}_{today}.json"]:
        d = _load(os.path.join(FIND_DIR, agent_file))
        if not d:
            continue
        sig = d.get("signal", "neutral")
        kps = d.get("key_points", [])
        for kp in kps[:2]:
            if not kp or len(kp) < 10:
                continue
            if sig == "bullish":
                bull.append(kp)
            elif sig == "bearish":
                bear.append(kp)

    # 从 narrative 提取更完整的叙述
    narr = _load(os.path.join(FIND_DIR, f"narrative_{sym}_{today}.json"))
    if narr:
        for key in ("tech", "fund", "sentiment"):
            ag = narr.get("agent_narratives", {}).get(key, {})
            text = ag.get("narrative", "")
            if text and len(text) > 20:
                if ag.get("signal") == "bullish":
                    bull.insert(0, text[:120])
                    break

    return {
        "bull_case":    list(dict.fromkeys(bull))[:4],
        "bear_case":    list(dict.fromkeys(bear))[:3],
        "web_enhanced": bool(bull or bear),
    }


def _merge_bull_bear(sym: str, agent_insights: dict) -> dict:
    """合并硬编码知识库与 agent 提取，硬编码优先（质量更高）"""
    kb = BULL_BEAR_MAP.get(sym.upper(), {})
    bull = kb.get("bull", []) + agent_insights.get("bull_case", [])
    bear = kb.get("bear", []) + agent_insights.get("bear_case", [])
    return {
        "bull_case":    list(dict.fromkeys(bull))[:4],
        "bear_case":    list(dict.fromkeys(bear))[:4],
        "web_enhanced": bool(bull or bear),
    }


def build_company_profile(sym: str) -> dict:
    """构建结构化公司画像，整合 yfinance + 固定知识库 + per-sym agent 数据"""
    sym_upper = sym.upper()
    fund = _load(os.path.join(FIND_DIR, f"fundamentals_{sym_upper}.json"))

    description     = fund.get("description_full") or fund.get("description","")
    long_name       = fund.get("long_name", sym_upper)
    sector          = fund.get("sector","")
    industry        = fund.get("industry","")
    country         = fund.get("country","")
    employees       = fund.get("employees")
    website         = fund.get("website","")

    # 竞争护城河
    moat_points = _derive_moat(fund)

    # 增长驱动
    growth_drivers = _derive_growth_drivers(fund, description)

    # 竞争对手
    competitors = COMPETITOR_MAP.get(sym_upper, [])
    peers_pe    = fund.get("peers_pe", {})

    # 估值锚
    pe_ttm  = fund.get("pe_ttm")
    pe_fwd  = fund.get("pe_fwd")
    peg     = fund.get("peg")
    sector_pe = fund.get("sector_pe")
    pe_premium = None
    if pe_fwd and sector_pe and sector_pe > 0:
        pe_premium = round((pe_fwd / sector_pe - 1) * 100)

    # 分析师共识
    analyst_target = fund.get("target_price")
    analyst_upside = fund.get("target_deviation")
    rec_key        = fund.get("rec_key","")
    n_analysts     = fund.get("n_analysts")

    # 主要风险（通用 + 行业特定）
    risks = []
    beta = fund.get("beta") or 1
    if beta and beta > 1.5:
        risks.append(f"高Beta={beta:.1f}x，大盘波动时股价放大{beta:.0f}倍，波动性风险高")
    short_pct = fund.get("short_pct") or 0
    if short_pct and short_pct > 5:
        risks.append(f"空头比例{short_pct:.1f}%较高，存在做空压力")
    if pe_premium and pe_premium > 30:
        risks.append(f"相对板块溢价{pe_premium}%，估值偏高，增长不及预期将面临估值压缩")
    debt = fund.get("debt_to_equity") or 0
    if debt and debt > 100:
        risks.append(f"负债率{debt:.0f}%，高杠杆在利率上行时面临偿债压力")

    # 特定公司补充知识
    if sym_upper == "NVDA":
        risks.insert(0, "出口管制风险：美国对华芯片出口限制已造成Q1 $4.5B减值，持续恶化是最大变数")
        risks.insert(1, "竞争加速：超大规模云厂商同时是最大客户和自研ASIC竞争者")
    elif sym_upper == "BABA":
        moat_points += [
            "电商生态护城河：淘宝/天猫 GMV 规模全球最大，买家/卖家双边网络效应难以复制",
            "阿里云：中国第一、亚太第一的云计算平台，AI基础设施先发优势5年以上",
            "支付宝/蚂蚁：14亿用户金融生态，支付→消费贷→理财垂直整合",
            "菜鸟物流：自建物流网络覆盖全国，电商履约竞争优势",
        ]
        growth_drivers += [
            "阿里云 AI 变现：文生图/大模型 API 商业化加速，云收入增速有望重回 20%+",
            "国际电商增速：Lazada/速卖通/Temu竞争中海外GMV仍保持双位数增长",
            "股票回购：过去12个月累计回购超$100亿，EPS 增速快于营收",
        ]
        risks += [
            "中美关系/监管不确定性：中概股退市风险、VIE 结构法律风险长期存在",
            "竞争全面加剧：拼多多/抖音电商蚕食市场份额，价格战压缩利润率",
            "中国经济复苏低于预期：消费降级影响GMV增速，B端需求疲软影响云业务",
        ]
    elif sym_upper == "MSFT":
        moat_points += [
            "企业软件生态锁定：Office 365/Teams/Azure 深度绑定企业 IT，切换成本极高",
            "GitHub + VS Code + Azure DevOps：开发者生态垄断，Copilot 变现路径最短",
            "Azure OpenAI 独家合作：与 OpenAI 排他性合作，领先竞争对手6-12个月",
        ]
        growth_drivers += [
            "Copilot 商业化：企业 M365 Copilot 每月$30/用户加价，潜在 TAM 超$100B",
            "Azure AI 服务：OpenAI API 流量 80%+ 走 Azure，云 AI 收入季度环比加速",
            "游戏/媒体：动视暴雪整合后 GamePass 订阅增长，Xbox 内容护城河加深",
        ]
        risks += [
            "反垄断监管：欧盟/美国对 Teams/Office 捆绑调查，结构性拆分风险",
            "OpenAI 依赖：独家合作到期或 OpenAI 估值崩塌将影响 Azure AI 叙事",
        ]
    elif sym_upper in ("IAU", "GLD"):
        moat_points += [
            "实物黄金 ETF：直接持有金条，成本最低（0.25%）的黄金敞口工具",
            "流动性最强的黄金 ETF 之一：日均成交额高，机构和散户均可高效配置",
        ]
        growth_drivers += [
            "央行购金加速：新兴市场央行持续增加黄金储备，去美元化长期趋势",
            "地缘风险溢价：中东/俄乌冲突持续推升避险需求",
            "实际利率下行预期：美联储降息周期黄金表现通常优于股票",
        ]
        risks.insert(0, "美联储鹰派延续：高利率抑制无息资产吸引力，实际利率上行是黄金最大压力")
        risks.append("美元走强：美元指数上涨时黄金通常承压")
    elif sym_upper == "MRVL":
        moat_points += [
            "定制 ASIC 设计能力：为 Google、Amazon、Microsoft 定制 AI 训练/推理芯片，客户粘性极高",
            "以太网 AI 网络芯片：Prestera/Teralynx 系列在超大规模数据中心网络中份额领先",
            "5G 基带与云RAN：与全球主要运营商深度合作，多年研发积累形成壁垒",
        ]
        growth_drivers += [
            "定制 AI ASIC 需求爆发：Google/Amazon/Microsoft 均在加速自研 AI 芯片，MRVL 是核心供应商",
            "以太网取代 InfiniBand 趋势：AI 集群规模扩大推动高速以太网需求，MRVL 是最大受益者",
        ]
        risks += [
            "客户集中度高：Google/Amazon/Microsoft 三家合计贡献大部分定制 ASIC 营收，订单波动风险大",
            "ASIC 定制周期长（2-3年）：量产前持续烧钱研发，一旦客户更换供应商损失惨重",
        ]
    elif sym_upper == "LITE":
        moat_points += [
            "光模块技术领先：400G/800G 高速光模块市场份额前三，AI 数据中心网络互联核心器件",
            "垂直整合能力：从激光器芯片到完整模块全栈自研，成本控制和性能优化优势明显",
        ]
        growth_drivers += [
            "AI 数据中心光互联需求爆发：GPU 集群规模扩大推动 800G/1.6T 光模块需求指数增长",
            "云厂商 Capex 创新高：微软/谷歌/Meta 数据中心扩张直接带动光模块采购",
        ]
        risks += [
            "竞争激烈：Coherent、II-VI、Innolight 等均在抢占 800G 份额",
            "客户集中度风险：少数超大规模云厂商贡献主要营收",
        ]

    return {
        "sym":          sym_upper,
        "long_name":    long_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sector":       sector,
        "industry":     industry,
        "country":      country,
        "employees":    employees,
        "website":      website,

        # 业务描述（原始 + 精简）
        "business_summary":     description[:500] if description else "",
        "business_summary_full": description,

        # 竞争护城河
        "competitive_moat": moat_points,

        # 增长驱动
        "growth_drivers": growth_drivers,

        # 竞争格局
        "competitors": competitors,
        "peers_pe":    peers_pe,

        # 估值锚
        "valuation_anchors": {
            "pe_ttm":      pe_ttm,
            "pe_fwd":      pe_fwd,
            "peg":         peg,
            "sector_pe":   sector_pe,
            "pe_premium_pct": pe_premium,
            "analyst_target": analyst_target,
            "analyst_upside_pct": analyst_upside,
            "rec_key":     rec_key,
            "n_analysts":  n_analysts,
        },

        # 主要风险
        "key_risks": risks[:5],

        # 合并硬编码知识库 + agent 提取的 bull/bear case
        **_merge_bull_bear(sym_upper, _load_agent_insights(sym_upper)),
        "revenue_breakdown": [],
        "latest_catalysts":  [],
    }


def write_company_profile(sym: str, data: dict) -> str:
    os.makedirs(FIND_DIR, exist_ok=True)
    path = os.path.join(FIND_DIR, f"company_profile_{sym.upper()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def main(syms: list[str] | None = None):
    if not syms:
        cfg  = _load(os.path.join(BASE, "config", "poll_config.json"))
        pos  = _load(os.path.join(BASE, "config", "positions.json"))
        syms = list({*cfg.get("default_symbols",[]),
                     *[k for k in pos.get("positions",{}) if not k.startswith("_")]})

    print(f"\n生成公司画像（{len(syms)} 只）\n")
    for sym in syms:
        profile = build_company_profile(sym)
        path    = write_company_profile(sym, profile)
        moat_n  = len(profile.get("competitive_moat",[]))
        risk_n  = len(profile.get("key_risks",[]))
        print(f"  {sym}: 护城河{moat_n}条 / 风险{risk_n}条 → ✅ {os.path.basename(path)}")


if __name__ == "__main__":
    main(sys.argv[1:] if len(sys.argv) > 1 else None)
