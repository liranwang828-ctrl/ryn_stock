"""
Bootstrap Agent v3 — 完整三层架构 + 三项大师改进
Layer 0: 宏观周期标注 (Druckenmiller) — 历史数据按宏观状态分类
Layer 1: 质量预过滤 (Minervini/Lynch) — Stage2/RS52w/MDD
Layer 2: 双宇宙模型训练 (Livermore) — 日内/波段分开
         + 时效性权重 (Minervini) — 近期数据权重更高

用法: python3.12 agents/bootstrap_agent.py [--symbols NVDA MRVL ...]
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
import joblib
from learning.features import (extract_intraday_features, extract_swing_features,
                                extract_quality_features, get_fundamental_features,
                                get_macro_regime)

BASE    = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
LRN_DIR = os.path.join(BASE, "learning")

# ── 质量过滤标准 ────────────────────────────────────────────────
QUALITY_FILTER = {
    "stage2_min": 2,
    "rs52w_min":  -20.0,
    "mdd_max":    -80.0,
}

# ── 宇宙划分标准 (Livermore) ────────────────────────────────────
INTRADAY_UNIVERSE = {
    "hist_vol_min": 40.0,    # 年化波动率 > 40%（有足够的日内空间）
}
SWING_UNIVERSE = {
    "hist_vol_max": 90.0,    # 年化波动率 < 90%（不能太疯狂）
    "bear_2022_min": -75.0,  # 2022熊市跌幅不超过-75%（有一定防守性）
}

# ── 时效性权重衰减 (Minervini) ─────────────────────────────────
TIME_DECAY_RATE = 0.003   # 每天衰减率，约1年后权重降到~1/3

def load_watchlist():
    cfg = json.load(open(os.path.join(BASE, "config", "poll_config.json"), encoding="utf-8"))
    syms = set(cfg.get("default_symbols", []) + cfg.get("watchlist", []))
    exclude = {"BABA", "PONY", "PDD", "JD", "BIDU"}
    return [s for s in syms if s not in exclude and not s.startswith("_")]

_SPY_CACHE = {}

def _get_spy(period="5y"):
    if "spy" not in _SPY_CACHE:
        _SPY_CACHE["spy"] = yf.Ticker("SPY").history(period=period)
    return _SPY_CACHE["spy"]

def passes_quality_filter(q: dict) -> tuple[bool, str]:
    if q.get("stage2_score", 0) < QUALITY_FILTER["stage2_min"]:
        return False, f"Stage2={q.get('stage2_score',0):.0f}<{QUALITY_FILTER['stage2_min']}"
    if q.get("rs_52w", 0) < QUALITY_FILTER["rs52w_min"]:
        return False, f"RS52w={q.get('rs_52w',0):.0f}%"
    if q.get("mdd_2y", -100) < QUALITY_FILTER["mdd_max"]:
        return False, f"MDD={q.get('mdd_2y',0):.0f}%"
    return True, "通过"

def in_intraday_universe(q: dict) -> bool:
    return q.get("hist_vol", 0) >= INTRADAY_UNIVERSE["hist_vol_min"]

def in_swing_universe(q: dict) -> bool:
    vol_ok  = q.get("hist_vol", 999) <= SWING_UNIVERSE["hist_vol_max"]
    bear_ok = q.get("bear_2022", -100) >= SWING_UNIVERSE["bear_2022_min"]
    return vol_ok and bear_ok

def compute_time_weight(date_str: str, today: datetime) -> float:
    """Minervini 时效性权重：近期数据权重指数衰减"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        days_ago = (today - d).days
        return float(np.exp(-TIME_DECAY_RATE * days_ago))
    except Exception:
        return 1.0

