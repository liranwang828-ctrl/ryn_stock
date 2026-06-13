"""
决策质量审计模块 — postmarket_decision_audit.py
核心功能：
1. 盘前入场决策 vs 实际操作 vs 市场结果（对比审计谁对谁错，覆写合理性）
2. 盘前预判场景 vs 盘中确认实际场景（大盘/个股预判准确率）
3. 盘前关键价位（阻力、支撑、止损） vs 实际日内高低价（支撑有效性，破位警告）
"""
import sys, os, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stock_team.data_ingest.postmarket_data_collector import _load

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))


def audit_entry_decisions(date_str: str, trade_review: dict, base_dir: str = BASE) -> dict:
    """
    审计盘前系统决策决策 vs 实际用户交易操作
    判断用户的主观覆写 (Override) 或跟单决策在今日收盘时的对错与质量
    """
    find_dir = os.path.join(base_dir, "findings")
    entry_dec = _load(os.path.join(find_dir, f"entry_decision_{date_str}.json"))
    decisions = entry_dec.get("decisions", {})
    
    trades = trade_review.get("reviewed_trades", [])
    
    audit_list = []
    override_count = 0
    override_success = 0
    adherence_count = 0
    
    # 对每笔今日交易进行决策质量比对
    for t in trades:
        sym = t["sym"]
        action = t["action"]
        cost = t["cost"]
        stats = t["stats"]
        
        # 1. 查找系统针对该股的盘前决议
        sys_decision = decisions.get(sym, {})
        sys_action = sys_decision.get("decision", "neutral")  # 默认 neutral/观察
        sys_score = sys_decision.get("consensus_score", 50)
        sys_reasons = sys_decision.get("veto_reasons", []) or sys_decision.get("reasons", [])
        
        # 2. 判断用户操作与系统计划的关系
        is_buy = "BUY" in action or "ADD" in action
        
        audit_status = "aligned"
        detail_note = ""
        
        if is_buy:
            if sys_action == "veto" or sys_action == "no_buy" or (sys_action == "observe" and sys_score < 55):
                # 用户进行了【买入覆写】（系统不建议或持保留意见，但用户买了）
                override_count += 1
                audit_status = "user_override"
                
                # 评估覆写是否成功（依据收盘表现：若日内涨了且买点好，则判定为成功覆写）
                day_ret = stats.get("close", cost) / cost - 1.0
                if day_ret > 0.005 and t["review"]["score"] >= 70:
                    override_success += 1
                    detail_note = f"用户成功覆写！系统持保留态度（{sys_action}，分数{sys_score}），但用户主观研究介入，且入场点位极佳，收盘录得正收益（{day_ret:+.2%}）。"
                else:
                    detail_note = f"用户强行覆写但效果欠佳。系统发出警示，用户买入后收盘表现疲软（日内涨跌幅 {day_ret:+.2%}），买入点位偏高。"
            else:
                # 顺风跟单（系统说买或建议介入，用户也买了）
                adherence_count += 1
                day_ret = stats.get("close", cost) / cost - 1.0
                detail_note = f"顺风执行。系统推荐介入（分数 {sys_score}），用户纪律性跟单建仓，日内表现为 {day_ret:+.2%}。"
        else:
            # 卖出审计
            if sys_action == "exit" or sys_action == "sell":
                adherence_count += 1
                detail_note = "执行止损/止盈计划。系统发出离场信号，用户严格执行清仓动作，锁定利润或限制了亏损。"
            else:
                override_count += 1
                audit_status = "user_override_sell"
                detail_note = "用户主观落袋为盈或防御性清仓，提早锁定了利润。"
                
        audit_list.append({
            "sym": sym,
            "action": action,
            "cost": cost,
            "sys_recommendation": sys_action,
            "sys_score": sys_score,
            "audit_status": audit_status,
            "day_ret_pct": round((stats.get("close", cost) / cost - 1.0) * 100, 2) if cost > 0 else 0.0,
            "entry_score": t["review"]["score"],
            "detail": detail_note
        })
        
    return {
        "override_total": override_count,
        "override_success_count": override_success,
        "override_success_rate": round(override_success / override_count * 100, 1) if override_count > 0 else 100.0,
        "adherence_count": adherence_count,
        "decisions_audit": audit_list
    }


def audit_scenario_accuracy(date_str: str, base_dir: str = BASE) -> dict:
    """
    审计盘前大盘及板块场景预判的准确率
    """
    find_dir = os.path.join(base_dir, "findings")
    
    # 尝试加载盘前分析
    pm_analysis_path = os.path.join(base_dir, f"premarket_analysis_{date_str}.json")
    pm_analysis = _load(pm_analysis_path)
    
    # 尝试加载盘中确认场景
    op_scene_path = os.path.join(base_dir, f"opening_scenarios_{date_str}.json")
    op_scene = _load(op_scene_path)
    
    pred_scenario = pm_analysis.get("macro_context", {}).get("scenario_expected") or "A"
    actual_scenario = op_scene.get("actual_scenario") or op_scene.get("scene_confirmed") or "A"
    
    success = pred_scenario == actual_scenario
    
    # 针对个股的场景验证
    stock_audits = []
    # 扫描预判总结文件
    import glob
    pm_summaries = glob.glob(os.path.join(find_dir, f"premarket_summary_{date_str}_*.json"))
    
    correct_stocks = 0
    total_stocks = 0
    
    for p in pm_summaries:
        data = _load(p)
        sym = data.get("sym", "").upper()
        if not sym:
            continue
            
        pred_s = data.get("stock_snapshot", {}).get("pred_scene")
        # 读取盘后数据对齐
        post_open = data.get("post_open_adj") or {}
        if not isinstance(post_open, dict):
            post_open = {}
        actual_s = post_open.get("scene_confirmed")
        
        if pred_s and actual_s:
            total_stocks += 1
            is_correct = pred_s == actual_s
            if is_correct:
                correct_stocks += 1
            stock_audits.append({
                "sym": sym,
                "pred_scene": pred_s,
                "actual_scene": actual_s,
                "is_correct": is_correct
            })
            
    return {
        "macro_pred_scenario": pred_scenario,
        "macro_actual_scenario": actual_scenario,
        "macro_scenario_correct": success,
        "stock_level_scenario_accuracy": round(correct_stocks / total_stocks * 100, 1) if total_stocks > 0 else 100.0,
        "stock_scenarios": stock_audits
    }


