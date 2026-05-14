#!/usr/bin/env python3
"""
stock_report.py — 机构级深度研究报告生成器（12章节版）
用法:
    python3.12 agents/stock_report.py AMD MRVL     # 指定标的
    python3.12 agents/stock_report.py               # 默认读 positions.json
"""

import os
import sys
import json
import math
import datetime
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    sys.exit("缺少 requests，请先 pip install requests")

try:
    import yfinance as yf
except ImportError:
    sys.exit("缺少 yfinance，请先 pip install yfinance")

try:
    import pandas as pd
except ImportError:
    sys.exit("缺少 pandas，请先 pip install pandas")

# ── 路径配置 ──────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE, "config")
REPORTS_DIR = os.path.join(BASE, "reports")
POSITIONS_FILE = os.path.join(CONFIG_DIR, "positions.json")
POLL_CONFIG_FILE = os.path.join(CONFIG_DIR, "poll_config.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
COMPANY_PROFILES_FILE = os.path.join(KNOWLEDGE_DIR, "company_profiles.json")

os.makedirs(REPORTS_DIR, exist_ok=True)

TODAY = datetime.date.today().isoformat()

# ── 竞争对手映射表 ──────────────────────────────────────────────────────────────
COMPETITORS = {
    "AMD":  ["NVDA", "INTC", "QCOM"],
    "NVDA": ["AMD", "INTC", "AVGO"],
    "MRVL": ["AVGO", "QCOM", "INTC"],
    "AAOI": ["LITE", "FN", "CIEN"],
    "INTC": ["AMD", "NVDA", "ARM"],
    "QCOM": ["AMD", "MRVL", "MTK"],
    "RKLB": ["SPCE", "LMT", "BA"],
    "IREN": ["MARA", "CLSK", "CORZ"],
    "MSFT": ["GOOGL", "AMZN", "ORCL"],
    "TSLA": ["GM", "F", "RIVN"],
    "META": ["GOOGL", "SNAP", "PINS"],
    "AAPL": ["MSFT", "GOOGL", "SAMSUNG"],
    "GOOGL": ["MSFT", "META", "AMZN"],
    "AMZN": ["MSFT", "GOOGL", "BABA"],
    "AVGO": ["NVDA", "MRVL", "QCOM"],
    "LITE": ["AAOI", "FN", "CIEN"],
    "FN":   ["LITE", "AAOI", "CIEN"],
    "MU":   ["WDC", "STX", "SNDK"],
    "SNDK": ["MU", "WDC", "STX"],
    "OKLO": ["BWXT", "NNE", "SMR"],
    "HOOD": ["IBKR", "SCHW", "SOFI"],
    "BBAI": ["PLTR", "AI", "SOUN"],
    "FLNC": ["ENPH", "SEDG", "RUN"],
    "OXY":  ["CVX", "XOM", "COP"],
    "MMM":  ["HON", "GE", "EMR"],
    "TTD":  ["PUBM", "APP", "GOOGL"],
    "RGTI": ["IONQ", "QBTS", "IBM"],
    "MXL":  ["MRVL", "AVGO", "QCOM"],
    "IAU":  ["GLD", "PHYS", "GLDM"],
}

# ── 行业上下游知识库 ──────────────────────────────────────────────────────────
SUPPLY_CHAIN = {
    "Semiconductors": {
        "upstream": "台积电(TSMC)、ASM、ASML、科磊(KLAC)",
        "downstream": "苹果、微软、谷歌、数据中心、汽车OEM",
        "threats": "中国芯片崛起、地缘政治出口管制、先进制程垄断"
    },
    "Technology": {
        "upstream": "云基础设施(AWS/Azure)、芯片供应商",
        "downstream": "企业客户、消费者、政府",
        "threats": "AI替代传统软件、监管反垄断、开源竞争"
    },
    "Communication Services": {
        "upstream": "云计算、内容创作工具",
        "downstream": "广告主、消费者",
        "threats": "隐私监管、AI内容生成冲击、用户注意力争夺"
    },
    "Consumer Cyclical": {
        "upstream": "制造商、物流供应链",
        "downstream": "消费者",
        "threats": "宏观消费降级、价格竞争"
    },
    "Energy": {
        "upstream": "钻探设备、管道基础设施",
        "downstream": "炼油厂、电力公司、工业用户",
        "threats": "能源转型、ESG压力、OPEC政策"
    },
}


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def safe(fn, default="N/A"):
    try:
        result = fn()
        if result is None or (isinstance(result, float) and math.isnan(result)):
            return default
        return result
    except Exception:
        return default


def fmt_num(v, unit="", decimals=2, default="N/A"):
    if v == "N/A" or v is None:
        return default
    try:
        v = float(v)
        if math.isnan(v):
            return default
        if abs(v) >= 1e12:
            return f"{v/1e12:.{decimals}f}T{unit}"
        if abs(v) >= 1e9:
            return f"{v/1e9:.{decimals}f}B{unit}"
        if abs(v) >= 1e6:
            return f"{v/1e6:.{decimals}f}M{unit}"
        if abs(v) >= 1e3:
            return f"{v/1e3:.{decimals}f}K{unit}"
        return f"{v:.{decimals}f}{unit}"
    except Exception:
        return default


def pct(a, b, default="N/A"):
    try:
        a, b = float(a), float(b)
        if b == 0:
            return default
        return f"{(a - b) / abs(b) * 100:.2f}%"
    except Exception:
        return default


def pct_float(a, b):
    try:
        a, b = float(a), float(b)
        if b == 0:
            return None
        return (a - b) / abs(b) * 100
    except Exception:
        return None


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_sector_map():
    cfg = load_json(POLL_CONFIG_FILE)
    return cfg.get("sector_map", {})


def load_positions():
    cfg = load_json(POSITIONS_FILE)
    return cfg.get("positions", {})


def price_change(hist, days):
    try:
        if hist is None or len(hist) < 2:
            return None
        end_price = float(hist["Close"].iloc[-1])
        idx = max(0, len(hist) - days)
        start_price = float(hist["Close"].iloc[idx])
        return pct_float(end_price, start_price)
    except Exception:
        return None


# ── 公司知识库读取 ─────────────────────────────────────────────────────────────

def load_company_profile(sym):
    """读取 company_profiles.json 中的公司定性知识，不存在则返回 {}"""
    try:
        profiles = load_json(COMPANY_PROFILES_FILE)
        return profiles.get(sym.upper(), {})
    except Exception:
        return {}


# ── 价格事件检测 ───────────────────────────────────────────────────────────────

def detect_price_events(h10y, sym, company_name, max_events=10):
    """
    找出10年内所有单周涨跌 >10% 的节点，并用 Google RSS 搜索对应新闻。
    返回：[{date, price_change_pct, headline, source}]，最多保留 max_events 个。
    """
    events = []
    try:
        if h10y is None or len(h10y) < 5:
            return events
        close = h10y["Close"]
        # 重采样为周线
        weekly = close.resample("W").last().dropna()
        weekly_chg = weekly.pct_change().dropna()

        # 找出涨跌幅 >10% 的周
        big_moves = weekly_chg[weekly_chg.abs() > 0.10].sort_values(key=abs, ascending=False)

        for date_idx, chg in big_moves.items():
            try:
                date_str = str(date_idx)[:10]
                # 构造搜索时间范围
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                after_dt = dt - datetime.timedelta(days=7)
                before_dt = dt + datetime.timedelta(days=3)
                after_str = after_dt.strftime("%Y-%m-%d")
                before_str = before_dt.strftime("%Y-%m-%d")

                query = f"{sym} {company_name} after:{after_str} before:{before_str}"
                url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"

                headline = "（未找到对应新闻）"
                source = "N/A"
                try:
                    resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.content)
                        first_item = next(root.iter("item"), None)
                        if first_item is not None:
                            title_raw = (first_item.findtext("title") or "").strip()
                            if " - " in title_raw:
                                parts = title_raw.rsplit(" - ", 1)
                                headline = parts[0].strip()
                                source = parts[1].strip()
                            else:
                                headline = title_raw
                except Exception:
                    pass

                events.append({
                    "date": date_str,
                    "price_change_pct": round(float(chg) * 100, 2),
                    "headline": headline,
                    "source": source,
                })
                if len(events) >= max_events:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return events


# ── 新闻抓取 ──────────────────────────────────────────────────────────────────

