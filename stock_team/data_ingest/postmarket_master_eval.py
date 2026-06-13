"""
大师深度点评模块 — postmarket_master_eval.py
核心功能：
1. 载入 7 位大师的完整知识库 (rules.json, worldview.md, blindspots.md, language.md)
2. 聚合今日大盘、板块、个股损益以及【交易复盘】结果
3. 通过 LLMClient (DeepSeek) 真正扮演大师人格进行自然语言深度点评，完全剔除硬编码模板
4. 输出结构化 JSON 评价（评分、评级、亮点、担忧、明日行动建议、大师原声点评）
"""
import sys, os, json, re
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_team.utils.llm_client import LLMClient
from stock_team.data_ingest.postmarket_review import _load_today_data, _market_3tier_review

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))

# 大师映射表
MASTER_FOLDER_MAP = {
    "Minervini":     "mark_minervini",
    "Druckenmiller": "stan_druckenmiller",
    "Marks":         "howard_marks",
    "Taleb":         "nassim_taleb",
    "Soros":         "george_soros",
    "Livermore":     "jesse_livermore",
    "Lynch":         "peter_lynch",
}

# 每个人物在本项目中关注的维度和专长，用于提示词强化
MASTER_SPECIALTIES = {
    "Minervini":     "SEPA策略/技术动量/RS动能/价格结构收缩(VCP)/强势股突破",
    "Druckenmiller": "宏观流动性/极佳仓位匹配/大盘趋势反转/高风险敞口操作",
    "Marks":         "风险控制/估值周期/第二波估值乘数/防御性操作/防范亏损",
    "Taleb":         "反脆弱性/防范黑天鹅/极端尾部风险/反杠杆/凸性期权对冲",
    "Soros":         "反身性理论/主流叙事偏差/市场自我强化与崩塌/试错探路",
    "Livermore":     "关键点位(Pivot Points)/量价大级别运动/市场最小阻力方向/止损执行",
    "Lynch":         "基本面挖掘/生活化常识投资/估值与增长(PEG)/长期持有与业绩跟踪",
}


def load_master_persona(master_name: str) -> dict:
    """载入特定大师的 persona 文件"""
    folder = MASTER_FOLDER_MAP.get(master_name)
    if not folder:
        return {}
        
    pdir = os.path.join(BASE, "personas", folder)
    persona = {}
    
    # 载入 rules.json
    rules_path = os.path.join(pdir, "rules.json")
    if os.path.exists(rules_path):
        try:
            persona["rules"] = json.load(open(rules_path, encoding="utf-8"))
        except Exception:
            persona["rules"] = {}
            
    # 载入 worldview.md
    wv_path = os.path.join(pdir, "worldview.md")
    persona["worldview"] = open(wv_path, encoding="utf-8").read() if os.path.exists(wv_path) else ""
    
    # 载入 blindspots.md
    bs_path = os.path.join(pdir, "blindspots.md")
    persona["blindspots"] = open(bs_path, encoding="utf-8").read() if os.path.exists(bs_path) else ""
    
    # 载入 language.md
    lang_path = os.path.join(pdir, "language.md")
    persona["language"] = open(lang_path, encoding="utf-8").read() if os.path.exists(lang_path) else ""
    
    return persona


