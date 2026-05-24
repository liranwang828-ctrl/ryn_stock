"""
Harvest Agent — 每个交易日收盘后运行
用法: python3.12 agents/harvest_agent.py
"""
import sys, os, json
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf

BASE    = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
LRN_DIR = os.path.join(BASE, "learning")
HARVEST = os.path.join(LRN_DIR, "daily_harvest.jsonl")
SHORT_H = os.path.join(LRN_DIR, "short_interest_history.jsonl")
OBS_LOG = os.path.join(LRN_DIR, "observation_log.jsonl")
OBS_OUT = os.path.join(LRN_DIR, "observation_outcomes.jsonl")

def get_today_symbols():
    today = datetime.now().strftime("%Y-%m-%d")
    snap_path = os.path.join(BASE, "knowledge", f"snapshots_{today}.jsonl")
    syms = set()
    if os.path.exists(snap_path):
        for line in open(snap_path, encoding="utf-8"):
            try:
                row = json.loads(line)
                syms.update(row.get("symbols", {}).keys())
            except Exception:
                pass
    return list(syms)

def record_intraday_outcome(sym, date_str):
    try:
        h = yf.Ticker(sym).history(period="2d")
        if len(h) < 1:
            return None
        open_p  = float(h["Open"].iloc[-1])
        close_p = float(h["Close"].iloc[-1])
        intra_ret = (close_p - open_p) / open_p * 100
        return {"sym": sym, "date": date_str, "track": "intraday",
                "open": open_p, "close": close_p, "ret": round(intra_ret, 2),
                "label": 1 if intra_ret > 1.5 else (-1 if intra_ret < -1.5 else 0),
                "recorded_at": datetime.now(timezone.utc).isoformat()}
    except Exception:
        return None

def record_swing_outcome(sym, entry_date_str):
    try:
        h = yf.Ticker(sym).history(period="10d")
        if len(h) < 6:
            return None
        entry_close = float(h["Close"].iloc[-6])
        cur_close   = float(h["Close"].iloc[-1])
        swing_ret   = (cur_close - entry_close) / entry_close * 100
        return {"sym": sym, "entry_date": entry_date_str,
                "harvest_date": datetime.now().strftime("%Y-%m-%d"),
                "track": "swing", "entry_close": entry_close,
                "cur_close": cur_close, "ret": round(swing_ret, 2),
                "label": 1 if swing_ret > 4.0 else (-1 if swing_ret < -4.0 else 0),
                "recorded_at": datetime.now(timezone.utc).isoformat()}
    except Exception:
        return None