def build_historical_records(sym, period="5y"):
    t = yf.Ticker(sym)
    h_daily = t.history(period=period)
    if h_daily.empty or len(h_daily) < 30:
        return [], None, None

    h_spy = _get_spy(period)
    q_feats = extract_quality_features(sym, h_daily, h_spy)
    f_feats = get_fundamental_features(sym)

    records = []
    spy_records = list(h_spy.iterrows())  # 预处理SPY数据

    for i in range(20, len(h_daily) - 5):
        window    = h_daily.iloc[:i+1]
        open_day  = float(h_daily["Open"].iloc[i])
        close_day = float(h_daily["Close"].iloc[i])
        date_str  = str(h_daily.index[i].date())

        intra_ret = (close_day - open_day) / open_day * 100
        intra_lbl = 1 if intra_ret > 1.5 else (0 if intra_ret > -1.5 else -1)
        close_5d  = float(h_daily["Close"].iloc[i+5])
        swing_ret = (close_5d - close_day) / close_day * 100
        swing_lbl = 1 if swing_ret > 4.0 else (0 if swing_ret > -4.0 else -1)

        feat_i = extract_intraday_features(window, peer_chg=0.0)
        feat_s = extract_swing_features(window, short_pct=0.0, catalyst_strength=1)
        if not feat_i or not feat_s:
            continue

        # Layer 0: 宏观周期标注
        spy_idx = min(i, len(h_spy)-1)
        macro_regime = get_macro_regime(h_spy, spy_idx)

        records.append({
            "sym": sym, "date": date_str,
            "macro_regime": macro_regime,
            **{f"i_{k}": v for k, v in feat_i.items()},
            **{f"s_{k}": v for k, v in feat_s.items()},
            "intra_ret": round(intra_ret, 2), "swing_ret": round(swing_ret, 2),
            "intra_lbl": intra_lbl, "swing_lbl": swing_lbl,
        })
    return records, q_feats, f_feats

def train_model(df, label_col, feature_prefix, time_weights=None, label=""):
    """带时效性权重的模型训练"""
    feat_cols = [c for c in df.columns if c.startswith(feature_prefix)]
    X = df[feat_cols].fillna(0).values
    y = df[label_col].values
    if len(np.unique(y)) < 2 or len(X) < 50:
        return None, feat_cols, {}

    clf = RandomForestClassifier(n_estimators=150, max_depth=7,
                                  random_state=42, n_jobs=-1)
    clf.fit(X, y, sample_weight=time_weights)

    acc = (clf.predict(X) == y).mean()
    importance = dict(zip(feat_cols, clf.feature_importances_))
    print(f"  {label}: {len(df)}行  准确率{acc:.1%}")
    return clf, feat_cols, importance

