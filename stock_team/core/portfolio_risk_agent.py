"""
Portfolio Risk Agent — 组合层风险聚合
计算：相关性矩阵、杠杆暴露、5%大盘跌VaR、压力测试
"""
import sys, os, json
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_possible_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))
BASE = _possible_base if os.path.exists(os.path.join(_possible_base, "templates")) else ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
POSITIONS_PATH = os.path.join(BASE, "config", "positions.json")
LEV_PAIRS_PATH = os.path.join(BASE, "config", "leveraged_pairs.json")

# 排除跟踪仓位（用户偏好，不纳入风险计算）
EXCLUDED_SYMS = {"PONY"}

# ── 数据加载 ──────────────────────────────────────────────────

def _load_positions():
    """读取 config/positions.json，返回 {sym: {cost, shares}} 列表（排除跟踪仓位）"""
    data = json.load(open(POSITIONS_PATH, encoding="utf-8"))
    positions = data.get("positions", {})
    result = {}
    for sym, info in positions.items():
        if sym.startswith("_") or sym in EXCLUDED_SYMS:
            continue
        result[sym] = {
            "cost": float(info["cost"]),
            "shares": float(info.get("shares", 0)),
            "broker_last_price": info.get("broker_last_price"),
        }
    return result


def _load_lev_pairs():
    """
    读取 config/leveraged_pairs.json，构建：
      lev_etf_sym → {underlying, leverage}
    (文件格式: underlying → {sym: lev_etf, leverage: N})
    """
    if not os.path.exists(LEV_PAIRS_PATH):
        return {}
    data = json.load(open(LEV_PAIRS_PATH, encoding="utf-8"))
    mapping = {}   # lev_etf → {underlying, leverage}
    for underlying, info in data.items():
        if underlying.startswith("_"):
            continue
        lev_sym = info.get("sym", "")
        lev_n   = int(info.get("leverage", 1))
        if lev_sym:
            mapping[lev_sym] = {"underlying": underlying, "leverage": lev_n}
    return mapping


# ── 市场数据获取 ──────────────────────────────────────────────

def _fetch_prices(syms, period="60d"):
    """
    用 yfinance 获取 syms 的日线收盘价 DataFrame（60天）。
    返回 pd.DataFrame，列=股票代码，行=日期；缺失列跳过不报错。
    """
    import yfinance as yf
    import pandas as pd
    frames = {}
    for sym in syms:
        try:
            h = yf.Ticker(sym).history(period=period)
            if not h.empty:
                frames[sym] = h["Close"].rename(sym)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames.values(), axis=1).dropna(how="all")


def _fetch_current_price(sym):
    """获取单个标的最新价格，失败返回 None"""
    try:
        import yfinance as yf
        h = yf.Ticker(sym).history(period="2d")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _fetch_beta(sym):
    """从 yfinance info 获取 beta，失败返回 1.0"""
    try:
        import yfinance as yf
        info = yf.Ticker(sym).info
        b = info.get("beta")
        if b is not None:
            return float(b)
    except Exception:
        pass
    return 1.0


def _fetch_sector(sym):
    """从 yfinance info 获取 sector，失败返回 'Unknown'"""
    try:
        import yfinance as yf
        info = yf.Ticker(sym).info
        return info.get("sector") or info.get("quoteType") or "Unknown"
    except Exception:
        pass
    return "Unknown"


# ── 核心计算 ──────────────────────────────────────────────────

