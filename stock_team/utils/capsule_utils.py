"""
"个股太空舱" (Stock Capsule) 路径解析公用库 — capsule_utils.py
管理个股太空舱目录下的所有数据读写路径，并提供向平铺 findings/ 目录的回退兼容。
"""
import os
import json


def _load_leveraged_pairs(base_dir: str) -> dict:
    path = os.path.join(base_dir, "config", "leveraged_pairs.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def resolve_tracking_symbol(sym: str, base_dir: str) -> str:
    """Resolve a tracking symbol so leveraged tools share the underlying capsule."""
    sym_upper = str(sym or "").upper().strip()
    if not sym_upper:
        return ""
    pairs = _load_leveraged_pairs(base_dir)
    for underlying, info in pairs.items():
        if not isinstance(info, dict):
            continue
        if str(info.get("sym") or "").upper().strip() == sym_upper:
            return str(underlying).upper().strip()
    return sym_upper

def get_capsule_dir(sym: str, base_dir: str) -> str:
    """获取个股太空舱根目录: findings/symbols/{SYM}"""
    tracking_sym = resolve_tracking_symbol(sym, base_dir)
    return os.path.join(base_dir, "findings", "symbols", tracking_sym)

def get_strategy_path(sym: str, base_dir: str) -> str:
    """获取个股太空舱专属策略文件路径: findings/symbols/{SYM}/strategy.json"""
    return os.path.join(get_capsule_dir(sym, base_dir), "strategy.json")

def get_latest_premarket_plan_path(sym: str, base_dir: str) -> str:
    """获取个股当前盘前计划路径: findings/symbols/{SYM}/latest_premarket_plan.json"""
    return os.path.join(get_capsule_dir(sym, base_dir), "latest_premarket_plan.json")

def get_current_nodes_path(sym: str, base_dir: str) -> str:
    """获取个股当前有效价格节点路径: findings/symbols/{SYM}/current_nodes.json"""
    return os.path.join(get_capsule_dir(sym, base_dir), "current_nodes.json")

def get_premarket_summary_path(sym: str, date: str, base_dir: str) -> str:
    """
    获取盘前报告路径。
    优先返回太空舱路径: findings/symbols/{SYM}/plans/premarket_summary_{date}.json
    不存在则回退至平铺路径: findings/premarket_summary_{date}_{SYM}.json
    """
    sym_upper = sym.upper()
    capsule_path = os.path.join(get_capsule_dir(sym_upper, base_dir), "plans", f"premarket_summary_{date}.json")
    if os.path.exists(capsule_path):
        return capsule_path
    
    # 回退兼容
    return os.path.join(base_dir, "findings", f"premarket_summary_{date}_{sym_upper}.json")

def get_intraday_snapshot_path(sym: str, date: str, base_dir: str) -> str:
    """
    获取盘中高频轮询快照路径。
    优先返回太空舱路径: findings/symbols/{SYM}/snapshots/intraday_snapshot_{date}.jsonl
    不存在则回退至平铺路径: findings/intraday_snapshot_{date}_{SYM}.jsonl
    """
    sym_upper = sym.upper()
    capsule_path = os.path.join(get_capsule_dir(sym_upper, base_dir), "snapshots", f"intraday_snapshot_{date}.jsonl")
    if os.path.exists(capsule_path):
        return capsule_path
    
    # 回退兼容
    return os.path.join(base_dir, "findings", f"intraday_snapshot_{date}_{sym_upper}.jsonl")

def get_debate_path(sym: str, date: str, base_dir: str) -> str:
    """
    获取大师心智交锋辩论日志路径。
    优先返回太空舱路径: findings/symbols/{SYM}/debates/debate_{date}.jsonl
    不存在则回退至平铺路径: findings/debate_{SYM}_{date}.jsonl
    """
    sym_upper = sym.upper()
    capsule_path = os.path.join(get_capsule_dir(sym_upper, base_dir), "debates", f"debate_{date}.jsonl")
    if os.path.exists(capsule_path):
        return capsule_path
    
    # 回退兼容
    return os.path.join(base_dir, "findings", f"debate_{sym_upper}_{date}.jsonl")

def get_narrative_path(sym: str, date: str, base_dir: str) -> str:
    """
    获取叙事报告路径。
    优先返回太空舱路径: findings/symbols/{SYM}/debates/narrative_{date}.json
    不存在则回退至平铺路径: findings/narrative_{SYM}_{date}.json
    """
    sym_upper = sym.upper()
    capsule_path = os.path.join(get_capsule_dir(sym_upper, base_dir), "debates", f"narrative_{date}.json")
    if os.path.exists(capsule_path):
        return capsule_path
    
    # 回退兼容
    return os.path.join(base_dir, "findings", f"narrative_{sym_upper}_{date}.json")
