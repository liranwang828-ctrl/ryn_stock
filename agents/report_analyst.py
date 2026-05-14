#!/usr/bin/env python3
"""
研究报告分析合成器 — 调用 Claude API 生成叙事性分析报告
需要先运行 stock_report.py 生成数据包

用法：
  python3.12 agents/report_analyst.py AMD
  python3.12 agents/report_analyst.py AMD MRVL AAOI  # 多标的
  python3.12 agents/report_analyst.py  # 默认用持仓列表
"""

import os
import sys
import json
import glob
import datetime
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 路径配置 ──────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(BASE, "agents")
REPORTS_DIR = os.path.join(BASE, "reports")
CONFIG_DIR  = os.path.join(BASE, "config")
POSITIONS_FILE = os.path.join(CONFIG_DIR, "positions.json")
PYTHON = sys.executable

os.makedirs(REPORTS_DIR, exist_ok=True)

TODAY = datetime.date.today().isoformat()

# ── Claude API 初始化 ──────────────────────────────────────────────────────────
try:
    import anthropic
    client = anthropic.Anthropic()  # 从 ANTHROPIC_API_KEY 环境变量读取
    CLAUDE_AVAILABLE = True
except ImportError:
    print("[警告] anthropic 库未安装，请执行: pip install anthropic")
    CLAUDE_AVAILABLE = False
except anthropic.AuthenticationError:
    print("[警告] ANTHROPIC_API_KEY 未设置或无效，请检查环境变量")
    CLAUDE_AVAILABLE = False


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def load_positions():
    """Return list of symbols from positions.json."""
    try:
        with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return list(cfg.get("positions", {}).keys())
    except Exception:
        return []


