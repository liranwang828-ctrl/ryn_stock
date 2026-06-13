import numpy as np
import pandas as pd

def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-9)
    return float((100 - 100 / (1 + rs)).iloc[-1])

def _macd_hist(series):
    e3 = series.ewm(span=3, adjust=False).mean()
    e8 = series.ewm(span=8, adjust=False).mean()
    macd = e3 - e8
    signal = macd.ewm(span=5, adjust=False).mean()
    return float((macd - signal).iloc[-1])

def _max_drawdown(series):
    """计算序列的最大回撤（负值）"""
    peak = series.cummax()
    dd = (series - peak) / peak
    return float(dd.min()) * 100

def _rs_vs_market(h_sym, h_spy, window=252):
    """计算相对于SPY的52周相对强度"""
    if len(h_sym) < window or len(h_spy) < window:
        window = min(len(h_sym), len(h_spy))
    if window < 20:
        return 0.0
    sym_ret = float(h_sym["Close"].iloc[-1]) / float(h_sym["Close"].iloc[-window]) - 1
    spy_ret = float(h_spy["Close"].iloc[-1]) / float(h_spy["Close"].iloc[-window]) - 1
    return round((sym_ret - spy_ret) * 100, 1)

def extract_intraday_features(h: pd.DataFrame, peer_chg: float = 0.0) -> dict:
    """日内特征：gap%、RSI-14、MACD、量比、板块联动、振幅、距52周高点"""
    if len(h) < 15:
        return {}
    prev_close = float(h["Close"].iloc[-2])
    today_open = float(h["Open"].iloc[-1])
    today_high = float(h["High"].iloc[-1])
    today_low  = float(h["Low"].iloc[-1])
    gap_pct    = (today_open - prev_close) / prev_close * 100

    vol_recent = float(h["Volume"].iloc[-3:].mean())
    vol_prev   = float(h["Volume"].iloc[-8:-3].mean()) if len(h) >= 8 else vol_recent
    vol_ratio  = vol_recent / vol_prev if vol_prev > 0 else 1.0

    hi52 = float(h["High"].max())
    pct_from_52w_high = (today_open - hi52) / hi52 * 100
    amplitude = (today_high - today_low) / prev_close * 100

    return {
        "gap_pct":           round(gap_pct, 2),
        "rsi14":             round(_rsi(h["Close"]), 1),
        "macd_hist":         round(_macd_hist(h["Close"]), 4),
        "vol_ratio":         round(vol_ratio, 2),
        "peer_chg":          round(peer_chg, 2),
        "pct_from_52w_high": round(pct_from_52w_high, 1),
        "amplitude":         round(amplitude, 2),
    }

def extract_swing_features(h: pd.DataFrame, short_pct: float = 0.0,
                            catalyst_strength: int = 1) -> dict:
    """波段特征：均线距离、空头比例、催化剂、趋势方向"""
    if len(h) < 20:
        return {}
    close = h["Close"]
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(h) >= 50 else ma20
    cur  = float(close.iloc[-1])

    trend_5d  = (cur - float(close.iloc[-6]))  / float(close.iloc[-6])  * 100 if len(h) >= 6  else 0
    trend_10d = (cur - float(close.iloc[-11])) / float(close.iloc[-11]) * 100 if len(h) >= 11 else 0

    return {
        "ma20_dist":         round((cur - ma20) / ma20 * 100, 1),
        "ma50_dist":         round((cur - ma50) / ma50 * 100, 1),
        "short_pct":         round(short_pct, 1),
        "catalyst_strength": catalyst_strength,
        "rsi14":             round(_rsi(close), 1),
        "trend_5d":          round(trend_5d, 1),
        "trend_10d":         round(trend_10d, 1),
    }

