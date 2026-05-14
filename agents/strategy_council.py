"""
策略评审委员会 — 大师团队评审交易规则，输出改进建议并可自动写入方法论
触发场景：用户修改T2条件、止损原则、仓位管理等交易规则
"""
import os, re
from datetime import datetime, timezone

BASE             = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METHODOLOGY_PATH = os.path.join(BASE, "knowledge", "trading_methodology.md")

STRATEGY_TYPE_MASTERS = {
    "入场条件":  ["minervini", "livermore", "marks"],
    "加仓策略":  ["marks", "taleb", "minervini"],
    "止损原则":  ["minervini", "livermore", "taleb"],
    "退出策略":  ["marks", "livermore", "soros"],
    "仓位管理":  ["marks", "taleb", "druckenmiller"],
    "风险管理":  ["taleb", "marks", "minervini"],
    "选股原则":  ["druckenmiller", "lynch", "minervini"],
    "持仓管理":  ["marks", "taleb", "minervini"],
}

STRATEGY_KEYWORDS = {
    "加仓策略":  [r"T2", r"T3", r"加仓", r"追加"],
    "止损原则":  [r"止损", r"stop", r"ATR.*止", r"止.*ATR"],
    "退出策略":  [r"退出", r"出场", r"卖出", r"目标价"],
    "仓位管理":  [r"仓位", r"比例", r"多大.*仓"],
    "风险管理":  [r"风险", r"R:R", r"盈亏比"],
    "选股原则":  [r"选股", r"筛选", r"标的"],
    "持仓管理":  [r"持仓", r"拿着", r"持有"],
    "入场条件":  [r"入场", r"买入", r"建仓"],
}


def parse_strategy(text: str) -> dict:
    strategy_type = "入场条件"
    for stype, patterns in STRATEGY_KEYWORDS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                strategy_type = stype
                break
        if strategy_type != "入场条件":
            break

    conditions = []
    for sep in ["+", "且", "和", "，", ","]:
        if sep in text:
            conditions = [p.strip() for p in text.split(sep) if len(p.strip()) > 2]
            break

    return {
        "raw_text":        text,
        "strategy_type":   strategy_type,
        "core_conditions": conditions or [text],
        "parsed_at":       datetime.now(timezone.utc).isoformat(),
    }


def _master_evaluate(master_name: str, strategy: dict) -> dict:
    text  = strategy["raw_text"]
    conds = strategy["core_conditions"]
    support_points, concerns, suggestion = [], [], ""

    if master_name == "minervini":
        if re.search(r"量缩|缩量", text):
            support_points.append("量缩条件正确——缩量回踩是健康的洗盘信号")
        if re.search(r"2\.5%|3%", text):
            concerns.append("回踩幅度上限过宽，在高ATR股票里可能已触及低点")
            suggestion = "建议回踩上限 = min(1.5%, 0.3×ATR)，让止损参数自动适配"
        if re.search(r"VWAP|vwap", text):
            support_points.append("VWAP守住是正确的——VWAP是机构成本参考")
        if not support_points and not concerns:
            support_points.append("条件逻辑清晰，有可执行的数字标准")

    elif master_name == "marks":
        if re.search(r"T2|T3", text):
            concerns.append("多仓位同时触发T2时，总风险敞口是否超标？")
            suggestion = "建议加入：当日已触发T2的标的>1只时，后续T2自动降档为半仓"
        if re.search(r"止损|stop", text):
            support_points.append("有明确止损，保护了永久性亏损的风险")
        if re.search(r"整数|\.0%", text):
            concerns.append("整数位止损容易被机器猎杀，需要加反拥挤噪声")
        if not support_points and not concerns:
            support_points.append("风险控制框架合理")

    elif master_name == "taleb":
        if re.search(r"时间止损|72小时|3天", text):
            support_points.append("时间止损正确——动量策略里等待本身就是风险")
        if re.search(r"固定.*%|百分比止损", text):
            concerns.append("固定百分比止损忽视了波动率——ATR×N比固定比例更合理")
            suggestion = "止损应是 ATR×N 而非固定百分比，让波动率决定止损宽度"
        if not re.search(r"极端|最坏|同时", text):
            concerns.append("策略中未考虑极端情景——若同时多个仓位止损，总损失是多少？")
        if not support_points and not concerns:
            support_points.append("尾部风险控制有考虑")

    elif master_name == "livermore":
        if re.search(r"时间.*止损|时间.*限制", text):
            support_points.append("时间止损是动量策略的生命线")
        if re.search(r"等待|观察.*多", text):
            concerns.append("过多等待条件会错过最好的入场——动量不等人")
        if not support_points and not concerns:
            support_points.append("基本执行逻辑合理")

    else:
        support_points.append(f"从{master_name}视角来看，策略框架基本合理")
        if len(conds) > 4:
            concerns.append("条件过多可能导致信号频率过低，实战中难以执行")

    resp_type = "A" if concerns and suggestion else "B" if support_points else "C"
    return {
        "master":         master_name,
        "support_points": support_points,
        "concerns":       concerns,
        "suggestion":     suggestion,
        "response_type":  resp_type,
    }


