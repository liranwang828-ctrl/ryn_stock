"""
自动触发逻辑 — 非盘中时段自动运行 CIO 全量分析

触发条件（任一满足）：
- 用户明确讨论某只股票的买卖/仓位决策
- 问题包含具体价格或仓位信息
- 用户使用了 review_strategy() 相关触发词

不触发（全部满足时跳过）：
- 只询问价格/数据
- 闲聊提及股票名称
- 市场开盘时段（9:30-16:00 ET）
"""
import os, re, sys, subprocess
from datetime import datetime, timezone

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable

# 触发关键词（需要分析）
TRIGGER_PATTERNS = [
    r"能买吗", r"该买吗", r"值得买", r"入场", r"建仓",
    r"止损.*多少", r"该不该.*卖", r"能拿吗",
    r"T1|T2|T3", r"加仓", r"减仓", r"止盈",
    r"怎么看.*今天", r"今天.*机会",
    r"分析一下", r"帮我.*看看", r"评估",
]

# 不触发的情况
NO_TRIGGER_PATTERNS = [
    r"^现价.*多少", r"^股价.*多少",
    r"^[A-Z]{2,5}现在.*\?",
]


def should_trigger(question: str, symbols: list = None) -> bool:
    """判断是否应该自动触发 CIO 分析"""
    # 盘中不自动触发
    if _is_market_hours():
        return False

    # 没有股票代码不触发
    if not symbols:
        syms = _extract_symbols(question)
        if not syms:
            return False

    # 明确不触发的模式
    for pattern in NO_TRIGGER_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            return False

    # 触发模式
    for pattern in TRIGGER_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            return True

    return False


def auto_run_cio(symbol: str, question_type: str = "日内/短线交易",
                 phases: str = "0123") -> dict:
    """Run the full CIO analysis pipeline and return the execution status."""
    agents_dir = os.path.join(BASE, "agents")
    cio_script = os.path.join(agents_dir, "cio.py")

    print(f"[AutoTrigger] 非盘中时段，自动运行 CIO 分析: {symbol}")
    print(f"[AutoTrigger] 问题类型: {question_type}")

    try:
        result = subprocess.run(
            [PYTHON, cio_script, symbol,
             "--phases", phases,
             "--question-type", question_type],
            cwd=BASE,
            capture_output=False,  # 输出到控制台
            timeout=300,
        )
        return {
            "status":      "success" if result.returncode == 0 else "error",
            "returncode":  result.returncode,
            "symbol":      symbol,
            "question_type": question_type,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "symbol": symbol}
    except Exception as e:
        return {"status": "error", "error": str(e), "symbol": symbol}


def trigger_if_needed(question: str, symbols: list = None,
                      question_type: str = "日内/短线交易") -> str:
    """Check if auto-trigger conditions are met and run CIO analysis if so."""
    syms = symbols or _extract_symbols(question)

    if not should_trigger(question, syms):
        return ""  # 不需要触发，静默返回

    if not syms:
        return ""

    # 触发第一个股票的分析
    sym = syms[0]
    result = auto_run_cio(sym, question_type)

    if result["status"] == "success":
        return f"[AutoTrigger] ✅ 已完成 {sym} 的 CIO 全量分析"
    else:
        return f"[AutoTrigger] ⚠️ {sym} 分析失败: {result.get('status')}"


def _is_market_hours() -> bool:
    """判断当前是否在美股交易时段（9:30-16:00 ET）"""
    now_utc = datetime.now(timezone.utc)
    et_h = (now_utc.hour - 4) % 24
    et_m = now_utc.minute
    total_min = et_h * 60 + et_m
    return 9 * 60 + 30 <= total_min <= 16 * 60


def _extract_symbols(question: str) -> list:
    """从问题中提取股票代码"""
    # 支持中英文边界，使用更宽松的正则
    matches = re.findall(r'(?<![A-Z])([A-Z]{2,5})(?![A-Z])', question)
    stop_words = {"AI","ETF","US","OK","RS","T1","T2","T3","MA","RSI","ATR","VIX","SPY","QQQ","VWAP","ET","CIO","DD","DL","LL","ST"}
    return [m for m in matches if m not in stop_words]


if __name__ == "__main__":
    # 快速测试
    print("=== AutoTrigger 自检 ===")

    # 禁用盘中检查以便测试
    original_is_market_hours = _is_market_hours
    _is_market_hours = lambda: False

    test_cases = [
        ("MRVL今天能买吗", True),
        ("MRVL现在多少钱", False),
        ("MRVL T2该不该加仓", True),
        ("分析一下NVDA", True),
        ("该不该减仓NBIS", True),
    ]

    print("\n触发逻辑测试:")
    for q, expected in test_cases:
        result = should_trigger(q)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{q}' -> {result}")

    print("\n符号提取测试:")
    test_syms = [
        "MRVL今天能买吗",
        "MRVL NBIS SPY明天怎么看",
        "该不该减仓NBIS"
    ]
    for q in test_syms:
        syms = _extract_symbols(q)
        print(f"  '{q}' -> {syms}")

    print("\n市场时段检测:")
    print(f"  当前是否盘中: {original_is_market_hours()}")

    # 恢复原始函数
    _is_market_hours = original_is_market_hours
    print("\n✓ 自检完成")