def compute_portfolio_risk():
    """
    计算组合风险快照，返回 dict 包含所有字段：
      positions_detail, total_exposure, leverage_ratio,
      var_5pct_loss, var_5pct_pct,
      sector_concentration, correlation_matrix,
      top_corr_pair, warnings
    """
    import numpy as np

    positions = _load_positions()
    lev_map   = _load_lev_pairs()   # lev_etf → {underlying, leverage}

    if not positions:
        return None

    # ── 步骤1：解析每个持仓，映射底层标的 + 杠杆倍数 ─────────
    detail = []   # list of dicts
    for sym, pos in positions.items():
        if sym in lev_map:
            underlying = lev_map[sym]["underlying"]
            leverage   = lev_map[sym]["leverage"]
        else:
            underlying = sym
            leverage   = 1

        cur_price = pos.get("broker_last_price")
        try:
            cur_price = float(cur_price) if cur_price is not None else None
        except Exception:
            cur_price = None
        if cur_price is None:
            cur_price = _fetch_current_price(sym)
        if cur_price is None:
            cur_price = pos["cost"]   # fallback 到成本价

        market_value  = cur_price * pos["shares"]
        net_exposure  = market_value * leverage    # 杠杆放大后的风险敞口

        detail.append({
            "sym":         sym,
            "underlying":  underlying,
            "leverage":    leverage,
            "shares":      pos["shares"],
            "cost":        pos["cost"],
            "cur_price":   cur_price,
            "market_value": market_value,
            "net_exposure": net_exposure,
        })

    total_value    = sum(d["market_value"] for d in detail)
    total_exposure = sum(d["net_exposure"] for d in detail)
    leverage_ratio = total_exposure / total_value if total_value > 0 else 1.0

    # ── 步骤2：板块集中度 ─────────────────────────────────────
    underlying_syms = list({d["underlying"] for d in detail})
    sector_map_live = {}
    for sym in underlying_syms:
        sector_map_live[sym] = _fetch_sector(sym)

    sector_exposure = {}
    for d in detail:
        sec = sector_map_live.get(d["underlying"], "Unknown")
        # 简化板块名称
        sec = _simplify_sector(sec, d["underlying"])
        sector_exposure[sec] = sector_exposure.get(sec, 0) + d["net_exposure"]

    sector_pct = {}
    for sec, exp in sorted(sector_exposure.items(), key=lambda x: -x[1]):
        sector_pct[sec] = round(exp / total_exposure * 100, 1) if total_exposure > 0 else 0

    # ── 步骤3：计算各底层标的 beta + VaR（SPY跌5%） ──────────
    total_var_loss = 0.0
    for d in detail:
        beta = _fetch_beta(d["underlying"])
        d["beta"] = beta
        # 若 SPY 跌 5%，该持仓预估损失 = 敞口 × beta × 5%
        d["var_5pct_loss"] = d["net_exposure"] * beta * 0.05

    total_var_loss = sum(d["var_5pct_loss"] for d in detail)
    var_5pct_pct   = total_var_loss / total_value * 100 if total_value > 0 else 0

    # ── 步骤4：相关性矩阵（60日日收益率） ─────────────────────
    price_df = _fetch_prices(underlying_syms, period="60d")
    corr_matrix = {}
    top_corr_pair = None
    top_corr_val  = 0.0

    if not price_df.empty and len(price_df.columns) >= 2:
        ret_df = price_df.pct_change().dropna()
        corr_df = ret_df.corr()
        # 转为 dict
        for col in corr_df.columns:
            corr_matrix[col] = {}
            for row in corr_df.index:
                corr_matrix[col][row] = round(float(corr_df.loc[row, col]), 3)
        # 找最高相关对（排除自相关）
        syms_c = list(corr_df.columns)
        for i in range(len(syms_c)):
            for j in range(i+1, len(syms_c)):
                val = abs(corr_df.loc[syms_c[i], syms_c[j]])
                if val > top_corr_val:
                    top_corr_val  = val
                    top_corr_pair = (syms_c[i], syms_c[j], round(float(corr_df.loc[syms_c[i], syms_c[j]]), 2))

    # ── 步骤5：风险警告生成 ────────────────────────────────────
    warnings = []

    # 杠杆风险
    if leverage_ratio > 1.5:
        warnings.append(f"组合杠杆比例 {leverage_ratio:.1f}x 偏高，波动放大风险大")

    # 集中度风险（单板块>60%）
    for sec, pct in sector_pct.items():
        if pct > 60:
            warnings.append(f"板块集中度过高：{sec} 占 {pct:.0f}%，分散化不足")

    # 相关性风险（最高相关对>0.8）
    if top_corr_pair and top_corr_val > 0.8:
        a, b, v = top_corr_pair
        warnings.append(f"高相关对 {a}<->{b}({v:.2f})，同向下跌时对冲效果差")


    # VaR 超过总仓位 15%
    if var_5pct_pct > 15:
        warnings.append(f"压力测试: 大盘跌5%估计亏损 {var_5pct_pct:.1f}%，超过警戒线(15%)")

    return {
        "positions_detail":   detail,
        "total_value":        round(total_value, 0),
        "total_exposure":     round(total_exposure, 0),
        "leverage_ratio":     round(leverage_ratio, 2),
        "var_5pct_loss":      round(total_var_loss, 0),
        "var_5pct_pct":       round(var_5pct_pct, 1),
        "sector_concentration": sector_pct,
        "correlation_matrix": corr_matrix,
        "top_corr_pair":      top_corr_pair,
        "warnings":           warnings,
    }


