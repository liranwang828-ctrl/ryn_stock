"""
板块龙头关系与联动风控模块 — sector_leadership.py
处理 config/market_relationships.json 规则，提供盘中跟风股入场否决与止损收紧判断。
"""
import os
import json

BASE = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
REL_PATH = os.path.join(BASE, "config", "market_relationships.json")

def load_relationships() -> dict:
    """载入板块映射配置"""
    if os.path.exists(REL_PATH):
        try:
            with open(REL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def find_sector_for_follower(symbol: str, rel_data: dict = None) -> tuple[str, dict] | tuple[None, None]:
    """寻找某只跟风个股所在的板块和对应规则"""
    if rel_data is None:
        rel_data = load_relationships()
    sym_upper = symbol.upper()
    for sector_name, info in rel_data.items():
        if sym_upper in info.get("followers", []):
            return sector_name, info
    return None, None

def check_leader_status(leader: str, stocks: dict) -> tuple[float, float]:
    """
    获取龙头股的最新的涨跌幅（chg）和成交量比（vol_ratio）。
    stocks 字典可以是 poll.py 的原始 stocks，或者是简易键值对。
    """
    leader_upper = leader.upper()
    chg = 0.0
    vol_ratio = 1.0
    
    if leader_upper in stocks:
        s_data = stocks[leader_upper]
        if isinstance(s_data, dict):
            chg = float(s_data.get("chg", s_data.get("chg_pct", 0.0)) or 0.0)
            vol_ratio = float(s_data.get("vol_ratio_5m", s_data.get("vol_ratio", 1.0)) or 1.0)
    return chg, vol_ratio

def is_leader_broken(symbol: str, stocks: dict) -> tuple[bool, str]:
    """
    判断个股所在的板块龙头是否已带量破位。
    返回：(是否破位, 详细描述字符串)
    """
    sector_name, info = find_sector_for_follower(symbol)
    if not sector_name or not info:
        return False, ""
    
    leader = info["leader"]
    rules = info.get("correlation_rules", {})
    if not rules:
        return False, ""
    
    leader_chg, leader_vr = check_leader_status(leader, stocks)
    
    break_pct = rules.get("leader_break_pct", -3.0)
    vr_trigger = rules.get("vol_ratio_trigger", 1.2)
    
    # 龙头跌破阈值 且 爆量
    if leader_chg <= break_pct and leader_vr >= vr_trigger:
        desc = f"板块龙头 {leader} 带量大跌 ({leader_chg:+.2f}%, 量比 {leader_vr:.2f}x <= {break_pct}%, 触发量比 >= {vr_trigger}x)"
        return True, desc
        
    return False, ""

def get_adjusted_stop_multiplier(symbol: str, stocks: dict) -> float:
    """
    如果板块龙头破位，获取对应的止损收紧系数（如 0.5）。
    否则返回 1.0 (不收紧)。
    """
    sector_name, info = find_sector_for_follower(symbol)
    if not sector_name or not info:
        return 1.0
    
    broken, _ = is_leader_broken(symbol, stocks)
    if broken:
        rules = info.get("correlation_rules", {})
        return float(rules.get("tighten_stop_multiplier", 1.0))
        
    return 1.0
