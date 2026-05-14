"""
entry_guard.py — 入场守卫
当用户报告买入/卖出时，显示入场核对卡片并记录交易。

公开接口：
  parse_trade_input(text)               → dict | None
  generate_entry_card(sym, price, shares, score=None, rs=None, wick_ok=True, date_str=None) → str
  record_trade(sym, action, price, shares, date_str) → None
  handle_trade_text(text, date_str)     → str   ← CLI/集成主入口

数据文件：
  读：~/stock_team/daily_plan_{date}.json（由 daily_plan.py 生成）
  写：~/stock_team/config/positions.json
  写：~/stock_team/knowledge/trading_history.jsonl
"""

import sys, os, re, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import atomic_write_json

BASE           = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSITIONS_PATH = os.path.join(BASE, "config", "positions.json")
HISTORY_PATH   = os.path.join(BASE, "knowledge", "trading_history.jsonl")

# ─── 从 daily_plan 导入，规避循环依赖只在函数内 import ────────────────
# （在 generate_entry_card 内部 import，便于测试 mock）

# 供测试 mock 替换的模块级引用
try:
    from agents.daily_plan import get_plan
except ImportError:
    get_plan = None  # 测试时由 mock 替换


# ════════════════════════════════════════════════════════════════════
# Layer 1: 自然语言解析
# ════════════════════════════════════════════════════════════════════

# 动作关键词映射
_ACTION_MAP = {
    "买了":  "buy",
    "卖了":  "sell",
    "止损了": "stop",
}

# 主解析正则（完整格式）：价格+数量，价格前可带可不带$
# group(1)=动作  group(2)=代码  group(3)=价格  group(4)=数量
_TRADE_RE_FULL = re.compile(
    r"^(买了|卖了|止损了)\s*([A-Za-z]+)"          # 动作 + 代码
    r"\s+\$?([\d]+(?:\.\d+)?)"                    # 必须有价格（$可选）
    r"(?:\s+([\d]+)股)?$",                         # 可选：数量+股
    re.UNICODE,
)

# 止损无参数格式：只有动作+代码
# group(1)=动作  group(2)=代码
_TRADE_RE_STOP_ONLY = re.compile(
    r"^(止损了)\s*([A-Za-z]+)\s*$",
    re.UNICODE,
)


def parse_trade_input(text: str) -> dict | None:
    """
    解析自然语言交易记录。

    支持格式（规格附录D）：
      "买了 MRVL $178 20股"
      "卖了 AAOI $213 10股"
      "止损了 MRVL $173.5 20股"
      "止损了 MRVL"               ← 无价格，price=None

    Args:
        text: 用户输入字符串

    Returns:
        dict  {"action": "buy"|"sell"|"stop",
               "symbol": str,
               "price":  float | None,
               "shares": int   | None}
        None  → 非交易格式，或解析失败
    """
    if not text:
        return None

    text = text.strip()

    # 先尝试完整格式（含价格）
    m = _TRADE_RE_FULL.match(text)
    if m:
        action_zh, symbol_raw, price_str, shares_str = m.groups()
        action = _ACTION_MAP[action_zh]
        symbol = symbol_raw.upper()
        price  = float(price_str)
        shares = int(shares_str) if shares_str else None
        return {
            "action": action,
            "symbol": symbol,
            "price":  price,
            "shares": shares,
        }

    # 再尝试止损无参数格式
    m2 = _TRADE_RE_STOP_ONLY.match(text)
    if m2:
        action_zh, symbol_raw = m2.groups()
        return {
            "action": "stop",
            "symbol": symbol_raw.upper(),
            "price":  None,
            "shares": None,
        }

    return None


# ════════════════════════════════════════════════════════════════════
# Layer 2: 入场核对卡片生成
# ════════════════════════════════════════════════════════════════════

