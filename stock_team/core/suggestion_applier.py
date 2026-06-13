"""
建议应用模块 — suggestion_applier.py
将用户确认的 next_day.suggestions 写回对应源文件。

用法（由 Claude skill 调用，不直接运行）:
  from stock_team.agents.suggestion_applier import apply_suggestion
  result = apply_suggestion(sym, suggestion, base_dir=BASE)
"""
import json, os
from datetime import datetime, timezone

BASE    = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
CFG_DIR = os.path.join(BASE, "config")

# 展示型建议：confirmed=True 表示"已知晓"，不写任何文件
DISPLAY_ONLY_TYPES = {"correlation_warning", "thesis_confirmation", "time_stop_eval"}


def _load(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def apply_suggestion(sym: str, suggestion: dict,
                     base_dir: str = BASE) -> dict:
    """
    应用一条已确认的建议。
    返回更新后的 suggestion dict（含 applied_at + applied_to）。
    """
    stype  = suggestion.get("type", "")
    pvalue = suggestion.get("proposed_value", {}) or {}

    if stype in DISPLAY_ONLY_TYPES:
        suggestion["applied_at"] = datetime.now(timezone.utc).isoformat()
        suggestion["applied_to"] = None
        return suggestion

    applied_to = None
    sym_upper  = sym.upper()

    if stype == "thesis_status":
        pos_path = os.path.join(base_dir, "config", "positions.json")
        data = _load(pos_path)
        old_val = data.get("positions", {}).get(sym_upper, {}).get("thesis_status")
        new_val = pvalue.get("new_status", "weakening")
        data.setdefault("positions", {}).setdefault(sym_upper, {})["thesis_status"] = new_val
        _save(pos_path, data)
        applied_to = {"file": "positions.json",
                      "field": f"positions.{sym_upper}.thesis_status",
                      "old_value": {"thesis_status": old_val},
                      "new_value": {"thesis_status": new_val}}

    elif stype == "stop_move":
        pos_path = os.path.join(base_dir, "config", "positions.json")
        data = _load(pos_path)
        old_val = data.get("positions", {}).get(sym_upper, {}).get("t1_stop_snapshot")
        new_val = pvalue.get("new_stop")
        if new_val is not None:
            data.setdefault("positions", {}).setdefault(sym_upper, {})["t1_stop_snapshot"] = new_val
            _save(pos_path, data)
        applied_to = {"file": "positions.json",
                      "field": f"positions.{sym_upper}.t1_stop_snapshot",
                      "old_value": {"t1_stop_snapshot": old_val},
                      "new_value": {"t1_stop_snapshot": new_val}}

    elif stype == "lesson_record":
        lessons_path = os.path.join(base_dir, "trading_lessons.json")
        try:
            with open(lessons_path, encoding="utf-8") as f:
                lessons = json.load(f)
            if not isinstance(lessons, list):
                lessons = []
        except Exception:
            lessons = []
        lesson = pvalue.get("lesson", "")
        lessons.append({"date": datetime.now().strftime("%Y-%m-%d"), "sym": sym_upper,
                        "lesson": lesson})
        _save(lessons_path, lessons)
        applied_to = {"file": "trading_lessons.json", "field": "[]",
                      "old_value": None, "new_value": {"lesson": lesson}}

    elif stype == "trigger_deep_research":
        queue_path = os.path.join(base_dir, "config", "rerun_queue.json")
        try:
            with open(queue_path, encoding="utf-8") as f:
                queue = json.load(f)
            if not isinstance(queue, list):
                queue = []
        except Exception:
            queue = []
        queue.append({"sym": sym_upper, "reason": pvalue.get("reason", ""),
                      "requested_at": datetime.now().strftime("%Y-%m-%d")})
        _save(queue_path, queue)
        applied_to = {"file": "config/rerun_queue.json", "field": "[]",
                      "old_value": None, "new_value": pvalue}

    elif stype == "tomorrow_risk_calendar":
        cal_path = os.path.join(base_dir, "config", "macro_events_tomorrow.json")
        events = pvalue.get("events", [])
        _save(cal_path, {"date": datetime.now().strftime("%Y-%m-%d"), "events": events})
        applied_to = {"file": "config/macro_events_tomorrow.json",
                      "field": "events",
                      "old_value": None, "new_value": {"events": events}}

    # 其他类型暂不实施（master_weight / scene_calibration / node_reset / stage_alert）

    suggestion["applied_at"] = datetime.now(timezone.utc).isoformat()
    suggestion["applied_to"] = applied_to
    return suggestion