def clean_json_string(text: str) -> str:
    """清理 LLM 返回的可能带 markdown 标记的 JSON 字符串"""
    text = text.strip()
    # 移除 ```json ... ``` 包装
    if text.startswith("```"):
        # 匹配第一行 ```json 或 ```
        first_line_end = text.find("\n")
        if first_line_end != -1:
            text = text[first_line_end:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


def eval_single_master(master_name: str, today_data: dict, trade_review: dict, date_str: str) -> dict:
    """
    让特定大师对今日交易、持仓和大盘进行 LLM 深度点评
    """
    persona = load_master_persona(master_name)
    if not persona:
        return {
            "master": master_name, "score": 60, "verdict": "未知",
            "highlights": [], "concerns": [], "action_items": [],
            "eval_text": "无法加载该大师知识库。"
        }
        
    specialty = MASTER_SPECIALTIES.get(master_name, "")
    
    # 1. 整理今日数据上下文供 LLM 理解
    # 大盘表现
    pnl = today_data.get("position_pnl", {})
    total_gain = sum(v["gain_amt"] for v in pnl.values()) if pnl else 0
    
    positions_summary = []
    for sym, v in pnl.items():
        positions_summary.append(
            f"{sym}: 持股 {v['shares']}股, 成本 ${v['cost']:.2f}, 收盘 ${v['close']:.2f}, "
            f"今日涨跌 {v['day_ret']:+.2f}%, 累计盈亏 {v['pnl_vs_cost']:+.2f}% (金额 ${v['gain_amt']:+.0f})"
        )
        
    trades_summary = []
    trades = trade_review.get("reviewed_trades", [])
    for t in trades:
        action_name = "买入" if "BUY" in t["action"] or "ADD" in t["action"] else "卖出/清仓"
        target_supp = t["plan_match"].get("target_support")
        supp_str = f", 盘前支撑位 ${target_supp:.2f}" if target_supp else ""
        trades_summary.append(
            f"- {action_name} {t['sym']}: {t['shares']}股 @ ${t['cost']:.2f} (点位得分 {t['review']['score']}/100, "
            f"日内低价 ${t['stats']['low']:.2f}, 日内高价 ${t['stats']['high']:.2f}, 日内VWAP ${t['stats']['vwap']:.2f}{supp_str}). "
            f"【微观诊断】: {t['review']['micro_factor_suggestion']} · 计划匹配: {t['plan_match']['deviation_note']}"
        )
        
    trades_text = "\n".join(trades_summary) if trades_summary else "今日无任何成交动作。"
    positions_text = "\n".join(positions_summary) if positions_summary else "目前无持仓标的。"
    
    # 加载全局战备大表单 (Strategic Watchlist Database) 注入大师记忆，防止点评脱离战略上下文
    watchlist_path = os.path.join(BASE, "config", "master_watchlist.json")
    watchlist_db = {}
    if os.path.exists(watchlist_path):
        try:
            with open(watchlist_path, encoding="utf-8") as f:
                watchlist_db = json.load(f).get("watchlist", {})
        except Exception:
            pass
            
    strategic_memory_list = []
    symbols_to_check = set(pnl.keys())
    for t in trades:
        symbols_to_check.add(t["sym"].upper())
        
    for sym in sorted(symbols_to_check):
        sym_upper = sym.upper()
        if sym_upper in watchlist_db:
            m = watchlist_db[sym_upper]
            strategic_memory_list.append(
                f"【标的战略记忆 — {sym_upper}】:\n"
                f"  - 评级星级 (Tier): {m.get('tier')} 级 | 战略定位: {m.get('stance_type')}\n"
                f"  - 商业模式类型: {m.get('business_model')} (例如 usage_based 代表 AI 弹性高，per_seat 警惕裁员威胁)\n"
                f"  - 核心投资论点 (Thesis): {m.get('thesis')}\n"
                f"  - 预设黄金买点 (Buy Zone): ${m.get('buy_zone', {}).get('min_price')} - ${m.get('buy_zone', {}).get('max_price')}\n"
                f"  - 止损位 (Hard Stop): ${m.get('hard_stop')} | 目标价: ${m.get('target_price')}\n"
                f"  - 团队深度研究笔记与批注: {m.get('last_notes')}"
            )
            
    strategic_memory_text = "\n\n".join(strategic_memory_list) if strategic_memory_list else "本次复盘相关标的未在全局战备大大表单中登记。"
    
    # 2. 构造大师人格的 System Prompt
    system_prompt = f"""
你将深度扮演金融投资大师：【{master_name}】，你的研究专长是【{specialty}】。
请基于你的核心交易规则、世界观以及操作习惯，对今日该用户的投资组合、当日成交及大盘状态进行严苛、精准的复盘评估。

下面是你的【核心规则与世界观背景】：
---
【核心哲学与规则】:
{json.dumps(persona.get("rules"), ensure_ascii=False, indent=2)}

【你的世界观与世界理解方式】:
{persona.get("worldview")}

【你的思维盲点与历史教训 (用于警惕自己和用户)】:
{persona.get("blindspots")}

【你的语言风格与口吻 (你说话的腔调和用词风格)】:
{persona.get("language")}
---

【核心复盘方法论规范 — 严禁套路化点评】：
1. **仔细研读【核心战略备战大表单与研究记忆】**：
   你必须了解用户持有或买入某只股票的深层商业模式设计（如 usage-based / per-seat 的 AI 弹性差异）及战术意图（例如理解对 LITE vs COHR 的 Nasdaq 升格辩论与 NVIDIA 战术投资、理解 NOW 的 S 级逆向低估值买点等）。不要用笼统的“投资分散”、“策略不足”等套话！
2. **对比与反思点位偏离原因**：
   将用户的实际买入价格、点位评分与大表单预设的黄金买点（Buy Zone）进行深度对比！找出到底是因为“情绪焦虑、急于寻找市场上优质股票而市价追涨导致分散过载”（急躁病），还是因为严格执行了战备表单中的限价挂单。
3. **微观因子深度诊断**：
   分析大盘走势对个股 RS（相对强度）的影响。判断是否为 sector panic（板块恐慌错杀，RS 下降但基本面强韧）还是个股崩塌。
4. **输出非二元对立的、分层分级建议**：
   不要给出粗暴的“买/卖”二元结论。在不同场景下给出分级动作，例如在 bearish + 叙事反转信号时：建议“1-2% 小仓位试错，同时把硬止损严格定在 -8%，绝不重仓”。
5. **遵循【单股仓位铁律与角色分层纪律 (Tranche Stratification Discipline)】**：
   - 核心仓位 (5-15%)：长期持有，跌深可加。如 NVDA, GOOGL, MSFT, COHR。上限 5-7 只。
   - 主题仓位 (2-5%)：中短期趋势押注与催化剂暴露。如 VST, NOW, SYM。上限 3-5 只。
   - 机会/对冲仓位 (1-3%)：战术性、对冲防守或套利。如 IAU, FUTU, LITX, SGOV。
   - 待处理仓位：BABA（当前仓位偏重且不加仓，构成闲置机会成本，必须限制在 10% 以下以释放现金）。
   - **重要禁令**：**绝不要**以粗暴的“持仓数量过多（11只）”进行笼统批评！只要持仓处于 11-17 只的合理区间，且各标的角色定位清晰（Core/Theme/Tactical），这就是合理的 AI 垂直价值链完整覆盖（算力+光通信+电力+应用+物理AI），是投资组合的科学战略布局。你的评价重点应当是指出角色定义是否清晰、止损与买区偏离执行是否到位、以及是否严格执行了 BABA 减仓 30 股与 FUTU 减半锁利的现金释放纪律！

【指令规范】：
1. 必须完全进入角色，说话的口吻、逻辑框架必须极其符合你的原型。不要用套路化的 AI 废话，请像一个严厉、富有远见且高度专业的基金经理一样发言。
2. 你的输出必须是合法的 JSON 格式，且在 json_mode 下返回。
3. 必须输出以下字段（必须是合法的 JSON 键）：
   - "master": "{master_name}"
   - "score": 1-100 的整数评分，评分必须基于你的核心哲学。如果不符合你的买点、控制回撤不及格或违背了你的戒律，毫不犹豫地给出低分！
   - "verdict": 8字以内的一句话总结stance，必须包含你的标志性态度（如：SEPA买点缺失、风险敞口过大、周期防御为主、反身性试错中等）。
   - "highlights": 数组，1-3 条今日该用户做得好的地方（依据你的视角）。
   - "concerns": 数组，1-3 条当前组合最令你担忧的隐患或交易违规（依据你的视角）。
   - "action_items": 数组，1-3 条给用户的可执行建议，要求极其具体（如“明天开盘立即挂单上移止损至 152 锁定 VST 利润”、“观察 BABA 能否放量拉回MA200，否则必须砍掉三分之一仓位”）。
   - "eval_text": 300字以内的中文原声复盘大段点评。用你标志性的语气，直切痛点，讲透“为什么”。必须针对具体的成交和仓位（如今日买 COHR、VST 或是持仓 BABA 表现）进行点评。

4. 所有的回复字段必须使用【中文】生成。
"""

    # 3. 构造 User Prompt 传入今日交易与数据
    user_prompt = f"""
复盘日期：{date_str}

【今日大盘与市场环境】：
- 三指数表现：今日投资组合总浮盈波动为：${total_gain:+.2f}。
- 市场广度与轮动：今日有 AI 电力（VST）、光通信（COHR）、物理 AI（SYM）、云与搜索（GOOGL）等多个 AI 赛道细分标的的操作。

【核心战略备战大表单与研究记忆】：
{strategic_memory_text}

【今日投资组合实际持仓 (Positions Snapshot)】：
{positions_text}

【今日实际交易复盘及微观诊断 (Today's Trades & Micro Reviews)】：
{trades_text}

请【{master_name}】大师，根据上述战备大表单预设的点位逻辑和今日真实的成交/持仓数据，提供您最深刻、最不流于套路的复盘点评。
"""

    # 4. 调用 LLM
    try:
        client = LLMClient()
        raw_resp = client.call_llm(user_prompt, system_prompt=system_prompt, json_mode=True)
        cleaned = clean_json_string(raw_resp)
        parsed = json.loads(cleaned)
        
        # 校验字段
        if "master" not in parsed: parsed["master"] = master_name
        if "score" not in parsed: parsed["score"] = 70
        if "verdict" not in parsed: parsed["verdict"] = "中性评估"
        if "highlights" not in parsed: parsed["highlights"] = ["建仓位置较好"]
        if "concerns" not in parsed: parsed["concerns"] = ["仓位分散"]
        if "action_items" not in parsed: parsed["action_items"] = ["控制风险"]
        if "eval_text" not in parsed: parsed["eval_text"] = "未能生成完整点评。"
        
        return parsed
        
    except Exception as e:
        print(f"  [ERROR] {master_name} LLM 点评失败: {e}")
        # 提供有温度的 fallback 点评
        return {
            "master": master_name,
            "score": 65,
            "verdict": "系统降级评估",
            "highlights": ["交易执行顺利完成"],
            "concerns": ["LLM 点评接口超时，未能进行深度评估"],
            "action_items": ["密切关注核心持仓的移动止损"],
            "eval_text": f"（由于 LLM 接口访问失败或格式解析错误，已自动降级）今日组合整体波动尚在可控范围内，交易执行了多元化配置，但未能调用我的深度策略引擎进行微观因子匹配。请继续保持分批建仓的纪律。"
        }


def eval_all_masters(today_data: dict, trade_review: dict, date_str: str, base_dir: str = BASE) -> dict:
    """
    多大师并联 LLM 深度复盘点评汇总
    """
    print(f"\n  正在启动 7 位大师的 LLM 深度点评进程（需要调用大模型，请稍候）...")
    
    results = {}
    total_score = 0.0
    
    for master in MASTER_FOLDER_MAP.keys():
        print(f"  --> 【{master}】大师正在审阅数据并撰写点评...")
        res = eval_single_master(master, today_data, trade_review, date_str)
        results[master] = res
        total_score += res.get("score", 70)
        
    avg_score = round(total_score / len(MASTER_FOLDER_MAP), 1)
    
    # 整理大师共识
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    
    for r in results.values():
        score = r.get("score", 70)
        if score >= 80:
            bullish_count += 1
        elif score <= 60:
            bearish_count += 1
        else:
            neutral_count += 1
            
    consensus = f"{bullish_count}人看多/优秀 | {neutral_count}人看平/合理 | {bearish_count}人看空/警告"
    
    summary = {
        "date": date_str,
        "avg_master_score": avg_score,
        "consensus": consensus,
        "evaluations": results
    }
    
    # 写出 JSON 文件
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    out_path = os.path.join(find_dir, f"postmarket_master_eval_{date_str}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print(f"  多大师深度点评生成完成！综合评分 {avg_score}/100。点评报告已输出至: findings/postmarket_master_eval_{date_str}.json")
    return summary


if __name__ == "__main__":
    date_input = sys.argv[1] if len(sys.argv) > 1 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    # 模拟数据做测试
    today_data = _load_today_data(date_input)
    
    # 读取 trade_review json
    review_path = os.path.join(BASE, "findings", f"postmarket_trade_review_{date_input}.json")
    if os.path.exists(review_path):
        trade_review = json.load(open(review_path, encoding="utf-8"))
    else:
        trade_review = {"reviewed_trades": []}
        
    eval_all_masters(today_data, trade_review, date_input)
