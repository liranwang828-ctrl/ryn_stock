"""
快速3人辩论脚本 — 信号 ≥5/6 时由 poll.py 异步触发
Minervini（技术）、Marks（风险）、Druckenmiller（宏观）并行发言
结果写入 ~/stock_team/quick_debate_{sym}.json，poll 下轮读取显示

用法：python3.12 agents/quick_debate.py <SYM> <DATA_JSON>
  DATA_JSON: JSON字符串，含 cur/chg/rs/rsi3/hist/dvwap/vol/hi/lo/
             atr14/spy_chg/qqq_chg/vix_cur/vix_dir/rs_streak
"""
import sys, os, json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import atomic_write_json

BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_TPL  = os.path.join(BASE, "quick_debate_{}.json")

# 大师注册表（快捷名到完整名映射）
MASTER_REGISTRY = {
    "minervini":     "mark_minervini",
    "druckenmiller": "stan_druckenmiller",
    "marks":         "howard_marks",
    "taleb":         "nassim_taleb",
    "soros":         "george_soros",
    "livermore":     "jesse_livermore",
    "lynch":         "peter_lynch",
}

# 默认3人辩论组合
DEFAULT_DEBATE_TRIO = ["minervini", "marks", "druckenmiller"]

# ── 三大师傅辩论逻辑 ────────────────────────────────────────

def minervini_debate(sym, d):
    """技术趋势：SEPA + RS + 量价 → 进/等/不进 + 理由"""
    rs      = d["rs"]
    hist    = d["hist"]
    rsi3    = d["rsi3"]
    dvwap   = d["dvwap"]
    vol     = d["vol"]
    streak  = d.get("rs_streak", 0)
    from_hi = (d["cur"] - d["hi"]) / d["hi"] * 100

    score = 0
    pros, cons = [], []

    if rs > 3:
        score += 3; pros.append(f"RS+{rs:.1f}%极强")
    elif rs > 1.5:
        score += 2; pros.append(f"RS+{rs:.1f}%强")
    elif rs > 0:
        score += 1; pros.append(f"RS+{rs:.1f}%正向")
    else:
        score -= 1; cons.append(f"RS{rs:.1f}%弱于大盘")

    if hist > 0:
        score += 2; pros.append("MACD柱正向")
    else:
        score -= 1; cons.append("MACD柱仍负")

    if 40 <= rsi3 <= 72:
        score += 2; pros.append(f"RSI3={rsi3:.0f}健康")
    elif rsi3 > 80:
        score -= 1; cons.append(f"RSI3={rsi3:.0f}超买")

    if dvwap > 0:
        score += 2; pros.append("站VWAP上方")
    else:
        cons.append(f"VWAP下方{dvwap:.1f}%")

    if "扩" in vol:
        score += 1; pros.append("量能扩张")
    elif "缩" in vol:
        pros.append("缩量（回踩健康）")

    if streak >= 3:
        score += 1; pros.append(f"RS连续{streak}轮强势")

    if abs(from_hi) < 1:
        score -= 1; cons.append("贴近日高追高风险")

    vote = "进" if score >= 7 else "等" if score >= 4 else "不进"
    reason = f"{'、'.join(pros[:3])}" + (f"；但{cons[0]}" if cons else "")
    return {"persona": "Minervini", "vote": vote, "score": score,
            "reason": reason, "pros": pros, "cons": cons}


def marks_debate(sym, d):
    """风险情绪：VIX + R:R + 仓位 → 进/等/不进 + 理由"""
    vix_cur = d["vix_cur"]
    vix_dir = d["vix_dir"]
    rsi3    = d["rsi3"]
    from_hi = (d["cur"] - d["hi"]) / d["hi"] * 100
    atr14   = d["atr14"]
    cur     = d["cur"]

    score = 0
    pros, cons = [], []

    # VIX 水平
    if vix_cur < 17:
        score += 3; pros.append(f"VIX{vix_cur:.0f}低位，市场稳定")
    elif vix_cur < 19:
        score += 2; pros.append(f"VIX{vix_cur:.0f}中性")
    elif vix_cur < 22:
        score += 0; cons.append(f"VIX{vix_cur:.0f}偏高需警惕")
    else:
        score -= 3; cons.append(f"VIX{vix_cur:.0f}高危，大幅缩仓")

    # VIX 方向
    if "降" in vix_dir:
        score += 2; pros.append("VIX下行，情绪改善")
    elif "升" in vix_dir:
        score -= 2; cons.append("VIX上升⚠️情绪转差")

    # RSI 超买
    if rsi3 > 82:
        score -= 2; cons.append(f"RSI3={rsi3:.0f}严重超买")
    elif rsi3 > 72:
        score -= 1; cons.append(f"RSI3={rsi3:.0f}偏热")
    else:
        score += 2; pros.append(f"RSI3={rsi3:.0f}健康")

    # 空间（距日高）
    if abs(from_hi) > 5:
        score += 2; pros.append(f"距日高{abs(from_hi):.0f}%空间充足")
    elif abs(from_hi) > 2:
        score += 1; pros.append(f"距日高{abs(from_hi):.0f}%尚有空间")
    else:
        score -= 1; cons.append(f"距日高仅{abs(from_hi):.1f}%，盈亏比差")

    vote = "进" if score >= 6 else "等" if score >= 3 else "不进"
    reason = f"{'、'.join(pros[:3])}" + (f"；但{cons[0]}" if cons else "")
    return {"persona": "Marks", "vote": vote, "score": score,
            "reason": reason, "pros": pros, "cons": cons}