def extract_quality_features(sym: str, h_long: pd.DataFrame,
                              h_spy: pd.DataFrame = None) -> dict:
    """
    质量特征层（大师建议的扩展维度）：
    - 52周RS vs 市场
    - 最大回撤（近2年）
    - 趋势强度（是否Stage 2）
    - 2022熊市抗跌性
    - 历史波动率
    """
    if len(h_long) < 50:
        return {}

    close = h_long["Close"]
    cur   = float(close.iloc[-1])

    # 52周 RS vs SPY
    rs_52w = 0.0
    if h_spy is not None and len(h_spy) >= 252:
        rs_52w = _rs_vs_market(h_long, h_spy, window=252)

    # 最大回撤（近2年）
    window_2y = min(len(close), 504)
    mdd_2y = _max_drawdown(close.iloc[-window_2y:])

    # Stage 2 判断：MA50 向上 且 价格 > MA50
    ma50  = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    ma150 = float(close.rolling(150).mean().iloc[-1]) if len(close) >= 150 else None
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    stage2_score = 0
    if ma50  and cur > ma50:  stage2_score += 1
    if ma150 and cur > ma150: stage2_score += 1
    if ma200 and cur > ma200: stage2_score += 1
    if ma50 and ma150 and ma50 > ma150: stage2_score += 1  # 均线多头排列

    # 2022熊市表现（2022-01-01 到 2022-12-31）
    bear_2022 = 0.0
    try:
        h_2022 = h_long[h_long.index.year == 2022]
        if len(h_2022) >= 20:
            bear_2022 = (float(h_2022["Close"].iloc[-1]) - float(h_2022["Close"].iloc[0])) \
                        / float(h_2022["Close"].iloc[0]) * 100
    except Exception:
        pass

    # 历史波动率（年化）
    daily_ret = close.pct_change().dropna()
    hist_vol = float(daily_ret.std() * np.sqrt(252) * 100) if len(daily_ret) > 20 else 50.0

    # 趋势斜率（近60日线性回归斜率，正值=上升趋势）
    trend_slope = 0.0
    if len(close) >= 60:
        y = close.iloc[-60:].values
        x = np.arange(len(y))
        slope = float(np.polyfit(x, y, 1)[0])
        trend_slope = round(slope / float(close.iloc[-60]) * 100, 3)

    return {
        "rs_52w":       rs_52w,
        "mdd_2y":       round(mdd_2y, 1),
        "stage2_score": stage2_score,          # 0-4，4=完美Stage 2
        "bear_2022":    round(bear_2022, 1),
        "hist_vol":     round(hist_vol, 1),
        "trend_slope":  trend_slope,
    }

def get_macro_regime(h_spy: pd.DataFrame, date_idx: int) -> str:
    """
    Druckenmiller Layer 0: 根据日期判断宏观周期
    使用SPY走势 + 移动平均判断当时的宏观环境
    返回: 'ai_bull' / 'recovery' / 'bear' / 'normal'
    """
    if h_spy is None or len(h_spy) < 50:
        return "normal"
    try:
        # 取该日期前的SPY数据
        window = h_spy.iloc[:date_idx+1] if date_idx < len(h_spy) else h_spy
        if len(window) < 50:
            return "normal"
        close = window["Close"]
        ma50  = float(close.rolling(50).mean().iloc[-1])
        cur   = float(close.iloc[-1])
        # 过去252天（约1年）的涨幅
        ret_1y = (cur - float(close.iloc[-min(252, len(close)-1)])) / float(close.iloc[-min(252, len(close)-1)]) * 100
        # 过去60天的方向
        ret_60d = (cur - float(close.iloc[-min(60, len(close)-1)])) / float(close.iloc[-min(60, len(close)-1)]) * 100

        if cur > ma50 * 1.05 and ret_1y > 15 and ret_60d > 5:
            return "ai_bull"     # 强牛市（AI主题）
        elif cur > ma50 and ret_1y > 5:
            return "recovery"    # 温和上涨/修复
        elif cur < ma50 * 0.95 and ret_60d < -10:
            return "bear"        # 熊市
        else:
            return "normal"      # 正常区间震荡
    except Exception:
        return "normal"

def get_fundamental_features(sym: str) -> dict:
    """
    基本面特征（从 yfinance 获取）：
    - 营收增速（近3年CAGR）
    - FCF margin
    - 毛利率趋势
    """
    try:
        import yfinance as yf
        t = yf.Ticker(sym)
        info = t.info

        # 营收增速
        rev_growth = info.get("revenueGrowth") or 0
        rev_growth = float(rev_growth) * 100

        # 毛利率
        gross_margin = info.get("grossMargins") or 0
        gross_margin = float(gross_margin) * 100

        # FCF (operating cash flow - capex)
        ocf = info.get("operatingCashflow") or 0
        capex = info.get("capitalExpenditures") or 0
        rev = info.get("totalRevenue") or 1
        fcf_margin = (float(ocf) - abs(float(capex))) / float(rev) * 100 if rev else 0

        # P/E 和 P/S 估值
        pe  = info.get("trailingPE") or 0
        ps  = info.get("priceToSalesTrailing12Months") or 0

        return {
            "rev_growth":   round(rev_growth, 1),
            "gross_margin": round(gross_margin, 1),
            "fcf_margin":   round(fcf_margin, 1),
            "pe_ratio":     round(float(pe), 1) if pe else 0,
            "ps_ratio":     round(float(ps), 1) if ps else 0,
        }
    except Exception:
        return {
            "rev_growth": 0, "gross_margin": 0,
            "fcf_margin": 0, "pe_ratio": 0, "ps_ratio": 0,
        }
