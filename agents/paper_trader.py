"""
模拟盘交易引擎 — 自我进化平台（三账号A/B测试版）

账号：strict（严格≥8.0）/ base（基准≥7.5）/ loose（宽松≥6.5）
每周对比三者胜率/盈亏比，自动推断最优参数

混合模式：
  - 日内：EOD平仓 + shadow继续跟踪（对比是否持有更好）
  - 波段：催化剂≥2或RS连续≥5轮 → 持仓过夜

核心宗旨：自我进化
"""
import os, sys, json, random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import atomic_write_json

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PT_DIR    = os.path.join(BASE, "paper_trading")
ACCT_CFG  = os.path.join(PT_DIR, "accounts.json")
ACCOUNTS  = ["strict", "base", "loose"]

def _paths(acct):
    d = os.path.join(PT_DIR, acct)
    return {
        "portfolio":  os.path.join(d, "portfolio.json"),
        "trades":     os.path.join(d, "trades.jsonl"),
        "evolution":  os.path.join(d, "evolution.jsonl"),
    }

def _load_acct_cfg(acct):
    if os.path.exists(ACCT_CFG):
        return json.load(open(ACCT_CFG)).get(acct, {})
    defaults = {"strict":{"entry_score_threshold":8.0,"entry_rs_threshold":2.0,"max_positions":4},
                "base":  {"entry_score_threshold":7.5,"entry_rs_threshold":1.5,"max_positions":6},
                "loose": {"entry_score_threshold":5.0,"entry_rs_threshold":0.8,"max_positions":6}}
    return defaults.get(acct, defaults["base"])

# ── 组合读写 ────────────────────────────────────────────────
def load_portfolio(acct="base"):
    p = _paths(acct)
    if os.path.exists(p["portfolio"]):
        return json.load(open(p["portfolio"]))
    return {"account":acct,"cash":100000,"initial_cash":100000,
            "positions":{},"shadow_positions":{}}

def save_portfolio(port, acct="base"):
    atomic_write_json(port, _paths(acct)["portfolio"], indent=2)

