"""
Intuition Agent — 推理层 + CIO协议接口
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

BASE    = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
LRN_DIR = os.path.join(BASE, "learning")

def _load_model(track):
    path = os.path.join(LRN_DIR, f"model_{track}.pkl")
    if not os.path.exists(path):
        return None
    import joblib
    return joblib.load(path)

def _load_cases():
    path = os.path.join(LRN_DIR, "case_library.json")
    if not os.path.exists(path):
        return []
    return json.load(open(path, encoding="utf-8"))

def score_symbol(sym: str, features: dict):
    results = {}
    for track, prefix in [("intraday", "i_"), ("swing", "s_")]:
        pkg = _load_model(track)
        if pkg is None:
            continue
        model_all = pkg.get("model_all") or pkg.get("model")
        model_mac = pkg.get("model_macro")
        feat_cols = pkg["features"]
        row = []
        for col in feat_cols:
            bare = col[len(prefix):]
            row.append(features.get(bare, features.get(col, 0.0)))
        X = np.array([row])
        classes = list(model_all.classes_)
        pos_idx = classes.index(1) if 1 in classes else 0
        prob_all = model_all.predict_proba(X)[0][pos_idx]

        # P1-1: 混合模型：数据充足时70%宏观+30%全量，不足时40%宏观+60%全量
        if model_mac and not pkg.get("model_macro_blend", False):
            prob_mac = model_mac.predict_proba(X)[0][pos_idx]
            pos_prob = prob_mac * 0.7 + prob_all * 0.3
        elif model_mac and pkg.get("model_macro_blend", False):
            prob_mac = model_mac.predict_proba(X)[0][pos_idx]
            pos_prob = prob_mac * 0.4 + prob_all * 0.6  # 数据稀疏时降低宏观权重
        else:
            pos_prob = prob_all
        results[track] = round(float(pos_prob), 3)
    if not results:
        return None
    results["similar"] = find_similar_cases(features, _load_cases(), top_k=3)
    return results

def find_similar_cases(features: dict, cases: list, top_k: int = 3) -> list:
    if not cases or not features:
        return []
    num_keys = [k for k, v in features.items() if isinstance(v, (int, float))]
    if not num_keys:
        return []
    query = np.array([features.get(k, 0.0) for k in num_keys])
    scored = []
    for case in cases:
        cf   = case.get("features", {})
        cval = np.array([cf.get(f"i_{k}", cf.get(f"s_{k}", cf.get(k, 0.0))) for k in num_keys])
        scored.append((float(np.linalg.norm(query - cval)), case))
    scored.sort(key=lambda x: x[0])
    return [c for _, c in scored[:top_k]]

def format_intuition_line(intra_score: float, swing_score: float, similar: list) -> str:
    line = f"[直觉评分] 日内命中率{intra_score*100:.0f}% | 波段命中率{swing_score*100:.0f}%"
    if similar:
        cases_str = " | ".join(f"{c['sym']} {c['date']}({c['ret']:+.1f}%)" for c in similar[:2])
        line += f"\n  最相似案例: {cases_str}"
    return line

def get_intuition_for_premarket(sym: str, gap_pct: float = 0.0, peer_chg: float = 0.0,
                                 short_pct: float = 0.0, catalyst_strength: int = 1):
    import yfinance as yf
    from learning.features import extract_intraday_features, extract_swing_features
    try:
        h = yf.Ticker(sym).history(period="60d")
        if h.empty:
            return None
        fi = extract_intraday_features(h, peer_chg=peer_chg)
        fs = extract_swing_features(h, short_pct=short_pct, catalyst_strength=catalyst_strength)
        result = score_symbol(sym, {**fi, **fs})
        if result is None:
            return None
        return format_intuition_line(result.get("intraday", 0.5), result.get("swing", 0.5),
                                     result.get("similar", []))
    except Exception:
        return None

def main():
    import argparse, re
    from agents.protocol import BOARD_PATH, FINDINGS_DIR, make_finding
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()

    result = get_intuition_for_premarket(args.symbol)
    score_text = result or "历史数据不足，跳过直觉评分"
    signal, confidence = "neutral", 55
    try:
        pcts = re.findall(r"(\d+)%", score_text)
        if pcts:
            avg = sum(int(p) for p in pcts) / len(pcts)
            signal = "bullish" if avg >= 60 else "bearish" if avg <= 40 else "neutral"
            confidence = int(avg)
    except Exception:
        pass

    os.makedirs(FINDINGS_DIR, exist_ok=True)
    msg = make_finding("IntuitionAgent", args.symbol, signal, confidence,
                       [score_text],
                       [{"field": "historical_model", "verified": True, "source": "local"}])
    with open(BOARD_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg) + "\n")

if __name__ == "__main__":
    main()
