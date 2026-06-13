# agents/position_builder.py
"""
建仓引导模块 — 三种模式：规划(planning) / 快速(quick) / 补全(catch_up)

用法（交互式，由 Claude skill 调用）:
  from stock_team.core.position_builder import (
      planning_mode, quick_mode, catch_up_mode,
      validate_position, list_pending
  )
"""
import json, os, sys
from datetime import datetime, timezone

BASE      = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
POS_PATH  = os.path.join(BASE, "config", "positions.json")
FIND_DIR  = os.path.join(BASE, "findings")
PYTHON = sys.executable

# ── 必填字段（_pending=False 时检查）───────────────────────────
REQUIRED_FIELDS = [
    "cost", "shares", "date", "position_type", "thesis",
    "thesis_status", "falsification_conditions",
    "t1_stop_snapshot", "gtc_stop_placed",
]

# ── 待补全字段（quick 模式写入 _pending_fields）─────────────────
PENDING_FIELDS_DEFAULT = [
    "falsification_conditions", "t1_stop_snapshot",
    "gtc_stop_placed", "t2_conditions", "macro_sensitivity",
]

def _load_positions() -> dict:
    try:
        with open(POS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"positions": {}, "_excluded": []}

def _save_positions(data: dict):
    with open(POS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _load_memo(sym: str) -> dict | None:
    path = os.path.join(BASE, f"strategic_memo_{sym.upper()}.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def validate_position(pos: dict) -> list[str]:
    """
    验证持仓记录是否符合 schema。
    _pending=True 时跳过必填检查（快速模式允许缺失）。
    返回 error 字符串列表，空列表 = 合法。
    """
    errors = []
    if pos.get("_pending"):
        return []   # pending 模式下不强制验证
    for field in REQUIRED_FIELDS:
        val = pos.get(field)
        if val is None or val == "" or val == []:
            errors.append(f"缺少必填字段: {field}")
    # position_type 枚举检查（仅在字段存在时）
    valid_types = {"thesis", "catalyst", "trend", "flex"}
    if pos.get("position_type") and pos.get("position_type") not in valid_types:
        errors.append(f"position_type 必须是 {valid_types} 之一")
    # thesis_status 枚举检查（仅在字段存在时）
    valid_status = {"intact", "weakening", "broken"}
    if pos.get("thesis_status") and pos.get("thesis_status") not in valid_status:
        errors.append(f"thesis_status 必须是 {valid_status} 之一")
    return errors

def list_pending() -> list[str]:
    """返回所有 _pending=True 的标的列表"""
    data = _load_positions()
    excluded = set(data.get("_excluded", []))
    return [sym for sym, pos in data.get("positions", {}).items()
            if pos.get("_pending") and sym not in excluded]

def write_position(sym: str, pos: dict, pos_path: str = POS_PATH):
    """将持仓记录写入 positions.json（新建或覆盖）"""
    try:
        with open(pos_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"positions": {}, "_excluded": []}
    data["positions"][sym.upper()] = pos
    with open(pos_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

VALID_POSITION_TYPES = {"thesis", "catalyst", "trend", "flex"}

def quick_mode(
    sym: str, cost: float, shares: int, date: str,
    position_type: str, thesis: str,
    pos_path: str = POS_PATH, find_dir: str = FIND_DIR,
) -> dict:
    """
    快速建仓模式（盘中使用）：仅填写最小字段，其余标记 _pending。
    返回 {"mode": "quick", "pending_fields": [...], "audit_path": "..."}
    """
    if position_type not in VALID_POSITION_TYPES:
        raise ValueError(f"position_type 必须是 {VALID_POSITION_TYPES} 之一，得到: {position_type}")

    today = date
    pos = {
        "cost": cost, "shares": shares, "date": today,
        "note": f"{sym.upper()} 快速建仓",
        "tranche": "T1",
        "t1_cost": cost, "t1_shares": shares, "t1_date": today,
        "t2_cost": None, "t2_shares": 0,
        "t2_conditions": {"note": "", "underlying_price_floor": None,
                          "etf_price_floor": None, "vol_ratio_min": None},
        "t3_cost": None, "t3_shares": 0,
        "position_type": position_type,
        "thesis": thesis,
        "thesis_status": "intact", "thesis_updated": today,
        "falsification_conditions": [],
        "falsification_updated": None,
        "catalyst_type": None, "catalyst_deadline": None,
        "catalyst_persistence": None,
        "daily_action": "B", "action_updated": today,
        "t1_stop_snapshot": None,
        "stop_note": "", "gtc_stop_placed": False, "gtc_stop_date": None,
        "macro_type": "", "macro_sensitivity": {},
        "target_pct": None, "min_pct": None, "max_pct": None,
        "_pending": True,
        "_pending_fields": PENDING_FIELDS_DEFAULT.copy(),
    }

    write_position(sym, pos, pos_path=pos_path)
    audit_path = write_entry_audit(
        sym=sym, date=today, mode="quick",
        fields_written=["cost", "shares", "date", "position_type", "thesis"],
        fields_pending=PENDING_FIELDS_DEFAULT,
        user_inputs={"position_type": position_type, "thesis": thesis},
        auto_filled={},
        find_dir=find_dir,
    )
    return {"mode": "quick", "pending_fields": PENDING_FIELDS_DEFAULT, "audit_path": audit_path}

def write_entry_audit(
    sym: str, date: str, mode: str,
    fields_written: list, fields_pending: list,
    user_inputs: dict, auto_filled: dict,
    find_dir: str = FIND_DIR,
    positions_updated: bool = True,
    premarket_triggered: bool = False,
) -> str:
    """生成 position_entry_{date}_{sym}.json 审计记录，返回文件路径"""
    os.makedirs(find_dir, exist_ok=True)
    record = {
        "date": date,
        "sym": sym.upper(),
        "session_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "source": "manual",
        "fields_written": fields_written,
        "fields_pending": fields_pending,
        "pending_count": len(fields_pending),
        "positions_json_updated": positions_updated,
        "premarket_triggered": premarket_triggered,
        "user_inputs": user_inputs,
        "auto_filled": auto_filled,
    }
    fname = f"position_entry_{date}_{sym.upper()}.json"
    path = os.path.join(find_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return path

_MACRO_SENSITIVITY_TEMPLATE = {
    "rate_up": "负", "inflation": "中", "recession": "负",
    "dollar_strong": "负", "credit_tight": "负",
}

def _memo_to_prefilled(memo: dict) -> dict:
    """从 strategic_memo 提取可预填的字段"""
    prefilled = {}
    synth = memo.get("synthesis", {})
    prefilled["thesis"] = synth.get("key_condition", "")

    mac = memo.get("support_and_risk", {}).get("macro_fit", {})
    headwinds = set(mac.get("active_headwinds", []))
    sens = _MACRO_SENSITIVITY_TEMPLATE.copy()
    for key in headwinds:
        if key in sens:
            sens[key] = "负"
    prefilled["macro_sensitivity"] = sens

    prefilled["main_risks"] = memo.get("support_and_risk", {}).get("main_risks", [])
    return prefilled

def planning_mode(
    sym: str,
    memo_dir: str = BASE,
    pos_path: str = POS_PATH,
    find_dir: str = FIND_DIR,
    write: bool = False,
    user_answers: dict | None = None,
) -> dict:
    """
    规划模式（建仓前使用）。
    write=False（默认）：仅返回引导信息（prefilled + questions），不写文件。
    write=True：user_answers 必须提供，写入 positions.json 并生成审计记录。
    """
    memo_path = os.path.join(memo_dir, f"strategic_memo_{sym.upper()}.json")
    memo = None
    if os.path.exists(memo_path):
        try:
            with open(memo_path, encoding="utf-8") as f:
                memo = json.load(f)
        except Exception:
            pass

    source = "strategic_memo" if memo else "manual"
    prefilled = _memo_to_prefilled(memo) if memo else {
        "thesis": None, "macro_sensitivity": None, "main_risks": [],
    }

    if not write:
        return {
            "source": source,
            "prefilled": prefilled,
            "questions": [
                "Q1: position_type（thesis/catalyst/trend/flex）？",
                "Q2: 确认/修改 thesis（一句话，≤50字）？",
                "Q3: 证伪条件（什么情况下承认错了，具体可观测）？",
                "Q4: 硬止损价是多少？GTC 是否已挂好？",
            ],
        }

    a = user_answers or {}
    today = a.get("date", datetime.now().strftime("%Y-%m-%d"))
    pos = {
        "cost": a.get("cost", 0.0),
        "shares": a.get("shares", 0),
        "date": today, "note": f"{sym.upper()} 规划建仓",
        "tranche": "T1",
        "t1_cost": a.get("cost", 0.0),
        "t1_shares": a.get("shares", 0),
        "t1_date": today,
        "t2_cost": None, "t2_shares": 0,
        "t2_conditions": {"note": "", "underlying_price_floor": None,
                          "etf_price_floor": None, "vol_ratio_min": None},
        "t3_cost": None, "t3_shares": 0,
        "position_type": a.get("position_type", "thesis"),
        "thesis": a.get("thesis", prefilled.get("thesis", "")),
        "thesis_status": "intact", "thesis_updated": today,
        "falsification_conditions": a.get("falsification_conditions", []),
        "falsification_updated": today,
        "catalyst_type": a.get("catalyst_type"),
        "catalyst_deadline": a.get("catalyst_deadline"),
        "catalyst_persistence": a.get("catalyst_persistence"),
        "daily_action": "B", "action_updated": today,
        "t1_stop_snapshot": a.get("t1_stop_snapshot"),
        "stop_note": a.get("stop_note", ""),
        "gtc_stop_placed": a.get("gtc_stop_placed", False),
        "gtc_stop_date": today if a.get("gtc_stop_placed") else None,
        "macro_type": a.get("macro_type", ""),
        "macro_sensitivity": a.get("macro_sensitivity") or prefilled.get("macro_sensitivity") or {},
        "target_pct": a.get("target_pct"),
        "min_pct": a.get("min_pct"),
        "max_pct": a.get("max_pct"),
        "_pending": False,
        "_pending_fields": [],
    }

    write_position(sym, pos, pos_path=pos_path)
    auto_filled = {}
    if memo:
        auto_filled = {"thesis": prefilled.get("thesis"),
                       "macro_sensitivity": prefilled.get("macro_sensitivity")}
    audit_path = write_entry_audit(
        sym=sym, date=today, mode="planning",
        fields_written=list(a.keys()),
        fields_pending=[],
        user_inputs=a, auto_filled=auto_filled,
        find_dir=find_dir,
    )
    if memo:
        with open(audit_path, encoding="utf-8") as f:
            audit_data = json.load(f)
        audit_data["source"] = "strategic_memo"
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=2, ensure_ascii=False)

    return {"source": source, "prefilled": prefilled, "audit_path": audit_path}

def catch_up_mode(
    sym: str, updates: dict,
    pos_path: str = POS_PATH, find_dir: str = FIND_DIR,
) -> dict:
    """
    补全模式：填写 _pending=True 持仓的缺失字段。
    updates: {field: value} 要更新的字段。
    返回 {"mode": "catch_up", "remaining_pending": [...], "complete": bool}
    """
    try:
        with open(pos_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"positions": {}, "_excluded": []}

    sym_upper = sym.upper()
    if sym_upper not in data["positions"]:
        raise KeyError(f"{sym_upper} 不在 positions.json 中")

    pos = data["positions"][sym_upper]
    pending_fields = list(pos.get("_pending_fields", []))

    for field, value in updates.items():
        pos[field] = value
        if field in pending_fields:
            pending_fields.remove(field)

    pos["_pending_fields"] = pending_fields
    pos["_pending"] = len(pending_fields) > 0

    data["positions"][sym_upper] = pos
    with open(pos_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    today = datetime.now().strftime("%Y-%m-%d")
    write_entry_audit(
        sym=sym, date=today, mode="catch_up",
        fields_written=list(updates.keys()),
        fields_pending=pending_fields,
        user_inputs=updates, auto_filled={},
        find_dir=find_dir,
        positions_updated=True,
        premarket_triggered=False,
    )

    return {
        "mode": "catch_up",
        "remaining_pending": pending_fields,
        "complete": not pos["_pending"],
    }


def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list_pending"
    if cmd == "list_pending":
        pending = list_pending()
        if pending:
            print(f"⚠️ 以下持仓有待补全字段：{', '.join(pending)}")
            for sym in pending:
                data = _load_positions()
                fields = data["positions"][sym].get("_pending_fields", [])
                print(f"  {sym}: {', '.join(fields)}")
        else:
            print("✅ 所有持仓记录完整，无待补全字段")

if __name__ == "__main__":
    main()