def _simplify_sector(sector_raw, sym):
    """将 yfinance sector 字符串简化为中文简称"""
    mapping = {
        "Technology":             "科技",
        "Consumer Cyclical":      "消费/零售",
        "Communication Services": "通信/媒体",
        "Energy":                 "能源",
        "Financial Services":     "金融",
        "Healthcare":             "医疗",
        "Industrials":            "工业",
        "Basic Materials":        "原材料",
        "Real Estate":            "房地产",
        "Utilities":              "公用事业",
        "Consumer Defensive":     "必需消费",
        "ETF":                    "ETF",
        "Unknown":                "其他",
    }
    # IAU 是黄金ETF
    if sym == "IAU":
        return "黄金/商品"
    return mapping.get(sector_raw, sector_raw)


# ── 格式化输出 ────────────────────────────────────────────────

def get_portfolio_summary() -> str:
    """
    返回格式化的组合风险快照字符串，供 poll.py 插入使用。
    若数据获取失败，返回错误提示行。
    """
    try:
        r = compute_portfolio_risk()
    except Exception as e:
        return f"[portfolio_risk_agent] 计算失败: {e}"

    if r is None:
        return "[portfolio_risk_agent] 无持仓数据（positions.json 为空）"

    lines = []
    lines.append("═" * 35)
    lines.append("  组合风险快照")
    lines.append(f"  总市值 ${r['total_value']:,.0f}  "
                 f"总敞口 ${r['total_exposure']:,.0f}  "
                 f"杠杆比例 {r['leverage_ratio']:.1f}x")
    lines.append("")
    lines.append(f"  若大盘跌5%，预计亏损 "
                 f"${r['var_5pct_loss']:,.0f} "
                 f"(-{r['var_5pct_pct']:.1f}%)")
    lines.append("")

    # 板块集中度（最多显示3个）
    sec_parts = [f"{sec}{pct:.0f}%" for sec, pct in list(r["sector_concentration"].items())[:3]]
    lines.append(f"  板块集中度: {' / '.join(sec_parts)}")

    # 最高相关对
    if r["top_corr_pair"]:
        a, b, v = r["top_corr_pair"]
        lines.append(f"  最高相关对: {a}<->{b} {v:.2f}")


    # 持仓明细（简洁版）
    lines.append("")
    lines.append("  持仓敞口明细:")
    for d in sorted(r["positions_detail"], key=lambda x: -x["net_exposure"]):
        lev_tag = f"×{d['leverage']}" if d["leverage"] > 1 else ""
        lines.append(f"    {d['sym']:6s}{lev_tag}  "
                     f"${d['cur_price']:>8.2f}×{d['shares']}股  "
                     f"敞口${d['net_exposure']:,.0f}  "
                     f"beta={d.get('beta', 1.0):.2f}")

    # 警告
    if r["warnings"]:
        lines.append("")
        for w in r["warnings"]:
            lines.append(f"  ⚠️  {w}")

    lines.append("═" * 35)
    return "\n".join(lines)


# ── 主函数（独立运行） ────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-only", action="store_true",
                        help="只输出关键指标行（供 poll.py 快速解析）")
    args = parser.parse_args()

    if args.summary_only:
        try:
            r = compute_portfolio_risk()
            if r is None:
                sys.exit(0)
            # 输出总敞口行和预计亏损行（供 poll.py 正则解析）
            print(f"总敞口 ${r['total_exposure']:,.0f}  杠杆{r['leverage_ratio']:.1f}x")
            print(f"若大盘跌5%，预计亏损 ${r['var_5pct_loss']:,.0f} ({-r['var_5pct_pct']:.1f}%)")
        except Exception as e:
            print(f"[portfolio_risk_agent] 计算失败: {e}", file=sys.stderr)
        sys.exit(0)

    print("[portfolio_risk_agent] 正在计算组合风险...")
    summary = get_portfolio_summary()
    print(summary)


if __name__ == "__main__":
    main()