def generate_entry_card(
    symbol: str,
    entry_price: float,
    shares: int,
    score: float = None,
    rs: float = None,
    wick_ok: bool = True,
    date_str: str = None,
) -> str:
    """
    生成入场核对卡片字符串（规格节点4格式）。

    从 daily_plan_{date}.json 读取该股票的预计划：
      - 场景/催化剂
      - t1_stop（直接显示，不重新计算）
      - t1_target1/t1_target2
      - t2_condition_b（路径B模板）

    T2路径A动态计算：entry_price × 1.005

    Args:
        symbol:      股票代码（大写）
        entry_price: 实际入场价
        shares:      入场股数
        score:       方法论评分（可选，传入则显示实际值）
        rs:          RS强度%（可选，传入则显示实际值）
        wick_ok:     影线是否正常（默认True）
        date_str:    日期 "YYYY-MM-DD"；None 则用今日 UTC

    Returns:
        格式化后的卡片字符串
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sym = symbol.upper()

    # 读取当日计划（允许测试通过 patch("agents.entry_guard.get_plan", ...) 替换）
    plan = get_plan(sym, date_str=date_str) if get_plan else None

    # ── 无预计划时的简版卡片 ────────────────────────────────────────
    if not plan:
        lines = [
            f"⚡ {sym} 入场核对",
            f"  入场：${entry_price}  数量：{shares}股",
            f"  ⚠️  无预计划：{sym} 不在今日 daily_plan 中",
            f"  提示：运行 `daily_plan.py add {sym}` 后重新触发",
        ]
        return "\n".join(lines)

    # ── 字段读取 ────────────────────────────────────────────────────
    scene      = plan.get("actual_scene") or plan.get("predicted_scene", "?")
    catalyst   = plan.get("catalyst") or "无催化剂记录"
    entry_hint = plan.get("t1_entry_hint", "")
    t1_stop    = plan.get("t1_stop", "?")
    t1_target1 = plan.get("t1_target1", "?")
    t1_target2 = plan.get("t1_target2", "?")
    atr        = plan.get("atr", "?")
    t2_b       = plan.get("t2_condition_b", "缩量回踩 + 守VWAP")

    # T2路径A：入场价 × 1.005
    t2_a_trigger = round(entry_price * 1.005, 2)

    # 风险计算
    if isinstance(t1_stop, (int, float)):
        risk_per_share = round(entry_price - t1_stop, 2)
        total_risk     = round(risk_per_share * shares, 2)
        risk_str = f"风险：${risk_per_share}/股 × {shares}股 = ${total_risk}"
    else:
        risk_str = "风险：无法计算（止损未知）"

    # ── 方法论核对区块 ───────────────────────────────────────────────
    if score is not None:
        score_ok  = "✅" if score >= 7.5 else "❌"
        score_cmp = "≥" if score >= 7.5 else "＜"
        score_line = f"  {score_ok} 评分 {score}/10 {score_cmp} 7.5"
    else:
        score_line = "  [需手动核对] 评分 ≥ 7.5"

    if rs is not None:
        rs_ok  = "✅" if rs >= 1.5 else "❌"
        rs_cmp = "≥" if rs >= 1.5 else "＜"
        rs_line = f"  {rs_ok} RS +{rs}% {rs_cmp} 1.5%"
    else:
        rs_line = "  [需手动核对] RS ≥ +1.5%"

    wick_status = "正常" if wick_ok else "有上影压力"
    wick_icon   = "✅" if wick_ok else "❌"
    wick_line   = f"  {wick_icon} 影线{wick_status}"

    methodology_block = (
        "方法论 #11 T1 核对：\n"
        f"{score_line}\n"
        f"{rs_line}\n"
        f"{wick_line}"
    )

    # ── 拼装卡片 ─────────────────────────────────────────────────────
    lines = [
        "─" * 53,
        f"⚡ {sym} 入场核对",
        f"当日计划：场景{scene}，{entry_hint}，催化剂{catalyst}",
        "",
        methodology_block,
        "",
        "【T1 参数（直接抄去 IBKR）】",
        f"  入场：${entry_price}  数量：{shares}股",
        f"  止损：${t1_stop}（ATR ${atr} × 0.3 + 反拥挤）",
        f"  {risk_str}",
        f"  目标1：${t1_target1}（减半仓）→ 止损上移至 ${entry_price}（保本）",
        f"  目标2：${t1_target2}（剩余出清）",
        "",
        "T2 触发条件（二选一）：",
        f"  路径A：价格 > ${t2_a_trigger} + 量比 > 0.85x",
        f"  路径B：{t2_b}",
        "─" * 53,
    ]
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# Layer 3: 持久化记录
# ════════════════════════════════════════════════════════════════════

def _load_positions() -> dict:
    """读取 positions.json；若不存在返回空骨架。原子写入保障数据一致性。"""
    path = os.path.join(BASE, "config", "positions.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"cash": 0, "positions": {}}


def _save_positions(data: dict) -> None:
    """原子写入 positions.json。"""
    path = os.path.join(BASE, "config", "positions.json")
    atomic_write_json(data, path, indent=2)


def _append_history(record: dict) -> None:
    """追加一条 JSON 记录到 trading_history.jsonl。"""
    path = os.path.join(BASE, "knowledge", "trading_history.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_trade(
    symbol: str,
    action: str,
    price: float,
    shares: int,
    date_str: str = None,
) -> None:
    """
    将交易记录写入 positions.json 和 trading_history.jsonl。

    positions.json 更新规则：
      buy  + 新仓位  → 直接写入
      buy  + 已有    → 加权平均成本，股数累加
      sell / stop    → 股数减少；归零时删除该仓位

    历史记录包含：ts/type/sym/price/shares/stop/target1/target2/scene/catalyst/date

    Args:
        symbol:   股票代码（大写）
        action:   "buy" | "sell" | "stop"
        price:    成交价；止损无价格时可传 None
        shares:   成交股数；止损无股数时可传 None
        date_str: 日期 "YYYY-MM-DD"；None 则用今日 UTC
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sym = symbol.upper()
    ts  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── 读取当日计划（用于历史记录字段，不阻断流程）────────────────
    plan = get_plan(sym, date_str=date_str) if get_plan else None

    # ── 更新 positions.json ─────────────────────────────────────────
    pos_data  = _load_positions()
    positions = pos_data.setdefault("positions", {})

    if action == "buy":
        if shares is not None and price is not None:
            if sym in positions:
                # 加权平均成本
                existing   = positions[sym]
                old_shares = existing.get("shares", 0)
                old_cost   = existing.get("cost", price)
                new_shares = old_shares + shares
                new_cost   = round((old_cost * old_shares + price * shares) / new_shares, 2)
                existing["shares"] = new_shares
                existing["cost"]   = new_cost
                existing["date"]   = date_str
            else:
                scene_label = (plan.get("actual_scene") or plan.get("predicted_scene", "?")) if plan else "?"
                positions[sym] = {
                    "cost":   price,
                    "shares": shares,
                    "date":   date_str,
                    "note":   f"由 entry_guard 自动记录，场景{scene_label}",
                }

    elif action in ("sell", "stop"):
        if sym in positions and shares is not None:
            remaining = positions[sym]["shares"] - shares
            if remaining <= 0:
                del positions[sym]
            else:
                positions[sym]["shares"] = remaining

    _save_positions(pos_data)

    # ── 追加 trading_history.jsonl ───────────────────────────────────
    history_record = {
        "ts":       ts,
        "type":     action,
        "sym":      sym,
        "price":    price,
        "shares":   shares,
        "stop":     plan.get("t1_stop")    if plan else None,
        "target1":  plan.get("t1_target1") if plan else None,
        "target2":  plan.get("t1_target2") if plan else None,
        "scene":    (plan.get("actual_scene") or plan.get("predicted_scene")) if plan else None,
        "catalyst": plan.get("catalyst")   if plan else None,
        "date":     date_str,
    }
    _append_history(history_record)


