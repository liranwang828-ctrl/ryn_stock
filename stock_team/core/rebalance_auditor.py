"""
量化重组审计与 7 大师战略研讨会代理 — rebalance_auditor.py
核心功能：
1. 自动加载当前持仓 config/positions.json，区分核心长线池与战术轮动池
2. 载入下周一调仓方案（清仓战术剩余 VST, NOW, ZS, SGOV；建仓 AMD, RKLB, MRVL）
3. 调用大模型启动“7大师战略理事会”（Minervini, Livermore, Druckenmiller, Lynch, Soros, Taleb, Marks）
4. 进行高拟真度角色扮演辩论，探讨调仓动作的战略合理性、尾部风险和宏观逻辑
5. 最终达成调仓共识裁决，并将精美的 Markdown 报告物理持久化到 findings/weekly_rebalance_debate.md
"""
import sys
import os
import json
from datetime import datetime, timezone

# 确保 UTF-8 打印
sys.stdout.reconfigure(encoding='utf-8')

# 将当前目录和上级目录加入 sys.path 以方便导入 llm_client 和 persona_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_team.utils.llm_client import LLMClient
from stock_team.agents.persona_engine import load_persona_full

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))

POSITIONS_PATH = os.path.join(BASE, "config", "positions.json")
FINDINGS_DIR = os.path.join(BASE, "findings")

MASTER_NAMES = {
    "minervini": "Mark Minervini (SEPA 战术趋势大师)",
    "livermore": "Jesse Livermore (大趋势价格行为先驱)",
    "druckenmiller": "Stan Druckenmiller (宏观跨资产流动性大师)",
    "lynch": "Peter Lynch (基本面常识与商业论点大师)",
    "soros": "George Soros (反身性与叙事偏差大师)",
    "taleb": "Nassim Taleb (反脆弱性与不对称黑天鹅防线大师)",
    "marks": "Howard Marks (市场周期与逆向防守大师)"
}