def load_data_json(sym: str) -> dict | None:
    """找最新的 data_{sym}_*.json 数据包"""
    pattern = os.path.join(REPORTS_DIR, f"data_{sym.upper()}_*.json")
    files = sorted(glob.glob(pattern))
    if files:
        try:
            with open(files[-1], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  [警告] 读取数据包失败 {files[-1]}: {e}")
    return None


def fetch_data_if_missing(sym: str) -> dict | None:
    """如果没有数据包，先运行 stock_report.py 生成"""
    data = load_data_json(sym)
    if data:
        return data

    print(f"  [{sym}] 未找到数据包，正在运行 stock_report.py ...")
    try:
        result = subprocess.run(
            [PYTHON, os.path.join(AGENTS_DIR, "stock_report.py"), sym],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            print(f"  [{sym}] stock_report.py 执行失败: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        print(f"  [{sym}] stock_report.py 超时")
    except Exception as e:
        print(f"  [{sym}] 启动 stock_report.py 失败: {e}")

    return load_data_json(sym)


def fmt_safe(v, suffix="", decimals=2, default="N/A"):
    """安全格式化数值"""
    if v is None or v == "N/A":
        return default
    try:
        fv = float(v)
        import math
        if math.isnan(fv):
            return default
        if abs(fv) >= 1e12:
            return f"{fv/1e12:.{decimals}f}T{suffix}"
        if abs(fv) >= 1e9:
            return f"{fv/1e9:.{decimals}f}B{suffix}"
        if abs(fv) >= 1e6:
            return f"{fv/1e6:.{decimals}f}M{suffix}"
        return f"{fv:.{decimals}f}{suffix}"
    except Exception:
        return default


# ── 各章节数据准备函数 ────────────────────────────────────────────────────────

def prepare_ch1_business(data: dict) -> str:
    """一、公司业务理解"""
    p = data.get("profile", {})
    info = data.get("info", {})
    lines = []
    lines.append(f"股票代码: {data.get('sym', 'N/A')}")
    lines.append(f"公司全名: {info.get('longName', p.get('name', 'N/A'))}")
    lines.append(f"行业: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}")
    lines.append(f"市值: {fmt_safe(info.get('marketCap'), ' USD')}")
    lines.append(f"员工数: {info.get('fullTimeEmployees', 'N/A')}")
    lines.append(f"总部: {info.get('city', '')} {info.get('state', '')} {info.get('country', '')}".strip())
    summary = info.get("longBusinessSummary", "")
    if summary:
        lines.append(f"\n业务描述（原文）:\n{summary[:800]}")
    lines.append(f"\n主营业务模式推断: {p.get('business_model', info.get('industry', 'N/A'))}")
    lines.append(f"核心叙事: {p.get('narrative', '暂无')}")
    lines.append(f"业务板块分布: {p.get('segments', '暂无')}")
    lines.append(f"关键客户: {p.get('key_customers', '暂无')}")
    lines.append(f"供应链上游: {p.get('upstream', '暂无')}")
    lines.append(f"供应链下游: {p.get('downstream', '暂无')}")
    return "\n".join(lines)


def prepare_ch2_competition(data: dict) -> str:
    """二、生态系统与竞争格局"""
    p = data.get("profile", {})
    info = data.get("info", {})
    comps = data.get("competitors", [])
    lines = []

    gm = info.get("grossMargins")
    fcf = info.get("freeCashflow")
    rev = info.get("totalRevenue")
    rnd = info.get("researchAndDevelopment") or info.get("researchDevelopment")

    lines.append(f"本股毛利率: {fmt_safe(gm and gm*100, '%') if gm else 'N/A'}")
    lines.append(f"本股FCF利润率: {fmt_safe(fcf/rev*100 if fcf and rev else None, '%')}")
    lines.append(f"R&D占比: {fmt_safe(rnd/rev*100 if rnd and rev else None, '%')}")
    lines.append(f"护城河评估: {p.get('moat', '暂无')}")
    lines.append(f"生态系统: {p.get('ecosystem', '暂无')}")
    lines.append(f"竞争威胁: {p.get('competitive_threats', '暂无')}")

    if comps:
        lines.append("\n竞争对手对比:")
        for c in comps[:4]:
            lines.append(f"  {c.get('sym','?')}: 价格={c.get('price','N/A')}, PE={c.get('pe','N/A')}, 毛利率={c.get('gross_margin','N/A')}, 市值={fmt_safe(c.get('market_cap'), ' USD')}")
    return "\n".join(lines)


def prepare_ch3_history(data: dict) -> str:
    """三、历史关键事件与股价叙事"""
    p = data.get("profile", {})
    tech = data.get("technical", {})
    lines = []
    lines.append(f"重要里程碑: {p.get('milestones', '暂无')}")
    ath = tech.get("all_time_high")
    atl = tech.get("all_time_low")
    cur = data.get("cur_price", "N/A")
    if ath:
        lines.append(f"历史最高价: ${ath:.2f}")
    if atl:
        lines.append(f"历史最低价: ${atl:.2f}")
    lines.append(f"当前价格: ${cur}")
    pct = tech.get("price_percentile")
    if pct is not None:
        lines.append(f"价格历史百分位: {pct:.1f}%（100%=历史最高）")
    stage = tech.get("weinstein_stage", "N/A")
    lines.append(f"Weinstein Stage: {stage}")
    news = data.get("news", [])
    if news:
        lines.append("\n近期重大新闻:")
        for n in news[:8]:
            lines.append(f"  [{n.get('date','?')}] {n.get('title','')[:100]}")
    return "\n".join(lines)


def prepare_ch4_earnings(data: dict) -> str:
    """四、近8季度财报分析"""
    quarters = data.get("quarterly_earnings", [])
    q_fin = data.get("quarterly_financials", [])
    info = data.get("info", {})
    lines = []
    lines.append(f"年化营收增速: {fmt_safe(info.get('revenueGrowth') and info.get('revenueGrowth')*100, '%')}")
    lines.append(f"年化EPS增速: {fmt_safe(info.get('earningsGrowth') and info.get('earningsGrowth')*100, '%')}")

    if quarters:
        lines.append("\n近期EPS财报数据（最近8季）:")
        lines.append("季度 | EPS实际 | EPS预期 | Beat%")
        for q in quarters[:8]:
            lines.append(f"  {q.get('quarter','?')} | {q.get('eps_actual','N/A')} | {q.get('eps_estimate','N/A')} | {q.get('surprise_pct','N/A')}")

    if q_fin:
        lines.append("\n季度财务数据:")
        lines.append("季度 | 营收 | 毛利 | 净利润")
        for q in q_fin[:8]:
            lines.append(f"  {q.get('quarter','?')} | {fmt_safe(q.get('revenue'), ' USD')} | {fmt_safe(q.get('gross_profit'), ' USD')} | {fmt_safe(q.get('net_income'), ' USD')}")

    return "\n".join(lines)


def prepare_ch5_profitability(data: dict) -> str:
    """五、盈利质量深析"""
    info = data.get("info", {})
    cash_flow = data.get("cash_flow", {})
    lines = []
    lines.append(f"毛利率: {fmt_safe(info.get('grossMargins') and info.get('grossMargins')*100, '%')}")
    lines.append(f"营业利润率: {fmt_safe(info.get('operatingMargins') and info.get('operatingMargins')*100, '%')}")
    lines.append(f"净利润率: {fmt_safe(info.get('profitMargins') and info.get('profitMargins')*100, '%')}")
    lines.append(f"ROE: {fmt_safe(info.get('returnOnEquity') and info.get('returnOnEquity')*100, '%')}")
    lines.append(f"ROA: {fmt_safe(info.get('returnOnAssets') and info.get('returnOnAssets')*100, '%')}")
    lines.append(f"自由现金流(FCF): {fmt_safe(info.get('freeCashflow'), ' USD')}")
    lines.append(f"经营现金流: {fmt_safe(info.get('operatingCashflow'), ' USD')}")
    lines.append(f"净利润: {fmt_safe(info.get('netIncomeToCommon'), ' USD')}")
    lines.append(f"总债务: {fmt_safe(info.get('totalDebt'), ' USD')}")
    lines.append(f"现金储备: {fmt_safe(info.get('totalCash'), ' USD')}")
    shares_pct = info.get("floatShares")
    shares_out = info.get("sharesOutstanding")
    if shares_pct and shares_out:
        try:
            buyback_note = f"流通股/总股本={float(shares_pct)/float(shares_out)*100:.1f}%"
            lines.append(f"股本情况: {buyback_note}")
        except Exception:
            pass
    return "\n".join(lines)


def prepare_ch6_valuation(data: dict) -> str:
    """六、估值分析"""
    info = data.get("info", {})
    cur_price = data.get("cur_price", 0)
    lines = []
    lines.append(f"当前股价: ${cur_price}")
    lines.append(f"PE (TTM): {fmt_safe(info.get('trailingPE'), 'x')}")
    lines.append(f"PE (Forward): {fmt_safe(info.get('forwardPE'), 'x')}")
    lines.append(f"PS: {fmt_safe(info.get('priceToSalesTrailing12Months'), 'x')}")
    lines.append(f"PB: {fmt_safe(info.get('priceToBook'), 'x')}")
    lines.append(f"EV/EBITDA: {fmt_safe(info.get('enterpriseToEbitda'), 'x')}")
    lines.append(f"EV/Revenue: {fmt_safe(info.get('enterpriseToRevenue'), 'x')}")
    lines.append(f"营收增速: {fmt_safe(info.get('revenueGrowth') and info.get('revenueGrowth')*100, '%')}")
    lines.append(f"EPS增速: {fmt_safe(info.get('earningsGrowth') and info.get('earningsGrowth')*100, '%')}")

    t_mean = info.get("targetMeanPrice")
    t_low  = info.get("targetLowPrice")
    t_high = info.get("targetHighPrice")
    t_rec  = info.get("recommendationMean")
    lines.append(f"\n分析师目标价: 最低=${t_low} / 平均=${t_mean} / 最高=${t_high}")
    lines.append(f"分析师评级(1=强烈买入,5=卖出): {t_rec}")
    if t_mean and cur_price:
        try:
            upside = (float(t_mean) - float(cur_price)) / float(cur_price) * 100
            lines.append(f"目标价隐含上涨空间: {upside:+.1f}%")
        except Exception:
            pass
    return "\n".join(lines)


def prepare_ch7_longterm(data: dict) -> str:
    """七、10年长期结构分析"""
    tech = data.get("technical", {})
    lines = []
    lines.append(f"Weinstein Stage: {tech.get('weinstein_stage', 'N/A')}")
    lines.append(f"MA200: {fmt_safe(tech.get('ma200'), ' USD')}")
    lines.append(f"历史最高价(10年): ${tech.get('all_time_high', 'N/A')}")
    lines.append(f"历史最低价(10年): ${tech.get('all_time_low', 'N/A')}")
    lines.append(f"当前价历史百分位: {fmt_safe(tech.get('price_percentile'), '%')}")
    lines.append(f"最大回撤(10年): {fmt_safe(tech.get('max_drawdown'), '%')}")
    lines.append(f"平均回调幅度: {fmt_safe(tech.get('avg_drawdown'), '%')}")
    lines.append(f"距历史高点: {fmt_safe(tech.get('pct_from_ath'), '%')}")
    rs = tech.get("relative_strength", {})
    if rs:
        lines.append(f"\n相对强度(vs SPY):")
        for period, val in rs.items():
            lines.append(f"  {period}: 超额{fmt_safe(val, '%')}")
    support = tech.get("key_support_levels", [])
    if support:
        lines.append(f"\n关键支撑/压力区: {', '.join([f'${x:.1f}' for x in support[:5]])}")
    return "\n".join(lines)


def prepare_ch8_sector(data: dict) -> str:
    """八、板块分析"""
    info = data.get("info", {})
    sector_data = data.get("sector_analysis", {})
    lines = []
    lines.append(f"所属板块: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}")
    lines.append(f"参照ETF: {sector_data.get('etf', 'N/A')}")
    for period, perf in sector_data.get("etf_performance", {}).items():
        lines.append(f"  {period} ETF表现: {fmt_safe(perf, '%')}")
    lines.append(f"板块内相对强度: {sector_data.get('relative_strength', 'N/A')}")
    lines.append(f"宏观驱动因素: {sector_data.get('macro_drivers', '暂无')}")
    lines.append(f"\n本股近期表现:")
    tech = data.get("technical", {})
    for period, val in tech.get("price_changes", {}).items():
        lines.append(f"  {period}: {fmt_safe(val, '%')}")
    return "\n".join(lines)


def prepare_ch9_sentiment(data: dict) -> str:
    """九、机构与市场情绪"""
    info = data.get("info", {})
    sentiment = data.get("sentiment", {})
    lines = []
    short_pct = info.get("shortPercentOfFloat")
    lines.append(f"空头比例(Float%): {fmt_safe(short_pct and short_pct*100, '%')}")
    lines.append(f"空头回补天数: {fmt_safe(info.get('shortRatio'))}")
    lines.append(f"机构持仓比例: {fmt_safe(info.get('heldPercentInstitutions') and info.get('heldPercentInstitutions')*100, '%')}")
    lines.append(f"内部人持仓比例: {fmt_safe(info.get('heldPercentInsiders') and info.get('heldPercentInsiders')*100, '%')}")
    lines.append(f"52周最高价: ${fmt_safe(info.get('fiftyTwoWeekHigh'))}")
    lines.append(f"52周最低价: ${fmt_safe(info.get('fiftyTwoWeekLow'))}")
    lines.append(f"RSI: {fmt_safe(sentiment.get('rsi'))}")
    lines.append(f"相对于52周高点: {fmt_safe(sentiment.get('pct_from_52w_high'), '%')}")
    lines.append(f"相对于52周低点: {fmt_safe(sentiment.get('pct_from_52w_low'), '%')}")
    lines.append(f"Beta: {fmt_safe(info.get('beta'))}")
    return "\n".join(lines)


def prepare_ch10_catalysts(data: dict) -> str:
    """十、催化剂地图"""
    info = data.get("info", {})
    news = data.get("news", [])
    lines = []
    next_er = info.get("nextEarningsDate") or info.get("earningsTimestamp")
    if next_er:
        lines.append(f"下次财报日期: {next_er}")
    lines.append(f"分析师评级: {info.get('recommendationKey', 'N/A')}")
    if news:
        lines.append("\n近30天新闻（按日期）:")
        for n in news[:12]:
            sentiment = n.get("sentiment", "")
            lines.append(f"  [{n.get('date','?')}][{sentiment}] {n.get('title','')[:100]}")
    lines.append("\n可能的做多催化剂：")
    lines.append("（从上述新闻和财务数据中分析）")
    lines.append("\n可能的做空风险事件：")
    lines.append("（从上述新闻和财务数据中分析）")
    return "\n".join(lines)


def prepare_ch11_risks(data: dict) -> str:
    """十一、风险矩阵"""
    info = data.get("info", {})
    tech = data.get("technical", {})
    lines = []
    lines.append(f"Beta(系统性风险): {fmt_safe(info.get('beta'))}")
    lines.append(f"空头比例: {fmt_safe(info.get('shortPercentOfFloat') and info.get('shortPercentOfFloat')*100, '%')}")
    lines.append(f"最大历史回撤: {fmt_safe(tech.get('max_drawdown'), '%')}")
    lines.append(f"总债务: {fmt_safe(info.get('totalDebt'), ' USD')}")
    lines.append(f"现金: {fmt_safe(info.get('totalCash'), ' USD')}")
    lines.append(f"债务/现金比: {fmt_safe((info.get('totalDebt') or 0) / (info.get('totalCash') or 1))}")
    lines.append(f"当前PE: {fmt_safe(info.get('trailingPE'), 'x')} (估值风险)")
    lines.append(f"Weinstein Stage: {tech.get('weinstein_stage', 'N/A')} (技术风险)")
    lines.append(f"竞争威胁: {data.get('profile', {}).get('competitive_threats', '暂无')}")
    lines.append(f"行业供应链威胁: {data.get('profile', {}).get('supply_chain_threats', '暂无')}")
    return "\n".join(lines)


def prepare_ch12_judgment(data: dict) -> str:
    """十二、综合判断"""
    info = data.get("info", {})
    tech = data.get("technical", {})
    pos = data.get("position", {})
    lines = []
    lines.append(f"股票: {data.get('sym', 'N/A')} @ ${data.get('cur_price', 'N/A')}")
    lines.append(f"市值: {fmt_safe(info.get('marketCap'), ' USD')}")
    lines.append(f"PE: {fmt_safe(info.get('trailingPE'), 'x')}")
    lines.append(f"营收增速: {fmt_safe(info.get('revenueGrowth') and info.get('revenueGrowth')*100, '%')}")
    lines.append(f"毛利率: {fmt_safe(info.get('grossMargins') and info.get('grossMargins')*100, '%')}")
    lines.append(f"FCF: {fmt_safe(info.get('freeCashflow'), ' USD')}")
    lines.append(f"Weinstein Stage: {tech.get('weinstein_stage', 'N/A')}")
    lines.append(f"价格历史百分位: {fmt_safe(tech.get('price_percentile'), '%')}")
    lines.append(f"最大回撤: {fmt_safe(tech.get('max_drawdown'), '%')}")
    lines.append(f"分析师平均目标价: ${info.get('targetMeanPrice', 'N/A')}")
    lines.append(f"分析师评级: {info.get('recommendationKey', 'N/A')}")
    if pos:
        lines.append(f"\n持仓信息: 成本${pos.get('cost','N/A')} / {pos.get('shares','N/A')}股")
        cur = data.get("cur_price", 0)
        cost = pos.get("cost", 0)
        if cur and cost:
            try:
                pnl = (float(cur) - float(cost)) / float(cost) * 100
                lines.append(f"当前盈亏: {pnl:+.1f}%")
            except Exception:
                pass
    return "\n".join(lines)


# ── 12章节定义 ────────────────────────────────────────────────────────────────
CHAPTERS = [
    ("一、公司业务理解",          prepare_ch1_business),
    ("二、生态系统与竞争格局",    prepare_ch2_competition),
    ("三、历史关键事件与股价叙事", prepare_ch3_history),
    ("四、近8季度财报分析",       prepare_ch4_earnings),
    ("五、盈利质量深析",          prepare_ch5_profitability),
    ("六、估值分析",              prepare_ch6_valuation),
    ("七、10年长期结构分析",      prepare_ch7_longterm),
    ("八、板块分析",              prepare_ch8_sector),
    ("九、机构与市场情绪",        prepare_ch9_sentiment),
    ("十、催化剂地图",            prepare_ch10_catalysts),
    ("十一、风险矩阵",            prepare_ch11_risks),
    ("十二、综合判断",            prepare_ch12_judgment),
]


# ── Claude API 章节生成 ───────────────────────────────────────────────────────

SECTION_PROMPTS = {
    "一、公司业务理解": """用自己的语言讲清楚"这家公司靠什么赚钱、未来靠什么赚更多钱"。
重点：连接商业模式、核心护城河、成长驱动。不要照搬业务描述，要有自己的判断。""",

    "二、生态系统与竞争格局": """分析护城河是否可持续，和谁竞争，上下游关系如何影响定价权。
重点：对比竞争对手的关键指标，解释为什么这家公司能或不能保持优势。""",

    "三、历史关键事件与股价叙事": """讲出"这家公司从哪里来，到哪里去"的故事。
重点：连接每次重大价格波动的原因，解释当前所处位置的历史意义。""",

    "四、近8季度财报分析": """不只列数据，分析"这个季度超预期/不及预期的原因是什么，是一次性的还是趋势性的"。
重点：识别营收和利润的拐点，解释驱动因素变化。""",

    "五、盈利质量深析": """分析利润是否真实，现金流质量如何。
重点：FCF vs 净利润的差距说明什么，资本支出方向，股本稀释情况。""",

    "六、估值分析": """解释当前估值是否合理，需要什么条件才能维持，有什么估值风险。
重点：用PEG或隐含增速量化估值合理性，分析分析师目标价的可信度。""",

    "七、10年长期结构分析": """从10年维度看这家公司现在在哪个位置。
重点：Weinstein Stage的含义，历史回调数据如何指导止损设置，长期相对强度趋势。""",

    "八、板块分析": """分析板块风口是否持续，该股在板块内的地位变化。
重点：板块轮动逻辑，该股是领涨还是落后，宏观因素对板块的影响。""",

    "九、机构与市场情绪": """解读机构行为信号。
重点：空头比例高/低意味着什么，机构持仓变化方向，内部人买卖是否有信号意义。""",

    "十、催化剂地图": """梳理未来3-6个月的重要事件节点。
重点：哪些是做多/做空的关键催化剂，财报日前后如何应对，近期新闻中哪些最重要。""",

    "十一、风险矩阵": """不只列风险，要解释每个风险的传导路径和概率。
重点：估值风险、竞争风险、宏观风险各自的影响路径和可能的触发事件。""",

    "十二、综合判断": """六位大师各给出有针对性的2-3句话（基于具体数据，不是模板），综合评分0-10并给出详细理由。
六位大师：巴菲特（价值/护城河）、彼得·林奇（成长/PEG）、西蒙斯（量化/趋势）、达里奥（宏观）、木头姐（颠覆创新）、伊坎（激进/催化剂）。
最后给出综合评分（0-10分）和一句话投资建议。""",
}


def synthesize_section(section_name: str, data: dict, context: str) -> str:
    """调用 Claude API 生成单个章节的分析文字"""
    if not CLAUDE_AVAILABLE:
        return f"> [API不可用] {context[:300]}\n"

    sym = data.get("sym", "未知")
    specific_prompt = SECTION_PROMPTS.get(section_name, "综合分析以上数据，给出深度洞察。")

    user_content = f"""你是一位专业股票分析师，正在为 {sym} 撰写深度研究报告的"{section_name}"章节。

背景数据：
{context}

分析任务：
{specific_prompt}

写作要求：
- 不要只列数据，要解释 WHY（原因和影响）
- 连接不同数据点（例如：毛利率扩张→因为数据中心占比提升→数据中心单价更高）
- 点名具体数字支撑论点
- 用中文，简洁有力，不废话
- 字数：300-500字

撰写"{section_name}"章节："""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": user_content}]
        )
        return response.content[0].text
    except anthropic.AuthenticationError:
        return f"> [认证失败] 请检查 ANTHROPIC_API_KEY 环境变量\n\n原始数据摘要：\n{context[:500]}"
    except anthropic.RateLimitError:
        return f"> [频率限制] 请稍后重试\n\n原始数据摘要：\n{context[:500]}"
    except anthropic.BadRequestError as e:
        return f"> [请求错误] {e}\n\n原始数据摘要：\n{context[:500]}"
    except Exception as e:
        return f"> [生成失败] {e}\n\n原始数据摘要：\n{context[:500]}"


# ── 主流程：生成完整报告 ─────────────────────────────────────────────────────

def generate_full_report(sym: str) -> str:
    """Load data package, call Claude API per chapter, and write a complete analysis report."""
    sym = sym.upper()
    print(f"  [{sym}] 开始生成分析报告...")

    # 1. 读取或生成数据包
    data = fetch_data_if_missing(sym)
    if not data:
        # 如果还没有数据包，尝试从现有 research_{sym}_*.md 报告文件中读取基础信息
        print(f"  [{sym}] 无法获取结构化数据包，将基于基本信息生成报告")
        data = {"sym": sym, "info": {}, "profile": {}, "technical": {}, "news": []}

    # 确保 sym 在 data 中
    if "sym" not in data:
        data["sym"] = sym

    # 2. 逐章节调用 Claude 生成叙述
    sections = []
    for chapter_name, prepare_fn in CHAPTERS:
        print(f"  [{sym}] 生成章节: {chapter_name}...")
        try:
            context = prepare_fn(data)
        except Exception as e:
            context = f"数据准备失败: {e}"

        try:
            text = synthesize_section(chapter_name, data, context)
        except Exception as e:
            text = f"> 章节生成失败: {e}\n"

        sections.append(f"## {chapter_name}\n\n{text}")

    # 3. 拼接完整报告
    cur_price = data.get("cur_price", "N/A")
    header = f"# {sym} 深度研究报告 | {TODAY}\n\n"
    header += f"> 当前价格：${cur_price} | 报告生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    header += "---\n\n"

    report = header + "\n\n".join(sections)
    report += f"\n\n---\n*本报告由 Claude AI 合成，数据来源：yfinance + Google News | 仅供参考，不构成投资建议*\n"

    # 4. 保存报告
    save_path = os.path.join(REPORTS_DIR, f"research_{sym}_{TODAY}.md")
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  [{sym}] 报告已保存: {save_path}")
        line_count = report.count("\n")
        print(f"  [{sym}] 报告行数: ~{line_count} 行")
    except Exception as e:
        print(f"  [{sym}] 保存失败: {e}")

    return save_path


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main():
    """CLI entry point: generate narrative analysis reports for given symbols or all positions."""
    symbols = [s.upper() for s in sys.argv[1:]]
    if not symbols:
        symbols = load_positions()
        if not symbols:
            print("positions.json 为空，请指定标的。用法: python3.12 agents/report_analyst.py AMD MRVL")
            sys.exit(1)
        print(f"未指定标的，使用持仓：{', '.join(symbols)}")

    if not CLAUDE_AVAILABLE:
        print("\n[错误] Claude API 不可用：")
        print("  1. 确认已安装 anthropic: pip install anthropic")
        print("  2. 确认已设置 ANTHROPIC_API_KEY 环境变量")
        print("  3. 继续生成（将跳过 AI 分析，仅输出原始数据摘要）...\n")

    print(f"生成深度分析报告：{', '.join(symbols)}")
    print(f"报告目录：{REPORTS_DIR}\n")

    results = {}
    max_workers = min(len(symbols), 3)  # 并行但限制 API 频率

    if len(symbols) == 1:
        # 单标的直接运行
        sym = symbols[0]
        try:
            path = generate_full_report(sym)
            results[sym] = ("OK", path)
        except Exception as e:
            results[sym] = ("FAIL", str(e))
            print(f"  [{sym}] 失败: {e}")
    else:
        # 多标的并行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(generate_full_report, sym): sym for sym in symbols}
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