# ════════════════════════════════════════════════════════════════════
# 主入口：三层串联
# ════════════════════════════════════════════════════════════════════

def handle_trade_text(text: str, date_str: str = None) -> str:
    """
    处理自然语言交易记录的主入口（Task 4 集成串联）。

    流程：
      1. parse_trade_input(text)
         失败 → 返回格式提示
      2. generate_entry_card(symbol, price, shares, date_str)
      3. record_trade(symbol, action, price, shares, date_str)

    Args:
        text:     用户输入
        date_str: 日期；None 则用今日 UTC

    Returns:
        组合输出字符串（卡片 + 记录确认，或错误提示）
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Step 1: 解析
    parsed = parse_trade_input(text)
    if parsed is None:
        return (
            "⚠️  无法识别交易记录格式。\n"
            "请用格式：买了/卖了/止损了 代码 价格 数量\n"
            "示例：买了 MRVL $178 20股"
        )

    action = parsed["action"]
    symbol = parsed["symbol"]
    price  = parsed["price"]
    shares = parsed["shares"]

    # Step 2: 生成卡片（仅买入时显示完整核对卡片；卖出/止损显示简短确认）
    if action == "buy" and price is not None and shares is not None:
        card = generate_entry_card(symbol, entry_price=price, shares=shares,
                                   date_str=date_str)
    else:
        # 卖出/止损：简短确认行
        price_str  = f"${price}"  if price  is not None else "（价格未知）"
        shares_str = f"{shares}股" if shares is not None else "（数量未知）"
        action_zh  = {"buy": "买入", "sell": "卖出", "stop": "止损"}[action]
        card = f"⚡ {symbol} {action_zh} {price_str} {shares_str}"

    # Step 3: 记录
    record_trade(symbol, action=action, price=price, shares=shares,
                 date_str=date_str)

    # 组合输出
    result = card + f"\n\n✅ 已记录 {symbol} {action} 到 positions.json 和 trading_history.jsonl"
    return result


# ════════════════════════════════════════════════════════════════════
# CLI 入口
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "entry_guard — 入场守卫\n\n"
            "用法1（自然语言）：python entry_guard.py '买了 MRVL $178 20股'\n"
            "用法2（仅卡片）：  python entry_guard.py card MRVL 178 20\n"
            "用法3（仅记录）：  python entry_guard.py record MRVL buy 178 20"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="cmd")

    # 子命令：card — 仅显示卡片
    p_card = sub.add_parser("card", help="仅显示入场核对卡片（不记录）")
    p_card.add_argument("symbol",      help="股票代码，如 MRVL")
    p_card.add_argument("entry_price", type=float, help="入场价，如 178.0")
    p_card.add_argument("shares",      type=int,   help="股数，如 20")
    p_card.add_argument("--date",      default=None, help="日期 YYYY-MM-DD（默认今日）")

    # 子命令：record — 仅记录
    p_rec = sub.add_parser("record", help="仅记录交易（不显示卡片）")
    p_rec.add_argument("symbol", help="股票代码")
    p_rec.add_argument("action", choices=["buy", "sell", "stop"], help="动作")
    p_rec.add_argument("price",  type=float, nargs="?", default=None, help="价格")
    p_rec.add_argument("shares", type=int,   nargs="?", default=None, help="股数")
    p_rec.add_argument("--date", default=None)

    args = parser.parse_args()

    if args.cmd == "card":
        print(generate_entry_card(args.symbol, args.entry_price, args.shares,
                                  date_str=args.date))

    elif args.cmd == "record":
        record_trade(args.symbol, action=args.action, price=args.price,
                     shares=args.shares, date_str=args.date)
        print(f"✅ 已记录：{args.symbol} {args.action} ${args.price} {args.shares}股")

    else:
        # 无子命令：把所有位置参数拼成自然语言
        parser2 = argparse.ArgumentParser(add_help=False)
        parser2.add_argument("text", nargs="+")
        args2, _ = parser2.parse_known_args()
        text = " ".join(args2.text)
        print(handle_trade_text(text))