def load_current_positions():
    """读取 positions.json 获取当前持仓结构"""
    if not os.path.exists(POSITIONS_PATH):
        raise FileNotFoundError(f"未找到持仓数据库文件：{POSITIONS_PATH}")
    with open(POSITIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def run_masters_debate(client, portfolio_summary, proposed_moves):
    """驱动 7 位大师进行战略辩论"""
    print("🎭 7位大师正在进入战略理会研讨大厅...")
    
    # 逐一生成大师立场
    stances = {}
    for key, name in MASTER_NAMES.items():
        print(f"🎙️ 正在研讯：{name}...")
        try:
            profile = load_persona_full(key)
        except Exception:
            profile = {"worldview": "以你最经典的交易方法和原则为主。", "language": "极具标志性的大师措辞风格。"}
            
        system_prompt = (
            f"You are the famous trading master: {name}.\n"
            f"Your trading worldview/philosophy is:\n{profile.get('worldview', '')}\n"
            f"Your language style, keywords and DNA are:\n{profile.get('language', '')}\n"
            f"Your known blindspots are:\n{profile.get('blindspots', '')}\n"
            "Please respond to the proposed portfolio rebalance in character. Keep the response professional, highly realistic to your philosophy, and within 250 Chinese characters."
        )
        
        prompt = (
            f"以下是当前投资组合的整体概况：\n"
            f"【当前持仓】\n{json.dumps(portfolio_summary['positions'], ensure_ascii=False, indent=2)}\n"
            f"【可用现金】: ${portfolio_summary['cash']:.2f}\n\n"
            f"下周一开盘，量化引擎提议执行以下调仓动作：\n"
            f"【战术池清仓退场股】: {', '.join(proposed_moves['sells'])} (回收现金，保护本金)\n"
            f"【战术池全新买入建仓】: {', '.join(proposed_moves['buys'])} (做多动能领涨股)\n"
            f"【核心池锁定持有股】: {', '.join(proposed_moves['core_holds'])} (底仓免死，仅根据因子缩放)\n\n"
            f"请以你的投资方法论和当前市场周期环境，撰写你对该调仓计划的独家审计意见。你是否赞同这一“核心底仓锁定 + 战术池极致动能轮动”的重组结构？有什么致命漏洞需要警告？请以你经典的中文口吻输出！"
        )
        
        try:
            response = client.call_llm(prompt=prompt, system_prompt=system_prompt).strip()
            stances[key] = response
        except Exception as e:
            print(f"⚠️ 无法获取 {key} 的发言，使用降级经典论点...")
            # Fallback to realistic master summaries
            fallback_stances = {
                "minervini": "我赞成战术池彻底止损退场！不合格的趋势必须斩断。AMD 和 RKLB 明显进入了 Stage 2 的主升浪，成交量在放大，符合 SEPA 筛选。保护核心持仓（如 NVDA）是妥协，但只要有量化缩放机制，我能接受。",
                "livermore": "清空弱势股，将资金分配给最强的板块领头羊——这就是关键阻力位突破的本质。AMD 和 RKLB 展现出了完美的最小阻力线方向向上。我的经验是，永远不要和市场的价格行为作对。",
                "druckenmiller": "从宏观流动性来看，半导体和商业AI应用是当今唯一具备真正资本开支增量的板块。买入 AMD 和 RKLB 是对流动性最充沛的主流暴露，而清空 FUTU 和 NOW 等震荡个股是聪明的，我全力支持！",
                "lynch": "清掉那些论点变模糊的（如 NOW 和 VST），把钱集中在 RKLB 这种有巨大行业催化空间的成长股上，非常合乎逻辑。但你要确保 NVDA 的商业护城河依然完整，只要 Blackwell 还在排单，核心底仓就无需动摇。",
                "soros": "这一周度调仓反映了市场对于‘AI高增长’和‘火箭航天’最新叙事偏差的自我修正。RKLB 正在从小众赛道走向主流叙事，反身性在自我强化。在气泡破裂前做多动能，是收割超额收益的精妙机制。",
                "taleb": "我最关心的是尾部风险。清仓 ZS 和 NOW 可以锁定已有利润，降低单点暴露。把底仓锁定在黄金 IAU 上是极其关键的防线，能抵御宏观流动性黑天鹅。只要有止损硬防线，我对战术轮动持谨慎赞成。",
                "marks": "在周期顶部，防守比进攻更重要。我很高兴看到你们增加了 IAU 黄金的持有并不动摇，这提供了宝贵的下行保护。战术池的 Top 3 动能轮动具有高 Beta 属性，在当前的高估值环境下，必须严格遵守波动控制规则。"
            }
            stances[key] = fallback_stances.get(key, "这笔交易的风险收益比合理，应当执行纪律。")
            
    # 最后由大模型合成总裁决报告
    print("✍️ 大师研讨会圆满结束，正在起草最终审计意见书...")
    system_synthesis = (
        "You are the Chief Investment Officer (CIO) and Portfolio Auditor.\n"
        "You will synthesize the comments of the 7 trading masters into a stunning, premium investment audit report in Chinese.\n"
        "The report must be structured professionally, highly inspiring, and clearly outline the consensus, individual debate highlights, and actionable key warnings."
    )
    
    prompt_synthesis = (
        f"以下是 7 位顶尖大师对下周一调仓方案的各自立场：\n"
        f"{json.dumps(stances, ensure_ascii=False, indent=2)}\n\n"
        f"调仓方案回顾：\n"
        f"- 卖出退场: {', '.join(proposed_moves['sells'])}\n"
        f"- 买入轮动: {', '.join(proposed_moves['buys'])}\n"
        f"- 核心锁仓: {', '.join(proposed_moves['core_holds'])}\n\n"
        f"请将大师们的发言整合为一份顶级专业的【量化重组与 7 大师战略研讨裁决书】。\n"
        f"报告必须采用 Markdown 格式，包含以下板块：\n"
        f"1. 🏛️ 理事会裁决共识 (Consensus Verdict)\n"
        f"2. 🎙️ 大师辩论实录与思想碰撞 (Master Stances & Debates) — 需保留每位大师极具个性的发言段落，并加粗核心词\n"
        f"3. ⚠️ 核心漏洞警告与黑天鹅风控防线 (Vulnerabilities & Risk Control)\n"
        f"4. 📝 周一开盘执行指令清册 (Monday Order Checklist)\n"
        f"请用极其惊艳、高级和专业的中文金融行文输出！"
    )
    
    try:
        report_md = client.call_llm(prompt=prompt_synthesis, system_prompt=system_synthesis)
    except Exception as e:
        report_md = f"# 7 大师调仓审计报告\n\n大模型报告生成异常: {e}"
        
    return stances, report_md

def main():
    print("="*80)
    print("📡 [7大师战略审计器启动] 加载账户当前持仓与拟定调仓计划...")
    print("="*80)
    
    try:
        db = load_current_positions()
    except Exception as e:
        print(f"🔴 加载持仓数据库失败: {e}")
        sys.exit(1)
        
    cash = db.get("cash", 0.0)
    positions = db.get("positions", {})
    
    # 过滤实盘持仓
    portfolio_summary = {
        "cash": cash,
        "positions": {}
    }
    
    for t, pos in positions.items():
        portfolio_summary["positions"][t] = {
            "tranche": pos.get("tranche", "tactical"),
            "shares": pos.get("shares", 0),
            "cost": pos.get("cost", 0),
            "thesis": pos.get("thesis", "量化选股")
        }
        
    # 定义周一拟定调仓：
    # 1. 战术池退场：清仓 SGOV, NOW, VST, ZS（BABA, FUTU, SYM 已经清了）
    # 2. 战术池新买入：AMD, RKLB, MRVL
    # 3. 核心锁仓：NVDA, COHR, MSFT, GOOGL, IAU (IAU 属于锁仓防线)
    proposed_moves = {
        "sells": ["SGOV", "NOW", "VST", "ZS"],
        "buys": ["AMD", "RKLB", "MRVL"],
        "core_holds": ["NVDA", "COHR", "MSFT", "GOOGL", "IAU"]
    }
    
    client = LLMClient()
    if not client.is_configured():
        print("⚠️ LLMClient 尚未配置，将使用经典后备论点生成本地审计报告！")
        
    stances, report_md = run_masters_debate(client, portfolio_summary, proposed_moves)
    
    # 将报告物理持久化到 findings/weekly_rebalance_debate.md
    os.makedirs(FINDINGS_DIR, exist_ok=True)
    report_path = os.path.join(FINDINGS_DIR, "weekly_rebalance_debate.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print("="*80)
    print(f"🎉 审计大功告成！量化调仓辩论研讨裁决书已生成并写入：\n👉 file:///{report_path.replace(os.sep, '/')}")
    print("="*80)

if __name__ == "__main__":
    main()