def run(symbols=None):
    os.makedirs(LRN_DIR, exist_ok=True)
    syms = symbols or load_watchlist()
    today = datetime.now()
    print(f"Bootstrap v3: {len(syms)} 只标的 (宏观分层+时效权重+双宇宙)\n")

    all_records = []
    quality_archive = {}
    intraday_syms, swing_syms = [], []

    for sym in syms:
        print(f"  {sym}...", end=" ", flush=True)
        recs, q_feats, f_feats = build_historical_records(sym)
        if q_feats is None:
            print("数据不足"); continue

        passed, reason = passes_quality_filter(q_feats)
        in_intra = in_intraday_universe(q_feats)
        in_swing = in_swing_universe(q_feats)

        quality_archive[sym] = {
            "quality_pass": passed, "reason": reason,
            "intraday_universe": in_intra,
            "swing_universe":    in_swing,
            **{f"q_{k}": v for k, v in q_feats.items()},
            **{f"f_{k}": v for k, v in f_feats.items()},
        }

        if not passed:
            print(f"❌ {reason}"); continue

        for rec in recs:
            rec["in_intraday"] = in_intra
            rec["in_swing"]    = in_swing
            rec["time_weight"] = compute_time_weight(rec["date"], today)

        all_records.extend(recs)
        if in_intra: intraday_syms.append(sym)
        if in_swing:  swing_syms.append(sym)
        print(f"{len(recs)}条 ✅ {'日内' if in_intra else ''}{'波段' if in_swing else ''}")

    df = pd.DataFrame(all_records)
    df.to_parquet(os.path.join(LRN_DIR, "historical_features.parquet"), index=False)
    json.dump(quality_archive,
              open(os.path.join(LRN_DIR, "quality_archive.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    print(f"\n宇宙划分: 日内{len(set(intraday_syms))}只  波段{len(set(swing_syms))}只")

    # ── 宏观分布统计 ─────────────────────────────────────────────
    if "macro_regime" in df.columns:
        print("\n宏观周期分布:")
        for regime, cnt in df["macro_regime"].value_counts().items():
            pct = cnt/len(df)*100
            print(f"  {regime:12} {cnt:5}行 ({pct:.1f}%)")

    # ── 训练四个模型：日内×当前宏观 / 波段×当前宏观 ─────────────
    current_macro = get_macro_regime(
        _get_spy(), len(_get_spy())-1
    ) if _get_spy() is not None else "ai_bull"
    print(f"\n当前宏观状态: {current_macro}")
    print("=== 模型训练 ===\n")

    models = {}
    for track, col, prefix, uni_col in [
        ("intraday", "intra_lbl", "i_", "in_intraday"),
        ("swing",    "swing_lbl", "s_", "in_swing"),
    ]:
        # 全量模型（所有时期）
        sub_all = df[df[uni_col]] if uni_col in df.columns else df
        w_all   = sub_all["time_weight"].values if "time_weight" in sub_all.columns else None
        clf_all, fcols, imp = train_model(sub_all, col, prefix, w_all, f"{track}(全量)")

        # 当前宏观匹配模型
        sub_mac = sub_all[sub_all["macro_regime"] == current_macro] if "macro_regime" in sub_all else sub_all
        w_mac   = sub_mac["time_weight"].values if "time_weight" in sub_mac.columns else None
        clf_mac, _, imp_mac = train_model(sub_mac, col, prefix, w_mac, f"{track}({current_macro})")

        if clf_all:
            # P1-1: 宏观子模型数据量不足时，标记使用混合模型
            MIN_MACRO_ROWS = 1000
            if clf_mac and len(sub_mac) < MIN_MACRO_ROWS:
                print(f"  ⚠️  {current_macro} 数据量不足({len(sub_mac)}行 < {MIN_MACRO_ROWS})，使用混合模型")
                model_macro_blend = True
            else:
                model_macro_blend = False

            pkg = {
                "model_all":      clf_all,
                "model_macro":    clf_mac,
                "features":       fcols,
                "track":          track,
                "current_macro":  current_macro,
                "universe_syms":  intraday_syms if track=="intraday" else swing_syms,
                "feature_importance": imp,
                "quality_filter": QUALITY_FILTER,
                "model_macro_blend": model_macro_blend,
                "model_macro_min_rows": MIN_MACRO_ROWS,
            }
            joblib.dump(pkg, os.path.join(LRN_DIR, f"model_{track}.pkl"))
            models[track] = pkg

        print(f"  特征重要性 Top5:")
        for feat, v in sorted(imp.items(), key=lambda x:x[1], reverse=True)[:5]:
            print(f"    {feat:30} {v:.4f}")
        print()

    # ── 质量档案报告 ─────────────────────────────────────────────
    print("=== 标的质量档案 ===")
    header = f"{'标的':6}{'通过':4}{'日内':4}{'波段':4}{'Stage2':8}{'RS52w':8}{'MDD':8}{'2022熊':8}{'波动率':8}"
    print(header)
    print("-" * 65)
    for sym in sorted(syms):
        arc = quality_archive.get(sym)
        if not arc: continue
        pf  = "✅" if arc["quality_pass"] else "❌"
        ii  = "✅" if arc.get("intraday_universe") else "—"
        sw  = "✅" if arc.get("swing_universe")    else "—"
        s2  = arc.get("q_stage2_score", 0)
        rs  = arc.get("q_rs_52w", 0)
        mdd = arc.get("q_mdd_2y", 0)
        b22 = arc.get("q_bear_2022", 0)
        vol = arc.get("q_hist_vol", 0)
        # 波段胜率
        sub = df[(df["sym"]==sym) & df["in_swing"]] if "in_swing" in df.columns and arc["quality_pass"] else pd.DataFrame()
        wr  = f"{(sub['swing_lbl']==1).mean():.0%}" if not sub.empty else "—"
        print(f"  {sym:6}{pf:4}{ii:4}{sw:4}{s2:6.0f}/4  {rs:+6.0f}%  {mdd:+6.0f}%  {b22:+6.0f}%  {vol:5.0f}%  波段{wr}")

    # ── 案例库 ────────────────────────────────────────────────────
    cases = []
    for lbl_col, track in [("intra_lbl","intraday"),("swing_lbl","swing")]:
        ret_col = "intra_ret" if track=="intraday" else "swing_ret"
        uni_col = "in_intraday" if track=="intraday" else "in_swing"
        sub = df[df[uni_col]] if uni_col in df.columns else df
        for _, row in pd.concat([
            sub[sub[lbl_col]==1].nlargest(10, ret_col),
            sub[sub[lbl_col]==-1].nsmallest(10, ret_col)
        ]).iterrows():
            cases.append({"sym":row["sym"],"date":row["date"],"track":track,
                          "ret":row[ret_col],"label":int(row[lbl_col]),
                          "macro_regime": row.get("macro_regime","?"),
                          "features":{c:row[c] for c in df.columns
                                      if c.startswith("i_") or c.startswith("s_")}})
    json.dump(cases, open(os.path.join(LRN_DIR,"case_library.json"),"w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"\n案例库: {len(cases)}条（含宏观标注）")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="*")
    args = parser.parse_args()
    run(args.symbols)
