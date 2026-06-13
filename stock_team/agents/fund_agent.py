import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from stock_team.utils.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)

def analyze(symbol, fields):
    def f(name):
        return fields.get(name, {}).get("value"), fields.get(name, {}).get("verified", False)
    pe, pe_v   = f("pe_ratio")
    pb, pb_v   = f("pb_ratio")
    eps, eps_v = f("eps")
    fcf, _          = f("fcf")
    ocf, _          = f("operating_cashflow")
    fcf_capex, _    = f("fcf_capex_driven")
    fcf_healthy, _  = f("fcf_healthy")
    rev_growth, _   = f("revenue_growth")
    roe, _          = f("roe5y_avg")

    points, score = [], 0

    # 估值
    if pe:
        if pe < 20:   points.append(f"P/E={pe:.1f} 估值偏低，具吸引力"); score += 20
        elif pe < 35: points.append(f"P/E={pe:.1f} 估值合理");           score += 10
        else:         points.append(f"P/E={pe:.1f} 估值偏高，需关注");   score -= 10

    if pb:
        if pb < 2:   points.append(f"P/B={pb:.1f} 破净或低估"); score += 15
        elif pb > 8: points.append(f"P/B={pb:.1f} 溢价较高");   score -= 5
        else:        points.append(f"P/B={pb:.1f} 合理区间")

    # 盈利
    if eps and eps > 0: points.append(f"EPS={eps:.2f} 正值，盈利稳定"); score += 15
    elif eps:           points.append(f"EPS={eps:.2f} 亏损状态");       score -= 20

    # 现金流（核心改进：区分经营性现金流 vs FCF）
    if fcf and fcf > 0:
        points.append(f"自由现金流正值，真实创造股东价值"); score += 15
    elif fcf_capex and ocf and ocf > 0:
        ocf_bn = ocf / 1e9
        points.append(f"FCF暂负（CapEx扩产驱动），经营性现金流${ocf_bn:.1f}B健康"); score += 8
    elif ocf and ocf <= 0:
        points.append("经营性现金流为负，主业造血能力不足"); score -= 20

    # ROE
    if roe and roe > 0.20:    points.append(f"ROE={roe:.0%} 优秀，护城河深厚"); score += 10
    elif roe and roe > 0.15:  points.append(f"ROE={roe:.0%} 达标");             score += 5
    elif roe and roe < 0.10:  points.append(f"ROE={roe:.0%} 偏低");             score -= 5

    # 成长性
    if rev_growth and rev_growth > 0.30:
        points.append(f"营收增速{rev_growth:.0%}，高成长弥补高估值"); score += 10

    signal     = "bullish" if score >= 20 else "bearish" if score <= -10 else "neutral"
    confidence = min(85, 50 + abs(score))
    data_refs  = [{"field": k, "verified": v, "source": "yfinance"}
                  for k, v in [("pe_ratio", pe_v), ("eps", eps_v)]]

    # ── Layer 2: 推理链 ──────────────────────────────────────────
    analysis = []

    def _val(name, default=""):
        val = fields.get(name, default)
        if isinstance(val, dict):
            return val.get("value") or val.get("val") or default
        return val or default

    def _num(name, default=0):
        val = fields.get(name)
        if isinstance(val, dict):
            ret = val.get("value")
            if ret is None:
                ret = val.get("val")
            return default if ret is None else ret
        return default if val is None else val

    def _pct_to_frac(val):
        if val is None:
            return 0
        if abs(val) > 1.0:
            return val / 100.0
        return val

    _desc = _val("description", "")
    _name = _val("long_name", "") or symbol
    _sect = _val("sector", "")
    _ind  = _val("industry", "")
    if _desc:
        analysis.append(f"{_name}（{_sect}/{_ind}）：{_desc[:120]}…")
    elif _sect:
        analysis.append(f"{_name} 属于 {_sect}/{_ind} 行业")

    fcf_v = _num("fcf", 0) or _num("fcf_B", 0) * 1e9
    rev_growth_v = _pct_to_frac(_num("revenue_growth", 0) or _num("rev_growth_pct", 0))
    gross_margin_v = _pct_to_frac(_num("grossMargins", 0) or _num("gross_margin", 0))
    pe_v2 = _num("pe_ratio", 0) or _num("pe_fwd", 0)

    if rev_growth_v:
        if rev_growth_v > 0.3:
            analysis.append(f"营收增速+{rev_growth_v*100:.0f}%处于高增长，市场愿意给成长溢价，估值偏高可接受")
        elif rev_growth_v < 0:
            analysis.append(f"营收负增长{rev_growth_v*100:.0f}%，业务收缩，估值需打折")
    if gross_margin_v:
        if gross_margin_v > 0.5:
            analysis.append(f"毛利率{gross_margin_v*100:.0f}%较高，具备定价权或差异化竞争优势")
        elif gross_margin_v < 0.25:
            analysis.append(f"毛利率{gross_margin_v*100:.0f}%偏低，处于商品化竞争市场")
    if fcf_v and fcf_v > 0:
        analysis.append(f"自由现金流为正(${fcf_v/1e9:.1f}B)，利润能转化为真实现金，盈利质量较好")
    elif fcf_v and fcf_v < 0:
        analysis.append(f"自由现金流为负，公司仍处于烧钱阶段，需关注现金储备和融资能力")

    # ── Layer 3: 专业结论 ────────────────────────────────────────
    if signal == "bullish":
        judgment = f"基本面健康：增速+盈利质量+{'估值合理' if pe_v2 and pe_v2 < 30 else '高增速支撑高估值'}"
        boundary = "若下季度增速低于预期或FCF转负，基本面支撑减弱"
        challenge = "Burry会问：FCF有没有水分？应收账款变化如何？"
    elif signal == "bearish":
        judgment = "基本面偏弱：增速/盈利质量/估值存在问题"
        boundary = "若公司发布下调指引，看空进一步强化"
        challenge = "Lynch会问：估值是否已反映坏消息？有没有被过度悲观的情况？"
    else:
        judgment = "基本面中性：各项指标混合，无明显好坏信号"
        boundary = "下次财报是关键催化剂"
        challenge = "Marks会问：我比市场多知道什么？如果没有，为何要参与？"

    conclusion = {
        "judgment": judgment,
        "boundary": boundary,
        "anticipated_challenge": challenge
    }

    return signal, confidence, points or ["基本面数据不足"], data_refs, analysis, conclusion

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()
    data = json.load(open(VERIFIED_PATH, encoding="utf-8"))
    signal, conf, points, refs, analysis, conclusion = analyze(args.symbol, data["fields"])
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    from stock_team.utils.protocol import apply_persona
    _fields_flat = {k: v.get("value") if isinstance(v, dict) else v for k, v in data["fields"].items()}
    if args.round is None:
        msg = make_finding("FundAgent", args.symbol, signal, conf, points, refs, analysis=analysis, conclusion=conclusion)
        _board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = apply_persona(msg, _fields_flat, "FundAgent", _board)
        json.dump(msg, open(os.path.join(FINDINGS_DIR, "FundAgent.json"), "w", encoding="utf-8"), indent=2)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH, encoding="utf-8") if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("FundAgent", args.symbol, board,
                                      signal, conf, points, refs, _fields_flat)
        if not msg:
            json.dump({}, open(os.path.join(FINDINGS_DIR, f"FundAgent_r{args.round}.json"), "w", encoding="utf-8"))
            return
        json.dump(msg, open(os.path.join(FINDINGS_DIR, f"FundAgent_r{args.round}.json"), "w", encoding="utf-8"), indent=2)

if __name__ == "__main__":
    main()