def audit_key_levels(date_str: str, trade_review: dict, base_dir: str = BASE) -> dict:
    """
    验证盘前阻力支撑位是否被实际日内波幅触及、虚破或强力支撑
    """
    trades = trade_review.get("reviewed_trades", [])
    level_audits = []
    
    for t in trades:
        sym = t["sym"]
        stats = t["stats"]
        if not stats.get("has_data") or not stats.get("low"):
            continue
            
        lo = stats["low"]
        hi = stats["high"]
        cl = stats["close"]
        
        plan_match = t.get("plan_match", {})
        target_support = plan_match.get("target_support")
        
        if not target_support:
            continue
            
        # 评估支撑位状态：
        # 1. 虚破收回：最低价低于支撑位，但收盘价高于支撑位 (典型诱空，支撑依然极其有效)
        # 2. 强力支撑：最低价非常贴近支撑位（跌幅偏差在 1% 以内），且未跌破，随后反弹
        # 3. 破位：最低价和收盘价全部跌破支撑位 1.5% 以上 (支撑彻底失效，论点受损)
        dist_low_to_support = (lo - target_support) / target_support * 100
        dist_close_to_support = (cl - target_support) / target_support * 100
        
        level_status = "normal"
        analysis_text = ""
        
        if lo < target_support and cl > target_support:
            level_status = "fake_breach_recover"
            analysis_text = f"支撑位被【日内虚破收回】！盘前支撑 ${target_support:.2f}，最低跌至 ${lo:.2f} (虚破 {dist_low_to_support:.1f}%)，但收盘成功站回 ${cl:.2f}。这是非常强烈的探底买入信号，证明了支撑位的核心有效性。"
        elif dist_low_to_support >= -1.0 and lo <= target_support * 1.01:
            level_status = "perfect_support"
            analysis_text = f"【完美强力支撑】！日内最低价 ${lo:.2f} 几乎完美在盘前支撑位 ${target_support:.2f} 附近止跌（最接近时仅差 {dist_low_to_support:.1f}%），全天未收在其下，反弹回升。这是极高精度的盘前点位预判！"
        elif lo < target_support * 0.985 and cl < target_support * 0.985:
            level_status = "breached"
            analysis_text = f"支撑位【破位失效】。支撑位 ${target_support:.2f} 被空头强力跌穿，最低触及 ${lo:.2f}，收盘仍收在 ${cl:.2f}（破位 {dist_close_to_support:.1f}%）。表明该标的主动抛压极其沉重，需重新校准支撑节点。"
        else:
            analysis_text = f"常规区间波动。日内最低点 ${lo:.2f} 未能回踩至盘前支撑位 ${target_support:.2f}（相差 {dist_low_to_support:+.1f}%），全天属于在支撑上方蓄势。"
            
        level_audits.append({
            "sym": sym,
            "plan_support": target_support,
            "actual_low": lo,
            "actual_close": cl,
            "status": level_status,
            "deviation_low_pct": round(dist_low_to_support, 2),
            "analysis": analysis_text
        })
        
    return {
        "key_level_audits": level_audits
    }


def generate_audit_report(date_str: str, trade_review: dict, base_dir: str = BASE) -> dict:
    """
    汇总所有决策审计数据，生成今日决策质量审计报告
    """
    print(f"  正在启动今日 {date_str} 决策质量与计划对齐审计...")
    
    entry_audit = audit_entry_decisions(date_str, trade_review, base_dir=base_dir)
    scenario_audit = audit_scenario_accuracy(date_str, base_dir=base_dir)
    level_audit = audit_key_levels(date_str, trade_review, base_dir=base_dir)
    
    report = {
        "date": date_str,
        "audited_at": datetime.now().isoformat(),
        "entry_audit": entry_audit,
        "scenario_audit": scenario_audit,
        "level_audit": level_audit,
    }
    
    # 写出到 findings/postmarket_decision_audit_{date}.json
    find_dir = os.path.join(base_dir, "findings")
    os.makedirs(find_dir, exist_ok=True)
    out_path = os.path.join(find_dir, f"postmarket_decision_audit_{date_str}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"  决策审计完成！系统共审计了 {len(entry_audit['decisions_audit'])} 笔操作。报告已输出至: findings/postmarket_decision_audit_{date_str}.json")
    return report


if __name__ == "__main__":
    date_input = sys.argv[1] if len(sys.argv) > 1 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 模拟读取 trade_review
    review_path = os.path.join(BASE, "findings", f"postmarket_trade_review_{date_input}.json")
    if os.path.exists(review_path):
        trade_review = json.load(open(review_path, encoding="utf-8"))
    else:
        trade_review = {"reviewed_trades": []}
        
    generate_audit_report(date_input, trade_review)
