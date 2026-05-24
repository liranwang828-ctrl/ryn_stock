import sys, os, json
sys.path.insert(0, ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team")))
from unittest.mock import patch


def test_load_entry_decision_returns_dict(tmp_path):
    """_load_entry_decision 正常读取文件时返回 decisions dict"""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")

    data = {
        "date": date_str,
        "decisions": {
            "LITE": {"decision": "可入场", "soft_vetoes": []},
            "MRVU": {"decision": "不入场", "hard_vetoes": ["RR不足"]},
        },
        "poll_needed": True,
        "poll_symbols": ["LITE"],
    }
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    f = findings_dir / f"entry_decision_{date_str}.json"
    f.write_text(json.dumps(data))

    import agents.poll as poll_mod
    findings_path = str(tmp_path)
    # Patch the findings path inside _load_entry_decision
    with patch("agents.poll._STOCK_BASE", str(tmp_path)):
        result = poll_mod._load_entry_decision()

    assert result["LITE"]["decision"] == "可入场"
    assert result["MRVU"]["decision"] == "不入场"


def test_load_entry_decision_returns_empty_on_missing():
    """_load_entry_decision 文件不存在时返回空 dict（向后兼容）"""
    import agents.poll as poll_mod
    with patch("agents.poll._STOCK_BASE", "/nonexistent/path"):
        result = poll_mod._load_entry_decision()
    assert result == {}
