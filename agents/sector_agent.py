"""SectorAgent — 自动识别板块、找同行标的、计算相对强弱"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, fetch_with_retry, atomic_write_json
log = get_logger(__name__)
from agents.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)
import yfinance as yf

# ── 公司级别精确覆盖（优先于行业自动识别）──────────────────────────────
# 适用于跨赛道、细分行业 yfinance 无法区分的知名公司
COMPANY_OVERRIDES = {
    "AMD": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "CPU/GPU/AI加速器板块",
        "tags": ["CPU(Ryzen/EPYC)", "GPU(Radeon/RDNA)", "AI加速器(MI系列)", "数据中心"],
        "peers": ["NVDA","INTC","QCOM","ARM","MRVL","MU","AVGO","TSM"],
        "note": "AMD横跨CPU、GPU、AI数据中心三大赛道，与NVDA AI竞争最直接"
    },
    "NVDA": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "GPU/AI训练推理板块",
        "tags": ["GPU(GeForce/H系列)", "AI训练(H100/H200)", "CUDA生态", "数据中心"],
        "peers": ["AMD","INTC","QCOM","ARM","MRVL","AVGO","TSM","AMAT"],
        "note": "AI算力核心标的，GPU市场份额>80%，CUDA护城河极深"
    },
    "INTC": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "CPU/代工板块",
        "tags": ["CPU(Core/Xeon)", "代工(Intel Foundry)", "AI加速器(Gaudi)"],
        "peers": ["AMD","NVDA","QCOM","ARM","TSM","AVGO","MU"],
        "note": "传统CPU龙头+代工业务转型，目前基本面承压，市场炒反转预期"
    },
    "ARM": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "芯片IP/架构授权板块",
        "tags": ["芯片架构授权", "移动CPU(Cortex)", "AI加速器IP", "RISC-V竞争"],
        "peers": ["NVDA","AMD","QCOM","MRVL","AVGO","TSM","AMAT"],
        "note": "全球90%移动芯片用ARM架构，AI时代向数据中心扩张，版税模式高利润"
    },
    "QCOM": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "移动/汽车芯片板块",
        "tags": ["移动SoC(骁龙)", "汽车芯片", "AI手机(Copilot+PC)", "5G基带"],
        "peers": ["AMD","NVDA","ARM","MRVL","AVGO","MTK","NXPI"],
        "note": "移动芯片霸主，正向PC和汽车拓展，骁龙X Elite是PC AI芯片重磅"
    },
    "MRVL": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "数据中心定制芯片板块",
        "tags": ["定制ASIC", "以太网芯片", "光互联IC", "AI加速器定制"],
        "peers": ["AVGO","NVDA","AMD","CIEN","LITE","COHR"],
        "note": "AI数据中心定制芯片+光互联两条腿，收购Polariton加码光计算"
    },
    "MSFT": {
        "etf": "IGV", "etf_name": "软件ETF",
        "name": "云计算/AI软件平台板块",
        "tags": ["Azure云", "OpenAI合作(Copilot)", "企业软件(Office365)", "游戏(Xbox)"],
        "peers": ["GOOG","AMZN","META","ORCL","CRM","NOW","ADBE"],
        "note": "AI时代最均衡的大型科技股，Azure AI增速强劲，估值比NVDA合理"
    },
    "AAOI": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "光学/光模块板块",
        "tags": ["光收发模块", "AI数据中心互联", "400G/800G光模块"],
        "peers": ["LITE","COHR","CIEN","VIAV","CALX","IIVI"],
        "note": "AI数据中心800G光模块需求爆发直接受益者，小盘高弹性"
    },
    "LITE": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "光学/光模块板块",
        "tags": ["光器件(ROADM)", "高速光模块", "AI数据中心互联", "纳入Nasdaq100"],
        "peers": ["AAOI","COHR","CIEN","VIAV","CALX","IIVI"],
        "note": "光模块龙头，纳入Nasdaq100带来机构被动买入持续压力"
    },
    "OXY": {
        "etf": "XOP", "etf_name": "油气ETF",
        "name": "油气勘探/生产板块",
        "tags": ["石油勘探(Permian盆地)", "化工(OxyChem)", "碳捕集(DAC)", "Buffett持仓"],
        "peers": ["CVX","XOM","COP","PXD","EOG","SLB","DVN"],
        "note": "Buffett伯克希尔第三大持仓，低成本Permian资产+碳捕集技术布局"
    },
    "RKLB": {
        "etf": "ITA", "etf_name": "航空航天ETF",
        "name": "商业航天板块",
        "tags": ["火箭发射(Electron)", "中型火箭(Neutron)", "卫星制造", "太空服务"],
        "peers": ["SPCE","BA","LMT","NOC","ASTR","MNTS"],
        "note": "商业小卫星发射龙头，Neutron中型火箭进军SpaceX市场"
    },
    "OKLO": {
        "etf": "NLR", "etf_name": "核能ETF",
        "name": "先进核能/小型堆板块",
        "tags": ["微型核反应堆(Aurora)", "AI数据中心供电", "核燃料回收"],
        "peers": ["SMR","CCJ","NNE","BWXT","LEU","BWX"],
        "note": "AI数据中心电力需求激增背景下，小型堆(SMR)概念龙头"
    },
    "IREN": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "AI算力/数字矿山板块",
        "tags": ["比特币挖矿", "AI算力租赁", "NVIDIA合作($34亿)", "可转债融资"],
        "peers": ["MARA","RIOT","CLSK","HUT","BTBT","CORZ"],
        "note": "从矿场转型AI算力，与NVIDIA签$34亿合作，但$20亿可转债稀释是风险"
    },
    "CRWV": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "AI云算力/租赁板块",
        "tags": ["GPU云租赁", "AI推理算力", "NVIDIA下游", "新上市IPO"],
        "peers": ["IREN","MARA","NVDA","AMZN","GOOG","MSFT"],
        "note": "AI算力租赁新IPO，商业模式依赖NVIDIA供货，负债高，尚未盈利"
    },
    "MRVL": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "数据中心定制芯片板块",
        "tags": ["定制ASIC", "以太网芯片", "光互联IC", "AI加速器定制"],
        "peers": ["AVGO","NVDA","AMD","CIEN","LITE","COHR"],
        "note": "AI数据中心定制芯片+光互联，收购Polariton加码光计算"
    },
    "SNDK": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "闪存/存储板块",
        "tags": ["NAND闪存", "固态硬盘(SSD)", "从WD分拆上市"],
        "peers": ["MU","KIOXIA","STX","WDC","AMAT"],
        "note": "SanDisk从Western Digital分拆，2025年新上市，NAND闪存市场"
    },
}

# ── 行业 ETF + 核心同行映射表 ──────────────────────────────────────────
INDUSTRY_MAP = {
    # key: yfinance info["industry"] 的关键词（做 partial match）
    "Semiconductors": {
        "etf": "SOXX", "etf_name": "半导体ETF",
        "name": "半导体/芯片板块",
        "peers": ["NVDA","AMD","INTC","QCOM","MRVL","ARM","MU","AMAT","TSM","AVGO"],
    },
    "Electronic Components": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "光学/光模块板块",
        "peers": ["LITE","COHR","AAOI","IIVI","NLIGHT","ACIA"],
    },
    "Communication Equipment": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "光学/通信器件板块",
        "peers": ["LITE","COHR","AAOI","CIEN","INFN","CALX","VIAV"],
    },
    "Capital Markets": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "AI算力/数字矿山板块",
        "peers": ["IREN","MARA","RIOT","CLSK","HUT","BTBT"],
    },
    "Software—Application": {
        "etf": "IGV", "etf_name": "软件ETF",
        "name": "企业软件板块",
        "peers": ["MSFT","CRM","NOW","ADBE","ORCL","WDAY","HUBS"],
    },
    "Software—Infrastructure": {
        "etf": "IGV", "etf_name": "软件ETF",
        "name": "基础设施软件板块",
        "peers": ["MSFT","ORCL","VMW","DDOG","SNOW","MDB"],
    },
    "Internet Content": {
        "etf": "ARKW", "etf_name": "互联网ETF",
        "name": "互联网/社媒板块",
        "peers": ["META","GOOG","GOOGL","SNAP","PINS","RDDT"],
    },
    "Computer Hardware": {
        "etf": "XLK", "etf_name": "科技ETF",
        "name": "计算机硬件板块",
        "peers": ["AAPL","HPQ","DELL","HPE","NTAP"],
    },
    "Oil": {
        "etf": "XOP", "etf_name": "油气开采ETF",
        "name": "油气勘探板块",
        "peers": ["OXY","CVX","XOM","COP","PXD","EOG","MPC","VLO"],
    },
    "Nuclear": {
        "etf": "NLR", "etf_name": "核能ETF",
        "name": "核能板块",
        "peers": ["OKLO","SMR","CCJ","NNE","BWXT","LEU"],
    },
    "Aerospace": {
        "etf": "ITA", "etf_name": "航空航天ETF",
        "name": "航空航天板块",
        "peers": ["RKLB","SPCE","BA","LMT","RTX","NOC","ASTR"],
    },
    "Biotechnology": {
        "etf": "XBI", "etf_name": "生物科技ETF",
        "name": "生物科技板块",
        "peers": ["MRNA","BNTX","REGN","BIIB","VRTX","GILD","AMGN"],
    },
    "Banks": {
        "etf": "KBE", "etf_name": "银行ETF",
        "name": "银行板块",
        "peers": ["JPM","BAC","WFC","C","GS","MS","USB"],
    },
    # AI/云计算通用映射（sector-level fallback）
    "Technology": {
        "etf": "QQQ", "etf_name": "纳斯达克100ETF",
        "name": "科技板块",
        "peers": ["AAPL","MSFT","NVDA","GOOG","META","AMZN"],
    },
    "Energy": {
        "etf": "XLE", "etf_name": "能源ETF",
        "name": "能源板块",
        "peers": ["XOM","CVX","OXY","COP","SLB","HAL"],
    },
    "Healthcare": {
        "etf": "XLV", "etf_name": "医疗ETF",
        "name": "医疗健康板块",
        "peers": ["JNJ","UNH","LLY","MRK","ABBV","PFE"],
    },
    # 数字矿山/AI算力
    "Utilities": {
        "etf": "XLU", "etf_name": "公用事业ETF",
        "name": "公用事业/算力板块",
        "peers": ["IREN","MARA","RIOT","CLSK","HUT"],
    },
}

CRYPTO_MINING_TICKERS = {"IREN","MARA","RIOT","CLSK","HUT","BTBT","CIFR"}

# 行业关键词 → 映射 key（模糊匹配）
INDUSTRY_KEYWORDS = {
    "semiconductor": "Semiconductors",
    "electronic component": "Electronic Components",
    "optical": "Electronic Components",
    "photon": "Electronic Components",
    "communication equipment": "Communication Equipment",
    "capital markets": "Capital Markets",
    "software—application": "Software—Application",
    "software—infra": "Software—Infrastructure",
    "internet content": "Internet Content",
    "internet retail": "Internet Content",
    "computer hardware": "Computer Hardware",
    "oil & gas": "Oil",
    "oil gas": "Oil",
    "nuclear": "Nuclear",
    "aerospace": "Aerospace",
    "biotechnology": "Biotechnology",
    "banks": "Banks",
    "bank—": "Banks",
}

def find_sector_info(symbol, info):
    """根据公司 override 或 yfinance info 找到最匹配的行业配置。"""
    sym_upper = symbol.upper()

    # 最高优先：公司级别 override
    if sym_upper in COMPANY_OVERRIDES:
        ov = COMPANY_OVERRIDES[sym_upper]
        cfg = {
            "etf": ov["etf"], "etf_name": ov["etf_name"],
            "name": ov["name"], "peers": ov["peers"],
        }
        return cfg, ov["name"], ov.get("note", "")

    industry = (info.get("industry") or "").lower()
    sector   = (info.get("sector") or "").lower()

    # 特殊处理：加密矿山/AI算力
    if sym_upper in CRYPTO_MINING_TICKERS:
        return INDUSTRY_MAP["Utilities"], "AI算力/数字矿山板块", industry

    # 精确行业匹配（优先）
    industry_title = info.get("industry") or ""
    if industry_title in INDUSTRY_MAP:
        return INDUSTRY_MAP[industry_title], INDUSTRY_MAP[industry_title]["name"], industry_title

    # 行业关键词匹配（fallback）
    for kw, map_key in INDUSTRY_KEYWORDS.items():
        if kw in industry:
            return INDUSTRY_MAP[map_key], INDUSTRY_MAP[map_key]["name"], industry

    # sector 级别 fallback
    for key in ["Technology","Energy","Healthcare"]:
        if key.lower() in sector:
            return INDUSTRY_MAP[key], INDUSTRY_MAP[key]["name"], industry

    return None, f"{info.get('sector','未知')}/{info.get('industry','未知')}", industry

def fetch_relative_strength(symbol, peers, etf, period="10d"):
    """计算个股相对 ETF 和同行的强弱。"""
    results = {}
    all_tickers = list({symbol} | set(peers[:6]) | {etf})

    for sym in all_tickers:
        try:
            h = fetch_with_retry(lambda: yf.Ticker(sym).history(period="20d"))
            if h.empty or len(h) < 2:
                continue
            last = float(h["Close"].iloc[-1])
            prev1 = float(h["Close"].iloc[-2]) if len(h)>1 else last
            prev5 = float(h["Close"].iloc[-5]) if len(h)>4 else last
            prev10= float(h["Close"].iloc[-10]) if len(h)>9 else last
            results[sym] = {
                "last":  last,
                "chg1":  (last-prev1)/prev1*100,
                "chg5":  (last-prev5)/prev5*100,
                "chg10": (last-prev10)/prev10*100,
            }
        except Exception:
            continue
    return results

def analyze(symbol):
    """Identify sector, compute relative strength vs ETF and peers, rank within sector."""
    t    = yf.Ticker(symbol)
    info = fetch_with_retry(lambda: t.info)

    sector_config, sector_name, raw_industry = find_sector_info(symbol, info)

    if not sector_config:
        return "neutral", 50, [f"板块未识别：{sector_name}"], [], {}

    etf      = sector_config["etf"]
    etf_name = sector_config["etf_name"]
    peers    = [p for p in sector_config["peers"] if p.upper() != symbol.upper()]

    # 拉相对强弱数据
    rs_data  = fetch_relative_strength(symbol, peers, etf)
    sym_data = rs_data.get(symbol.upper(), {})
    etf_data = rs_data.get(etf, {})

    points = []
    score  = 0

    # 板块 ETF 表现
    if etf_data:
        e10 = etf_data.get("chg10", 0)
        e5  = etf_data.get("chg5", 0)
        e1  = etf_data.get("chg1", 0)
        tag = "🟢" if e10 > 5 else "🔴" if e10 < -5 else "🟡"
        points.append(f"── {sector_name} ──")
        points.append(f"{tag} [{etf_name}] 10日{e10:+.1f}% / 5日{e5:+.1f}% / 1日{e1:+.1f}%")
        if e10 > 5:   score += 15
        elif e10 < -5: score -= 15

    # 个股 vs ETF 相对强弱
    if sym_data and etf_data:
        rs10 = sym_data.get("chg10",0) - etf_data.get("chg10",0)
        rs5  = sym_data.get("chg5", 0) - etf_data.get("chg5", 0)
        rs_icon = "💪" if rs10 > 5 else "📉" if rs10 < -5 else "📊"
        points.append(f"{rs_icon} {symbol} 相对板块强弱: 10日{rs10:+.1f}% / 5日{rs5:+.1f}%")
        if rs10 > 10:  score += 20
        elif rs10 > 3: score += 10
        elif rs10 < -10: score -= 20
        elif rs10 < -3: score -= 10

    # 同行对比（按10日涨幅排序）
    peer_rows = []
    for p, d in rs_data.items():
        if p == symbol.upper() or p == etf:
            continue
        peer_rows.append((p, d.get("chg10",0), d.get("chg5",0), d.get("chg1",0)))
    peer_rows.sort(key=lambda x: x[1], reverse=True)

    if peer_rows:
        points.append("同行近期表现（10日/5日/1日）:")
        for p, c10, c5, c1 in peer_rows[:6]:
            icon = "🟢" if c10 > 10 else "🔴" if c10 < -5 else "🟡"
            flag = " ← 你" if p == symbol.upper() else ""
            points.append(f"  {icon} {p:6s}  {c10:>+6.1f}%  {c5:>+6.1f}%  {c1:>+6.1f}%{flag}")

        # 个股在板块中的相对排名
        all_ranked = sorted([(p,d10) for p,d10,_,_ in peer_rows] +
                            [(symbol.upper(), sym_data.get("chg10",0))],
                            key=lambda x: x[1], reverse=True)
        rank  = next((i+1 for i,v in enumerate(all_ranked) if v[0]==symbol.upper()), None)
        total = len(all_ranked)
        if rank:
            rank_icon = "🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else f"#{rank}"
            points.append(f"板块排名: {rank_icon} / {total}  (10日涨幅)")
            if rank <= total//3:   score += 15
            elif rank >= total*2//3: score -= 15

    signal     = "bullish" if score >= 20 else "bearish" if score <= -10 else "neutral"
    confidence = min(85, 50 + abs(score))
    refs       = [{"field": "sector_etf", "verified": False, "source": "yfinance"}]

    # ── 推理链 ────────────────────────────────────────────────────────────
    analysis = []

    # 板块 ETF 整体强弱推理
    if etf_data:
        e10 = etf_data.get("chg10", 0)
        if e10 > 5:
            analysis.append(f"板块ETF [{etf_name}] 10日{e10:+.1f}%，板块处于上行趋势，个股有顺风")
        elif e10 < -5:
            analysis.append(f"板块ETF [{etf_name}] 10日{e10:+.1f}%，板块处于弱势，逆风中个股上涨难度更大")
        else:
            analysis.append(f"板块ETF [{etf_name}] 10日{e10:+.1f}%，板块整体横盘整理，方向不明")

    # 个股相对板块强弱推理
    if sym_data and etf_data:
        rs10 = sym_data.get("chg10", 0) - etf_data.get("chg10", 0)
        rs5  = sym_data.get("chg5",  0) - etf_data.get("chg5",  0)
        if rs10 > 5:
            analysis.append(f"个股RS领先板块{rs10:.1f}%（10日），是本板块的龙头标的，资金优先流入龙头")
        elif rs10 < -5:
            analysis.append(f"个股RS落后板块{abs(rs10):.1f}%（10日），是板块内的弱势标的，资金在回避它")
        else:
            analysis.append(f"个股相对板块10日RS差值{rs10:+.1f}%，与板块基本同步，无明显超额或落后")
        if rs5 > 3:
            analysis.append(f"5日RS差值{rs5:+.1f}%，近期相对强势在加速")
        elif rs5 < -3:
            analysis.append(f"5日RS差值{rs5:+.1f}%，近期相对弱势在扩大，需警惕")

    # 板块排名推理
    if peer_rows:
        all_ranked = sorted([(p, d10) for p, d10, _, _ in peer_rows] +
                            [(symbol.upper(), sym_data.get("chg10", 0))],
                            key=lambda x: x[1], reverse=True)
        rank  = next((i+1 for i, v in enumerate(all_ranked) if v[0] == symbol.upper()), None)
        total = len(all_ranked)
        if rank:
            if rank <= total // 3:
                analysis.append(f"板块内排名第{rank}/{total}，处于头部梯队，资金偏好显著")
            elif rank >= total * 2 // 3:
                analysis.append(f"板块内排名第{rank}/{total}，处于尾部梯队，相对同行明显落后")
            else:
                analysis.append(f"板块内排名第{rank}/{total}，中等位置，无明显板块内优势")

    # ── 专业结论 ──────────────────────────────────────────────────────────
    if signal == "bullish":
        judgment   = "板块地位看多：个股在板块内处于龙头位置，板块行情有利"
        boundary   = "若板块整体转弱或个股RS开始落后板块，板块优势减弱"
        challenge  = "Druckenmiller会问：这个板块在整个宏观周期里是顺风还是逆风？板块轮动到了哪个阶段？"
    elif signal == "bearish":
        judgment   = "板块地位看空：个股在板块内处于弱势，板块行情不利"
        boundary   = "若个股RS转强或板块整体反转，空头依据减弱"
        challenge  = "Soros会问：板块弱势是否创造了反身性的反弹条件？"
    else:
        judgment   = "板块地位中性：个股与板块同步，无明显超额"
        boundary   = "等待个股RS相对板块出现明显偏离（超出或落后超过5%）"
        challenge  = "Livermore会问：如果没有板块领涨优势，为什么选这只而不是板块ETF？"

    conclusion = {
        "judgment":             judgment,
        "boundary":             boundary,
        "anticipated_challenge": challenge,
    }

    return signal, confidence, points, refs, {
        "sector": sector_name, "etf": etf, "peers": peers[:6], "rs_data": rs_data
    }, analysis, conclusion

def main():
    """Parse args, run sector analysis, and write finding JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()

    os.makedirs(FINDINGS_DIR, exist_ok=True)
    signal, conf, points, refs, extra, analysis, conclusion = analyze(args.symbol)
    _data = {}
    if os.path.exists(VERIFIED_PATH):
        raw = json.load(open(VERIFIED_PATH, encoding="utf-8")).get("fields", {})
        _data = {k: v.get("value") if isinstance(v, dict) else v for k, v in raw.items()}
    board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []

    if args.round is None:
        msg = make_finding("SectorAgent", args.symbol, signal, conf, points, refs,
                           analysis=analysis, conclusion=conclusion)
        msg["sector_info"] = extra
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, "SectorAgent.json"), indent=2)
    else:
        msg = compute_phase2_response("SectorAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            atomic_write_json({}, os.path.join(FINDINGS_DIR, f"SectorAgent_r{args.round}.json"))
            return
        msg["sector_info"] = extra
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, f"SectorAgent_r{args.round}.json"), indent=2)

if __name__ == "__main__":
    main()
