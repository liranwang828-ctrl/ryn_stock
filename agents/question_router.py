"""问题类型分类器 + 主角大师分配"""
import re

QUESTION_TYPE_MASTERS = {
    "日内/短线交易":    {"primary": ["minervini","livermore","soros"],   "jury": ["marks"]},
    "催化剂分析":       {"primary": ["druckenmiller","soros"],            "jury": ["marks"]},
    "板块轮动":         {"primary": ["druckenmiller","lynch"],            "jury": ["marks"]},
    "比较分析":         {"primary": ["minervini","druckenmiller","marks","taleb","soros","livermore","lynch"], "jury": []},
    "持仓加仓(T2/T3)": {"primary": ["marks","taleb","minervini"],        "jury": ["druckenmiller"]},
    "止损/减仓执行":    {"primary": ["minervini","livermore"],            "jury": ["marks","taleb"]},
    "风险评估":         {"primary": ["taleb","marks"],                    "jury": ["minervini"]},
    "中线成长股":       {"primary": ["lynch","druckenmiller"],            "jury": ["marks","taleb"]},
}

QUESTION_PATTERNS = {
    "比较分析":         [r"vs\b", r"对比", r"哪个.*好", r"哪个.*值得", r"比较"],
    "持仓加仓(T2/T3)": [r"T2", r"T3", r"加仓"],
    "止损/减仓执行":    [r"止损", r"减仓", r"出场", r"卖出", r"清仓"],
    "风险评估":         [r"风险", r"危险", r"脆弱"],
    "催化剂分析":       [r"财报", r"催化", r"新闻.*影响", r"事件"],
    "板块轮动":         [r"板块", r"行业", r"轮动"],
    "中线成长股":       [r"中线", r"长线", r"几周", r"几个月"],
    "日内/短线交易":    [r"今天", r"今日", r"盘中", r"日内", r"短线", r"能买吗", r"入场"],
}

def classify_question(question: str, symbols: list = None) -> dict:
    """Classify a user question into a type and assign primary/jury masters."""
    symbols = symbols or _extract_symbols(question)
    if symbols and len(symbols) >= 2:
        q_type = "比较分析"
    else:
        q_type = "日内/短线交易"
        for qtype, patterns in QUESTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question, re.IGNORECASE):
                    q_type = qtype
                    break
            if q_type != "日内/短线交易":
                break

    cfg = QUESTION_TYPE_MASTERS.get(q_type, QUESTION_TYPE_MASTERS["日内/短线交易"])
    return {"type": q_type, "symbols": symbols or [],
            "primary_masters": cfg["primary"], "jury_masters": cfg["jury"]}

def get_primary_masters(question_type: str) -> list:
    """Return the list of primary master names for a given question type."""
    cfg = QUESTION_TYPE_MASTERS.get(question_type, QUESTION_TYPE_MASTERS["日内/短线交易"])
    return cfg["primary"]

def _extract_symbols(question: str) -> list:
    """Extract stock ticker symbols from a question string."""
    matches = re.findall(r'\b([A-Z]{2,5})\b', question)
    stop_words = {"AI","ETF","US","OK","RS","T1","T2","T3","MA","RSI","ATR","VIX","SPY","QQQ","VWAP"}
    return [m for m in matches if m not in stop_words]