def evaluate_strategy(strategy: dict) -> dict:
    stype   = strategy["strategy_type"]
    masters = STRATEGY_TYPE_MASTERS.get(stype, ["minervini", "marks", "taleb"])

    master_reviews = {m: _master_evaluate(m, strategy) for m in masters}

    kept, improved, pending = [], [], []
    for m, r in master_reviews.items():
        for sp in r["support_points"]:
            if sp not in kept:
                kept.append(sp)
        if r["suggestion"]:
            improved.append({"suggestion": r["suggestion"], "by": m,
                             "concern": r["concerns"][0] if r["concerns"] else ""})
        elif r["concerns"]:
            pending.append({"concern": r["concerns"][0], "by": m})

    return {
        "strategy":       strategy,
        "master_reviews": master_reviews,
        "kept":           kept,
        "improved":       improved,
        "pending":        pending,
        "reviewed_at":    datetime.now(timezone.utc).isoformat(),
    }


def format_review_output(review: dict, title: str = "") -> str:
    lines = [
        f"## 策略评审：{title or review['strategy']['strategy_type']}",
        f"原始陈述：{review['strategy']['raw_text']}", "",
        "### 各大师意见",
    ]
    for master, r in review.get("master_reviews", {}).items():
        lines.append(f"\n**{master}**")
        for sp in r.get("support_points", []):
            lines.append(f"  ✅ {sp}")
        for c in r.get("concerns", []):
            lines.append(f"  ⚠️ {c}")
        if r.get("suggestion"):
            lines.append(f"  💡 建议：{r['suggestion']}")

    lines += ["", "### 综合结论", "", "**保留（有共识）：**"]
    for item in review.get("kept", []):
        lines.append(f"- {item}")

    lines.append("\n**改进建议（有共识）：**")
    for item in review.get("improved", []):
        lines.append(f"- [{item['by']}] {item['suggestion']}")

    lines.append("\n**待议（需进一步确认）：**")
    for item in review.get("pending", []):
        lines.append(f"- [{item['by']}] {item['concern']}")

    return "\n".join(lines)


def confirm_and_update(review: dict, user_confirmed_improvements: list = None,
                       rule_number: int = None) -> str:
    strategy    = review["strategy"]
    improvements = user_confirmed_improvements or [i["suggestion"] for i in review.get("improved", [])]
    now          = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stype        = strategy["strategy_type"]
    num_str      = f"#{rule_number}" if rule_number else "#NEW"

    rule_text = f"""

---

## 方法论 {num_str}：{stype}（策略评审版）
**来源**：用户策略 + 大师评审（{now}）

**原始策略：**
{strategy["raw_text"]}

**经评审后的改进：**
"""
    for imp in improvements:
        rule_text += f"- {imp}\n"

    masters_str = " ".join(review.get("master_reviews", {}).keys())
    rule_text  += f"\n**参与评审大师：** {masters_str}\n"

    with open(METHODOLOGY_PATH, "a", encoding="utf-8") as f:
        f.write(rule_text)

    return f"✅ 策略已写入 trading_methodology.md（{len(improvements)} 条改进建议采纳）"


def review_strategy(text: str, auto_update: bool = False) -> str:
    """一键评审入口"""
    strategy = parse_strategy(text)
    review   = evaluate_strategy(strategy)
    output   = format_review_output(review, f"{strategy['strategy_type']}评审")
    if auto_update and review.get("improved"):
        output += f"\n\n{confirm_and_update(review)}"
    return output