def druckenmiller_debate(sym, d):
    """宏观主题：大盘/期货/RS/催化剂 → 进/等/不进 + 理由"""
    spy_chg = d["spy_chg"]
    qqq_chg = d["qqq_chg"]
    rs      = d["rs"]
    streak  = d.get("rs_streak", 0)
    vix_cur = d["vix_cur"]
    avg_mkt = (spy_chg + qqq_chg) / 2

    score = 0
    pros, cons = [], []

    # 大盘方向
    if avg_mkt > 0.5:
        score += 3; pros.append(f"大盘顺风SPY{spy_chg:+.1f}%/QQQ{qqq_chg:+.1f}%")
    elif avg_mkt > 0:
        score += 2; pros.append(f"大盘微涨{avg_mkt:+.1f}%")
    elif avg_mkt > -0.3:
        score += 0; cons.append(f"大盘{avg_mkt:+.1f}%中性偏弱")
    else:
        score -= 2; cons.append(f"大盘{avg_mkt:+.1f}%逆风")

    # 个股RS（主题强度）
    if rs > 6:
        score += 3; pros.append(f"RS+{rs:.1f}%领涨市场，主题极强")
    elif rs > 3:
        score += 2; pros.append(f"RS+{rs:.1f}%，个股主题明确")
    elif rs > 1:
        score += 1; pros.append(f"RS+{rs:.1f}%略优于大盘")
    else:
        cons.append(f"RS{rs:.1f}%无超额，主题不清晰")

    # 连续强势
    if streak >= 5:
        score += 2; pros.append(f"RS连续{streak}轮强势，主题持续发酵")
    elif streak >= 3:
        score += 1; pros.append(f"RS连续{streak}轮，趋势确立")

    # VIX 宏观风险
    if vix_cur > 22:
        score -= 2; cons.append("宏观风险偏高，减少暴露")

    score = min(10, max(0, score))
    vote = "进" if score >= 7 else "等" if score >= 4 else "不进"
    reason = f"{'、'.join(pros[:3])}" + (f"；但{cons[0]}" if cons else "")
    return {"persona": "Druckenmiller", "vote": vote, "score": score,
            "reason": reason, "pros": pros, "cons": cons}


def run_debate(sym, data):
    """并行执行三人辩论，返回完整辩论结果"""
    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {
            ex.submit(minervini_debate, sym, data):    "Minervini",
            ex.submit(marks_debate, sym, data):        "Marks",
            ex.submit(druckenmiller_debate, sym, data): "Druckenmiller",
        }
        for fut in as_completed(futs, timeout=25):
            r = fut.result()
            results[r["persona"]] = r

    # 多数决
    votes = [r["vote"] for r in results.values()]
    vote_count = {v: votes.count(v) for v in set(votes)}
    majority = max(vote_count, key=vote_count.get)
    consensus = "🟢进场" if majority == "进" else \
                "🟡观望" if majority == "等" else "🔴不进"

    scores = {k: v["score"] for k, v in results.items()}
    avg_score = sum(scores.values()) / len(scores)

    return {
        "sym":       sym,
        "time":      datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "consensus": consensus,
        "majority":  majority,
        "vote_count": vote_count,
        "avg_score": round(avg_score, 1),
        "votes":     {k: v["vote"] for k, v in results.items()},
        "results":   results,
    }


def format_debate(debate):
    """格式化辩论输出"""
    sym  = debate["sym"]
    cons = debate["consensus"]
    avg  = debate["avg_score"]
    t    = debate["time"]
    lines = [
        f"╔{'═'*52}╗",
        f"║  ⚡ {sym} 快速辩论  {t}  综合{avg}/10  {cons:<10}  ║",
        f"╠{'═'*52}╣",
    ]
    for persona, r in debate["results"].items():
        vote_icon = "🟢" if r["vote"]=="进" else "🟡" if r["vote"]=="等" else "🔴"
        lines.append(f"║  {vote_icon}{r['vote']}  {persona:<16} {r['score']:>2}/10  {r['reason'][:28]:<28}║")
    lines.append(f"╚{'═'*52}╝")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3.12 agents/quick_debate.py <SYM> '<JSON_DATA>'")
        sys.exit(1)

    sym      = sys.argv[1]
    data     = json.loads(sys.argv[2])
    out_path = OUT_TPL.format(sym)

    debate = run_debate(sym, data)
    debate["formatted"] = format_debate(debate)

    atomic_write_json(debate, out_path, indent=2)
    print(debate["formatted"])
