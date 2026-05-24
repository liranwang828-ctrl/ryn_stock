"""
Learning Agent — 每周运行，用累积数据重新训练模型 + 更新案例库
用法: python3.12 agents/learning_agent.py
"""
import sys, os, json
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

BASE    = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
LRN_DIR = os.path.join(BASE, "learning")

def load_all_data():
    parquet = os.path.join(LRN_DIR, "historical_features.parquet")
    harvest = os.path.join(LRN_DIR, "daily_harvest.jsonl")
    dfs = []
    if os.path.exists(parquet):
        dfs.append(pd.read_parquet(parquet))
    if os.path.exists(harvest):
        rows = [json.loads(l) for l in open(harvest, encoding="utf-8") if l.strip()]
        if rows:
            dfs.append(pd.DataFrame(rows))
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def retrain(df, label_col, feature_prefix):
    feat_cols = [c for c in df.columns if c.startswith(feature_prefix)]
    df_clean  = df[feat_cols + [label_col]].dropna()
    if len(df_clean) < 50 or len(df_clean[label_col].unique()) < 2:
        print(f"  数据不足（{len(df_clean)}行），跳过 {label_col}")
        return None, feat_cols
    X = df_clean[feat_cols].values
    y = df_clean[label_col].values
    clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
    split = int(len(df_clean) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    clf.fit(X_train, y_train)
    train_acc = clf.score(X_train, y_train)
    test_acc  = clf.score(X_test, y_test) if len(X_test) > 5 else train_acc
    print(f"  {label_col}: {len(df_clean)}行  训练{train_acc:.1%}  测试(OOS){test_acc:.1%}")
    return clf, feat_cols

def check_model_degradation():
    """检查最近预测是否退化（基于 daily_harvest.jsonl 近10条的准确率）"""
    harvest = os.path.join(LRN_DIR, "daily_harvest.jsonl")
    if not os.path.exists(harvest):
        return
    rows = [json.loads(l) for l in open(harvest, encoding="utf-8") if l.strip()]
    recent = rows[-20:] if len(rows) >= 20 else rows
    if len(recent) < 5:
        return
    # 简单检查：label=1 的比例是否异常（正常应在30-50%）
    pos_rate = sum(1 for r in recent if r.get("label") == 1) / len(recent)
    if pos_rate < 0.15 or pos_rate > 0.85:
        print(f"⚠️  模型退化警告: 近{len(recent)}条记录正例率={pos_rate:.0%}（正常30-50%），模型可能已退化")
    else:
        print(f"  模型健康检查: 近{len(recent)}条正例率={pos_rate:.0%} ✅")

def update_case_library(df):
    cases = []
    for lbl_col, ret_col, track in [
        ("intra_lbl", "intra_ret", "intraday"),
        ("swing_lbl", "swing_ret", "swing"),
    ]:
        if lbl_col not in df.columns:
            continue
        top_pos = df[df[lbl_col] == 1].nlargest(15, ret_col)
        top_neg = df[df[lbl_col] == -1].nsmallest(15, ret_col)
        feat_keys = [c for c in df.columns if c.startswith("i_") or c.startswith("s_")]
        for _, row in pd.concat([top_pos, top_neg]).iterrows():
            cases.append({
                "sym":      row.get("sym", "?"),
                "date":     str(row.get("date", "?")),
                "track":    track,
                "ret":      float(row.get(ret_col, 0)),
                "label":    int(row.get(lbl_col, 0)),
                "features": {k: float(row.get(k, 0)) for k in feat_keys if k in row},
            })
    json.dump(cases, open(os.path.join(LRN_DIR, "case_library.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"案例库更新: {len(cases)} 条")

def run():
    os.makedirs(LRN_DIR, exist_ok=True)
    print(f"Learning Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    check_model_degradation()
    df = load_all_data()
    if df.empty:
        print("无数据，请先运行 bootstrap_agent.py")
        return
    print(f"总数据量: {len(df)} 行")
    clf_i, fcols_i = retrain(df, "intra_lbl", "i_")
    if clf_i:
        joblib.dump({"model": clf_i, "features": fcols_i, "track": "intraday",
                     "updated_at": datetime.now(timezone.utc).isoformat()},
                    os.path.join(LRN_DIR, "model_intraday.pkl"))
    clf_s, fcols_s = retrain(df, "swing_lbl", "s_")
    if clf_s:
        joblib.dump({"model": clf_s, "features": fcols_s, "track": "swing",
                     "updated_at": datetime.now(timezone.utc).isoformat()},
                    os.path.join(LRN_DIR, "model_swing.pkl"))
    update_case_library(df)
    log_path = os.path.join(LRN_DIR, "weights_log.json")
    log = json.load(open(log_path, encoding="utf-8")) if os.path.exists(log_path) else []
    log.append({"date": datetime.now().strftime("%Y-%m-%d"),
                "rows": len(df), "retrained": bool(clf_i or clf_s)})
    json.dump(log, open(log_path, "w", encoding="utf-8"), indent=2)
    print("学习完成")

if __name__ == "__main__":
    run()