def record_short_interest(syms):
    today = datetime.now().strftime("%Y-%m-%d")
    records = []
    for sym in syms:
        try:
            info = yf.Ticker(sym).info
            sp = info.get("shortPercentOfFloat")
            if sp:
                records.append({"sym": sym, "date": today,
                                "short_pct": round(float(sp) * 100, 1)})
        except Exception:
            pass
    if records:
        with open(SHORT_H, "a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
    print(f"空头比例记录: {len(records)} 只")

def update_master_accuracy(sym, actual_label, date_str):
    """Compare yesterday's CIO agent signals with actual intraday outcome."""
    yesterday = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    signals_path = os.path.join(LRN_DIR, f"cio_signals_{yesterday}_{sym}.json")
    if not os.path.exists(signals_path):
        return
    try:
        signals = json.load(open(signals_path, encoding="utf-8"))
        agent_signals = signals.get("agent_signals", {})
        acc_path = os.path.join(LRN_DIR, "master_accuracy.json")
        acc_data = json.load(open(acc_path, encoding="utf-8")) if os.path.exists(acc_path) else {}

        for agent, sig_data in agent_signals.items():
            if agent.startswith("_"):
                continue
            signal = sig_data.get("signal", "neutral") if isinstance(sig_data, dict) else "neutral"
            predicted_label = 1 if signal == "bullish" else (-1 if signal == "bearish" else 0)
            # 仅统计有明确观点（非中性）的预测
            if predicted_label == 0:
                continue
            correct = (predicted_label == actual_label)
            if agent not in acc_data:
                acc_data[agent] = {"correct": 0, "total": 0, "accuracy": 0.5}
            acc_data[agent]["total"] += 1
            if correct:
                acc_data[agent]["correct"] += 1
            n = acc_data[agent]["total"]
            c = acc_data[agent]["correct"]
            # Bayesian 更新，先验 0.5（等价于 10 次抛硬币）
            acc_data[agent]["accuracy"] = round((c + 5) / (n + 10), 3)

        json.dump(acc_data, open(acc_path, "w", encoding="utf-8"), indent=2)
        print(f"  [accuracy] {sym} 精度已更新（{len([a for a in agent_signals if not a.startswith('_')])} agents）")
    except Exception as _e:
        pass

def process_observation_log():
    """
    盘后将今日 observation_log.jsonl 与实际收盘结果配对：
    - 入场门通过 → 看股票之后是否上涨（信号是否正确）
    - 门控禁止   → 看股票之后是否没涨（禁止是否正确）
    写入 learning/observation_outcomes.jsonl，供 bootstrap 训练和大师权重校准。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(OBS_LOG):
        print("观察日志不存在，跳过配对")
        return

    from collections import defaultdict
    by_sym = defaultdict(list)
    for line in open(OBS_LOG, encoding="utf-8"):
        try:
            r = json.loads(line)
            if r.get("date") == today:
                by_sym[r["sym"]].append(r)
        except Exception:
            pass

    if not by_sym:
        print("今日无观察记录，跳过配对")
        return

    print(f"观察配对: {len(by_sym)} 只标的，{sum(len(v) for v in by_sym.values())} 条记录")
    outcomes, correct, total_pred = [], 0, 0

    for sym, records in by_sym.items():
        try:
            h = yf.Ticker(sym).history(period="2d")
            if len(h) < 1:
                continue
            open_p  = float(h["Open"].iloc[-1])
            close_p = float(h["Close"].iloc[-1])
            high_p  = float(h["High"].iloc[-1])
            low_p   = float(h["Low"].iloc[-1])
            day_ret = round((close_p - open_p) / open_p * 100, 2)

            for r in records:
                obs_p     = r["price"]
                move      = round((close_p - obs_p) / obs_p * 100, 2)
                max_up    = round((high_p  - obs_p) / obs_p * 100, 2)
                max_down  = round((low_p   - obs_p) / obs_p * 100, 2)
                gate_pass = r.get("gate_pass", False)
                gate_blk  = r.get("gate_block", "")

                if gate_blk:        sig_correct = move <= 0.5;  pred = "no_entry"
                elif gate_pass:     sig_correct = move > 0;     pred = "entry"
                else:               sig_correct = None;         pred = "neutral"

                if sig_correct is not None:
                    total_pred += 1
                    if sig_correct:
                        correct += 1

                outcomes.append({
                    "date": today, "obs_time": r.get("time"), "session": r.get("session"),
                    "sym": sym, "is_position": r.get("is_position", False),
                    "obs_price": obs_p, "close_price": round(close_p, 2),
                    "move_pct": move, "max_up_pct": max_up, "max_down_pct": max_down,
                    "day_ret": day_ret, "prediction": pred,
                    "gate_pass": gate_pass, "gate_block": gate_blk,
                    "signal_correct": sig_correct,
                    "gate_detail": r.get("gate_detail", {}),
                    "key_obs": r.get("key_obs", ""),
                    "key_levels": r.get("key_levels", {}),
                    "rsi3_at_obs": r.get("rsi3"), "macd_at_obs": r.get("macd"),
                    "rs_at_obs": r.get("rs_pct"),
                    "has_catalyst": bool((r.get("catalyst_strength") or 0) > 0),
                })
        except Exception as e:
            print(f"  {sym} 配对失败: {e}")

    if outcomes:
        with open(OBS_OUT, "a", encoding="utf-8") as f:
            for o in outcomes:
                f.write(json.dumps(o, ensure_ascii=False) + "\n")
        acc_str = f"{correct}/{total_pred}" if total_pred else "无有效预测"
        print(f"  配对完成: {len(outcomes)} 条，信号正确率 {acc_str}")
    return by_sym.keys()   # 返回今日观察标的，供 harvest 扩展


def verify_master_judgments(today):
    """核对昨日大师时间线判断的准确性"""
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    judgment_path = os.path.join(LRN_DIR, f"master_timeline_judgments_{yesterday}.json")
    if not os.path.exists(judgment_path):
        return

    try:
        judgments = json.load(open(judgment_path, encoding="utf-8"))
        sym = judgments.get("sym", "NBIS")
        masters = judgments.get("masters", {})

        # 获取今日实际收盘
        h = yf.Ticker(sym).history(period="2d")
        if len(h) < 1:
            return
        today_close = float(h["Close"].iloc[-1])
        prev_close  = float(h["Close"].iloc[-2]) if len(h) >= 2 else today_close
        today_ret   = (today_close - prev_close) / prev_close * 100

        # 简单验证：判断正确 = 价格比昨收高（看涨）或低（看空）
        # 实际用 condition_str 做描述性验证（非自动）
        acc_path = os.path.join(LRN_DIR, "master_accuracy.json")
        acc_data = json.load(open(acc_path, encoding="utf-8")) if os.path.exists(acc_path) else {}

        print(f"\n[判断核对] {yesterday} {sym} 今日收盘 ${today_close:.2f}({today_ret:+.1f}%)")
        for master, data in masters.items():
            cond = data.get("condition_str", "")
            verdict = data.get("verdict", "")
            print(f"  {master}: {cond}")

            # 更新 master_accuracy（时间线判断类别）
            key = f"{master}_timeline"
            if key not in acc_data:
                acc_data[key] = {"total": 0, "correct": 0, "accuracy": 0.5}
            # 简单判断：看涨判断 + 股价上涨 = 正确
            bullish_words = ["守住", "反弹", "多", "上涨", ">", "持有"]
            is_bullish_pred = any(w in cond for w in bullish_words)
            is_correct = (is_bullish_pred and today_ret > 0) or (not is_bullish_pred and today_ret <= 0)
            acc_data[key]["total"] += 1
            if is_correct:
                acc_data[key]["correct"] += 1
            n, c = acc_data[key]["total"], acc_data[key]["correct"]
            acc_data[key]["accuracy"] = round((c + 5) / (n + 10), 3)

        json.dump(acc_data, open(acc_path, "w", encoding="utf-8"), indent=2)
        print(f"[判断核对] master_accuracy 已更新（时间线判断类别）")
    except Exception as e:
        print(f"[判断核对失败] {e}")


def verify_master_scores(date_str):
    """
    验证今日大师评分时间序列的准确性。
    读取 learning/master_score_log_{date}.jsonl（每2分钟一条），
    对每条记录，取评分时刻后约10分钟的价格，判断高/低分预测是否正确。
    写入 master_accuracy.json 的 {master}_realtime 键。
    """
    ms_log_path = os.path.join(LRN_DIR, f"master_score_log_{date_str}.jsonl")
    if not os.path.exists(ms_log_path):
        print(f"[大师评分验证] master_score_log_{date_str}.jsonl 不存在，跳过")
        return

    snap_path = os.path.join(BASE, "knowledge", f"snapshots_{date_str}.jsonl")
    if not os.path.exists(snap_path):
        print(f"[大师评分验证] snapshots_{date_str}.jsonl 不存在，跳过")
        return

    try:
        # 建立 snapshots 价格时间序列：{sym: [(time_str, price), ...]}
        snap_prices = {}
        for line in open(snap_path, encoding="utf-8"):
            try:
                row = json.loads(line)
                t = row.get("time", "")
                for sym, sdata in row.get("stocks", {}).items():
                    price = sdata.get("price")
                    if price is not None:
                        snap_prices.setdefault(sym, []).append((t, float(price)))
            except Exception:
                pass

        # 读取大师评分时间序列
        ms_entries = []
        for line in open(ms_log_path, encoding="utf-8"):
            try:
                ms_entries.append(json.loads(line))
            except Exception:
                pass

        if not ms_entries:
            print(f"[大师评分验证] 无评分记录，跳过")
            return

        acc_path = os.path.join(LRN_DIR, "master_accuracy.json")
        acc_data = json.load(open(acc_path, encoding="utf-8")) if os.path.exists(acc_path) else {}
        master_results = {}
        MASTERS = ["Minervini", "Marks", "Druckenmiller"]
        SKIP_WINDOW = 5   # 评分后跳过N条（约10分钟）才验证

        for entry in ms_entries:
            entry_time = entry.get("time", "")
            scores_data = entry.get("scores", {})

            for sym, sym_info in scores_data.items():
                ms = sym_info.get("master", {})
                if not ms:
                    continue
                obs_price = sym_info.get("price", 0)
                if obs_price <= 0:
                    continue

                # 找评分时刻之后第5条 snapshot 的价格（~10分钟后）
                sym_snaps = snap_prices.get(sym, [])
                # 找到比 entry_time 晚的第5个价格点
                later = [p for t, p in sym_snaps if t > entry_time]
                if len(later) < SKIP_WINDOW:
                    continue
                future_price = later[SKIP_WINDOW - 1]
                pct_change = (future_price - obs_price) / obs_price * 100 if obs_price > 0 else 0

                for master in MASTERS:
                    master_data = ms.get(master, {})
                    score = master_data.get("score", 5) if isinstance(master_data, dict) else 5
                    if 3 < score < 7:
                        continue  # 中性不计

                    bullish = score >= 7
                    correct = (pct_change > 0.5) if bullish else (pct_change < -0.5)

                    master_results.setdefault(master, {"correct": 0, "total": 0})
                    master_results[master]["total"] += 1
                    if correct:
                        master_results[master]["correct"] += 1

        # 写入 master_accuracy.json
        for master, res in master_results.items():
            key = f"{master}_realtime"
            if key not in acc_data:
                acc_data[key] = {"correct": 0, "total": 0, "accuracy": 0.5}
            acc_data[key]["total"] += res["total"]
            acc_data[key]["correct"] += res["correct"]
            n, c = acc_data[key]["total"], acc_data[key]["correct"]
            acc_data[key]["accuracy"] = round((c + 5) / (n + 10), 3)

        json.dump(acc_data, open(acc_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        total_checks = sum(r["total"] for r in master_results.values())
        print(f"[大师评分验证] {len(ms_entries)}条记录，{total_checks}次验证，结果写入 master_accuracy.json")
        for master, res in master_results.items():
            acc = res["correct"] / res["total"] if res["total"] > 0 else 0
            print(f"  {master}_realtime: {res['correct']}/{res['total']} ({acc:.0%})")

    except Exception as e:
        print(f"[大师评分验证失败] {e}")


def record_scene_development(date_str):
    """
    记录今日场景发展序列。
    从 snapshots 提取每只股票的日高/日低时间、振幅，
    从 opening_scenarios 提取今日实际场景，
    与 premarket_analysis 中的预测场景对比。
    写入 learning/scene_development_{date_str}.json。
    """
    snap_path = os.path.join(BASE, "knowledge", f"snapshots_{date_str}.jsonl")
    if not os.path.exists(snap_path):
        print(f"[场景记录] snapshots_{date_str}.jsonl 不存在，跳过")
        return

    scenarios_path = os.path.join(BASE, f"opening_scenarios_{date_str}.json")
    premarket_path = os.path.join(BASE, f"premarket_analysis_{date_str}.json")

    # 读取 snapshots，对每只股票追踪价格、RS、MACD
    sym_prices = {}   # sym -> list of {time, price, chg, rs, macd}
    for line in open(snap_path, encoding="utf-8"):
        try:
            row = json.loads(line)
            t = row.get("time", "")
            for sym, sdata in row.get("stocks", {}).items():
                if sym not in sym_prices:
                    sym_prices[sym] = []
                sym_prices[sym].append({
                    "time": t,
                    "price": sdata.get("price"),
                    "chg": sdata.get("chg"),
                    "rs": sdata.get("rs"),
                    "macd": sdata.get("macd"),
                })
        except Exception:
            pass

    # 读取 opening_scenarios（sym -> {pattern, conf, macro, action, ...}）
    opening_scenes = {}
    if os.path.exists(scenarios_path):
        try:
            opening_scenes = json.load(open(scenarios_path, encoding="utf-8"))
        except Exception:
            pass

    # 读取 premarket_analysis（{stocks: {sym: {pred_scene, actual_scene, ...}}}）
    premarket_stocks = {}
    if os.path.exists(premarket_path):
        try:
            pm = json.load(open(premarket_path, encoding="utf-8"))
            premarket_stocks = pm.get("stocks", {})
        except Exception:
            pass

    results = {}
    for sym, ticks in sym_prices.items():
        if not ticks:
            continue

        # 计算日高、日低时间和振幅
        prices_valid = [(t["time"], t["price"]) for t in ticks if t["price"] is not None]
        if not prices_valid:
            continue

        high_time, high_price = max(prices_valid, key=lambda x: x[1])
        low_time,  low_price  = min(prices_valid, key=lambda x: x[1])
        first_price = prices_valid[0][1]
        last_price  = prices_valid[-1][1]
        amplitude = round((high_price - low_price) / first_price * 100, 2) if first_price else 0
        day_ret   = round((last_price - first_price) / first_price * 100, 2) if first_price else 0

        # 从 opening_scenarios 提取今日场景（字母 pattern）
        actual_scene = None
        opening_entry = opening_scenes.get(sym, {})
        if isinstance(opening_entry, dict):
            actual_scene = opening_entry.get("pattern") or opening_entry.get("actual_scene")

        # 从 premarket_analysis 提取预测场景和实际场景
        pm_entry = premarket_stocks.get(sym, {})
        pred_scene   = pm_entry.get("pred_scene")
        pm_actual    = pm_entry.get("actual_scene")
        pred_vs_actual = pm_entry.get("pred_vs_actual")

        # 以 opening_scenarios 的 actual_scene 为优先；premarket 的作为备用
        final_actual = actual_scene or pm_actual

        # 简单场景发展序列（从 snapshots 中的连续 chg 变化推断方向变化点）
        # 用 RS 正负变化来标记场景切换
        scene_seq = []
        prev_rs_positive = None
        for tick in ticks:
            rs = tick.get("rs")
            if rs is None:
                continue
            rs_pos = rs > 0
            if prev_rs_positive is None or rs_pos != prev_rs_positive:
                scene_seq.append("强" if rs_pos else "弱")
                prev_rs_positive = rs_pos
        scene_str = "→".join(scene_seq) if scene_seq else "无"

        results[sym] = {
            "date": date_str,
            "sym": sym,
            "first_price": round(first_price, 2),
            "last_price":  round(last_price, 2),
            "day_ret_pct": day_ret,
            "high_price": round(high_price, 2),
            "high_time":  high_time,
            "low_price":  round(low_price, 2),
            "low_time":   low_time,
            "amplitude_pct": amplitude,
            "rs_scene_seq": scene_str,
            "pred_scene":   pred_scene,
            "actual_scene": final_actual,
            "pred_vs_actual": pred_vs_actual,
            "opening_pattern": opening_entry.get("pattern") if isinstance(opening_entry, dict) else None,
            "opening_action":  opening_entry.get("action") if isinstance(opening_entry, dict) else None,
        }
        print(f"  [场景记录] {sym} 振幅{amplitude:.1f}% 日高{high_time} 日低{low_time} "
              f"预测{pred_scene or '?'} 实际{final_actual or '?'}")

    out_path = os.path.join(LRN_DIR, f"scene_development_{date_str}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[场景记录] 写入 {out_path}，共 {len(results)} 只股票")


def run():
    os.makedirs(LRN_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    syms = get_today_symbols()
    if not syms:
        cfg  = json.load(open(os.path.join(BASE, "config", "poll_config.json"), encoding="utf-8"))
        syms = cfg.get("watchlist", cfg.get("default_symbols", []))

    print(f"Harvest {today}: {len(syms)} 只标的")

    with open(HARVEST, "a", encoding="utf-8") as f:
        for sym in syms:
            rec = record_intraday_outcome(sym, today)
            if rec:
                f.write(json.dumps(rec) + "\n")
                ret_str = f"{rec['ret']:+.1f}%"
                print(f"  {sym:6s} 日内{ret_str} → {'正' if rec['label']==1 else '负' if rec['label']==-1 else '中'}")
                update_master_accuracy(sym, rec["label"], today)
        for sym in syms:
            rec = record_swing_outcome(sym, five_days_ago)
            if rec:
                f.write(json.dumps(rec) + "\n")

    record_short_interest(syms)

    # 观察日志配对（非持仓标的也产出经验）
    obs_syms = process_observation_log() or set()
    extra = [s for s in obs_syms if s not in syms]
    if extra:
        print(f"补录观察标的: {' '.join(extra)}")
        with open(HARVEST, "a", encoding="utf-8") as f:
            for sym in extra:
                rec = record_intraday_outcome(sym, today)
                if rec:
                    f.write(json.dumps(rec) + "\n")
                    print(f"  {sym:6s} 日内{rec['ret']:+.1f}% → {'正' if rec['label']==1 else '负' if rec['label']==-1 else '中'}")
                    update_master_accuracy(sym, rec["label"], today)

    verify_master_judgments(today)
    verify_master_scores(today)
    record_scene_development(today)
    print(f"Harvest 完成，数据写入 {HARVEST}")

if __name__ == "__main__":
    run()
