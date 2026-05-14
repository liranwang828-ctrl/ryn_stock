import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import get_logger, fetch_with_retry, atomic_write_json
log = get_logger(__name__)
from agents.protocol import (BASE, VERIFIED_PATH, BOARD_PATH, FINDINGS_DIR,
                              make_finding, make_revision, compute_phase2_response)
import yfinance as yf

def analyze(symbol):
    points, score = [], 0
    refs = []
    spy_1d = 0
    qqq_1d = 0
    vix_val = 20
    try:
        spy_t   = yf.Ticker("SPY")
        spy_h   = fetch_with_retry(lambda: spy_t.history(period="5d"))["Close"]
        spy_info= fetch_with_retry(lambda: spy_t.info)
        vix_h   = fetch_with_retry(lambda: yf.Ticker("^VIX").history(period="5d"))["Close"]
        qqq_h   = fetch_with_retry(lambda: yf.Ticker("QQQ").history(period="5d"))["Close"]

        # 昨日正式收盘变动（5日区间）
        spy_5d  = (spy_h.iloc[-1] - spy_h.iloc[0]) / spy_h.iloc[0]
        # 昨日单日涨跌
        spy_1d  = (spy_h.iloc[-1] - spy_h.iloc[-2]) / spy_h.iloc[-2] if len(spy_h) > 1 else 0
        # 盘前/盘后 SPY 实时方向（最重要：感知当日开盘倾向）
        spy_pre  = spy_info.get("preMarketPrice")
        spy_post = spy_info.get("postMarketPrice")
        spy_ext  = spy_pre or spy_post
        spy_overnight = (spy_ext - spy_h.iloc[-1]) / spy_h.iloc[-1] if spy_ext else None

        vix_val = vix_h.iloc[-1]
        qqq_1d  = (qqq_h.iloc[-1] - qqq_h.iloc[-2]) / qqq_h.iloc[-2] if len(qqq_h) > 1 else 0

        # 盘前方向（权重最高，代表当前市场情绪）
        if spy_overnight is not None:
            session = "盘前" if spy_pre else "盘后"
            if spy_overnight > 0.005:
                points.append(f"SPY {session} +{spy_overnight:.2%}，今日开盘倾向偏多"); score += 25
            elif spy_overnight < -0.005:
                points.append(f"SPY {session} {spy_overnight:.2%}，今日开盘倾向偏空"); score -= 25
            else:
                points.append(f"SPY {session} 持平({spy_overnight:+.2%})，方向不明"); score += 0

        # 昨日收盘表现
        if spy_1d > 0.01:   points.append(f"SPY昨日涨{spy_1d:.1%}，前一日收盘强势"); score += 10
        elif spy_1d < -0.01: points.append(f"SPY昨日跌{spy_1d:.1%}，前一日收盘弱势"); score -= 10

        # VIX 恐慌指数
        vix_5d_chg = (vix_h.iloc[-1] - vix_h.iloc[0]) / vix_h.iloc[0]
        if vix_val < 15:
            points.append(f"VIX={vix_val:.1f} 低恐慌，风险偏好高"); score += 15
        elif vix_val > 25:
            points.append(f"VIX={vix_val:.1f} 恐慌上升，市场避险"); score -= 15
        else:
            trend = f"↑{vix_5d_chg:.1%}" if vix_5d_chg > 0.05 else f"↓{vix_5d_chg:.1%}" if vix_5d_chg < -0.05 else "平稳"
            points.append(f"VIX={vix_val:.1f} 中性 ({trend})")
            if vix_5d_chg > 0.1: score -= 8   # VIX 快速上升是预警

        refs = [{"field": "SPY_overnight", "verified": False, "source": "yfinance"},
                {"field": "VIX",           "verified": False, "source": "yfinance"}]
    except Exception as e:
        points = [f"宏观数据拉取失败: {e}"]
        score  = 0
        refs   = []
        spy_1d = 0
        qqq_1d = 0
        vix_val = 20
    signal     = "bullish" if score >= 20 else "bearish" if score <= -15 else "neutral"
    confidence = min(85, 50 + abs(score))

    # ── Layer 2: 推理链 ──────────────────────────────────────────
    analysis = []
    avg_mkt = ((spy_1d or 0) + (qqq_1d or 0)) / 2
    if avg_mkt > 0.5:
        analysis.append(f"大盘SPY/QQQ平均+{avg_mkt:.1f}%，资金风险偏好上升，做多环境有利")
    elif avg_mkt < -0.5:
        analysis.append(f"大盘SPY/QQQ平均{avg_mkt:.1f}%，市场避险情绪上升，个股上涨难度加大")
    if vix_val:
        if vix_val < 17:
            analysis.append(f"VIX={vix_val:.1f}低位，市场极度平静，适合持有或加仓")
        elif vix_val > 25:
            analysis.append(f"VIX={vix_val:.1f}高位，市场存在系统性恐慌，谨慎加仓")
        else:
            analysis.append(f"VIX={vix_val:.1f}正常区间，市场情绪中性")

    # ── Layer 3: 专业结论 ────────────────────────────────────────
    if signal == "bullish":
        judgment = "宏观环境顺风：大盘强+VIX低，适合进攻"
        boundary = "若VIX突然上升或大盘单日跌幅>1%，宏观顺风结束"
        challenge = "Taleb会问：VIX低是假性平静还是真实稳定？黑天鹅概率被低估了吗？"
    elif signal == "bearish":
        judgment = "宏观环境逆风：大盘弱+VIX高，防守优先"
        boundary = "若大盘企稳+VIX回落，逆风减弱"
        challenge = "Druckenmiller会问：逆风中还有哪些做空/防守机会？"
    else:
        judgment = "宏观环境中性：大盘混合信号，个股需自力更生"
        boundary = "等待大盘明确方向"
        challenge = "Soros会问：市场的不确定性本身是不是一个投资信号？"

    conclusion = {
        "judgment": judgment,
        "boundary": boundary,
        "anticipated_challenge": challenge
    }

    return signal, confidence, points, refs, analysis, conclusion

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()
    signal, conf, points, refs, analysis, conclusion = analyze(args.symbol)
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    from agents.protocol import VERIFIED_PATH, apply_persona
    _raw = json.load(open(VERIFIED_PATH)).get("fields", {}) if os.path.exists(VERIFIED_PATH) else {}
    _data = {k: v.get("value") if isinstance(v, dict) else v for k, v in _raw.items()}
    if args.round is None:
        msg = make_finding("MacroAgent", args.symbol, signal, conf, points, refs, analysis=analysis, conclusion=conclusion)
        _board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = apply_persona(msg, _data, "MacroAgent", _board)
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, "MacroAgent.json"), indent=2)
    else:
        board = [json.loads(l) for l in open(BOARD_PATH) if l.strip()] if os.path.exists(BOARD_PATH) else []
        msg = compute_phase2_response("MacroAgent", args.symbol, board,
                                      signal, conf, points, refs, _data)
        if not msg:
            atomic_write_json({}, os.path.join(FINDINGS_DIR, f"MacroAgent_r{args.round}.json"))
            return
        atomic_write_json(msg, os.path.join(FINDINGS_DIR, f"MacroAgent_r{args.round}.json"), indent=2)

if __name__ == "__main__":
    main()
