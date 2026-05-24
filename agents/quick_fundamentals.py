"""
quick_fundamentals.py — 个股基本面数据一站式获取

用法：
    python3.12 agents/quick_fundamentals.py MRVL
    python3.12 agents/quick_fundamentals.py NVDA --json

在分析前调用，确保数据完备。
"""
import sys, os, json, argparse
import yfinance as yf
from datetime import datetime, timezone

def fetch(sym: str) -> dict:
    """
    拉取 yfinance 所有 Tier 1/Tier 2 数据，返回结构化 dict。
    失败字段设为 None，不抛出异常。
    对 curl_cffi SSL 错误自动重试最多 3 次。
    """
    import time as _time
    t = yf.Ticker(sym)
    info = {}
    last_err = None
    for _attempt in range(3):
        try:
            info = t.info or {}
            if info:  # 成功拿到数据
                break
        except Exception as e:
            last_err = str(e)
            if 'SSL' in last_err or 'TLS' in last_err or 'curl' in last_err.lower():
                print(f"  ⚠️ yfinance SSL error (attempt {_attempt+1}/3): {last_err[:80]}")
                _time.sleep(2 * (_attempt + 1))  # 递增等待
                t = yf.Ticker(sym)  # 重建 ticker 对象以重置连接
                continue
            break  # 非 SSL 错误不重试

    # 记录数据抓取状态
    try:
        from agents.error_logger import record_yfinance_status
        if info:
            record_yfinance_status(sym, True)
        else:
            record_yfinance_status(sym, False, last_err or "Empty info dictionary returned from yfinance")
    except Exception:
        pass

    def g(key, default=None):
        v = info.get(key)
        return v if v is not None else default

    # ── 价格 ───────────────────────────────────────────────────
    cur  = g('currentPrice') or g('regularMarketPrice')
    prev = g('regularMarketPreviousClose')
    chg  = round((cur - prev) / prev * 100, 2) if cur and prev else None

    # ── 估值 ──────────────────────────────────────────────────
    target  = g('targetMeanPrice')
    tgt_dev = round((target - cur) / cur * 100, 1) if target and cur else None
    rec     = g('recommendationMean')   # 1=强买 … 5=强卖
    n_ana   = g('numberOfAnalystOpinions')

    # ── 基本面 ────────────────────────────────────────────────
    rev_growth_pct = round(g('revenueGrowth', 0) * 100, 1)
    earn_growth_pct = round(g('earningsGrowth', 0) * 100, 1)

    fcf = g('freeCashflow')
    fcf_b = round(fcf / 1e9, 2) if fcf else None

    rev = g('totalRevenue')
    rev_b = round(rev / 1e9, 2) if rev else None

    cash = g('totalCash')
    cash_b = round(cash / 1e9, 2) if cash else None

    # ── 季度营收 YoY ──────────────────────────────────────────
    q_rev_growth = None
    try:
        qf = t.quarterly_financials
        if 'Total Revenue' in qf.index and len(qf.columns) >= 5:
            r = qf.loc['Total Revenue']
            q_rev_growth = round((r.iloc[0] - r.iloc[4]) / abs(r.iloc[4]) * 100, 1)
    except Exception:
        pass

    # ── 内部人 ────────────────────────────────────────────────
    insider_buy_3m = None
    try:
        ins = t.insider_transactions
        if ins is not None and not ins.empty:
            recent = ins.head(20)
            buys = recent[recent['Transaction'].str.contains('Purchase', na=False)]
            insider_buy_3m = int(buys['Shares'].sum()) if not buys.empty else 0
    except Exception:
        pass

    # ── 风险指标 ──────────────────────────────────────────────
    short_pct = g('shortPercentOfFloat')
    short_pct_fmt = round(short_pct * 100, 1) if short_pct else None

    # ── 公司概况（之前完全缺失）─────────────────────────────────────────
    long_name   = g('longName') or g('shortName') or sym.upper()
    sector      = g('sector') or g('sectorKey', '').replace('-',' ').title()
    industry    = g('industry') or g('industryKey', '').replace('-',' ').title()
    description = g('longBusinessSummary', '')
    employees   = g('fullTimeEmployees')
    country     = g('country')
    website     = g('website')

    # ── 同行对比（固定映射 + 动态获取板块 ETF PE）─────────────────────
    SECTOR_ETF_MAP = {
        'Technology': 'XLK', 'Communication Services': 'XLC',
        'Consumer Discretionary': 'XLY', 'Consumer Staples': 'XLP',
        'Energy': 'XLE', 'Financials': 'XLF', 'Health Care': 'XLV',
        'Industrials': 'XLI', 'Materials': 'XLB', 'Real Estate': 'XLRE',
        'Utilities': 'XLU',
        'Semiconductors': 'SOXX', 'Software': 'IGV',
        'Biotech': 'XBI', 'Banks': 'KBE', 'Gold': 'GDX',
    }
    PEER_MAP = {
        'NVDA': ['AMD', 'INTC', 'QCOM', 'AVGO'],
        'MRVL': ['NVDA', 'AVGO', 'QCOM', 'BRCM'],
        'MSFT': ['GOOGL', 'AAPL', 'AMZN', 'META'],
        'AAPL': ['MSFT', 'GOOGL', 'META', 'AMZN'],
        'AMZN': ['MSFT', 'GOOGL', 'BABA', 'JD'],
        'BABA': ['JD', 'PDD', 'AMZN', 'MSFT'],
        'IAU':  ['GLD', 'SGOL', 'PHYS'],
        'GLD':  ['IAU', 'SGOL', 'GDX'],
        'LITE': ['IIVI', 'FNSR', 'NPTN', 'AAOI'],
    }
    sector_etf  = SECTOR_ETF_MAP.get(sector, SECTOR_ETF_MAP.get(industry, ''))
    peers_list  = PEER_MAP.get(sym.upper(), [])

    # 板块 ETF PE
    sector_pe = None
    try:
        if sector_etf:
            etf_info = yf.Ticker(sector_etf).info
            sector_pe = etf_info.get('trailingPE') or etf_info.get('forwardPE')
            if sector_pe:
                sector_pe = round(sector_pe, 1)
    except Exception:
        pass

    # 同行 PE 快速对比（只取 forwardPE，避免太慢）
    peers_pe = {}
    try:
        for p in peers_list[:3]:
            pinfo = yf.Ticker(p).fast_info
            pprice = getattr(pinfo, 'last_price', None)
            if pprice:
                # fast_info 没有 PE，改用 info 里的 forwardPE
                pdata = yf.Ticker(p).info
                ppe = pdata.get('forwardPE') or pdata.get('trailingPE')
                if ppe:
                    peers_pe[p] = round(ppe, 1)
    except Exception:
        pass

    # ── 额外财务质量指标 ─────────────────────────────────────────────
    operating_margin = round(g('operatingMargins', 0) * 100, 1)
    current_ratio    = g('currentRatio')
    price_to_book    = g('priceToBook')
    rec_key          = g('recommendationKey', '')   # 'strong_buy'/'buy'/'hold' 等

    result = {
        "sym":              sym.upper(),
        "fetched_at":       datetime.now(timezone.utc).isoformat(),

        # ── 公司概况（新增）──────────────────────────────────────────
        "long_name":        long_name,
        "sector":           sector,
        "industry":         industry,
        "country":          country,
        "website":          website,
        "employees":        employees,
        "description":      description[:500] if description else "",
        "description_full": description,

        # ── 同行对比（新增）──────────────────────────────────────────
        "sector_etf":       sector_etf,
        "sector_pe":        sector_pe,   # 板块 ETF 的 PE，与个股对比
        "peers":            peers_list,
        "peers_pe":         peers_pe,    # {SYM: pe} 快速对比

        # 价格
        "cur":              cur,
        "chg_pct":          chg,
        "hi52":             g('fiftyTwoWeekHigh'),
        "lo52":             g('fiftyTwoWeekLow'),
        "beta":             g('beta'),
        "mktcap_B":         round(g('marketCap', 0) / 1e9, 1),

        # 估值
        "pe_ttm":           g('trailingPE'),
        "pe_fwd":           g('forwardPE'),
        "price_to_book":    price_to_book,
        "eps_fwd":          g('forwardEps'),
        "peg":              g('pegRatio'),
        "target_price":     target,
        "target_deviation": tgt_dev,
        "rec_mean":         rec,
        "rec_key":          rec_key,     # 新增：文字评级
        "n_analysts":       n_ana,

        # 成长
        "rev_ttm_B":        rev_b,
        "rev_growth_pct":   rev_growth_pct,
        "rev_growth_q_yoy": q_rev_growth,
        "earn_growth_pct":  earn_growth_pct,

        # 盈利质量
        "gross_margin":     round(g('grossMargins', 0) * 100, 1),
        "operating_margin": operating_margin,   # 新增
        "net_margin":       round(g('profitMargins', 0) * 100, 1),
        "roe":              round(g('returnOnEquity', 0) * 100, 1),
        "fcf_B":            fcf_b,
        "fcf_margin":       round(fcf / rev * 100, 1) if (fcf and rev and rev > 0) else None,
        "quality_warning":  bool(
            g('revenueGrowth', 0) * 100 > 10 and
            (fcf / rev if (fcf and rev and rev > 0) else 1.0) < 0.15
        ),

        # 资产负债
        "debt_to_equity":   g('debtToEquity'),
        "current_ratio":    current_ratio,   # 新增
        "cash_B":           cash_b,

        # 持仓结构
        "insider_pct":      round(g('heldPercentInsiders', 0) * 100, 2),
        "inst_pct":         round(g('heldPercentInstitutions', 0) * 100, 1),
        "insider_buys_3m":  insider_buy_3m,

        # 风险
        "short_pct":        short_pct_fmt,

        # 数据完备度
        "coverage": {
            "price":       cur is not None,
            "profile":     bool(sector),       # 新增
            "valuation":   g('forwardPE') is not None,
            "target":      target is not None,
            "growth":      rev_growth_pct != 0,
            "fcf":         fcf_b is not None,
            "insider":     insider_buy_3m is not None,
            "peers":       bool(peers_pe),     # 新增
        }
    }

    try:
        _findings = os.path.join(os.path.dirname(os.path.dirname(__file__)), "findings")
        os.makedirs(_findings, exist_ok=True)
        json.dump(result, open(os.path.join(_findings, f"fundamentals_{sym.upper()}.json"),
                               "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass

    return result


def fmt_report(d: dict) -> str:
    """格式化为人类可读输出"""
    sym    = d['sym']
    cur    = d['cur']
    chg    = d['chg_pct']
    tgt    = d['target_price']
    tgt_d  = d['target_deviation']
    rec    = d['rec_mean']
    n_a    = d['n_analysts']

    rec_label = {1: "强买", 2: "买入", 3: "持有", 4: "卖出", 5: "强卖"}
    rec_str   = rec_label.get(round(rec) if rec else 3, "N/A") if rec else "N/A"
    tgt_str   = f"${tgt:.1f}（{'高于' if tgt_d and tgt_d > 0 else '低于'}现价{abs(tgt_d):.1f}%）" if tgt and tgt_d else "N/A"
    short_s   = f"{d['short_pct']}%" if d['short_pct'] else "N/A"

    cov = d['coverage']
    cov_str = " ".join(
        f"{'✅' if v else '❌'}{k}" for k, v in cov.items()
    )

    # 公司概况
    profile_line = ""
    if d.get('sector') or d.get('industry'):
        profile_line = f"{d.get('sector','')} / {d.get('industry','')} | {d.get('country','')} | 员工 {d.get('employees','N/A'):,}" if d.get('employees') else f"{d.get('sector','')} / {d.get('industry','')}"

    # 板块 PE 对比
    pe_compare = ""
    if d.get('sector_pe') and d.get('pe_fwd'):
        premium = round((d['pe_fwd'] / d['sector_pe'] - 1) * 100)
        pe_compare = f" | 板块({d.get('sector_etf','')}) PE: {d['sector_pe']:.1f}x → 个股溢价 {premium:+d}%"

    # 同行 PE
    peers_str = ""
    if d.get('peers_pe'):
        peers_str = " | ".join(f"{k} {v:.1f}x" for k, v in d['peers_pe'].items())
        peers_str = f"同行PE: {peers_str}"

    lines = [
        f"【{d.get('long_name', sym)} ({sym})】{d['fetched_at'][:10]}",
        profile_line,
        d.get('description','')[:120] + "…" if d.get('description') else "",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"价格:  ${cur:.2f} ({chg:+.2f}%)" if cur and chg else f"价格:  N/A",
        f"市值:  ${d['mktcap_B']:.1f}B | Beta: {d['beta']:.2f}" if d.get('beta') and d.get('mktcap_B') else (f"市值:  ${d['mktcap_B']:.1f}B" if d.get('mktcap_B') else "市值: N/A"),
        f"52周:  ${d['lo52']:.1f} – ${d['hi52']:.1f}" if d.get('lo52') and d.get('hi52') else "52周: N/A",
        "",
        f"【估值】",
        f"PE(ttm): {d['pe_ttm']:.1f}x | PE(fwd): {d['pe_fwd']:.1f}x | PEG: {d['peg']:.2f}{pe_compare}" if all([d.get('pe_ttm'), d.get('pe_fwd'), d.get('peg')]) else "PE: N/A",
        peers_str,
        f"P/B: {d['price_to_book']:.1f}x" if d.get('price_to_book') else "",
        f"EPS(fwd): ${d['eps_fwd']:.2f}" if d.get('eps_fwd') else "EPS(fwd): N/A",
        f"分析师目标: {tgt_str} | 评级: {d.get('rec_key','').upper()} {rec_str} ({n_a}人覆盖)",
        "",
        f"【成长】",
        f"营收(TTM): ${d['rev_ttm_B']:.1f}B | 营收增速: {d['rev_growth_pct']:+.1f}% YoY" if d.get('rev_ttm_B') is not None else "营收(TTM): N/A",
        f"季度营收YoY: {d['rev_growth_q_yoy']:+.1f}%" if d.get('rev_growth_q_yoy') else "季度营收YoY: N/A",
        f"盈利增速: {d['earn_growth_pct']:+.1f}% YoY" if d.get('earn_growth_pct') is not None else "盈利增速: N/A",
        "",
        f"【盈利质量】",
        f"毛利率: {d.get('gross_margin',0):.1f}% | 营业利润率: {d.get('operating_margin',0):.1f}% | 净利率: {d.get('net_margin',0):.1f}% | ROE: {d.get('roe',0):.1f}%",
        f"自由现金流: ${d['fcf_B']:.2f}B | 现金: ${d['cash_B']:.2f}B" if d.get('fcf_B') else "FCF: N/A",
        *(
            [f"盈利质量: ⚠️ 增收不增利（营收+{d.get('rev_growth_pct',0):.1f}% FCF转化率{d.get('fcf_margin',0):.1f}%偏低）"]
            if d.get("quality_warning") else
            ([f"盈利质量: ✅ FCF Margin {d.get('fcf_margin',0):.1f}%"] if d.get("fcf_margin") else [])
        ),
        f"负债/权益: {d['debt_to_equity']:.1f} | 流动比率: {d.get('current_ratio','N/A')}" if d.get('debt_to_equity') is not None else "负债/权益: N/A",
        "",
        f"【持仓结构】",
        f"内部人: {d.get('insider_pct',0):.2f}% | 机构: {d.get('inst_pct',0):.1f}%",
        f"内部人近20条记录中买入: {d['insider_buys_3m']:,}股" if d['insider_buys_3m'] is not None else "内部人买入: N/A",
        f"空头占比: {short_s}",
        "",
        f"【数据完备度】{cov_str}",
        f"⚠️ Tier3缺失（需WebSearch）: 分部营收占比 | 期权流向 | 短线趋势",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="个股基本面快照")
    parser.add_argument("symbol", help="股票代码，如 MRVL")
    parser.add_argument("--json", action="store_true", help="输出 JSON 而非格式化文本")
    args = parser.parse_args()

    data = fetch(args.symbol)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(fmt_report(data))


if __name__ == "__main__":
    main()
