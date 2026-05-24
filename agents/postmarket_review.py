"""
收盘复盘 agent — 数据驱动的有根据复盘
核心原则：先列出已知/未知条件，基于实际数据讨论，不武断假设
"""
import sys, os, json, glob
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")

MASTER_PERSPECTIVES = {
    "Minervini":     "技术动量/SEPA/RS",
    "Druckenmiller": "宏观/流动性/大仓位",
    "Marks":         "风险控制/市场周期",
    "Taleb":         "尾部风险/反脆弱",
    "Soros":         "反身性/市场叙事",
    "Livermore":     "价格行为/关键位",
    "Lynch":         "基本面/长期价值",
}

def load_session_log(date_str=None):
    """加载今日交易日记"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(KNOWLEDGE_DIR, f"session_{date_str}.md")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    return None

def load_methodology():
    """加载历史方法论知识库"""
    path = os.path.join(KNOWLEDGE_DIR, "trading_methodology.md")
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""

def extract_unknowns(session_log):
    """从 session_log 提取未知条件"""
    unknowns = []
    for line in session_log.split('\n'):
        if line.strip().startswith('- ❓'):
            unknowns.append(line.strip()[4:].strip())
    return unknowns

def generate_review_prompt(session_log, methodology):
    """生成复盘讨论的结构化 prompt"""
    unknowns = extract_unknowns(session_log)

    prompt = f"""
## 收盘复盘协议

### 已知信息（来自 session_log）
{session_log}

### 历史方法论参考
{methodology[:1000]}

### 复盘规则（所有 agent 必须遵守）
1. **先列未知条件**：每个 agent 发言前，必须明确标注自己在哪些假设上讨论
2. **不武断归因**：如果缺少用户操作记录，说"在不知道入场时间的前提下"
3. **条件性结论**：结论必须附带条件，例如"如果用户在10:30之后入场，则..."
4. **知识提炼**：讨论结束后提炼出可复用的方法论