def fetch_news(sym, days=30, max_items=15):
    url = f"https://news.google.com/rss/search?q={sym}+stock&hl=en-US&gl=US&ceid=US:en"
    items = []
    try:
        resp = requests.get(url, timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            pub_str = (item.findtext("pubDate") or "").strip()
            try:
                pub_dt = datetime.datetime.strptime(
                    pub_str, "%a, %d %b %Y %H:%M:%S %Z"
                ).replace(tzinfo=datetime.timezone.utc)
            except Exception:
                pub_dt = None
            if pub_dt and pub_dt < cutoff:
                continue
            pub_date = pub_dt.strftime("%Y-%m-%d") if pub_dt else "未知"
            source = "未知"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                source = parts[1].strip()
            items.append({"date": pub_date, "title": title, "source": source})
            if len(items) >= max_items:
                break
    except Exception:
        pass
    return items


def classify_news(title):
    title_lower = title.lower()
    bullish = ["beat", "record", "surge", "rally", "strong", "upgrade", "buy",
               "outperform", "growth", "profit", "win", "expand", "boost"]
    bearish = ["miss", "cut", "downgrade", "sell", "weak", "loss", "decline",
               "drop", "concern", "risk", "warn", "below", "layoff", "slow"]
    b = sum(1 for w in bullish if w in title_lower)
    s = sum(1 for w in bearish if w in title_lower)
    if b > s:
        return "利多"
    elif s > b:
        return "利空"
    return "中性"


# ── 技术指标 ──────────────────────────────────────────────────────────────────

def compute_rsi(close, period=14):
    try:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    except Exception:
        return None


# ── 章节一：公司业务理解 ────────────────────────────────────────────────────────

def section_business(sym, info, lines):
    lines.append("## 一、公司业务理解\n\n")
    try:
        name = info.get("longName") or info.get("shortName") or sym
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        country = info.get("country", "N/A")
        city = info.get("city", "")
        state = info.get("state", "")
        hq = f"{city}, {state}, {country}".strip(", ").strip()
        employees = info.get("fullTimeEmployees")
        emp_str = f"{employees:,}" if employees else "N/A"

        ipo_year = "N/A"
        if info.get("firstTradeDateEpochUtc"):
            try:
                ipo_year = datetime.datetime.fromtimestamp(
                    info["firstTradeDateEpochUtc"]
                ).strftime("%Y")
            except Exception:
                pass

        # 业务简述
        summary = info.get("longBusinessSummary", "")
        if summary:
            # 取前2句作为核心定位
            sentences = summary.replace("  ", " ").split(". ")
            core = ". ".join(sentences[:2]) + "." if len(sentences) >= 2 else summary[:300]
        else:
            core = "暂无业务简述数据"

        # 推断业务模式
        biz_model = "N/A"
        if industry:
            ind_lower = industry.lower()
            if any(x in ind_lower for x in ["software", "saas", "cloud"]):
                biz_model = "SaaS/软件订阅（B2B为主）"
            elif any(x in ind_lower for x in ["semiconductor", "chip", "electronic"]):
                biz_model = "半导体硬件销售（B2B，OEM/ODM为主）"
            elif any(x in ind_lower for x in ["internet", "media", "social"]):
                biz_model = "广告+订阅（B2C为主）"
            elif any(x in ind_lower for x in ["oil", "gas", "energy"]):
                biz_model = "资源开采+销售（B2B）"
            elif any(x in ind_lower for x in ["retail", "consumer"]):
                biz_model = "零售/消费品（B2C）"
            elif any(x in ind_lower for x in ["financial", "bank"]):
                biz_model = "金融服务（B2C/B2B混合）"
            elif any(x in ind_lower for x in ["aero", "defense"]):
                biz_model = "航天/国防（B2G为主）"
            else:
                biz_model = f"{industry}行业"

        lines.append(f"**公司名称**：{name}（{sym}）\n\n")
        lines.append(f"**一句话定位**：{core}\n\n")
        lines.append(f"**主营业务模式**：{biz_model}\n\n")

        # 基本信息表
        mktcap = fmt_num(info.get("marketCap"), " USD")
        lines.append("| 项目 | 信息 |\n|---|---|\n")
        lines.append(f"| 行业大类 | {sector} |\n")
        lines.append(f"| 细分行业 | {industry} |\n")
        lines.append(f"| 总部 | {hq} |\n")
        lines.append(f"| 员工数 | {emp_str} |\n")
        lines.append(f"| 上市年份 | {ipo_year} |\n")
        lines.append(f"| 市值 | {mktcap} |\n\n")

        # 上下游信息
        sc = SUPPLY_CHAIN.get(sector, {})
        if sc:
            lines.append(f"**上游依赖**：{sc.get('upstream', 'N/A')}\n\n")
            lines.append(f"**下游客户**：{sc.get('downstream', 'N/A')}\n\n")
    except Exception as e:
        lines.append(f"> 业务理解数据获取失败：{e}\n\n")


# ── 章节：业务线详解 ───────────────────────────────────────────────────────────

def section_segments(sym, profile, ticker, lines):
    """利用 company_profiles.json 的 segments 字段生成业务线详解章节"""
    segments = profile.get("segments", [])
    if not segments:
        return  # 无数据则跳过此章节

    lines.append("## 二、业务线详解\n\n")
    try:
        # 尝试从 yfinance quarterly_financials 推导趋势（仅参考）
        rev_trend = {}
        try:
            qfin = ticker.quarterly_financials
            if qfin is not None and not qfin.empty:
                # 取近4季度 Total Revenue 趋势
                if "Total Revenue" in qfin.index:
                    rev_series = qfin.loc["Total Revenue"].iloc[:4]
                    if len(rev_series) >= 2:
                        latest = float(rev_series.iloc[0])
                        prev = float(rev_series.iloc[1])
                        if prev and prev != 0:
                            rev_qoq = (latest - prev) / abs(prev) * 100
                            rev_trend["overall_qoq"] = rev_qoq
        except Exception:
            pass

        lines.append("| 业务线 | 描述 | 当前趋势 |\n|---|---|---|\n")
        for seg in segments:
            name = seg.get("name", "未知")
            desc = seg.get("desc", "N/A")
            # 趋势描述：从 desc 中提取关键词或用整体趋势
            trend = "持续观察"
            desc_lower = desc.lower()
            if any(w in desc_lower for w in ["增长", "爆发", "增速", "核心增长", "快速", "高增速", "高速"]):
                trend = "增长中"
            elif any(w in desc_lower for w in ["承压", "低迷", "萎缩", "亏损", "下滑", "周期末"]):
                trend = "承压"
            elif any(w in desc_lower for w in ["稳定", "平稳", "稳健"]):
                trend = "稳定"
            elif any(w in desc_lower for w in ["转型", "赌注", "期权", "未来"]):
                trend = "长期布局"
            lines.append(f"| {name} | {desc} | {trend} |\n")
        lines.append("\n")

        # 附加整体叙事
        narrative = profile.get("narrative", "")
        if narrative:
            lines.append(f"**公司核心叙事**：{narrative}\n\n")

        # 里程碑时间线
        milestones = profile.get("milestones", [])
        if milestones:
            lines.append("**关键里程碑**：\n\n")
            for m in milestones[-5:]:  # 只显示最近5条
                lines.append(f"- **{m.get('year', '?')}年**：{m.get('event', '')}\n")
            lines.append("\n")

    except Exception as e:
        lines.append(f"> 业务线详解生成失败：{e}\n\n")


# ── 章节二（原）：竞争格局 ──────────────────────────────────────────────────────

def section_competition(sym, info, cur_price, lines):
    lines.append("## 二、竞争格局\n\n")
    try:
        # 竞争对手股价对比
        competitors = COMPETITORS.get(sym, [])
        if competitors:
            lines.append("### 2.1 直接竞争对手\n\n")
            lines.append("| 标的 | 当前价 | 市值 | PE | PS | 毛利率 |\n|---|---|---|---|---|---|\n")

            # 当前标的自己
            pe_self = info.get("trailingPE")
            ps_self = info.get("priceToSalesTrailing12Months")
            gm_self = info.get("grossMargins")
            lines.append(
                f"| **{sym}（本股）** | ${cur_price:.2f} if cur_price else N/A"
                f" | {fmt_num(info.get('marketCap'), ' USD')}"
                f" | {f'{pe_self:.1f}x' if pe_self else 'N/A'}"
                f" | {f'{ps_self:.1f}x' if ps_self else 'N/A'}"
                f" | {f'{gm_self*100:.1f}%' if gm_self else 'N/A'} |\n"
            )

            for comp in competitors:
                try:
                    ct = yf.Ticker(comp)
                    ci = ct.info or {}
                    cp = ci.get("currentPrice") or ci.get("regularMarketPrice") or 0
                    cm = ci.get("marketCap")
                    cpe = ci.get("trailingPE")
                    cps = ci.get("priceToSalesTrailing12Months")
                    cgm = ci.get("grossMargins")
                    lines.append(
                        f"| {comp} | ${cp:.2f}"
                        f" | {fmt_num(cm, ' USD')}"
                        f" | {f'{cpe:.1f}x' if cpe else 'N/A'}"
                        f" | {f'{cps:.1f}x' if cps else 'N/A'}"
                        f" | {f'{cgm*100:.1f}%' if cgm else 'N/A'} |\n"
                    )
                except Exception:
                    lines.append(f"| {comp} | N/A | N/A | N/A | N/A | N/A |\n")
            lines.append("\n")

        # 护城河评估
        lines.append("### 2.2 护城河评估\n\n")
        moat_factors = []

        gm = info.get("grossMargins")
        if gm:
            gm_pct = float(gm) * 100
            if gm_pct > 60:
                moat_factors.append(f"强定价权：毛利率 {gm_pct:.1f}%（>60%），具备显著定价能力")
            elif gm_pct > 40:
                moat_factors.append(f"中等定价权：毛利率 {gm_pct:.1f}%（40-60%），具有一定溢价能力")
            else:
                moat_factors.append(f"弱定价权：毛利率 {gm_pct:.1f}%（<40%），竞争激烈")

        fcf = info.get("freeCashflow")
        rev = info.get("totalRevenue")
        if fcf and rev:
            fcf_margin = float(fcf) / float(rev) * 100
            if fcf_margin > 20:
                moat_factors.append(f"强运营护城河：FCF利润率 {fcf_margin:.1f}%（>20%），现金生成能力强")
            elif fcf_margin > 10:
                moat_factors.append(f"中等运营护城河：FCF利润率 {fcf_margin:.1f}%（10-20%）")
            elif fcf_margin < 0:
                moat_factors.append(f"运营护城河弱：FCF为负（{fcf_margin:.1f}%），仍在烧钱阶段")

        rnd = info.get("researchAndDevelopment") or info.get("researchDevelopment")
        if rnd and rev:
            rnd_pct = float(rnd) / float(rev) * 100
            if rnd_pct > 15:
                moat_factors.append(f"技术护城河：R&D/营收 {rnd_pct:.1f}%（>15%），技术壁垒高")
            elif rnd_pct > 8:
                moat_factors.append(f"中等技术护城河：R&D/营收 {rnd_pct:.1f}%（8-15%）")

        rev_g = info.get("revenueGrowth")
        if rev_g:
            rg_pct = float(rev_g) * 100
            if rg_pct > 30:
                moat_factors.append(f"高成长护城河：营收增速 {rg_pct:.1f}%（>30%），市场份额持续扩张")

        if moat_factors:
            for f_item in moat_factors:
                lines.append(f"- {f_item}\n")
        else:
            lines.append("- 护城河评估数据不足\n")
        lines.append("\n")

        # 竞争威胁
        sector = info.get("sector", "")
        sc = SUPPLY_CHAIN.get(sector, {})
        threats = sc.get("threats", "")
        if threats:
            lines.append(f"**主要竞争威胁**：{threats}\n\n")

    except Exception as e:
        lines.append(f"> 竞争格局数据获取失败：{e}\n\n")


# ── 章节三：近8季度财报表现 ──────────────────────────────────────────────────────

def section_earnings(sym, ticker, info, lines):
    lines.append("## 三、近8季度财报表现\n\n")
    try:
        # 财报历史
        eh = safe(lambda: ticker.earnings_history, None)
        qf = safe(lambda: ticker.quarterly_financials, None)

        beat_count = 0
        total_count = 0

        if eh is not None and len(eh) > 0:
            lines.append("| 季度 | EPS实际 | EPS预期 | EPS Beat% | 营收预期 | 说明 |\n")
            lines.append("|---|---|---|---|---|---|\n")

            # earnings_history 包含 epsActual, epsEstimate
            rows_shown = 0
            for idx, row in eh.head(8).iterrows():
                try:
                    quarter = str(idx)[:10] if idx else "N/A"
                    eps_act = row.get("epsActual")
                    eps_est = row.get("epsEstimate")
                    eps_diff = row.get("epsDifference")
                    eps_surp = row.get("surprisePercent")

                    eps_act_str = f"${eps_act:.3f}" if eps_act is not None else "N/A"
                    eps_est_str = f"${eps_est:.3f}" if eps_est is not None else "N/A"

                    if eps_surp is not None:
                        beat_pct = f"{eps_surp*100:.1f}%"
                        if float(eps_surp) > 0:
                            beat_count += 1
                    else:
                        beat_pct = "N/A"
                    total_count += 1

                    lines.append(f"| {quarter} | {eps_act_str} | {eps_est_str} | {beat_pct} | N/A | — |\n")
                    rows_shown += 1
                except Exception:
                    continue
            lines.append("\n")

            if total_count > 0:
                lines.append(f"**连续超EPS预期次数**：{beat_count}/{total_count} 季\n\n")
        else:
            lines.append("> EPS历史数据暂不可用\n\n")

        # 季度营收趋势（来自 quarterly_financials）
        if qf is not None and len(qf.columns) > 0:
            lines.append("### 3.1 季度营收趋势\n\n")
            lines.append("| 季度 | 营收 | 毛利 | 净利润 |\n|---|---|---|---|\n")

            cols = sorted(qf.columns, reverse=True)[:8]
            rev_vals = []
            for col in cols:
                try:
                    q_label = str(col)[:10]
                    rev_val = qf.loc["Total Revenue", col] if "Total Revenue" in qf.index else None
                    gross_val = qf.loc["Gross Profit", col] if "Gross Profit" in qf.index else None
                    net_val = qf.loc["Net Income", col] if "Net Income" in qf.index else None

                    rev_str = fmt_num(rev_val, " USD") if rev_val and not (isinstance(rev_val, float) and math.isnan(rev_val)) else "N/A"
                    gross_str = fmt_num(gross_val, " USD") if gross_val and not (isinstance(gross_val, float) and math.isnan(gross_val)) else "N/A"
                    net_str = fmt_num(net_val, " USD") if net_val and not (isinstance(net_val, float) and math.isnan(net_val)) else "N/A"

                    if rev_val and not (isinstance(rev_val, float) and math.isnan(rev_val)):
                        rev_vals.append(float(rev_val))

                    lines.append(f"| {q_label} | {rev_str} | {gross_str} | {net_str} |\n")
                except Exception:
                    continue
            lines.append("\n")

            # 收入增速趋势
            if len(rev_vals) >= 2:
                growth = (rev_vals[0] - rev_vals[-1]) / abs(rev_vals[-1]) * 100
                trend_word = "上升" if growth > 0 else "下降"
                lines.append(f"**营收趋势**：近8季整体{trend_word}，累计变化 {growth:+.1f}%\n\n")

    except Exception as e:
        lines.append(f"> 财报数据获取失败：{e}\n\n")


# ── 章节四：盈利能力深析 ────────────────────────────────────────────────────────

def section_profitability(sym, ticker, info, lines):
    lines.append("## 四、盈利能力深析\n\n")
    try:
        qf = safe(lambda: ticker.quarterly_financials, None)

        if qf is not None and len(qf.columns) > 0:
            lines.append("### 4.1 季度利润率趋势（近8季）\n\n")
            lines.append("| 季度 | 毛利率 | 营业利润率 | 净利润率 |\n|---|---|---|---|\n")

            cols = sorted(qf.columns, reverse=True)[:8]
            gm_vals = []
            for col in cols:
                try:
                    q_label = str(col)[:10]
                    rev = qf.loc["Total Revenue", col] if "Total Revenue" in qf.index else None
                    gross = qf.loc["Gross Profit", col] if "Gross Profit" in qf.index else None
                    op = qf.loc["Operating Income", col] if "Operating Income" in qf.index else None
                    net = qf.loc["Net Income", col] if "Net Income" in qf.index else None

                    def margin_str(num, denom):
                        try:
                            if num is None or denom is None:
                                return "N/A"
                            n, d = float(num), float(denom)
                            if math.isnan(n) or math.isnan(d) or d == 0:
                                return "N/A"
                            return f"{n/d*100:.1f}%"
                        except Exception:
                            return "N/A"

                    gm_str = margin_str(gross, rev)
                    op_str = margin_str(op, rev)
                    net_str = margin_str(net, rev)

                    if gm_str != "N/A":
                        gm_vals.append(float(gm_str.rstrip('%')))

                    lines.append(f"| {q_label} | {gm_str} | {op_str} | {net_str} |\n")
                except Exception:
                    continue
            lines.append("\n")

            # 毛利率趋势判断
            if len(gm_vals) >= 2:
                if gm_vals[0] > gm_vals[-1]:
                    lines.append(f"**毛利率趋势**：扩张（最新 {gm_vals[0]:.1f}% vs 最早 {gm_vals[-1]:.1f}%）\n\n")
                elif gm_vals[0] < gm_vals[-1]:
                    lines.append(f"**毛利率趋势**：收缩（最新 {gm_vals[0]:.1f}% vs 最早 {gm_vals[-1]:.1f}%）\n\n")
                else:
                    lines.append(f"**毛利率趋势**：稳定在 {gm_vals[0]:.1f}%\n\n")

        # FCF vs 净利润质量分析
        lines.append("### 4.2 FCF 质量分析\n\n")
        fcf = info.get("freeCashflow")
        net_income = info.get("netIncomeToCommon")
        op_cf = info.get("operatingCashflow")

        lines.append("| 指标 | 数值 |\n|---|---|\n")
        lines.append(f"| 自由现金流(FCF) TTM | {fmt_num(fcf, ' USD')} |\n")
        lines.append(f"| 净利润 TTM | {fmt_num(net_income, ' USD')} |\n")
        lines.append(f"| 经营现金流 TTM | {fmt_num(op_cf, ' USD')} |\n")

        if fcf and net_income:
            try:
                fcf_f = float(fcf)
                ni_f = float(net_income)
                if ni_f != 0:
                    quality = fcf_f / ni_f
                    if quality > 1.2:
                        quality_comment = f"高质量（FCF/净利润={quality:.2f}，FCF远超会计利润）"
                    elif quality > 0.8:
                        quality_comment = f"正常（FCF/净利润={quality:.2f}）"
                    elif quality > 0:
                        quality_comment = f"一般（FCF/净利润={quality:.2f}，现金转化不足）"
                    else:
                        quality_comment = f"警惕（FCF为负，现金流质量差）"
                    lines.append(f"| FCF/净利润比值 | {quality_comment} |\n")
            except Exception:
                pass
        lines.append("\n")

        # 股本变化
        lines.append("### 4.3 股本结构\n\n")
        shares_out = info.get("sharesOutstanding")
        shares_float = info.get("floatShares")
        buyback = info.get("buybackYield") or info.get("repurchaseOfStock")
        lines.append("| 指标 | 数值 |\n|---|---|\n")
        lines.append(f"| 流通股数 | {fmt_num(shares_out)} |\n")
        lines.append(f"| 自由流通股 | {fmt_num(shares_float)} |\n")
        if buyback:
            lines.append(f"| 股票回购 | {fmt_num(buyback, ' USD')} |\n")
        lines.append("\n")

        # 资本分配
        div_yield = info.get("dividendYield")
        div_rate = info.get("dividendRate")
        if div_yield or div_rate:
            div_y_str = f"{div_yield*100:.2f}%" if div_yield else "N/A"
            lines.append(f"**股息收益率**：{div_y_str}，年化股息：{fmt_num(div_rate, ' USD/股')}\n\n")
        else:
            lines.append("**股息**：无分红（成长型再投资策略）\n\n")

    except Exception as e:
        lines.append(f"> 盈利能力数据获取失败：{e}\n\n")


# ── 章节五：估值分析 ────────────────────────────────────────────────────────────

def section_valuation(sym, info, cur_price, competitors, lines):
    lines.append("## 五、估值分析\n\n")
    try:
        pe = info.get("trailingPE")
        fpe = info.get("forwardPE")
        ps = info.get("priceToSalesTrailing12Months")
        pb = info.get("priceToBook")
        ev_ebitda = info.get("enterpriseToEbitda")
        ev_rev = info.get("enterpriseToRevenue")
        rev_g = info.get("revenueGrowth")
        eps_g = info.get("earningsGrowth")

        lines.append("### 5.1 当前估值倍数\n\n")
        lines.append("| 估值指标 | 数值 | 解读 |\n|---|---|---|\n")

        def pe_comment(pe_val):
            if pe_val is None:
                return "N/A"
            v = float(pe_val)
            if v < 0:
                return "亏损中"
            elif v < 15:
                return "低估"
            elif v < 25:
                return "合理"
            elif v < 50:
                return "偏贵"
            elif v < 100:
                return "成长溢价"
            else:
                return "极高，依赖高增速"

        lines.append(f"| PE (TTM) | {f'{pe:.1f}x' if pe else 'N/A'} | {pe_comment(pe)} |\n")
        lines.append(f"| PE (Forward) | {f'{fpe:.1f}x' if fpe else 'N/A'} | {pe_comment(fpe)} |\n")
        lines.append(f"| PS | {f'{ps:.1f}x' if ps else 'N/A'} | {'高溢价' if ps and float(ps) > 20 else '合理' if ps else 'N/A'} |\n")
        lines.append(f"| PB | {f'{pb:.1f}x' if pb else 'N/A'} | N/A |\n")
        lines.append(f"| EV/EBITDA | {f'{ev_ebitda:.1f}x' if ev_ebitda else 'N/A'} | {'偏贵' if ev_ebitda and float(ev_ebitda) > 40 else '合理' if ev_ebitda else 'N/A'} |\n")
        lines.append(f"| EV/Revenue | {f'{ev_rev:.1f}x' if ev_rev else 'N/A'} | N/A |\n")
        lines.append("\n")

        # PEG
        if pe and rev_g:
            try:
                peg = float(pe) / (float(rev_g) * 100)
                peg_comment = "低估(<1)" if peg < 1 else "合理(1-2)" if peg < 2 else "偏贵(>2)"
                lines.append(f"**PEG**：{peg:.2f}（= PE {pe:.1f} / 营收增速 {rev_g*100:.1f}%）→ {peg_comment}\n\n")
            except Exception:
                pass
        elif pe and eps_g:
            try:
                peg = float(pe) / (float(eps_g) * 100)
                peg_comment = "低估(<1)" if peg < 1 else "合理(1-2)" if peg < 2 else "偏贵(>2)"
                lines.append(f"**PEG**：{peg:.2f}（= PE {pe:.1f} / EPS增速 {eps_g*100:.1f}%）→ {peg_comment}\n\n")
            except Exception:
                pass

        # 隐含增速
        if fpe:
            try:
                fpe_v = float(fpe)
                # 假设合理PE=25，隐含增速 = fpe/25 - 1
                implied_g = (fpe_v / 25 - 1) * 100
                lines.append(f"**隐含增速**（以PE=25为基准）：当前估值需要约 {implied_g:.1f}% 年化EPS增速才合理\n\n")
            except Exception:
                pass

        # 分析师目标价
        target_mean = info.get("targetMeanPrice")
        target_low = info.get("targetLowPrice")
        target_high = info.get("targetHighPrice")
        if target_mean and cur_price:
            upside = pct_float(target_mean, cur_price)
            lines.append("### 5.2 分析师目标价\n\n")
            lines.append("| 目标价 | 最低 | 平均 | 最高 | 上涨空间 |\n|---|---|---|---|---|\n")
            low_s = f"${target_low:.2f}" if target_low else "N/A"
            mean_s = f"${target_mean:.2f}" if target_mean else "N/A"
            high_s = f"${target_high:.2f}" if target_high else "N/A"
            up_s = f"{upside:+.1f}%" if upside else "N/A"
            lines.append(f"| 目标价 | {low_s} | {mean_s} | {high_s} | {up_s} |\n\n")

    except Exception as e:
        lines.append(f"> 估值数据获取失败：{e}\n\n")


# ── 章节六：长期结构分析（10年日K）─────────────────────────────────────────────

def section_long_term(sym, ticker, cur_price, lines):
    lines.append("## 六、长期结构分析（10年日K）\n\n")
    try:
        h10y = safe(lambda: ticker.history(period="10y"), None)
        if h10y is None or len(h10y) < 200:
            lines.append("> 10年历史数据不足，跳过长期结构分析\n\n")
            return

        close = h10y["Close"]
        high_col = h10y["High"]
        low_col = h10y["Low"]
        vol_col = h10y["Volume"]

        # ── 6.1 Weinstein Stage ──────────────────────────────────────────────
        lines.append("### 6.1 Weinstein Stage 判断\n\n")
        try:
            if len(close) >= 200:
                ma200 = close.rolling(200).mean()
                ma200_last = float(ma200.iloc[-1])
                ma200_20d_ago = float(ma200.iloc[-20]) if len(ma200) >= 20 else ma200_last
                ma200_slope = ma200_last - ma200_20d_ago
                price_vs_ma200 = float(close.iloc[-1]) / ma200_last - 1

                if ma200_slope > 0 and cur_price > ma200_last:
                    stage = "Stage 2（上升趋势）"
                    stage_detail = f"MA200向上（20日斜率 {ma200_slope:+.2f}），价格在MA200上方 {price_vs_ma200*100:+.1f}%"
                elif ma200_slope > 0 and cur_price < ma200_last:
                    stage = "Stage 1（横盘积累）或 Stage 3（顶部分配）"
                    stage_detail = f"MA200向上但价格在MA200下方 {price_vs_ma200*100:+.1f}%，需进一步判断"
                elif ma200_slope < 0 and cur_price < ma200_last:
                    stage = "Stage 4（下降趋势）"
                    stage_detail = f"MA200向下（20日斜率 {ma200_slope:+.2f}），价格在MA200下方 {price_vs_ma200*100:+.1f}%"
                else:
                    stage = "Stage 3（顶部分配）"
                    stage_detail = f"MA200向下但价格仍在MA200上方 {price_vs_ma200*100:+.1f}%，警惕顶部"

                lines.append(f"**当前 Stage**：{stage}\n\n")
                lines.append(f"**判断依据**：{stage_detail}\n\n")
                lines.append(f"**MA200当前值**：${ma200_last:.2f}\n\n")
            else:
                lines.append("> 数据不足200日，无法计算 MA200\n\n")
        except Exception as e:
            lines.append(f"> Weinstein Stage 计算失败：{e}\n\n")

        # ── 6.2 历史价格全景 ───────────────────────────────────────────────
        lines.append("### 6.2 历史价格全景\n\n")
        try:
            all_time_high = float(high_col.max())
            all_time_low = float(low_col.min())
            ath_idx = high_col.idxmax()
            atl_idx = low_col.idxmin()
            ath_date = str(ath_idx)[:10] if ath_idx is not None else "N/A"
            atl_date = str(atl_idx)[:10] if atl_idx is not None else "N/A"

            from_low = pct_float(cur_price, all_time_low)
            from_high = pct_float(cur_price, all_time_high)

            # 价格百分位（当前价在10年区间中的位置）
            price_percentile = (cur_price - all_time_low) / (all_time_high - all_time_low) * 100 if (all_time_high - all_time_low) > 0 else 50

            lines.append("| 指标 | 数值 |\n|---|---|\n")
            lines.append(f"| 历史最高价(10年) | ${all_time_high:.2f}（{ath_date}） |\n")
            lines.append(f"| 历史最低价(10年) | ${all_time_low:.2f}（{atl_date}） |\n")
            lines.append(f"| 当前价 | ${cur_price:.2f} |\n")
            lines.append(f"| 距历史最高 | {from_high:+.1f}% |\n" if from_high else "| 距历史最高 | N/A |\n")
            lines.append(f"| 从历史最低涨幅 | {from_low:+.1f}% |\n" if from_low else "| 从历史最低涨幅 | N/A |\n")
            lines.append(f"| 当前价历史百分位 | {price_percentile:.1f}%（100%=历史最高，0%=历史最低） |\n")
            lines.append("\n")

            if price_percentile > 85:
                lines.append("**位置解读**：当前处于历史高位区（>85%分位），上方套牢盘少但估值风险高。\n\n")
            elif price_percentile > 50:
                lines.append("**位置解读**：当前处于历史中高位区（50-85%分位），有历史套牢盘压力但技术结构尚可。\n\n")
            elif price_percentile > 20:
                lines.append("**位置解读**：当前处于历史中低位区（20-50%分位），可能处于修复阶段。\n\n")
            else:
                lines.append("**位置解读**：当前处于历史低位区（<20%分位），潜在超卖或基本面恶化。\n\n")

        except Exception as e:
            lines.append(f"> 历史价格全景计算失败：{e}\n\n")

        # ── 6.3 关键支撑压力区（最近3年，≥3次出现）───────────────────────
        lines.append("### 6.3 关键历史价位（最近3年，重复出现≥3次）\n\n")
        try:
            # 只取最近3年数据
            cutoff_3y = h10y.index[-1] - pd.DateOffset(years=3)
            h3y = h10y[h10y.index >= cutoff_3y]
            if len(h3y) < 50:
                h3y = h10y  # fallback: 数据不足时用全量

            close_3y = h3y["Close"]
            high_3y = h3y["High"]
            low_3y = h3y["Low"]

            price_min_3y = float(low_3y.min())
            price_max_3y = float(high_3y.max())

            if price_max_3y > price_min_3y:
                # 将价格空间分为100个桶，找在某价格±2%范围内出现≥3次的价位
                bins_n = 100
                bins_arr = pd.cut(close_3y, bins=bins_n, include_lowest=True)
                vol_by_price = h3y.groupby(bins_arr, observed=True)["Volume"].sum()
                cnt_by_price = h3y.groupby(bins_arr, observed=True)["Close"].count()

                # 筛选出现次数≥3次的价格区间
                sig_levels = []
                for interval, cnt in cnt_by_price.items():
                    try:
                        if cnt >= 3:
                            mid = (interval.left + interval.right) / 2
                            vol = vol_by_price.get(interval, 0)
                            sig_levels.append((mid, int(cnt), float(vol)))
                    except Exception:
                        continue

                # 按成交量倒序，取前8个最重要价位
                sig_levels.sort(key=lambda x: x[2], reverse=True)
                top8 = sig_levels[:8]

                if top8:
                    lines.append("| 关键价位 | 出现次数 | 成交量权重 | 意义 |\n|---|---|---|---|\n")
                    for mid, cnt, vol in top8:
                        rel = "支撑区" if mid < cur_price else "压力区"
                        pct_from_cur = (mid - cur_price) / cur_price * 100 if cur_price else 0
                        lines.append(
                            f"| ${mid:.1f}（距当前{pct_from_cur:+.1f}%）"
                            f" | {cnt}次 | {fmt_num(vol)} | {rel} |\n"
                        )
                    lines.append("\n")
                else:
                    lines.append("> 未找到满足条件的关键价位（出现≥3次）\n\n")
            else:
                lines.append("> 价格区间数据不足\n\n")
        except Exception as e:
            lines.append(f"> 关键价位识别失败：{e}\n\n")

        # ── 6.4 历史回调统计 ──────────────────────────────────────────────
        lines.append("### 6.4 历史回调统计（>10% 的回调）\n\n")
        try:
            h10y_close = close.values
            drawdowns = []
            recovery_days = []

            peak = h10y_close[0]
            peak_idx = 0
            in_drawdown = False
            drawdown_start = 0
            min_price = peak
            min_idx = 0

            for i, price in enumerate(h10y_close):
                if price > peak:
                    # 如果之前在回调中，计算恢复
                    if in_drawdown and drawdowns:
                        # 找回调结束点（价格恢复到峰值）
                        recovery_days.append(i - drawdown_start)
                        in_drawdown = False
                    peak = price
                    peak_idx = i
                    min_price = price
                    min_idx = i

                dd = (price - peak) / peak * 100
                if dd < -10:
                    if not in_drawdown:
                        in_drawdown = True
                        drawdown_start = peak_idx
                    if price < min_price:
                        min_price = price
                        min_idx = i
                    drawdowns.append(dd)

            if drawdowns:
                avg_dd = sum(drawdowns) / len(drawdowns)
                max_dd = min(drawdowns)
                avg_rec = sum(recovery_days) / len(recovery_days) if recovery_days else 0

                lines.append("| 统计项 | 数值 | 意义 |\n|---|---|---|\n")
                lines.append(f"| 10%以上回调次数 | {len(set(int(d/5)*5 for d in drawdowns))} 次（估算） | 历史波动频率 |\n")
                lines.append(f"| 平均回调幅度 | {avg_dd:.1f}% | 正常波动预期 |\n")
                lines.append(f"| 最大回撤(10年) | {max_dd:.1f}% | 极端情况参考 |\n")
                if avg_rec > 0:
                    lines.append(f"| 平均恢复时间 | {avg_rec:.0f} 交易日 | 止损宽度参考 |\n")
                lines.append("\n")
                lines.append(f"**止损参考**：基于历史平均回调 {avg_dd:.1f}%，建议止损不超过 {abs(avg_dd)*0.6:.1f}%，最大容忍 {abs(avg_dd):.1f}%\n\n")
            else:
                lines.append("> 未找到超过10%的历史回调\n\n")
        except Exception as e:
            lines.append(f"> 历史回调统计失败：{e}\n\n")

        # ── 6.5 长期相对强度 ──────────────────────────────────────────────
        lines.append("### 6.5 长期相对强度（vs SPY）\n\n")
        try:
            spy_10y = safe(lambda: yf.Ticker("SPY").history(period="10y"), None)

            periods_rs = [("5年", -1260), ("10年", 0)]
            lines.append("| 周期 | 本股涨幅 | SPY涨幅 | 超额收益 |\n|---|---|---|---|\n")
            for label, start_idx in periods_rs:
                try:
                    sym_start = float(close.iloc[start_idx]) if start_idx == 0 else float(close.iloc[max(0, len(close)+start_idx)])
                    sym_end = float(close.iloc[-1])
                    sym_ret = (sym_end - sym_start) / sym_start * 100

                    spy_ret = None
                    if spy_10y is not None and len(spy_10y) > 0:
                        spy_start = float(spy_10y["Close"].iloc[start_idx]) if start_idx == 0 else float(spy_10y["Close"].iloc[max(0, len(spy_10y)+start_idx)])
                        spy_end_v = float(spy_10y["Close"].iloc[-1])
                        spy_ret = (spy_end_v - spy_start) / spy_start * 100

                    alpha = sym_ret - spy_ret if spy_ret is not None else None
                    lines.append(
                        f"| {label} | {sym_ret:+.1f}% | {spy_ret:+.1f}% | {alpha:+.1f}% |\n"
                        if spy_ret is not None else
                        f"| {label} | {sym_ret:+.1f}% | N/A | N/A |\n"
                    )
                except Exception:
                    lines.append(f"| {label} | N/A | N/A | N/A |\n")
            lines.append("\n")
        except Exception as e:
            lines.append(f"> 长期相对强度计算失败：{e}\n\n")

        # ── 6.6 近期位置解读 ──────────────────────────────────────────────
        lines.append("### 6.6 近期位置解读\n\n")
        try:
            all_time_high = float(high_col.max())
            pct_from_ath = (cur_price - all_time_high) / all_time_high * 100

            if abs(pct_from_ath) < 5:
                lines.append(f"- 当前价格接近历史高点（距ATH {pct_from_ath:.1f}%），处于突破关键区域\n")
                lines.append("- 突破历史高点若成功：进入无压力区间，缺少历史套牢盘阻力，可能加速上涨\n")
                lines.append("- 若未能突破：可能形成双顶或头肩顶，面临显著回调风险\n\n")
            elif pct_from_ath > -20:
                lines.append(f"- 当前价格距历史高点 {pct_from_ath:.1f}%，处于近期高位区\n")
                lines.append("- 上方存在历史套牢盘压力，需关注是否有足够成交量突破\n\n")
            elif pct_from_ath > -50:
                lines.append(f"- 当前价格距历史高点 {pct_from_ath:.1f}%，处于修复阶段\n")
                lines.append("- 历史套牢盘较多，反弹面临重重阻力，需配合基本面改善\n\n")
            else:
                lines.append(f"- 当前价格较历史高点下跌 {abs(pct_from_ath):.1f}%，处于深度回撤区域\n")
                lines.append("- 可能存在逆向机会，但需验证基本面是否发生根本性恶化\n\n")
        except Exception as e:
            lines.append(f"> 近期位置解读失败：{e}\n\n")

    except Exception as e:
        lines.append(f"> 长期结构分析失败：{e}\n\n")


# ── 章节七：板块分析 ────────────────────────────────────────────────────────────

def section_sector(sym, info, sector_map, lines):
    lines.append("## 七、板块分析\n\n")
    try:
        sect_info = sector_map.get(sym, {})
        sect_etf = sect_info.get("ref")
        sect_etf_name = sect_info.get("ref_name", sect_etf or "N/A")

        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")

        lines.append(f"**所属板块**：{sector} / {industry}\n\n")
        lines.append(f"**参照ETF**：{sect_etf_name}（{sect_etf or 'N/A'}）\n\n")

        if sect_etf:
            try:
                etf_tick = yf.Ticker(sect_etf)
                etf_hist = safe(lambda: etf_tick.history(period="6mo"), None)
                spy_hist = safe(lambda: yf.Ticker("SPY").history(period="6mo"), None)
                sym_tick = yf.Ticker(sym)
                sym_hist_6m = safe(lambda: sym_tick.history(period="6mo"), None)

                periods_sect = [("1月", 21), ("3月", 63), ("6月", 126)]
                lines.append(f"| 周期 | {sym} | {sect_etf_name} | SPY | 相对板块 |\n|---|---|---|---|---|\n")
                for label, days in periods_sect:
                    s_pct = price_change(sym_hist_6m, days)
                    e_pct = price_change(etf_hist, days)
                    spy_pct = price_change(spy_hist, days)
                    rel = (s_pct - e_pct) if s_pct is not None and e_pct is not None else None

                    s_str = f"{s_pct:+.1f}%" if s_pct is not None else "N/A"
                    e_str = f"{e_pct:+.1f}%" if e_pct is not None else "N/A"
                    spy_str = f"{spy_pct:+.1f}%" if spy_pct is not None else "N/A"
                    rel_str = f"{rel:+.1f}%" if rel is not None else "N/A"
                    lines.append(f"| {label} | {s_str} | {e_str} | {spy_str} | {rel_str} |\n")
                lines.append("\n")

                # 板块内相对地位
                if etf_hist is not None and sym_hist_6m is not None:
                    s_1m = price_change(sym_hist_6m, 21)
                    e_1m = price_change(etf_hist, 21)
                    if s_1m is not None and e_1m is not None:
                        if s_1m > e_1m + 5:
                            lines.append(f"**板块内地位**：近1月{sym}领涨（超板块 {s_1m-e_1m:.1f}%）\n\n")
                        elif s_1m > e_1m:
                            lines.append(f"**板块内地位**：近1月{sym}同步板块（微超 {s_1m-e_1m:.1f}%）\n\n")
                        else:
                            lines.append(f"**板块内地位**：近1月{sym}落后板块（差 {s_1m-e_1m:.1f}%）\n\n")
            except Exception as e:
                lines.append(f"> 板块ETF数据获取失败：{e}\n\n")

        # 宏观驱动
        theme_map = {
            "Technology": "核心驱动：AI算力需求、云支出、企业数字化转型；关注：利率环境、科技监管",
            "Semiconductors": "核心驱动：AI/HPC芯片需求、数据中心扩张；关注：出口管制、TSMC产能、存储周期",
            "Communication Services": "核心驱动：数字广告复苏、AI应用商业化；关注：隐私监管、用户增长瓶颈",
            "Consumer Cyclical": "核心驱动：消费者信心、就业市场；关注：通胀、利率、消费降级",
            "Energy": "核心驱动：油价、OPEC+政策；关注：能源转型、地缘政治",
            "Financials": "核心驱动：利率周期、信贷质量；关注：商业地产敞口、监管收紧",
        }
        for key, theme in theme_map.items():
            if key.lower() in sector.lower() or key.lower() in industry.lower():
                lines.append(f"**宏观驱动**：{theme}\n\n")
                break

    except Exception as e:
        lines.append(f"> 板块分析数据获取失败：{e}\n\n")


# ── 章节八：机构与市场情绪 ──────────────────────────────────────────────────────

def section_sentiment(sym, ticker, info, lines):
    lines.append("## 八、机构与市场情绪\n\n")
    try:
        # 空头比例
        short_pct = info.get("shortPercentOfFloat")
        short_ratio = info.get("shortRatio")
        lines.append("### 8.1 空头数据\n\n")
        lines.append("| 指标 | 数值 | 解读 |\n|---|---|---|\n")
        if short_pct:
            s_pct_f = float(short_pct) * 100
            comment = "高空头（>20%，潜在轧空）" if s_pct_f > 20 else "中等" if s_pct_f > 10 else "低空头"
            lines.append(f"| 空头占流通股比 | {s_pct_f:.1f}% | {comment} |\n")
        if short_ratio:
            lines.append(f"| 空头回补天数 | {float(short_ratio):.1f}天 | {'>5天 轧空风险高' if float(short_ratio)>5 else '正常'} |\n")
        lines.append("\n")

        # 主要机构持仓
        lines.append("### 8.2 主要机构持仓（前5大）\n\n")
        try:
            inst = safe(lambda: ticker.institutional_holders, None)
            if inst is not None and len(inst) > 0:
                lines.append("| 机构 | 持仓比例 | 持仓价值 |\n|---|---|---|\n")
                for _, row in inst.head(5).iterrows():
                    try:
                        holder = row.get("Holder", "N/A")
                        pct_held = row.get("% Out", None)
                        value = row.get("Value", None)
                        pct_str = f"{float(pct_held)*100:.2f}%" if pct_held is not None else "N/A"
                        val_str = fmt_num(value, " USD") if value else "N/A"
                        lines.append(f"| {holder} | {pct_str} | {val_str} |\n")
                    except Exception:
                        continue
                lines.append("\n")
            else:
                lines.append("> 机构持仓数据不可用\n\n")
        except Exception:
            lines.append("> 机构持仓数据不可用\n\n")

        # 内部人交易
        lines.append("### 8.3 内部人交易（近期）\n\n")
        try:
            insiders = safe(lambda: ticker.insider_transactions, None)
            if insiders is not None and len(insiders) > 0:
                lines.append("| 日期 | 内部人 | 职位 | 操作 | 数量 | 价格 |\n|---|---|---|---|---|---|\n")
                for _, row in insiders.head(8).iterrows():
                    try:
                        date_s = str(row.get("Start Date", "N/A"))[:10]
                        name = row.get("Name", "N/A")
                        title = row.get("Title", "N/A")
                        text = row.get("Text", "")
                        shares = row.get("Shares", 0)
                        price_val = row.get("Value", None)
                        action = "买入" if "purchase" in text.lower() or "buy" in text.lower() else "卖出" if "sale" in text.lower() or "sell" in text.lower() else text[:20]
                        lines.append(f"| {date_s} | {name} | {str(title)[:20]} | {action} | {fmt_num(shares)} | {fmt_num(price_val, ' USD')} |\n")
                    except Exception:
                        continue
                lines.append("\n")
            else:
                lines.append("> 内部人交易数据不可用\n\n")
        except Exception:
            lines.append("> 内部人交易数据不可用\n\n")

        # 分析师评级分布
        lines.append("### 8.4 分析师评级\n\n")
        rec = info.get("recommendationKey", "N/A")
        rec_mean = info.get("recommendationMean")
        n_analysts = info.get("numberOfAnalystOpinions", 0)
        lines.append(f"**综合评级**：{rec.upper() if rec and rec != 'N/A' else 'N/A'}（均值={rec_mean:.2f}/5，{n_analysts}位分析师）\n\n" if rec_mean else f"**综合评级**：{rec.upper() if rec else 'N/A'}（{n_analysts}位分析师）\n\n")

        try:
            upgrades = safe(lambda: ticker.upgrades_downgrades, None)
            if upgrades is not None and len(upgrades) > 0:
                lines.append("**近期评级变动**（最新5条）：\n\n")
                lines.append("| 日期 | 机构 | 评级前 | 评级后 |\n|---|---|---|---|\n")
                for idx, row in upgrades.head(5).iterrows():
                    date_str = str(idx)[:10] if idx else "N/A"
                    firm = row.get("Firm", "N/A")
                    from_g = row.get("FromGrade", "")
                    to_g = row.get("ToGrade", "")
                    lines.append(f"| {date_str} | {firm} | {from_g} | {to_g} |\n")
                lines.append("\n")
        except Exception:
            pass

    except Exception as e:
        lines.append(f"> 机构情绪数据获取失败：{e}\n\n")


# ── 章节九：催化剂地图 ──────────────────────────────────────────────────────────

def section_catalysts(sym, ticker, news_items, lines):
    lines.append("## 九、催化剂地图\n\n")
    try:
        # 下次财报日期
        cal = safe(lambda: ticker.calendar, None)
        if cal is not None:
            try:
                if isinstance(cal, dict):
                    earn_date = cal.get("Earnings Date") or cal.get("earningsDate")
                elif hasattr(cal, 'loc'):
                    try:
                        earn_date = cal.loc["Earnings Date"].values if "Earnings Date" in cal.index else None
                    except Exception:
                        earn_date = None
                else:
                    earn_date = None

                if earn_date is not None:
                    if hasattr(earn_date, '__iter__') and not isinstance(earn_date, str):
                        earn_date_str = str(list(earn_date)[0])[:10] if earn_date is not None else "N/A"
                    else:
                        earn_date_str = str(earn_date)[:10]
                    lines.append(f"**下次财报日期**：{earn_date_str}\n\n")
                else:
                    lines.append("**下次财报日期**：暂无数据\n\n")
            except Exception:
                lines.append("**下次财报日期**：暂无数据\n\n")

        # 近30天新闻时间线
        if news_items:
            lines.append("### 9.1 近30天新闻时间线\n\n")
            lines.append("| 日期 | 来源 | 标题 | 情绪 |\n|---|---|---|---|\n")
            for n in news_items:
                sentiment = classify_news(n["title"])
                title_safe = n["title"].replace("|", "｜")
                lines.append(f"| {n['date']} | {n['source']} | {title_safe} | {sentiment} |\n")
            lines.append("\n")

            # 情绪统计
            sentiments = [classify_news(n["title"]) for n in news_items]
            bull_cnt = sentiments.count("利多")
            bear_cnt = sentiments.count("利空")
            neu_cnt = sentiments.count("中性")
            total = len(sentiments)
            lines.append(f"**情绪分布**：利多 {bull_cnt}/{total}，利空 {bear_cnt}/{total}，中性 {neu_cnt}/{total}\n\n")

            # 整体情绪判断
            if bull_cnt > bear_cnt * 1.5:
                lines.append("**新闻情绪**：偏乐观，利多消息为主\n\n")
            elif bear_cnt > bull_cnt * 1.5:
                lines.append("**新闻情绪**：偏悲观，利空消息为主，需关注基本面验证\n\n")
            else:
                lines.append("**新闻情绪**：中性偏混合，等待明确催化剂\n\n")
        else:
            lines.append("> 未获取到近期新闻（网络限制）\n\n")

    except Exception as e:
        lines.append(f"> 催化剂数据获取失败：{e}\n\n")


# ── 章节十：风险矩阵 ────────────────────────────────────────────────────────────

def section_risks(sym, info, ticker, lines):
    lines.append("## 十、风险矩阵\n\n")
    try:
        lines.append("| 风险类型 | 具体描述 | 严重度 | 备注 |\n|---|---|---|---|\n")

        risks_table = []

        # 估值风险
        ps = info.get("priceToSalesTrailing12Months")
        pe = info.get("trailingPE")
        if ps and float(ps) > 100:
            risks_table.append(("估值风险", f"PS={float(ps):.1f}x，超过100倍", "高", "依赖极高增速，任何预期差都会导致股价大幅下跌"))
        elif pe and float(pe) > 0 and float(pe) > 200:
            risks_table.append(("估值风险", f"PE={float(pe):.1f}x，超过200倍", "高", "利润基数极低，盈利持续性存疑"))
        elif ps and float(ps) > 50:
            risks_table.append(("估值风险", f"PS={float(ps):.1f}x，偏高", "中", "需持续高增速支撑"))

        # 杠杆风险
        de = info.get("debtToEquity")
        if de:
            de_v = float(de)
            if de_v > 200:
                risks_table.append(("杠杆风险", f"D/E={de_v:.1f}%（>200%）", "高", "高负债在利率上升环境下压力大"))
            elif de_v > 100:
                risks_table.append(("杠杆风险", f"D/E={de_v:.1f}%（>100%）", "中", "负债水平值得关注"))

        # 现金跑道
        cash = info.get("totalCash") or 0
        burn = info.get("freeCashflow") or 0
        if cash and burn and float(burn) < 0:
            try:
                runway = abs(float(cash) / float(burn))
                if runway < 1.5:
                    risks_table.append(("现金跑道", f"约{runway:.1f}年（<1.5年）", "高", "可能需要再融资，稀释股东"))
                elif runway < 3:
                    risks_table.append(("现金跑道", f"约{runway:.1f}年（<3年）", "中", "中期内可能面临融资需求"))
            except Exception:
                pass

        # 超买风险（从1年历史数据推算RSI）
        try:
            tick_temp = yf.Ticker(sym)
            h1y = safe(lambda: tick_temp.history(period="3mo"), None)
            if h1y is not None and len(h1y) >= 14:
                rsi_series = compute_rsi(h1y["Close"])
                if rsi_series is not None:
                    rsi_v = float(rsi_series.iloc[-1])
                    if rsi_v > 80:
                        risks_table.append(("超买风险", f"RSI={rsi_v:.1f}（>80）", "中", "短期超买，可能面临技术性回调"))
        except Exception:
            pass

        # 宏观敏感
        beta = info.get("beta")
        if beta:
            beta_v = float(beta)
            if beta_v > 2.5:
                risks_table.append(("宏观敏感", f"Beta={beta_v:.2f}（>2.5）", "高", "大盘回调时放大跌幅，波动剧烈"))
            elif beta_v > 1.8:
                risks_table.append(("宏观敏感", f"Beta={beta_v:.2f}（>1.8）", "中", "显著高于大盘波动"))

        # 竞争风险
        sector = info.get("sector", "")
        sc = SUPPLY_CHAIN.get(sector, {})
        threats = sc.get("threats", "")
        if threats:
            risks_table.append(("竞争风险", threats[:60] + "...", "中", "行业结构性风险"))

        # 输出表格
        if risks_table:
            for rt, desc, severity, note in risks_table:
                lines.append(f"| {rt} | {desc} | {severity} | {note} |\n")
        else:
            lines.append("| 综合评估 | 未识别到明显高危风险指标 | 低 | 不代表无风险，需结合宏观环境判断 |\n")
        lines.append("\n")

    except Exception as e:
        lines.append(f"> 风险矩阵生成失败：{e}\n\n")


# ── 章节十一：持仓信息 ──────────────────────────────────────────────────────────

def section_position(sym, info, cur_price, positions, lines):
    lines.append("## 十一、持仓信息\n\n")
    try:
        pos_info = positions.get(sym)
        if pos_info:
            cost = float(pos_info.get("cost", 0))
            shares = float(pos_info.get("shares", 0))
            entry_date = pos_info.get("date", "N/A")
            note = pos_info.get("note", "")
            pnl_pct = pct_float(cur_price, cost) if cur_price else None
            pnl_abs = (cur_price - cost) * shares if cur_price else None
            total_val = cur_price * shares if cur_price else None

            total_port = sum(
                float(p.get("cost", 0)) * float(p.get("shares", 0))
                for p in positions.values()
            )
            cost_basis = cost * shares
            port_pct = cost_basis / total_port * 100 if total_port else None

            lines.append("| 项目 | 数值 |\n|---|---|\n")
            lines.append(f"| 买入成本 | ${cost:.2f} |\n")
            lines.append(f"| 持仓股数 | {int(shares)} 股 |\n")
            lines.append(f"| 买入日期 | {entry_date} |\n")
            lines.append(f"| 当前价 | ${cur_price:.2f} |\n" if cur_price else "| 当前价 | N/A |\n")
            if pnl_pct is not None:
                pnl_sign = "+" if pnl_abs and pnl_abs >= 0 else ""
                lines.append(f"| 浮动盈亏 | {pnl_pct:+.2f}%（${pnl_sign}{pnl_abs:.0f}）|\n")
            if total_val:
                lines.append(f"| 持仓市值 | ${total_val:.0f} |\n")
            if port_pct:
                lines.append(f"| 持仓占比（成本基础）| {port_pct:.1f}% |\n")
            if note:
                lines.append(f"| 备注 | {note} |\n")
            lines.append("\n")
        else:
            lines.append(f"> {sym} 当前未持仓。\n\n")
    except Exception as e:
        lines.append(f"> 持仓信息加载失败：{e}\n\n")


# ── 章节十二：综合判断 ──────────────────────────────────────────────────────────

def section_judgment(sym, info, cur_price, tech_data, news_items, pos_info, lines):
    lines.append("## 十二、综合判断\n\n")
    try:
        pe = info.get("trailingPE")
        ps = info.get("priceToSalesTrailing12Months")
        gm = info.get("grossMargins")
        fcf = info.get("freeCashflow")
        rev_g = info.get("revenueGrowth")
        de = info.get("debtToEquity")
        beta = info.get("beta")
        sector = info.get("sector", "")
        industry = info.get("industry", "")

        ma200 = tech_data.get("ma200")
        stage = tech_data.get("stage", "N/A")
        price_percentile = tech_data.get("price_percentile", 50)
        max_dd = tech_data.get("max_drawdown", None)
        short_pct = info.get("shortPercentOfFloat")

        # 情绪总结
        bull_cnt = sum(1 for n in news_items if classify_news(n["title"]) == "利多")
        news_sentiment = "偏乐观" if bull_cnt > len(news_items) * 0.5 else "偏悲观" if bull_cnt < len(news_items) * 0.3 else "中性"

        # 获取大盘变化百分比
        spy_chg = None
        try:
            spy_hist = safe(lambda: yf.Ticker("SPY").history(period="1d"), None)
            if spy_hist is not None and len(spy_hist) >= 1:
                spy_chg = (spy_hist["Close"].iloc[-1] - spy_hist["Open"].iloc[0]) / spy_hist["Open"].iloc[0] * 100
        except Exception:
            spy_chg = None

        # ── Minervini（技术趋势+RS）
        try:
            if "Stage 2" in stage:
                min_view = f"{sym} 处于 {stage}，MA200向上，技术趋势强势。"
                if price_percentile and float(price_percentile) > 80:
                    min_view += " 但价格处于历史高位区，追高需谨慎，等待强势回调买点。"
                else:
                    min_view += f" 价格历史百分位 {price_percentile:.0f}%，仍有上升空间。"
            elif "Stage 4" in stage:
                min_view = f"{sym} 处于 {stage}，MA200向下，技术趋势悲观。建议回避，等待趋势逆转信号（价格站稳MA200+量能放大）。"
            else:
                min_view = f"{sym} 处于 {stage}，趋势不明朗。等待突破确认后再介入，勿提前抄底。"
        except Exception:
            min_view = "技术数据不足，无法评估。"

        # ── George Soros（反身性+市场心理+大势）
        try:
            soros_pts = []
            if news_sentiment == "正面":
                soros_pts.append(f"{sym}新闻情绪正面，市场预期向上")
            if price_percentile and float(price_percentile) > 70:
                soros_pts.append(f"价格处于{price_percentile:.0f}%历史高位，市场心理高涨，反身性强")
            if spy_chg and float(spy_chg) > 0:
                soros_pts.append(f"市场环境顺风(SPY+{spy_chg:.1f}%)，趋势动量强")
            if rev_g and float(rev_g) > 0.2:
                soros_pts.append(f"基本面增长{float(rev_g)*100:.0f}%支撑价格上行")
            if de and float(de) > 200:
                soros_pts.append(f"杠杆比例高(D/E={float(de):.0f}%)，高风险高收益")

            if soros_pts:
                soros_view = f"{sym}：反身性视角 - " + "；".join(soros_pts[:3]) + "。当市场情绪与基本面互相强化时，买入反身性参与。"
                if len(soros_pts) > 3:
                    soros_view += " 风险提示：" + "；".join(soros_pts[3:]) + "。"
            else:
                soros_view = f"{sym} 反身性条件评估数据不足，需等待市场心理与基本面对齐的窗口。"
        except Exception:
            soros_view = "反身性评估数据不足，无法评估。"

        # ── Druckenmiller（主题+宏观+催化剂）
        try:
            theme_map = {
                "Technology": "AI/数字化转型",
                "Semiconductors": "AI芯片/算力军备赛",
                "Communication Services": "数字广告/AI应用",
                "Consumer Cyclical": "消费复苏",
                "Energy": "能源转型",
            }
            theme = next((v for k, v in theme_map.items() if k.lower() in sector.lower()), f"{sector}主题")
            druck_view = f"{sym} 所在的 {theme} 赛道，{news_sentiment}新闻情绪。"
            if rev_g and float(rev_g) > 0.3:
                druck_view += f" 营收增速{float(rev_g)*100:.0f}%，具备动量性机会。"
            druck_view += " 关注下季财报能否持续超预期，以及板块资金流向。"
        except Exception:
            druck_view = "宏观主题数据不足，无法评估。"

        # ── Howard Marks（风险+情绪钟摆）
        try:
            marks_pts = []
            if price_percentile and float(price_percentile) > 80:
                marks_pts.append(f"价格处于10年{price_percentile:.0f}%历史高位，市场乐观情绪充分定价")
            if short_pct and float(short_pct) < 0.03:
                marks_pts.append("空头比例极低，市场情绪偏乐观，逆向需谨慎")
            if de and float(de) > 150:
                marks_pts.append(f"D/E={float(de):.0f}%，高息环境下债务成本上升风险")
            if marks_pts:
                marks_view = "当前 " + "；".join(marks_pts) + "。情绪钟摆偏热，建议控制仓位、留现金应对波动。"
            else:
                marks_view = f"{sym} 当前风险指标未见极端信号，但需持续关注宏观流动性和市场情绪变化。"
        except Exception:
            marks_view = "风险数据不足，无法评估。"

        # ── Jesse Livermore（趋势跟踪+技术+支撑阻力）
        try:
            livermore_pts = []
            if price_percentile and float(price_percentile) > 60:
                livermore_pts.append(f"价格{price_percentile:.0f}%分位，处于上升趋势")
            if rev_g and float(rev_g) > 0.15:
                livermore_pts.append(f"营收增速{float(rev_g)*100:.0f}%，趋势向上")
            if spy_chg and float(spy_chg) > 0:
                livermore_pts.append(f"大盘环境顺风SPY+{spy_chg:.1f}%，顺势而为")
            if pe and float(pe) > 0 and float(pe) < 50:
                livermore_pts.append(f"PE={float(pe):.0f}x，估值相对合理")
            if max_dd and float(max_dd) > -50:
                livermore_pts.append("近期未见深度回撤，趋势连贯")

            if livermore_pts:
                livermore_view = f"{sym}：趋势跟踪视角 - " + "；".join(livermore_pts[:3]) + "。当价格突破关键支撑位时介入，顺势加仓。"
                if len(livermore_pts) > 3:
                    livermore_view += " 补充条件：" + "；".join(livermore_pts[3:]) + "。"
            else:
                livermore_view = f"{sym} 趋势信号不明朗，等待明确的技术突破或支撑位确认。"
        except Exception:
            livermore_view = "趋势评估数据不足，无法评估。"

        # ── Taleb（尾部风险+反脆弱性）
        try:
            taleb_pts = []
            if beta and float(beta) > 2:
                taleb_pts.append(f"Beta={float(beta):.1f}，黑天鹅事件时跌幅可能超预期")
            if pe and float(pe) > 100:
                taleb_pts.append(f"极高PE={float(pe):.0f}x，对预期变化极度敏感，尾部风险高")
            cash = info.get("totalCash")
            total_debt = info.get("totalDebt")
            if cash and total_debt and float(total_debt) > float(cash) * 3:
                taleb_pts.append("现金覆盖债务不足，流动性危机脆弱性高")
            if not taleb_pts:
                taleb_pts.append("未识别到显著尾部风险指标")

            taleb_view = "尾部风险评估：" + "；".join(taleb_pts) + "。建议分批建仓、不重仓单只股票。"
        except Exception:
            taleb_view = "尾部风险数据不足，无法评估。"

        # 输出七位大师视角
        lines.append("### 12.1 七位大师视角\n\n")
        masters = [
            ("Minervini（技术趋势+RS）", min_view),
            ("George Soros（反身性+市场心理）", soros_view),
            ("Stan Druckenmiller（主题+宏观）", druck_view),
            ("Howard Marks（风险+情绪钟摆）", marks_view),
            ("Jesse Livermore（趋势跟踪+技术）", livermore_view),
            ("Nassim Taleb（尾部风险+反脆弱）", taleb_view),
            ("Peter Lynch（成长性+商业模式）", "Peter Lynch 视角数据整合中..."),
        ]
        for master_name, view in masters:
            lines.append(f"**{master_name}**：{view}\n\n")

        # 综合评分
        lines.append("### 12.2 综合评分\n\n")
        score = 5.0

        # 技术趋势
        if "Stage 2" in stage:
            score += 1.0
        elif "Stage 4" in stage:
            score -= 1.0

        # 基本面
        if rev_g and float(rev_g) > 0.3:
            score += 1.0
        elif rev_g and float(rev_g) > 0.1:
            score += 0.5
        elif rev_g and float(rev_g) < 0:
            score -= 0.5

        if gm and float(gm) > 0.5:
            score += 0.5

        if fcf and float(fcf) > 0:
            score += 0.5

        # 估值合理性
        if pe and float(pe) > 0 and float(pe) < 25:
            score += 0.5
        elif pe and float(pe) > 100:
            score -= 0.5

        # 风险扣分
        if de and float(de) > 200:
            score -= 1.0
        if beta and float(beta) > 2.5:
            score -= 0.5
        if short_pct and float(short_pct) > 0.2:
            score -= 0.5

        # 持仓加分
        if pos_info:
            cost = pos_info.get("cost", 0)
            if cur_price and cost and float(cur_price) > float(cost):
                score += 0.3

        score = round(min(10.0, max(0.0, score)), 1)

        if score >= 8:
            rating = "强烈关注"
        elif score >= 6.5:
            rating = "积极关注"
        elif score >= 5:
            rating = "中性观望"
        elif score >= 3:
            rating = "谨慎回避"
        else:
            rating = "不推荐"

        lines.append(f"**综合评分：{score} / 10（{rating}）**\n\n")
        lines.append(
            "> 评分基于技术趋势（Stage/MA200）、基本面质量（增速/毛利/FCF）、"
            "估值合理性（PE/PEG）、风险指标（负债/Beta）综合量化，仅供参考，不构成投资建议。\n\n"
        )

    except Exception as e:
        lines.append(f"> 综合判断生成失败：{e}\n\n")


# ── 主报告生成函数 ─────────────────────────────────────────────────────────────

def generate_report(sym, positions, sector_map):
    sym = sym.upper()
    lines = []
    lines.append(f"# {sym} 深度研究报告 | {TODAY}\n\n")

    # ── 数据获取 ─────────────────────────────────────────────────────────────
    ticker = yf.Ticker(sym)
    info = safe(lambda: ticker.info, {}) or {}

    cur_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    try:
        cur_price = float(cur_price)
    except Exception:
        cur_price = 0

    # 新闻（提前获取，多章节复用）
    news_items = fetch_news(sym, days=30, max_items=15)

    # 公司定性知识库
    profile = load_company_profile(sym)

    # 长期技术数据（第六章用，提前计算部分供十二章使用）
    tech_data = {}
    h10y = None
    price_events = []
    try:
        h10y = safe(lambda: ticker.history(period="10y"), None)
        if h10y is not None and len(h10y) >= 200:
            close = h10y["Close"]
            high_col = h10y["High"]
            low_col = h10y["Low"]

            ma200 = close.rolling(200).mean()
            ma200_last = float(ma200.iloc[-1])
            ma200_20d_ago = float(ma200.iloc[-20])
            ma200_slope = ma200_last - ma200_20d_ago

            if ma200_slope > 0 and cur_price > ma200_last:
                stage = "Stage 2（上升趋势）"
            elif ma200_slope > 0 and cur_price < ma200_last:
                stage = "Stage 1/3（横盘）"
            elif ma200_slope < 0 and cur_price < ma200_last:
                stage = "Stage 4（下降趋势）"
            else:
                stage = "Stage 3（顶部分配）"

            tech_data["stage"] = stage
            tech_data["ma200"] = ma200_last

            all_time_high = float(high_col.max())
            all_time_low = float(low_col.min())
            if all_time_high > all_time_low:
                pp = (cur_price - all_time_low) / (all_time_high - all_time_low) * 100
                tech_data["price_percentile"] = pp

            # 最大回撤
            h10y_close = close.values
            peak = h10y_close[0]
            min_dd = 0
            for price in h10y_close:
                if price > peak:
                    peak = price
                dd = (price - peak) / peak * 100
                if dd < min_dd:
                    min_dd = dd
            tech_data["max_drawdown"] = min_dd

            # 价格事件检测（单周涨跌 >10%）
            company_name = profile.get("full_name", info.get("longName", sym))
            try:
                price_events = detect_price_events(h10y, sym, company_name)
            except Exception:
                price_events = []
    except Exception:
        pass

    # ── 报告正文：12个章节 + 业务线详解 ────────────────────────────────────────

    section_business(sym, info, lines)

    # 业务线详解（紧接在公司业务之后，使用 profile 数据）
    section_segments(sym, profile, ticker, lines)

    section_competition(sym, info, cur_price, lines)

    section_earnings(sym, ticker, info, lines)

    section_profitability(sym, ticker, info, lines)

    section_valuation(sym, info, cur_price, COMPETITORS.get(sym, []), lines)

    section_long_term(sym, ticker, cur_price, lines)

    section_sector(sym, info, sector_map, lines)

    section_sentiment(sym, ticker, info, lines)

    section_catalysts(sym, ticker, news_items, lines)

    section_risks(sym, info, ticker, lines)

    section_position(sym, info, cur_price, positions, lines)

    section_judgment(sym, info, cur_price, tech_data, news_items,
                     positions.get(sym), lines)

    lines.append(f"---\n*报告生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    # ── 写 Markdown 报告 ──────────────────────────────────────────────────────
    out_path = os.path.join(REPORTS_DIR, f"research_{sym}_{TODAY}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # ── 写 JSON 数据包 ────────────────────────────────────────────────────────
    try:
        # 财务数据序列化（去掉不可序列化的对象）
        financials_dict = {}
        try:
            fin_keys = [
                "marketCap", "currentPrice", "regularMarketPrice",
                "trailingPE", "forwardPE", "priceToSalesTrailing12Months",
                "grossMargins", "operatingMargins", "profitMargins",
                "revenueGrowth", "earningsGrowth", "totalRevenue",
                "freeCashflow", "totalCash", "totalDebt", "debtToEquity",
                "beta", "shortPercentOfFloat", "sector", "industry",
                "longName", "shortName", "country"
            ]
            for k in fin_keys:
                v = info.get(k)
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    financials_dict[k] = v
        except Exception:
            pass

        # 机构持仓
        institutional_dict = {}
        try:
            inst_holders = safe(lambda: ticker.institutional_holders, None)
            if inst_holders is not None and not inst_holders.empty:
                top3 = inst_holders.head(3)
                institutional_dict["top_holders"] = [
                    {"holder": str(row.get("Holder", "")),
                     "shares": int(row.get("Shares", 0)) if row.get("Shares") else 0,
                     "pct_out": float(row.get("% Out", 0)) if row.get("% Out") else 0}
                    for _, row in top3.iterrows()
                ]
        except Exception:
            pass

        data_pkg = {
            "sym": sym,
            "date": TODAY,
            "profile": profile,
            "financials": financials_dict,
            "price_events": price_events,
            "technical": tech_data,
            "institutional": institutional_dict,
            "news": news_items,
        }

        json_path = os.path.join(REPORTS_DIR, f"data_{sym}_{TODAY}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data_pkg, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"  [WARN] {sym} JSON数据包写入失败：{e}")

    return out_path


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main():
    symbols = [s.upper() for s in sys.argv[1:]]
    if not symbols:
        pos = load_positions()
        symbols = list(pos.keys())
        if not symbols:
            print("positions.json 为空，请指定标的。用法: python3.12 agents/stock_report.py AMD MRVL")
            sys.exit(1)
        print(f"未指定标的，使用持仓：{', '.join(symbols)}")

    positions = load_positions()
    sector_map = load_sector_map()

    print(f"生成报告中：{', '.join(symbols)} ...")

    results = {}
    with ThreadPoolExecutor(max_workers=min(len(symbols), 6)) as exe:
        futures = {
            exe.submit(generate_report, sym, positions, sector_map): sym
            for sym in symbols
        }
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                path = fut.result()
                results[sym] = ("OK", path)
                print(f"  [OK] {sym} -> {path}")
            except Exception as e:
                results[sym] = ("FAIL", str(e))
                print(f"  [FAIL] {sym}: {e}")

    print("\n─── 生成摘要 ───")
    for sym in symbols:
        status, detail = results.get(sym, ("FAIL", "未知错误"))
        print(f"  {sym}: {status}  {detail}")


if __name__ == "__main__":
    main()
