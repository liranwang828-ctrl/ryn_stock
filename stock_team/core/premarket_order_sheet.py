"""
premarket_order_sheet.py — 盘前条件订单表生成器

为每只关注标的生成"条件订单表"：入场条件、订单参数、取消条件、Flex级别。
这是 Constrained Mode 的核心盘前输出，替代纯方向判断。

用法:
    python3.12 agents/premarket_order_sheet.py LITE MRVU
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import yfinance as yf
from datetime import datetime, timezone

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
_BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
BASE = _BASE
_MACRO_PATH = os.path.join(_BASE, "findings", "macro.json")
_REGIME_PATH = os.path.join(_BASE, "config", "market_regime.json")
_POS_PATH    = os.path.join(_BASE, "config", "positions.json")
_FUND_DIR    = os.path.join(_BASE, "findings")


def _load_json(path, default=None):
    try:
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
    except Exception:
        pass
    return default or {}


def _get_atr(sym: str) -> float:
    """获取 ATR14（基于日线数据）"""
    try:
        h = yf.Ticker(sym).history(period="20d")
        if len(h) >= 14:
            tr = (h["High"] - h["Low"]).tail(14)
            return round(float(tr.mean()), 2)
    except Exception:
        pass
    return 0.0


def _get_overnight_data(sym: str) -> dict:
    """获取盘后/盘前价格和变动。返回 {overnight_price, overnight_chg, already_in_zone}"""
    try:
        i    = yf.Ticker(sym).info
        cur  = i.get("regularMarketPrice", 0)
        post = i.get("postMarketPrice") or i.get("preMarketPrice")
        chg  = round((post - cur) / cur, 4) if (post and cur) else None
        return {"overnight_price": post, "overnight_chg": chg, "already_in_zone": None}
    except Exception:
        return {"overnight_price": None, "overnight_chg": None, "already_in_zone": None}


def _get_technicals(sym: str) -> dict:
    """获取关键技术位"""
    try:
        h = yf.Ticker(sym).history(period="30d")
        if h.empty:
            return {}
        cur    = float(h["Close"].iloc[-1])
        ma20   = float(h["Close"].rolling(20).mean().iloc[-1]) if len(h) >= 20 else cur
        lo5    = float(h["Low"].tail(5).min())
        lo10   = float(h["Low"].tail(10).min())
        hi20   = float(h["High"].tail(20).max())
        hi5    = float(h["High"].tail(5).max())
        atr    = _get_atr(sym)
        return {
            "cur": cur, "ma20": ma20, "atr14": atr,
            "lo5": lo5, "lo10": lo10, "hi20": hi20, "hi5": hi5,
            "ma20_dev": round((cur - ma20) / ma20 * 100, 1),
        }
    except Exception:
        return {}


# ETF 关键词映射（板块取消条件具体化）
_SECTOR_ETF = {
    "光模块": "XAR", "光学": "XAR", "photon": "XAR",
    "AI芯片": "SOXX", "半导体": "SOXX", "chip": "SOXX",
    "太空": "ROKT", "空天": "ROKT", "航天": "ROKT",
    "能源": "XLE", "石油": "XLE", "oil": "XLE",
    "黄金": "GDX", "矿业": "GDX", "gold": "GDX",
}


def _personalized_cancel_conditions(sym: str, pos_cfg: dict,
                                    tech: dict, macro: dict) -> list:
    """
    根据持仓配置生成个性化取消条件（5条规则）。
    所有条件均可观测，开盘即知。
    """
    conds = ["QQQ 开跌 > -1.5%"]  # 规则1：固定基础条件

    # 规则2：node1 — 论点支撑线
    node1 = (pos_cfg or {}).get("node1") or (tech or {}).get("lo5")
    if node1:
        conds.append(f"{sym} 开盘直接跌破 ${node1:.2f}（论点支撑线）")

    # 规则3：catalyst_type
    cat = (pos_cfg or {}).get("catalyst_type", "")
    if cat == "order":
        conds.append("同客户链大厂相关标的跌 >3%")
    elif cat == "earnings":
        conds.append("同期公司 earnings miss（盘前数据）")
    elif cat == "policy":
        conds.append("相关政策出现负面转向")

    # 规则4：macro_sensitivity 活跃逆风 → 具体数字
    ms  = (pos_cfg or {}).get("macro_sensitivity", {})
    yc  = (macro or {}).get("yield_curve", "")
    dxy = float((macro or {}).get("dxy") or 0)
    y10 = (macro or {}).get("yield_10y")
    if ms.get("rate_up") == "负" and yc == "倒挂" and y10:
        conds.append(f"10Y 收益率持续高于 {float(y10):.2f}%（利率逆风加剧）")
    if ms.get("dollar_strong") == "负" and dxy > 103:
        conds.append(f"DXY 继续走强超过 {dxy:.0f}（美元逆风）")

    # 规则5：板块 ETF 具体化
    macro_type = (pos_cfg or {}).get("macro_type", "")
    thesis     = (pos_cfg or {}).get("thesis", "")
    etf = None
    for kw, e in _SECTOR_ETF.items():
        if kw in macro_type or kw in thesis:
            etf = e
            break
    if etf:
        conds.append(f"{etf} 开盘跌超 -2%（板块 ETF 整体走弱）")
    else:
        conds.append("同板块 ETF 开盘 < -2%")

    return conds


def generate_order_sheet(sym: str, manual_target: float = None) -> dict:
    """
    为单只标的生成条件订单表。
    返回结构化 dict，包含入场条件/参数/取消条件/Flex级别。

    manual_target: 手动指定目标价（分析师目标价或自设目标）
    """
    tech = _get_technicals(sym)
    fund = _load_json(os.path.join(_FUND_DIR, f"fundamentals_{sym.upper()}.json"))
    pos  = _load_json(_POS_PATH).get("positions", {}).get(sym, {})
    macro = _load_json(_MACRO_PATH)
    regime = _load_json(_REGIME_PATH)

    cur    = tech.get("cur", 0)
    ma20   = tech.get("ma20", cur)
    atr    = tech.get("atr14", cur * 0.03)
    lo5    = tech.get("lo5", cur * 0.97)
    lo10   = tech.get("lo10", cur * 0.95)
    hi5    = tech.get("hi5", cur * 1.03)

    # 入场区间：MA20 ± 1/2 ATR，不追高
    entry_low  = round(max(lo5 * 0.99, ma20 - atr * 0.5), 2)
    entry_high = round(ma20 + atr * 0.5, 2)
    entry_base = round((entry_low + entry_high) / 2, 2)

    # 止损：近5日低点下方
    stop_base = round(lo5 - atr * 0.3, 2)

    # 目标：分析师目标或 MA20 + 1.5×ATR
    analyst_tgt = fund.get("target_price")
    if manual_target:
        target = round(manual_target, 2)
    elif analyst_tgt and analyst_tgt > cur:
        target = round(min(analyst_tgt, ma20 + atr * 2), 2)
    else:
        target = round(ma20 + atr * 1.5, 2)

    # 持仓信息
    cost   = float(pos.get("cost", 0)) if pos else 0
    shares = int(pos.get("shares", 0)) if pos else 0
    thesis = pos.get("thesis", "") if pos else ""
    is_held = bool(pos and shares > 0)

    # 取消条件（个性化）
    cancel_conditions = _personalized_cancel_conditions(sym, pos if pos else {}, tech, macro)

    # 入场条件
    entry_conditions = [
        f"{sym} 开盘在 ${entry_low:.2f}–${entry_high:.2f} 区间",
        "QQQ 开盘不跌超 -1%",
        f"{sym} 不破今日盘前最低点 ${lo5:.2f}",
    ]

    # 隔夜数据集成
    ov     = _get_overnight_data(sym)
    op     = ov.get("overnight_price")

    overnight_note = ""
    if op is not None:
        if op < entry_low:
            overnight_note = (f"已跌入目标区间（盘前${op:.2f} < 入场下限${entry_low:.2f}），"
                              "等开盘缩量确认")
        elif op > entry_high + 0.5 * atr:
            overnight_note = (f"区间失效（盘前${op:.2f} 大幅高出上限${entry_high:.2f}+0.5ATR），"
                              "今天跳过或等回踩")
        else:
            overnight_note = (f"已在目标区间（盘前${op:.2f}），开盘即可关注，入场确信度+1级")

    # 叙事命中检查
    overnight_sig = (regime.get("overnight_signal") or "").upper()
    narrative_hit = sym.upper() in overnight_sig

    # Regime板块对齐注释
    regime_name = regime.get("regime", "")
    macro_type  = pos.get("macro_type", "") if pos else ""
    regime_note = ""
    if regime_name == "sector_hot" and "成长型" in macro_type:
        regime_note = "⚠️ 热点不在科技，注意板块阻力"
    elif regime_name == "trending_up" and "成长型" in macro_type:
        regime_note = "✅ 趋势向上对成长型有利"

    return {
        "sym":               sym.upper(),
        "date":              datetime.now().strftime("%Y-%m-%d"),
        "is_held":           is_held,
        "current_price":     cur,
        "atr14":             atr,
        "entry_conditions":  entry_conditions,
        "entry_range":       (entry_low, entry_high),
        "entry_base":        entry_base,
        "stop_loss":         stop_base,
        "target_price":      target,
        "risk_per_share":    round(entry_base - stop_base, 2),
        "reward_per_share":  round(target - entry_base, 2),
        "rr_ratio":          round((target - entry_base) / max(entry_base - stop_base, 0.01), 1),
        "cancel_conditions": cancel_conditions,
        "cost":              cost,
        "shares":            shares,
        "thesis":            thesis,
        "flex_add_level":    round(lo10, 2),
        "flex_add_note":     f"近10日低点 ${lo10:.2f} + 缩量守住 → 可考虑加仓",
        "flex_reduce_level": round(hi5, 2),
        "flex_reduce_note":  f"近5日高点 ${hi5:.2f} → 价格逼近时考虑减仓",
        "overnight_price":   op,
        "overnight_chg":     ov.get("overnight_chg"),
        "overnight_note":    overnight_note,
        "narrative_hit":     narrative_hit,
        "regime_note":       regime_note,
    }


def fmt_order_sheet(d: dict) -> str:
    """格式化为人类可读的订单表"""
    sym   = d["sym"]
    cur   = d["current_price"]
    atr   = d["atr14"]
    held  = "（已持仓）" if d["is_held"] else "（新建仓）"

    lines = [
        "",
        "━" * 52,
        f"  {sym} 今日条件订单表 {d['date']} {held}",
        f"  现价 ${cur:.2f}  ATR14 ${atr:.2f}",
        "━" * 52,
        "",
        "【入场条件】（前30分钟观察期核查）",
    ]
    for i, c in enumerate(d["entry_conditions"], 1):
        lines.append(f"  {i}. {c}")

    # 隔夜/盘前信息
    ov_note = d.get("overnight_note", "")
    if ov_note:
        lines += ["", f"【盘前/盘后】{ov_note}"]
    if d.get("narrative_hit"):
        lines.append("  ⭐ 今晚叙事命中")
    rn = d.get("regime_note", "")
    if rn:
        lines.append(f"  Regime: {rn}")

    lines += [
        "",
        "【订单参数】（后30分钟执行窗口）",
        f"  入场区间: ${d['entry_range'][0]:.2f} – ${d['entry_range'][1]:.2f}",
        f"  参考入场: ${d['entry_base']:.2f} 限价",
        f"  止损 GTC: ${d['stop_loss']:.2f}（只能收紧，不能放宽）",
        f"  目标 GTC: ${d['target_price']:.2f}",
        f"  风险/回报: -${d['risk_per_share']:.2f} / +${d['reward_per_share']:.2f}  RR={d['rr_ratio']:.1f}x",
        "",
        "【取消条件】（任一满足则取消今日计划）",
    ]
    for c in d["cancel_conditions"]:
        lines.append(f"  × {c}")

    if d["is_held"]:
        lines += [
            "",
            f"【持仓信息】成本 ${d['cost']:.2f} × {d['shares']}股",
            f"  论点: {d['thesis'][:50] if d['thesis'] else '未填写'}",
        ]

    lines += [
        "",
        "【Flex参考】（非今日，后续条件成熟时）",
        f"  {d['flex_add_note']}",
        "",
        "⏰ 10:30 ET 后: GTC单接管，停止主动监控",
        "━" * 52,
    ]
    return "\n".join(lines)


def write_order_sheet_files(sheets: dict, findings_dir: str = None,
                             base_dir: str = None) -> None:
    """
    将订单表字典写入两个文件：
    1. findings/order_sheet_{date}.json — 含 date/symbols 包装的结构化订单表
    2. daily_plan_{date}.json — poll.py 兼容格式（plan.get("stocks",{}).get(sym)）
       字段: stop / t1_target / t2_target
    """
    import os as _os
    from datetime import datetime as _dt

    _base     = base_dir     or _BASE
    _findings = findings_dir or _FUND_DIR
    _os.makedirs(_findings, exist_ok=True)

    date_str = _dt.now().strftime("%Y-%m-%d")

    # File 1: order_sheet_{date}.json with date + symbols wrapper
    order_out = _os.path.join(_findings, f"order_sheet_{date_str}.json")
    with open(order_out, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "symbols": {sym: {k: v for k, v in d.items()
                              if not isinstance(v, tuple)}
                        for sym, d in sheets.items()},
        }, f, ensure_ascii=False, indent=2)

    # File 2: daily_plan_{date}.json compat for poll.py
    # poll.py reads: plan.get("stocks", {}).get(sym) → {stop, t1_target, t2_target}
    plan_stocks = {}
    for sym, d in sheets.items():
        tgt = float(d.get("target_price") or 0)
        plan_stocks[sym] = {
            "stop":      d.get("stop_loss", 0),
            "t1_target": tgt,
            "t2_target": round(tgt * 1.04, 2) if tgt else 0,
        }
    plan_out = _os.path.join(_base, f"daily_plan_{date_str}.json")
    existing = {}
    if _os.path.exists(plan_out):
        try:
            with open(plan_out, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.setdefault("stocks", {}).update(plan_stocks)
    with open(plan_out, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="盘前条件订单表生成器")
    parser.add_argument("symbols", nargs="+", help="标的代码，如 LITE MRVU")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    sheets = {}
    for sym in args.symbols:
        d = generate_order_sheet(sym.upper())
        sheets[sym.upper()] = d
        if not args.json:
            print(fmt_order_sheet(d))

    if args.json:
        print(json.dumps(sheets, ensure_ascii=False, indent=2))

    if not args.json:
        write_order_sheet_files(sheets)
        print(f"✅ 订单表写入 findings/order_sheet_{datetime.now().strftime('%Y-%m-%d')}.json")


if __name__ == "__main__":
    main()