### 当前已知的未知条件
"""
    for i, u in enumerate(unknowns):
        prompt += f"{i+1}. {u}\n"

    prompt += "\n### 今日待讨论问题\n"
    # 提取用户问题
    in_questions = False
    for line in session_log.split('\n'):
        if '盘后问题' in line:
            in_questions = True
        elif in_questions and line.strip().startswith('-'):
            prompt += f"{line}\n"

    return prompt

def _load_today_data(date_str):
    """加载今日持仓、harvest、CIO信号等实际数据"""
    data = {"positions": {}, "position_pnl": {}, "harvest": [], "cio_signals": {}, "obs_outcomes": []}

    # ── 读取持仓配置 ────────────────────────────────────────
    pos_cfg = {}
    try:
        pos_path = os.path.join(BASE, "config", "positions.json")
        if os.path.exists(pos_path):
            pos_cfg = json.load(open(pos_path, encoding="utf-8")).get("positions", {})
            data["positions"] = pos_cfg
    except Exception:
        pass

    # ── 读取杠杆ETF映射（MRVU→MRVL, NBIL→NBIS, ANEL→ANET）────
    lev_map = {}
    try:
        lev_path = os.path.join(BASE, "config", "leveraged_pairs.json")
        if os.path.exists(lev_path):
            lev_cfg = json.load(open(lev_path, encoding="utf-8"))
            for underlying, v in lev_cfg.items():
                if isinstance(v, dict) and v.get("sym"):
                    lev_map[v["sym"]] = underlying  # ETF → 底层
    except Exception:
        pass

    # ── 实时拉取所有持仓今日收益（最重要的修复）──────────────
    import yfinance as yf
    for sym, pos in pos_cfg.items():
        try:
            cost  = float(pos.get("cost", 0))
            shares = int(pos.get("shares", 0))
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if len(h) < 2:
                continue
            prev_close = float(h["Close"].iloc[-2])  # 昨日收盘
            close_p    = float(h["Close"].iloc[-1])  # 今日收盘
            open_p     = float(h["Open"].iloc[-1])
            # 今日涨跌 = 昨收→今收（含缺口），不是开收
            day_ret = (close_p - prev_close) / prev_close * 100
            pnl_vs_cost = (close_p - cost) / cost * 100 if cost > 0 else 0
            market_val = close_p * shares
            gain_amt   = (close_p - cost) * shares

            # 底层标的（杠杆ETF对应的底层股票）
            underlying = lev_map.get(sym, "")
            note = pos.get("note", "")
            if underlying:
                note = f"底层:{underlying}"

            data["position_pnl"][sym] = {
                "cost": cost, "shares": shares,
                "open": round(open_p, 2), "close": round(close_p, 2),
                "day_ret": round(day_ret, 2),
                "pnl_vs_cost": round(pnl_vs_cost, 2),
                "market_val": round(market_val, 2),
                "gain_amt": round(gain_amt, 2),
                "note": note,
                "underlying": underlying,
            }
        except Exception:
            pass

    # ── Harvest（watchlist标的日内结果）────────────────────
    try:
        harvest_path = os.path.join(BASE, "learning", "daily_harvest.jsonl")
        if os.path.exists(harvest_path):
            data["harvest"] = [json.loads(l) for l in open(harvest_path, encoding="utf-8")
                               if l.strip() and json.loads(l).get("date") == date_str]
    except Exception:
        pass

    # ── CIO信号档案 ─────────────────────────────────────────
    try:
        for f in glob.glob(os.path.join(BASE, "learning", f"cio_signals_{date_str}_*.json")):
            sym = f.split("_")[-1].replace(".json", "")
            data["cio_signals"][sym] = json.load(open(f, encoding="utf-8"))
    except Exception:
        pass

    # ── 观察配对结果 ─────────────────────────────────────────
    try:
        out_path = os.path.join(BASE, "learning", "observation_outcomes.jsonl")
        if os.path.exists(out_path):
            data["obs_outcomes"] = [json.loads(l) for l in open(out_path, encoding="utf-8")
                                    if l.strip() and json.loads(l).get("date") == date_str]
    except Exception:
        pass

    return data


def _master_response(master, specialty, today_data, questions):
    """基于实际持仓数据生成大师回应（数据驱动）"""
    pnl  = today_data.get("position_pnl", {})   # 实际持仓今日数据
    harv = {r["sym"]: r for r in today_data["harvest"] if r.get("track") == "intraday"}
    cio  = today_data["cio_signals"]
    obs  = today_data["obs_outcomes"]

    lines = [f"【{master}（{specialty}）】"]

    # ── 持仓实际表现（position_pnl 优先）────────────────────
    if pnl:
        pos_summary = []
        for sym, v in pnl.items():
            pos_summary.append(f"{sym}{v['day_ret']:+.1f}%(浮{v['pnl_vs_cost']:+.1f}%)")
        lines.append(f"  今日持仓: {', '.join(pos_summary)}")
        total_gain = sum(v["gain_amt"] for v in pnl.values())
        lines.append(f"  总浮盈变动: ${total_gain:+.0f}")

    # ── CIO 信号回测 ─────────────────────────────────────────
    cio_hits, cio_miss = [], []
    for sym, sig_data in cio.items():
        sig = sig_data.get("signal", "neutral")
        if sym in harv:
            ret   = harv[sym].get("ret", 0)
            label = harv[sym].get("label", 0)
            pred  = 1 if sig == "bullish" else (-1 if sig == "bearish" else 0)
            if pred != 0:
                (cio_hits if pred == label else cio_miss).append(f"{sym}({'✅' if pred==label else '❌'}{sig}→{ret:+.1f}%)")
    if cio_hits: lines.append(f"  CIO命中: {', '.join(cio_hits)}")
    if cio_miss: lines.append(f"  CIO失误: {', '.join(cio_miss)}")

    # ── 大师专属视角 ─────────────────────────────────────────
    if "Minervini" in master:
        # 获取今日 SPY 实际收益（用于 RS 计算）
        spy_ret = 0.0
        try:
            import yfinance as _yf
            _sh = _yf.Ticker("SPY").history(period="2d")
            if len(_sh) >= 2:
                spy_ret = (_sh["Close"].iloc[-1] - _sh["Close"].iloc[-2]) / _sh["Close"].iloc[-2] * 100
        except Exception:
            spy_ret = harv.get("SPY", {}).get("ret", -1.0)
        # 关注 RS 最强/最弱标的
        rs_data = [(sym, v["day_ret"] - spy_ret)
                   for sym, v in pnl.items()]
        strongest = max(rs_data, key=lambda x: x[1], default=(None, 0))
        weakest   = min(rs_data, key=lambda x: x[1], default=(None, 0))
        if strongest[0]: lines.append(f"  今日最强持仓: {strongest[0]}(RS{strongest[1]:+.1f}%) — 论点是否验证？")
        if weakest[0]  : lines.append(f"  今日最弱持仓: {weakest[0]}(RS{weakest[1]:+.1f}%) — 需重新评估论点")
        winners = [s for s, r in harv.items() if r.get("ret", 0) > 1.5][:5]
        if winners: lines.append(f"  市场强势标的: {', '.join(winners)}")

    elif "Druckenmiller" in master:
        lines.append("  宏观角度: 今日大盘整体偏弱，个股表现受大盘压制")
        lines.append("  明日关注: QQQ 方向 + VIX 趋势，决定明日持仓是否需要调整")

    elif "Marks" in master:
        if pnl:
            worst = min(pnl.items(), key=lambda x: x[1]["day_ret"])
            best  = max(pnl.items(), key=lambda x: x[1]["day_ret"])
            lines.append(f"  今日最大亏损持仓: {worst[0]} {worst[1]['day_ret']:+.1f}% — 止损执行了吗？")
            lines.append(f"  今日最佳持仓: {best[0]} {best[1]['day_ret']:+.1f}%")
            neg_pnl = [(s, v) for s, v in pnl.items() if v["pnl_vs_cost"] < -3]
            if neg_pnl:
                neg_str = ', '.join(f"{s}({v['pnl_vs_cost']:+.1f}%)" for s, v in neg_pnl)
                lines.append(f"  浮亏>3%的持仓: {neg_str} — 论点是否仍有效？")

    elif "Taleb" in master:
        if pnl:
            lev = [(s, v) for s, v in pnl.items() if "底层" in v.get("note", "")]
            if lev:
                lev_str = ', '.join(f"{s}{v['day_ret']:+.1f}%" for s, v in lev)
                lines.append(f"  杠杆持仓波动: {lev_str}")
                lines.append("  杠杆放大了今日的跌幅，检查是否在可接受的尾部风险范围内")

    elif "Soros" in master:
        lines.append("  反身性观察: 今日持仓整体随大盘下跌，是大盘拖累还是论点变化？")
        lines.append("  关键信号: 明天持仓能否独立于大盘走强，是判断论点是否成立的关键")

    elif "Livermore" in master:
        if pnl:
            for sym, v in pnl.items():
                if "底层" in v.get("note", "") or v["shares"] > 0:
                    lines.append(f"  {sym}: 今收${v['close']:.2f}，明日开盘守${v['close']*0.99:.2f}是关键支撑")
                    break

    elif "Lynch" in master:
        lines.append("  基本面提醒: 今日价格波动不影响长期论点，关注下季度财报和业务进展")
        if cio:
            lines.append(f"  今日有CIO信号的标的: {', '.join(cio.keys())} — 基本面论点是否仍成立？")

    if len(lines) == 1:
        lines.append("  （无持仓数据）")
    return "\n".join(lines)


def _market_3tier_review(date_str=None):
    """大盘三段式复盘：趋势结构 / 资金情绪 / 主线板块（11个板块ETF）"""
    import yfinance as yf
    from datetime import datetime as _dt

    if not date_str:
        date_str = _dt.now().strftime("%Y-%m-%d")

    print("【大盘三段式复盘】")
    print("━" * 50)

    try:
        spy  = yf.Ticker("SPY").history(period="7d")
        qqq  = yf.Ticker("QQQ").history(period="7d")
        dia  = yf.Ticker("DIA").history(period="7d")
        vix  = yf.Ticker("^VIX").history(period="7d")

        def chg1d(h):
            if len(h) >= 2:
                return (float(h["Close"].iloc[-1]) - float(h["Close"].iloc[-2])) / float(h["Close"].iloc[-2]) * 100
            return 0.0

        spy_chg = chg1d(spy); qqq_chg = chg1d(qqq); dia_chg = chg1d(dia)
        vix_chg = chg1d(vix)
        vix_cur = float(vix["Close"].iloc[-1]) if not vix.empty else 20

        spy_vol_today = float(spy["Volume"].iloc[-1]) if not spy.empty else 0
        spy_vol_avg5  = float(spy["Volume"].tail(6).iloc[:-1].mean()) if len(spy) >= 6 else spy_vol_today
        vol_ratio = spy_vol_today / spy_vol_avg5 if spy_vol_avg5 > 0 else 1.0
        vol_label = "放量" if vol_ratio > 1.2 else "缩量" if vol_ratio < 0.8 else "平量"

        all_up   = all(c > 0 for c in [spy_chg, qqq_chg, dia_chg])
        all_down = all(c < 0 for c in [spy_chg, qqq_chg, dia_chg])
        align    = "三指数同步上涨" if all_up else "三指数同步下跌" if all_down else "三指数分化"
        trend_note = "强势" if (all_up and vol_ratio > 1.1) else "弱势" if (all_down and vol_ratio > 1.1) else "混合"

        # ① 趋势结构
        print(f"① 趋势: SPY {spy_chg:+.2f}% | QQQ {qqq_chg:+.2f}% | DIA {dia_chg:+.2f}%  {align}")
        print(f"   成交量: {vol_ratio:.1f}x均量（{vol_label}{'上涨' if spy_chg > 0 else '下跌'}，{trend_note}）")

        # ② 资金情绪
        vix_dir = "↑" if vix_chg > 3 else "↓" if vix_chg < -3 else "→"
        sentiment = "偏多" if spy_chg > 0.5 and vix_chg < 0 else "偏空" if spy_chg < -0.5 and vix_chg > 0 else "中性"
        print(f"\n② 情绪: VIX {vix_cur:.1f} {vix_dir}（{vix_chg:+.1f}%）| 成交额 {vol_ratio:.1f}x均量")
        print(f"   情绪方向: {sentiment}")

        # ③ 主线板块（11个ETF）
        SECTORS = {"XLK": "科技", "XLF": "金融", "XLE": "能源",
                   "XLV": "医疗", "XLI": "工业", "XLC": "通信",
                   "XLY": "消费", "XLU": "公用", "XLRE": "地产",
                   "XLB": "材料", "XLP": "必需消费"}
        sector_perf = []
        for etf, name in SECTORS.items():
            try:
                eh = yf.Ticker(etf).history(period="3d")
                if len(eh) >= 2:
                    ec = (float(eh["Close"].iloc[-1]) - float(eh["Close"].iloc[-2])) / float(eh["Close"].iloc[-2]) * 100
                    sector_perf.append((name, ec, etf))
            except Exception:
                pass

        if sector_perf:
            sector_perf.sort(key=lambda x: x[1], reverse=True)
            up_count = sum(1 for _, c, _ in sector_perf if c > 0)
            breadth  = "宽幅参与" if up_count >= 8 else "窄幅领涨" if up_count >= 4 else "广度极弱"
            day_type = "进攻日" if (all_up and up_count >= 7) else "防守日" if all_down else "轮动日"
            print(f"\n③ 主线: 领涨 {sector_perf[0][0]}({sector_perf[0][1]:+.2f}%) "
                  f"| 领跌 {sector_perf[-1][0]}({sector_perf[-1][1]:+.2f}%) "
                  f"| 板块扩散 {up_count}/{len(sector_perf)}")
            print(f"   判断: {breadth}，{day_type}")
        else:
            print("\n③ 主线: 板块数据不可用")

    except Exception as e:
        print(f"  数据拉取失败: {e}")

    print("━" * 50)
    print()


def run_review(date_str=None):
    """运行收盘复盘（数据驱动版）"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    _market_3tier_review(date_str)

    today_data = _load_today_data(date_str)
    session    = load_session_log(date_str)
    methodology = load_methodology()

    print(f"{'='*60}")
    print(f"  收盘复盘  {date_str}  {datetime.now().strftime('%H:%M')}")
    print(f"{'='*60}")
    print()

    # Step 1: 今日持仓实际表现（最重要）
    print("【Step 1: 今日持仓实际表现】")
    pnl  = today_data["position_pnl"]
    harv = {r["sym"]: r for r in today_data["harvest"] if r.get("track") == "intraday"}
    obs  = today_data["obs_outcomes"]

    if pnl:
        total_gain = sum(v["gain_amt"] for v in pnl.values())
        print(f"  {'标的':6} {'股数':5} {'成本':8} {'收盘':8} {'今日':8} {'浮盈%':8} {'浮盈额':10} {'备注'}")
        print(f"  {'─'*70}")
        for sym, v in pnl.items():
            icon = "📈" if v["pnl_vs_cost"] >= 0 else "📉"
            print(f"  {sym:6} {v['shares']:4}股  ${v['cost']:6.2f}  ${v['close']:6.2f}"
                  f"  {v['day_ret']:+5.1f}%  {v['pnl_vs_cost']:+6.1f}%"
                  f"  ${v['gain_amt']:+7.0f}  {icon} {v['note']}")
        print(f"  {'─'*70}")
        print(f"  总持仓浮盈: ${total_gain:+.0f}")
    else:
        print("  （持仓数据获取失败，请检查 yfinance）")

    print(f"\n  CIO信号档案: {', '.join(today_data['cio_signals'].keys()) or '无'}")
    print(f"  观察配对记录: {len(obs)} 条")
    print()

    # Step 2: 未知条件（如有 session_log）
    if session:
        unknowns = extract_unknowns(session)
        if unknowns:
            print("【Step 2: 待确认条件】")
            for i, u in enumerate(unknowns, 1):
                print(f"  {i}. {u}")
            print()

        # Step 3: 用户问题
        questions = []
        in_q = False
        for line in session.split('\n'):
            if '盘后问题' in line: in_q = True
            elif in_q and line.strip().startswith('-'):
                questions.append(line.strip()[1:].strip())
    else:
        questions = []
        print("【提示】未找到今日交易日记，基于可用数据做通用复盘")
        print(f"  如需个性化复盘，填写: {KNOWLEDGE_DIR}/session_{date_str}.md")
        print()

    # Step 4: 大师数据驱动点评
    print("【Step 3: 大师复盘（数据驱动）】")
    print()
    for master, specialty in MASTER_PERSPECTIVES.items():
        print(_master_response(master, specialty, today_data, questions))
        print()

    # Step 4: 方法论提炼
    print("【Step 4: 方法论提炼】")
    pnl = today_data.get("position_pnl", {})

    # 持仓论点状态
    if pnl:
        print("  持仓论点状态:")
        for sym, v in pnl.items():
            status = "⚠️待确认" if v["pnl_vs_cost"] < -5 else ("✅正常" if v["pnl_vs_cost"] > 0 else "🟡观察")
            und = f"(底层:{v['underlying']})" if v.get("underlying") else ""
            print(f"    {sym}{und}: 今日{v['day_ret']:+.1f}%  浮盈{v['pnl_vs_cost']:+.1f}%  {status}")

    # 市场表现统计
    if harv:
        total  = len(harv)
        wins   = sum(1 for r in harv.values() if r.get("label") == 1)
        losses = sum(1 for r in harv.values() if r.get("label") == -1)
        print(f"\n  市场表现: {total}只标的  正例{wins}  负例{losses}  中性{total-wins-losses}")
        top3 = sorted(harv.items(), key=lambda x: x[1].get("ret", 0), reverse=True)[:3]
        bot3 = sorted(harv.items(), key=lambda x: x[1].get("ret", 0))[:3]
        top3_str = ', '.join(f"{s}{r['ret']:+.1f}%" for s, r in top3)
        bot3_str = ', '.join(f"{s}{r['ret']:+.1f}%" for s, r in bot3)
        print(f"  今日前3强: {top3_str}")
        print(f"  今日后3弱: {bot3_str}")

    # 门控信号验证
    if obs:
        gate_pass_correct  = sum(1 for o in obs if o.get("gate_pass") and o.get("signal_correct"))
        gate_pass_total    = sum(1 for o in obs if o.get("gate_pass"))
        gate_block_correct = sum(1 for o in obs if o.get("gate_block") and o.get("signal_correct"))
        gate_block_total   = sum(1 for o in obs if o.get("gate_block"))
        print(f"\n  门控验证:")
        if gate_pass_total:
            print(f"    入场门通过→正确率: {gate_pass_correct}/{gate_pass_total} ({gate_pass_correct/gate_pass_total:.0%})")
        if gate_block_total:
            print(f"    门控禁止→正确率: {gate_block_correct}/{gate_block_total} ({gate_block_correct/gate_block_total:.0%})")

    # 明日关注点
    print(f"\n  明日关注:")
    if pnl:
        for sym, v in pnl.items():
            if v["pnl_vs_cost"] < -3:
                print(f"    ⚠️ {sym}: 浮亏{v['pnl_vs_cost']:+.1f}%，明日需确认论点是否仍有效")
    print(f"    📋 详见 knowledge/session_{date_str}.md 明日计划")
    print()

if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    run_review(date_str)