def log_trade(record, acct="base"):
    with open(_paths(acct)["trades"],"a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def log_evolution(record, acct="base"):
    with open(_paths(acct)["evolution"],"a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# ── 仓位计算 ────────────────────────────────────────────────
def calc_stop(cur, vwap, atr14):
    noise = round(random.uniform(0.003, 0.008), 4)
    return round((vwap - atr14 * 0.3) * (1 - noise), 2)

def calc_targets(cur, atr14, mode="intraday"):
    if mode == "swing":
        return round(cur + atr14, 2), round(cur + atr14 * 2, 2)
    return round(cur + atr14 * 0.5, 2), round(cur + atr14, 2)

def portfolio_equity(portfolio, live_prices):
    eq = portfolio["cash"]
    for sym, pos in portfolio["positions"].items():
        eq += pos["shares"] * live_prices.get(sym, pos["cost"])
    return eq

def calc_shares(portfolio, cur, stop, live_prices, acct="base"):
    cfg    = _load_acct_cfg(acct)
    equity = portfolio_equity(portfolio, live_prices)
    risk   = equity * cfg.get("risk_per_trade_pct", 0.01)
    dist   = cur - stop
    if dist <= 0:
        return 0
    by_risk = int(risk / dist)
    by_cap  = int(equity * cfg.get("max_position_pct", 0.15) / cur / 3)
    return max(1, min(by_risk, by_cap))

def decide_mode(catalyst_strength, rs_streak, signal_info):
    """
    判断这笔是日内还是波段
    波段条件：催化剂★★+（≥2）OR RS连续强势5轮以上
    """
    if catalyst_strength >= 2:
        return "swing", f"催化剂强度{catalyst_strength}/3→波段"
    if rs_streak >= 5:
        return "swing", f"RS连续{rs_streak}轮强势→波段"
    return "intraday", "日内模式"

# ── 入场 ────────────────────────────────────────────────────
def try_enter(sym, cur, vwap, atr14, rs, persona_score,
              signal_info, spy_chg, live_prices=None,
              catalyst_strength=1, acct="base"):
    """
    尝试入场 T1
    返回操作信息字符串，None=无操作
    """
    lp        = live_prices or {}
    portfolio = load_portfolio(acct)
    cfg       = _load_acct_cfg(acct)

    # 门槛检查
    if persona_score < cfg.get("t1_entry_score", cfg.get("entry_score_threshold", 7.5)):
        return None
    if rs < cfg.get("t1_rs_threshold", cfg.get("entry_rs_threshold", 1.5)):
        return None
    if len(portfolio["positions"]) >= cfg.get("max_positions", 6):
        return None  # 满仓时静默跳过

    # 已有持仓则走加仓逻辑（需要额外指标，这里传默认值，poll.py直接调用有完整数据）
    if sym in portfolio["positions"]:
        return None  # 加仓由 poll.py 通过 try_add_tranche() 单独调用

    stop    = calc_stop(cur, vwap, atr14)
    shares  = calc_shares(portfolio, cur, stop, lp, acct)
    cost    = round(shares * cur, 2)
    if portfolio["cash"] < cost or shares < 1:
        return f"[{sym}] 跳过：现金不足"

    # 判断日内/波段
    rs_streak = signal_info.get("rs_streak", 0)
    mode, mode_reason = decide_mode(catalyst_strength, rs_streak, signal_info)
    tgt1, tgt2 = calc_targets(cur, atr14, mode)
    now  = datetime.now(timezone.utc).isoformat()

    portfolio["cash"] -= cost
    portfolio["positions"][sym] = {
        "shares":    shares, "cost":     cur,
        "stop":      stop,   "target1":  tgt1,  "target2": tgt2,
        "entry_time": now,   "mode":     mode,
        "tranche":   1,      "t2_done":  False,  "t3_done": False,
        "t1_half_done": False,
        "pattern":   signal_info.get("pattern","?"),
        "rs_streak": rs_streak,
        "score":     persona_score, "rs": rs,
        "catalyst":  catalyst_strength,
        "mode_reason": mode_reason,
    }
    portfolio.setdefault("shadow_positions", {})[sym] = {
        "cost": cur, "entry_time": now, "atr14": atr14,
        "stop": stop, "target_5d": round(cur + atr14 * 3, 2),
        "parent_mode": mode,
    }
    save_portfolio(portfolio, acct)

    record = {
        "time":now,"sym":sym,"action":f"BUY_T1_{mode.upper()}",
        "price":cur,"shares":shares,"cost_total":cost,
        "stop":stop,"target1":tgt1,"target2":tgt2,
        "score":persona_score,"rs":rs,"catalyst":catalyst_strength,
        "mode":mode,"mode_reason":mode_reason,
        "pattern":signal_info.get("pattern","?"),"acct":acct,
    }
    log_trade(record, acct)
    mode_icon = "📈波段" if mode=="swing" else "⚡日内"
    return (f"[{acct}/{sym}] ✅ T1{mode_icon}入场 ${cur}×{shares}股  "
            f"止损${stop}  目标${tgt1}/${tgt2}  评分{persona_score}/10")

def _check_add_block(cur, vwap, vol_ratio, rsi3, qqq_5m, pos, cfg):
    """禁止加仓条件，参数来自账号配置"""
    if vol_ratio > cfg.get("block_vol_decline", 1.5) and cur < pos["cost"] * 0.99:
        return f"放量下跌(量比{vol_ratio:.1f}x)，禁止加仓"
    if qqq_5m < cfg.get("block_qqq_drop", -0.5):
        return f"大盘急跌QQQ{qqq_5m:+.2f}%，禁止加仓"
    if rsi3 < cfg.get("block_rsi_floor", 35):
        return f"RSI3={rsi3:.0f}动能崩溃，禁止加仓"
    if cur < vwap * cfg.get("block_vwap_pct", 0.97):
        return f"深度跌破VWAP，禁止加仓"
    return None


def try_add_tranche(sym, cur, vwap, vol_ratio, rsi3, hist, qqq_5m,
                    portfolio=None, acct="base"):
    """
    动态档位加仓 — 参数完全由账号配置驱动

    路径A 强势加仓：价格新高 + 量确认 + RSI未超买
    路径B 回踩加仓：缩量洗盘 + 守VWAP + RSI健康 + 大盘未崩
    T3   突破加仓：达到目标1 + 量放大

    strict/base/loose 三账号的触发阈值、止损设置均不同
    """
    if portfolio is None:
        portfolio = load_portfolio(acct)
    pos = portfolio["positions"].get(sym)
    if not pos:
        return None

    cfg   = _load_acct_cfg(acct)
    block = _check_add_block(cur, vwap, vol_ratio, rsi3, qqq_5m, pos, cfg)
    if block:
        return None

    now  = datetime.now(timezone.utc).isoformat()
    msgs = []
    t1   = pos["cost"]
    atr  = pos.get("atr14", 5.0)

    # ── T2 ──────────────────────────────────────────────────
    if not pos["t2_done"]:
        # 路径A：强势加仓（各账号阈值不同）
        path_a = (cur > t1 * cfg.get("t2a_price_above", 1.005) and
                  vol_ratio > cfg.get("t2a_vol_min", 0.85) and
                  rsi3 < cfg.get("t2a_rsi_max", 78) and
                  qqq_5m > cfg.get("t2a_qqq_min", -0.2))

        # 路径B：回踩加仓（各账号回踩幅度/量比/VWAP要求不同）
        pullback_pct = (t1 - cur) / t1 * 100
        macd_ok = hist >= 0 if cfg.get("t2b_need_macd_pos", True) else True
        path_b = (cfg.get("t2b_pullback_min", 0.3) <= pullback_pct
                                                    <= cfg.get("t2b_pullback_max", 2.5) and
                  vol_ratio < cfg.get("t2b_vol_max", 0.72) and
                  cur >= vwap * cfg.get("t2b_vwap_floor", 0.995) and
                  rsi3 > cfg.get("t2b_rsi_min", 38) and
                  qqq_5m > cfg.get("t2b_qqq_min", -0.3) and
                  macd_ok)

        if path_a or path_b:
            path_label = "A强势" if path_a else f"B回踩{pullback_pct:.1f}%"
            extra = pos["shares"]
            cost  = round(extra * cur, 2)
            if portfolio["cash"] >= cost:
                portfolio["cash"] -= cost
                total    = pos["shares"] + extra
                avg_cost = round((pos["shares"]*t1 + extra*cur) / total, 2)

                # T2止损：各账号不同
                stop_mode = cfg.get("t2_stop_mode", "t1_cost")
                if stop_mode == "t1_cost":
                    new_stop = t1
                elif stop_mode == "buffer":
                    buf = atr * cfg.get("t2_stop_buffer_atr", 0.2)
                    new_stop = round(t1 - buf, 2)
                else:
                    new_stop = t1

                pos.update({"shares":total, "cost":avg_cost, "stop":new_stop,
                            "t2_done":True, "tranche":2,
                            "t2_path":path_label, "t2_price":cur})
                save_portfolio(portfolio, acct)
                log_trade({"time":now,"sym":sym,"action":f"BUY_T2_{path_label}",
                           "price":cur,"shares":extra,"new_avg":avg_cost,
                           "new_stop":new_stop,"path":path_label,"acct":acct}, acct)
                msgs.append(f"[{acct}/{sym}] ✅ T2{path_label}加仓 ${cur}×{extra}股  "
                            f"均${avg_cost}  止损→${new_stop}")

    # ── T3：突破加仓（各账号量比要求不同）──────────────────
    if (not pos["t3_done"] and
            cur >= pos["target1"] * 0.98 and
            vol_ratio > cfg.get("t3_vol_min", 1.25) and
            rsi3 < cfg.get("t3_rsi_max", 82)):
        extra = max(1, pos["shares"] // 3)
        cost  = round(extra * cur, 2)
        if portfolio["cash"] >= cost:
            portfolio["cash"] -= cost
            total    = pos["shares"] + extra
            avg_cost = round((pos["shares"]*pos["cost"] + extra*cur) / total, 2)
            new_stop = pos["target1"]  # T3止损统一上移到目标1
            pos.update({"shares":total, "cost":avg_cost,
                        "stop":new_stop, "t3_done":True, "tranche":3})
            save_portfolio(portfolio, acct)
            log_trade({"time":now,"sym":sym,"action":"BUY_T3_BREAKOUT",
                       "price":cur,"shares":extra,"new_avg":avg_cost,
                       "new_stop":new_stop,"acct":acct}, acct)
            msgs.append(f"[{acct}/{sym}] ✅ T3突破加仓 ${cur}×{extra}股  "
                        f"止损→${new_stop}（目标1）")

    return "\n".join(msgs) if msgs else None

# ── 出场 ────────────────────────────────────────────────────
def check_exits(sym, cur, hi=None, lo=None, acct="base"):
    portfolio = load_portfolio(acct)
    pos  = portfolio["positions"].get(sym)
    if not pos:
        return None
    now  = datetime.now(timezone.utc).isoformat()
    msgs = []
    check_lo = lo if lo else cur

    def close_position(action, price):
        pnl = round((price - pos["cost"]) / pos["cost"] * 100, 2)
        proceeds = round(pos["shares"] * price, 2)
        portfolio["cash"] += proceeds
        _record_shadow_result(sym, portfolio, price, "forced_close", acct)
        del portfolio["positions"][sym]
        save_portfolio(portfolio, acct)
        log_trade({"time":now,"sym":sym,"action":action,"price":price,
                   "shares":pos["shares"],"pnl_pct":pnl,"proceeds":proceeds,
                   "mode":pos.get("mode","?"),"acct":acct}, acct)
        return pnl, proceeds

    if check_lo <= pos["stop"]:
        pnl, proceeds = close_position("STOP_LOSS", cur)
        msgs.append(f"[{sym}] 🛑 止损 ${cur}  {pnl:+.1f}%")

    elif cur >= pos["target2"]:
        pnl, proceeds = close_position("TARGET2_EXIT", cur)
        msgs.append(f"[{sym}] 🎯🎯 目标2全出 ${cur}  {pnl:+.1f}%")

    elif cur >= pos["target1"] and not pos.get("t1_half_done"):
        half     = pos["shares"] // 2
        proceeds = round(half * cur, 2)
        portfolio["cash"] += proceeds
        pnl = round((cur - pos["cost"]) / pos["cost"] * 100, 2)
        pos["shares"]        -= half
        pos["t1_half_done"]   = True
        pos["stop"]           = pos["cost"]
        save_portfolio(portfolio, acct)
        log_trade({"time":now,"sym":sym,"action":"TARGET1_HALF","price":cur,
                   "shares":half,"pnl_pct":pnl,"mode":pos.get("mode","?"),"acct":acct}, acct)
        msgs.append(f"[{acct}/{sym}] 🎯 目标1减半 ${cur}  {pnl:+.1f}%  止损→保本")

    return "\n".join(msgs) if msgs else None

def _record_shadow_result(sym, portfolio, exit_price, reason, acct="base"):
    """记录 shadow 出场结果，用于日内 vs 波段对比"""
    shadow = portfolio.get("shadow_positions", {}).get(sym)
    if not shadow:
        return
    pnl = round((exit_price - shadow["cost"]) / shadow["cost"] * 100, 2)
    log_evolution({
        "time": datetime.now(timezone.utc).isoformat(),
        "sym": sym, "type": "shadow_close",
        "exit_price": exit_price, "entry_price": shadow["cost"],
        "pnl_pct": pnl, "reason": reason,
        "parent_mode": shadow.get("parent_mode","?"),
    }, acct)
    del portfolio["shadow_positions"][sym]

def eod_close_all(live_prices, acct="base"):
    """EOD 平仓所有日内持仓，波段单保留"""
    portfolio = load_portfolio(acct)
    msgs = []
    now  = datetime.now(timezone.utc).isoformat()
    for sym in list(portfolio["positions"].keys()):
        pos = portfolio["positions"][sym]
        if pos.get("mode") == "swing":
            msgs.append(f"[{acct}/{sym}] 📈波段单保留")
            continue
        price    = live_prices.get(sym, pos["cost"])
        pnl      = round((price - pos["cost"]) / pos["cost"] * 100, 2)
        proceeds = round(pos["shares"] * price, 2)
        portfolio["cash"] += proceeds
        shadow = portfolio.get("shadow_positions", {}).get(sym)
        tgt5d  = shadow.get("target_5d", price) if shadow else price
        del portfolio["positions"][sym]
        log_trade({"time":now,"sym":sym,"action":"EOD_CLOSE","price":price,
                   "shares":pos["shares"],"pnl_pct":pnl,"mode":"intraday",
                   "shadow_target":tgt5d,"acct":acct}, acct)
        log_evolution({"time":now,"sym":sym,"type":"eod_compare","actual_pnl":pnl,
                       "actual_price":price,"shadow_target":tgt5d,
                       "lesson":"持有更好" if price<tgt5d else "日内足够"}, acct)
        note = f"  (shadow目标${tgt5d}，{'持有更好' if price<tgt5d else '日内足够'})"
        msgs.append(f"[{acct}/{sym}] 🔔 日内平仓 ${price}  {pnl:+.1f}%{note}")
    if msgs:
        save_portfolio(portfolio, acct)
    return "\n".join(msgs) if msgs else None

# ── 状态显示 ────────────────────────────────────────────────
def get_status(live_prices=None, accounts=None):
    lp    = live_prices or {}
    accts = accounts or ACCOUNTS
    lines = ["── 模拟盘状态 ──"]
    for acct in accts:
        cfg     = _load_acct_cfg(acct)
        port    = load_portfolio(acct)
        equity  = portfolio_equity(port, lp)
        initial = port.get("initial_cash", 100000)
        pnl     = round((equity - initial) / initial * 100, 2)
        n_pos   = len(port["positions"])
        lines.append(
            f"  [{cfg.get('label',acct)}] 权益${equity:,.0f}  {pnl:+.1f}%  "
            f"现金${port['cash']:,.0f}  持仓{n_pos}/{cfg.get('max_positions',6)}"
        )
        for sym, pos in port["positions"].items():
            price   = lp.get(sym, pos["cost"])
            pos_pnl = round((price - pos["cost"]) / pos["cost"] * 100, 2)
            mic     = "📈" if pos.get("mode")=="swing" else "⚡"
            lines.append(
                f"    {mic}{sym} T{pos.get('tranche',1)} ${price:.2f}({pos_pnl:+.1f}%)"
                f" 止损${pos['stop']} 目标${pos['target1']}"
            )
    return "\n".join(lines)

def get_autonomous_watchlist(user_active=True, user_symbols=None, max_auto=3):
    """
    选股规则：
      用户参与时：以用户关注的股票优先（user_symbols）
      用户不参与：自主从 poll_config 的 default_symbols 里选最多 max_auto 只
      选股标准：RS最强 + 催化剂分析 + 当日盘前预测非F场景
    """
    import datetime as _dt
    if user_active and user_symbols:
        return user_symbols  # 用户在线，跟着用户的关注列表

    # 用户不在，自主选股
    cfg_path = os.path.join(BASE, "config", "poll_config.json")
    if not os.path.exists(cfg_path):
        return []
    cfg  = json.load(open(cfg_path))
    pool = cfg.get("default_symbols", [])

    # 读盘前分析，过滤掉F场景（跳水），选RS强的
    today = _dt.date.today().isoformat()
    pm_path = os.path.join(BASE, f"premarket_analysis_{today}.json")
    candidates = []
    if os.path.exists(pm_path):
        pm = json.load(open(pm_path)).get("stocks", {})
        for sym in pool:
            r = pm.get(sym, {})
            if r.get("pred_scene") == "F":
                continue  # 跳过跳水标的
            gap = r.get("gap_pct", 0)
            cs  = r.get("catalyst_strength", 1)
            score = gap * 0.5 + cs * 2  # 简单打分
            candidates.append((sym, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in candidates[:max_auto]]

    # 没有盘前分析，返回默认前3
    return pool[:max_auto]

def load_trade_history(n=5, acct="base"):
    path = _paths(acct)["trades"]
    if not os.path.exists(path):
        return []
    with open(path) as f:
        lines = f.readlines()
    return [json.loads(l) for l in lines[-n:]]

# ── 自我进化：周度统计 ────────────────────────────────────────
def weekly_evolution_report():
    """
    统计最近7天交易，输出：
      - 胜率/盈亏比
      - 日内 vs 波段效果对比
      - 参数调整建议
    """
    if not os.path.exists(TRADE_LOG):
        return "暂无交易记录"

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    trades = []
    with open(TRADE_LOG) as f:
        for line in f:
            t = json.loads(line)
            if t.get("time","") >= cutoff and "pnl_pct" in t:
                trades.append(t)

    if not trades:
        return "近7天无完整交易记录"

    wins    = [t for t in trades if t["pnl_pct"] > 0]
    losses  = [t for t in trades if t["pnl_pct"] <= 0]
    intraday= [t for t in trades if t.get("mode")=="intraday"]
    swing   = [t for t in trades if t.get("mode")=="swing"]

    win_rate = len(wins) / len(trades) * 100
    avg_win  = sum(t["pnl_pct"] for t in wins)  / max(len(wins),1)
    avg_loss = sum(t["pnl_pct"] for t in losses) / max(len(losses),1)
    rr       = abs(avg_win / avg_loss) if avg_loss else 0

    lines = [
        "═══ 模拟盘周度进化报告 ═══",
        f"  交易笔数: {len(trades)}  胜率: {win_rate:.0f}%  盈亏比: 1:{rr:.1f}",
        f"  平均盈利: +{avg_win:.1f}%  平均亏损: {avg_loss:.1f}%",
        f"  日内: {len(intraday)}笔  波段: {len(swing)}笔",
    ]

    if intraday:
        id_pnl = sum(t["pnl_pct"] for t in intraday) / len(intraday)
        lines.append(f"  日内平均盈亏: {id_pnl:+.1f}%")
    if swing:
        sw_pnl = sum(t["pnl_pct"] for t in swing) / len(swing)
        lines.append(f"  波段平均盈亏: {sw_pnl:+.1f}%")

    # 进化建议
    lines.append("\n  进化建议：")
    if win_rate < 50:
        lines.append("  ⚠️ 胜率<50%，考虑提高入场评分门槛（当前7.5→8.0）")
    if rr < 1.5:
        lines.append("  ⚠️ 盈亏比<1.5，考虑放宽止盈目标（ATR×0.5→ATR×0.8）")
    if win_rate >= 60 and rr >= 2:
        lines.append("  ✅ 胜率和盈亏比良好，可考虑适当放宽持仓上限至3只")
    if intraday and swing and len(swing)>0:
        id_avg = sum(t["pnl_pct"] for t in intraday)/len(intraday)
        sw_avg = sum(t["pnl_pct"] for t in swing)/len(swing)
        if sw_avg > id_avg * 1.5:
            lines.append("  📈 波段显著优于日内，考虑提高波段比例（降低催化剂强度门槛）")
        elif id_avg > sw_avg:
            lines.append("  ⚡ 日内表现不差，当前策略适合日内")

    report = "\n".join(lines)
    log_evolution({"time": datetime.now(timezone.utc).isoformat(),
                   "type": "weekly_report", "content": report})
    return report
