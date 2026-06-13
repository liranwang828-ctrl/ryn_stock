"""
盘前清单生成器 — 为每只关注股票生成五步决策清单
用法: python3.12 agents/premarket_checklist.py [SYM1 SYM2 ...]

输出：
  - 控制台格式化清单
  - daily_checklist_{date}.json 供 poll.py 引用
"""
import json
import os
import sys
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))


# ──────────────────────────────────────────────
# 内部辅助
# ──────────────────────────────────────────────

def _load_positions():
    path = os.path.join(BASE, "config", "positions.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {}


def _load_premarket(date_str):
    path = os.path.join(BASE, f"premarket_analysis_{date_str}.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {}


def _load_poll_state(date_str):
    path = os.path.join(BASE, "learning", f"poll_state_{date_str}.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {}


def _env_label(spy_pre):
    """根据 SPY 盘前涨跌给环境打标签"""
    if spy_pre is None:
        return "未知环境"
    if spy_pre >= 0.005:
        return f"顺风(+{spy_pre:.1%})"
    if spy_pre <= -0.01:
        return f"逆风({spy_pre:.1%})"
    return f"中性({spy_pre:.1%})"


def _flex_action(rsi, vwap_dev, vol_ratio, macd_positive):
    """
    判断今日 Flex 行动方向：
      add  — 超卖信号 ≥3/4 → 可加仓
      cut  — 超买信号 ≥3/4 → 可减仓
      hold — 无明显信号
    """
    add_signals = 0
    cut_signals = 0

    if rsi is not None:
        if rsi < 25:
            add_signals += 1
        if rsi > 80:
            cut_signals += 1

    if vwap_dev is not None:
        if vwap_dev < -0.02:
            add_signals += 1
        if vwap_dev > 0.02:
            cut_signals += 1

    if vol_ratio is not None:
        # 量萎缩(vol_ratio<0.8)：超卖时佐证加仓，超买时佐证减仓
        if vol_ratio < 0.8:
            add_signals += 1
            cut_signals += 1

    if macd_positive is not None:
        # MACD 底背离(macd_positive=False 但价格在低位) → 加分
        if not macd_positive:
            add_signals += 1
        if macd_positive:
            cut_signals += 1

    if add_signals >= 3:
        return "add", add_signals
    if cut_signals >= 3:
        return "cut", cut_signals
    return "hold", 0


def _action_label(action_code, flex_dir):
    """根据持仓类型行动码+flex方向生成说明"""
    base = {
        "A": "主动操作",
        "B": "被动守护",
        "C": "评估日",
    }.get(action_code, "待定")
    if flex_dir == "add":
        hint = "（超卖信号≥3/4，可Flex加仓）"
    elif flex_dir == "cut":
        hint = "（超买信号≥3/4，可Flex减仓）"
    else:
        hint = "（无明显超买超卖）"
    return f"{action_code} — {base}{hint}"


def _position_summary(sym, pos_cfg, poll_snap):
    """返回持仓状态行"""
    t1_shares = pos_cfg.get("t1_shares", pos_cfg.get("shares", 0))
    t1_cost = pos_cfg.get("t1_cost", pos_cfg.get("cost", 0))
    t2_shares = pos_cfg.get("t2_shares", 0) or 0
    total_shares = t1_shares + t2_shares
    last_price = None
    if poll_snap:
        last_price = poll_snap.get("last_price")
    cost_price = t1_cost
    if last_price:
        total_val = total_shares * last_price
        return (f"T1={t1_shares}股@${cost_price:.2f}  "
                f"Flex={t2_shares}股  "
                f"总=${total_val:.0f}  当前=${last_price:.2f}")
    return f"T1={t1_shares}股@${cost_price:.2f}  Flex={t2_shares}股"


_MACRO_JSON_PATH_CL = os.path.join(os.path.dirname(os.path.dirname(__file__)), "findings", "macro.json")

def _load_macro_json():
    """静默读取 findings/macro.json，失败返回空 dict"""
    if os.path.exists(_MACRO_JSON_PATH_CL):
        try: return json.load(open(_MACRO_JSON_PATH_CL, encoding="utf-8"))
        except: pass
    return {}

def _macro_fit_line(pos_cfg, macro):
    """
    根据当前宏观数据和持仓 macro_sensitivity，生成一行宏观适配摘要。
    若 macro 为空或 pos_cfg 无 macro_sensitivity，返回 None。
    """
    ms = pos_cfg.get("macro_sensitivity")
    if not ms or not macro:
        return None

    yield_curve  = macro.get("yield_curve", "")
    dxy          = macro.get("dxy") or 0
    cpi_raw      = macro.get("cpi_latest")
    macro_score  = macro.get("macro_score", 5)

    try: cpi_val = float(str(cpi_raw).replace("%",""))
    except: cpi_val = 0  # 解析失败时 inflation 不触发（保守降级，不误报）

    active = {}
    if yield_curve == "倒挂":
        active["rate_up"] = ms.get("rate_up", "中")
        if macro_score <= 5:
            active["credit_tight"] = ms.get("credit_tight", "中")
    if dxy > 103:
        active["dollar_strong"] = ms.get("dollar_strong", "中")
    if cpi_val > 300:
        active["inflation"] = ms.get("inflation", "中")
    if macro_score <= 3:
        active["recession"] = ms.get("recession", "中")

    if not active:
        return "  宏观适配: ✅ 当前无显著宏观逆风"

    neg = [k for k, v in active.items() if v == "负"]
    pos_vars = [k for k, v in active.items() if v == "正"]
    neg_labels = {"rate_up": "利率高位↓", "credit_tight": "信贷紧↓",
                  "dollar_strong": "美元强↓", "inflation": "通胀高↓", "recession": "衰退风险↓"}
    pos_labels = {"rate_up": "利率高位↑", "credit_tight": "信贷紧↑",
                  "dollar_strong": "美元强↑", "inflation": "通胀高↑", "recession": "衰退风险↑"}

    macro_type = pos_cfg.get("macro_type", "")
    if len(neg) == 0:
        icon, detail = "✅", "当前宏观环境友好"
    elif len(neg) <= 2:
        icon = "⚠️"
        detail = " ".join(neg_labels[k] for k in neg) + f" — {macro_type}承压，催化剂驱动为主"
    else:
        icon = "🔴"
        detail = " ".join(neg_labels[k] for k in neg) + f" — 多维逆风，论点需更强支撑"
    if pos_vars:
        detail += " | 顺风: " + " ".join(pos_labels.get(k, k) for k in pos_vars)
    return f"  宏观适配: {icon} {detail}"


_MACRO_JSON_EMO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "findings", "macro.json")

def _emotion_bottom_check(sym: str, pm_data: dict) -> tuple:
    """
    情绪底部五维核查（美股适配版），满足 3/5 维度触发显示。
    返回 (score: int, detail: str) 或 (0, "") 若不满足。
    """
    import yfinance as yf
    score = 0
    dims  = []

    macro = {}
    if os.path.exists(_MACRO_JSON_EMO):
        try: macro = json.load(open(_MACRO_JSON_EMO, encoding="utf-8"))
        except: pass

    try:
        t   = yf.Ticker(sym)
        h1y = t.history(period="1y")

        # 维度1：量能萎缩（近5日均量 < 52周中位数 60%）
        if len(h1y) >= 60:
            vol_med  = float(h1y["Volume"].median())
            vol_5d   = float(h1y["Volume"].tail(5).mean())
            if vol_5d < vol_med * 0.6:
                score += 1; dims.append("量萎缩✅")
            else:
                dims.append("量萎缩❌")
        else:
            dims.append("量萎缩?")

        # 维度2：恐慌不高（VIX < 18）
        vix_val = float(macro.get("vix") or 20)
        if vix_val < 18:
            score += 1; dims.append("恐慌低✅")
        else:
            dims.append("恐慌低❌")

        # 维度3：新闻情绪中性/负面
        news_ok = False
        if pm_data:
            s = pm_data.get("stocks", {}).get(sym, {})
            if s.get("sentiment") in ("neutral", "negative", "bearish"):
                news_ok = True
        if news_ok:
            score += 1; dims.append("情绪中性✅")
        else:
            dims.append("情绪中性❌")

        # 维度4：价格在 MA20 ± 3% 以内
        if len(h1y) >= 20:
            ma20 = float(h1y["Close"].rolling(20).mean().iloc[-1])
            cur  = float(h1y["Close"].iloc[-1])
            if abs(cur - ma20) / ma20 * 100 < 3.0:
                score += 1; dims.append("价格合理✅")
            else:
                dims.append("价格合理❌")
        else:
            dims.append("价格合理?")

        # 维度5：筹码稳定（空头占比 < 5%）
        try:
            info = t.info
            sp   = info.get("shortPercentOfFloat", 0) or 0
            if float(sp) < 0.05:
                score += 1; dims.append("筹码稳✅")
            else:
                dims.append("筹码稳❌")
        except Exception:
            dims.append("筹码稳?")

    except Exception:
        return 0, ""

    if score < 3:
        return 0, ""

    icon  = "💡" if score >= 4 else "🔍"
    label = "强底部信号" if score >= 4 else "底部信号"
    detail = f"  情绪底部: {icon} {label}（{score}/5）— " + " ".join(dims)
    return score, detail


def _cancel_conditions(sym: str, pos_cfg: dict = None, macro: dict = None) -> list:
    """个性化取消条件，委托给 premarket_order_sheet 的实现"""
    from stock_team.core.premarket_order_sheet import _personalized_cancel_conditions
    tech = {}
    if pos_cfg:
        node1 = pos_cfg.get("node1")
        if node1:
            tech["lo5"] = node1
    return _personalized_cancel_conditions(sym, pos_cfg or {}, tech, macro or {})


def _format_held(sym, pos_cfg, pm_data, poll_snap, vix):
    """为已持仓股票生成清单块"""
    pos_type = pos_cfg.get("position_type", "thesis")
    thesis = pos_cfg.get("thesis", "（未填写论点）")
    thesis_status = pos_cfg.get("thesis_status", "intact")
    daily_action = pos_cfg.get("daily_action", "B")
    flex_min = pos_cfg.get("flex_min", 0)
    flex_max = pos_cfg.get("flex_max", 0)
    catalyst_type        = pos_cfg.get("catalyst_type")
    catalyst_persistence = pos_cfg.get("catalyst_persistence")
    _ct_cn = {
        "earnings":   "业绩",
        "policy":     "政策",
        "order":      "订单",
        "capital":    "资本运作",
        "regulatory": "监管",
    }
    _cp_cn = {"structural": "结构性", "one_time": "一次性"}

    # 技术数据
    rsi = None
    vwap_dev = None
    vol_ratio = None
    macd_positive = None
    spy_pre = None

    has_catalyst = False
    catalyst_str = "无已知催化剂"

    if pm_data:
        macro = pm_data.get("macro", {})
        spy_pre = macro.get("spy_pre")
        stocks = pm_data.get("stocks", {})
        # 尝试直接 sym，也尝试 underlying（杠杆ETF场景）
        underlying = pos_cfg.get("underlying", sym)
        s_data = stocks.get(underlying) or stocks.get(sym)
        if s_data:
            vwap_current = s_data.get("vwap_current")
            prev_close = s_data.get("prev_close")
            if vwap_current and prev_close and prev_close != 0:
                vwap_dev = (vwap_current - prev_close) / prev_close
            news_type = s_data.get("news_type", "")
            catalyst_strength = s_data.get("catalyst_strength", 0) or 0
            top_headline = s_data.get("top_headline", "")
            if news_type in ("earnings", "upgrade", "catalyst") or catalyst_strength >= 2:
                has_catalyst = True
                if top_headline:
                    catalyst_str = top_headline[:60]

    if poll_snap:
        rsi = poll_snap.get("last_rsi14_5m")
        vol_ratio = poll_snap.get("last_vol_ratio")
        macd_val = poll_snap.get("last_macd")
        if macd_val is not None:
            macd_positive = float(macd_val) > 0

    flex_dir, flex_cnt = _flex_action(rsi, vwap_dev, vol_ratio, macd_positive)
    env_str = _env_label(spy_pre)
    vix_str = f"VIX={vix:.0f}" if vix else ""

    # 仓位上限提示
    cap_note = ""
    if spy_pre is not None and spy_pre < -0.005:
        cap_note = f" → 仓位上限{flex_min}股（逆风限仓）"
    else:
        cap_note = f" → 仓位上限{flex_max}股"

    type_cn = {
        "thesis": "论点型",
        "catalyst": "催化剂型",
        "flex": "Flex独立型",
        "trend": "趋势型",
    }.get(pos_type, pos_type)

    status_icon = {"intact": "✅", "weakening": "⚠️", "broken": "❌"}.get(thesis_status, "❓")
    action_str = _action_label(daily_action, flex_dir)
    pos_str = _position_summary(sym, pos_cfg, poll_snap)

    _macro_line = _macro_fit_line(pos_cfg, _load_macro_json())
    _emo_score, _emo_line = _emotion_bottom_check(sym, pm_data)
    lines = [
        "━" * 40,
        f"[{sym}] {type_cn} | {datetime.now().strftime('%Y-%m-%d')}",
        "━" * 40,
        f"【论点】{thesis}",
        f"【论点状态】{thesis_status} {status_icon}",
        *(
            [f"【催化剂】类型: {_ct_cn.get(catalyst_type, catalyst_type)} | "
             f"持续性: {_cp_cn.get(catalyst_persistence, 'N/A')} | "
             f"{catalyst_str}"]
            if (has_catalyst and catalyst_type) else
            [f"【催化剂】{catalyst_str}"]
        ),
        *([_macro_line] if _macro_line else []),
        *([_emo_line] if _emo_score >= 3 else []),
        f"【今日环境】{env_str} {vix_str}{cap_note}",
        f"【今日行动】{action_str}",
        "【关键价位】",
        f"  Flex加仓触发: RSI14<25 + VWAP偏离<-2% + 量萎缩 + MACD背离 ≥3/4",
        f"  Flex减仓触发: RSI14>80 + VWAP偏离>+2% + 量放量 + MACD顶背离 ≥3/4",
        f"  T1止损: 论点破裂（不基于价格）",
        f"  三节点（盘前填写）:",
        f"    节点1（支撑/保护）: ___ （跌破+放量→论点警告）",
        f"    节点2（怀疑位）:    ___ （跌破+放量→论点承压）",
        f"    节点3（突破位）:    ___ （突破+放量→论点验证）",
        f"    当前状态: B（论点区间，盘中由poll.py更新）",
        f"【持仓状态】{pos_str}",
        "【取消条件】今日若以下任一发生则取消计划：",
        *[f"  × {c}" for c in _cancel_conditions(sym, pos_cfg, _load_macro_json())],
        "━" * 40,
    ]
    return "\n".join(lines)


def _format_watch(sym, pm_data, vix):
    """为无持仓关注股票生成建仓评估块"""
    spy_pre = None
    has_catalyst = False
    catalyst_str = "无已知催化剂"
    entry_type = "flex"

    if pm_data:
        macro = pm_data.get("macro", {})
        spy_pre = macro.get("spy_pre")
        stocks = pm_data.get("stocks", {})
        s_data = stocks.get(sym, {})
        if s_data:
            news_type = s_data.get("news_type", "")
            catalyst_strength = s_data.get("catalyst_strength", 0) or 0
            top_headline = s_data.get("top_headline", "")
            if news_type in ("earnings", "upgrade", "catalyst") or catalyst_strength >= 2:
                has_catalyst = True
                entry_type = "catalyst"
                if top_headline:
                    catalyst_str = top_headline[:60]

    env_str = _env_label(spy_pre)
    vix_str = f"VIX={vix:.0f}" if vix else ""

    type_cn = "催化剂型" if has_catalyst else "Flex独立型"

    lines = [
        "━" * 40,
        f"[{sym}] {type_cn} | {datetime.now().strftime('%Y-%m-%d')} | 无仓建仓评估",
        "━" * 40,
        f"【催化剂】{catalyst_str}",
        f"【今日环境】{env_str} {vix_str}",
        "【入场条件】4/4信号同时满足（更严格）",
        "  RSI14<25 + VWAP偏离<-2% + 量萎缩<0.8 + MACD底背离",
        "【关键价位】",
        "  入场确认: 4/4信号齐备 + 放量突破或守稳关键支撑",
        "  止损基准: 关键支撑跌破或催化剂失效",
        "  三节点（盘前填写）:",
        "    节点1（支撑/保护）: ___ （跌破+放量→论点警告）",
        "    节点2（怀疑位）:    ___ （跌破+放量→论点承压）",
        "    节点3（突破位）:    ___ （突破+放量→论点验证）",
        "    当前状态: B（论点区间，盘中由poll.py更新）",
        "━" * 40,
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────
# 核心入口
# ──────────────────────────────────────────────

def generate_checklist(symbols, date_str=None):
    """
    生成每只股票的盘前决策清单。
    返回格式化字符串，同时写 daily_checklist_{date}.json。

    symbols: list[str] — 股票代码列表
    date_str: str | None — YYYY-MM-DD，默认今天
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    pos_data = _load_positions()
    positions = pos_data.get("positions", {})
    pm_data = _load_premarket(date_str)
    poll_state = _load_poll_state(date_str)
    poll_syms = poll_state.get("symbols", {})

    # VIX
    vix = None
    try:
        import yfinance as yf
        vix = float(yf.Ticker("^VIX").history(period="1d")["Close"].iloc[-1])
    except Exception:
        pass

    output_blocks = []
    json_records = {}

    for sym in symbols:
        if not sym:
            continue
        sym = sym.upper()
        pos_cfg = positions.get(sym)
        poll_snap = poll_syms.get(sym)

        if pos_cfg:
            block = _format_held(sym, pos_cfg, pm_data, poll_snap, vix)
        else:
            block = _format_watch(sym, pm_data, vix)

        output_blocks.append(block)

        # JSON 记录
        json_records[sym] = {
            "sym": sym,
            "date": date_str,
            "has_position": pos_cfg is not None,
            "position_type": pos_cfg.get("position_type") if pos_cfg else None,
            "thesis_status": pos_cfg.get("thesis_status") if pos_cfg else None,
            "daily_action": pos_cfg.get("daily_action") if pos_cfg else None,
            "flex_min": pos_cfg.get("flex_min") if pos_cfg else None,
            "flex_max": pos_cfg.get("flex_max") if pos_cfg else None,
            # 三节点（盘前填写）：用户手动填写后 poll.py 实时更新 node_state
            "node1": None,       # 论点支撑位（跌破+放量→论点警告）
            "node2": None,       # 论点怀疑位（跌破+放量→论点承压）
            "node3": None,       # 论点突破位（突破+放量→论点验证）
            "node_state": "B",   # 默认B（论点区间），盘中由poll.py实时更新
        }

    # 写 JSON
    out_path = os.path.join(BASE, f"daily_checklist_{date_str}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "symbols": json_records,
        }, f, ensure_ascii=False, indent=2)

    header = f"\n{'═'*50}\n盘前操作清单 {date_str}\n{'═'*50}"
    full_output = header + "\n" + "\n".join(output_blocks)
    print(full_output)
    return full_output


def prepare_master_brief_context(sym: str, tech: dict, macro: dict,
                                  pos_cfg: dict, order_sheet: dict) -> dict:
    """
    整理大师 brief 所需的结构化输入数据，返回 input dict。
    不涉及 LLM 调用——结果供盘前对话中 Claude 读取后按 brief 格式生成分析。
    同时将结果追加写入 findings/premarket_masters_{date}.json。
    """
    from datetime import datetime

    sym  = sym.upper()
    date = datetime.now().strftime("%Y-%m-%d")

    # --- Minervini 所需：技术位置 ---
    cur    = tech.get("cur", 0)
    ma20   = tech.get("ma20", 0)
    dev    = tech.get("ma20_dev", 0)
    atr    = tech.get("atr14", 0)
    lo5    = tech.get("lo5", 0)
    minervini_ctx = {
        "current_price": cur,
        "ma20":          ma20,
        "ma20_dev_pct":  dev,
        "atr14":         atr,
        "lo5":           lo5,
        "ma20_position": "上方" if cur > ma20 else "下方",
        "dev_quality":   "合理区间" if -8 <= dev <= 8 else ("深度超卖" if dev < -8 else "高于均线"),
    }

    # --- Druckenmiller 所需：宏观+sizing ---
    macro_tone  = macro.get("macro_tone", "中性")
    macro_score = macro.get("macro_score", 5)
    vix         = macro.get("vix", 0)
    ms          = (pos_cfg or {}).get("macro_sensitivity", {})
    macro_type  = (pos_cfg or {}).get("macro_type", "")
    if macro_score >= 7 and macro_tone != "偏空":
        sizing_note = "标准仓（宏观顺风）"
    elif macro_score >= 5:
        sizing_note = "小仓（0.5x标准）（宏观中性）"
    else:
        sizing_note = "不做或极小仓（宏观逆风）"

    druckenmiller_ctx = {
        "regime":      macro.get("regime", macro_tone),
        "macro_tone":  macro_tone,
        "macro_score": macro_score,
        "vix":         vix,
        "macro_type":  macro_type,
        "sizing_note": sizing_note,
        "headwinds":   [k for k, v in ms.items() if v == "负"],
    }

    # --- Marks 所需：RR 比 + 风险点 ---
    rr    = order_sheet.get("rr_ratio", 0)
    entry = order_sheet.get("entry_base", 0)
    stop  = order_sheet.get("stop_loss", 0)
    tgt   = order_sheet.get("target_price", 0)
    risks = order_sheet.get("cancel_conditions", [])[:2]

    marks_ctx = {
        "rr_ratio":   rr,
        "entry":      entry,
        "stop":       stop,
        "target":     tgt,
        "rr_ok":      rr >= 2.5,
        "main_risks": risks,
    }

    result = {
        "sym":           sym,
        "date":          date,
        "thesis":        (pos_cfg or {}).get("thesis", ""),
        "thesis_status": (pos_cfg or {}).get("thesis_status", ""),
        "minervini":     minervini_ctx,
        "druckenmiller": druckenmiller_ctx,
        "marks":         marks_ctx,
    }

    # 写入 findings/premarket_masters_{date}.json
    findings_dir = os.path.join(BASE, "findings")
    os.makedirs(findings_dir, exist_ok=True)
    out_path = os.path.join(findings_dir, f"premarket_masters_{date}.json")

    existing = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing[sym] = result
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return result


# ──────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    syms = sys.argv[1:] if len(sys.argv) > 1 else []
    if not syms:
        # 默认读持仓
        try:
            _pos = json.load(open(os.path.join(BASE, "config", "positions.json"), encoding="utf-8"))
            syms = list(_pos.get("positions", {}).keys())
        except Exception:
            syms = []
    if not syms:
        print("用法: python3.12 agents/premarket_checklist.py [SYM1 SYM2 ...]")
        sys.exit(1)
    generate_checklist(syms)
