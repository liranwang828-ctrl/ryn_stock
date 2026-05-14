import json, os, subprocess
PYTHON = "/tool/pandora/bin/python3.12"
BASE   = "/home/lirawang/stock_team"

def test_macro_agent_writes_finding():
    os.makedirs(f"{BASE}/findings", exist_ok=True)
    r = subprocess.run([PYTHON, f"{BASE}/agents/macro_agent.py", "AMD"],
                       capture_output=True, text=True, cwd=BASE, timeout=30)
    assert r.returncode == 0
    out = json.load(open(f"{BASE}/findings/MacroAgent.json"))
    assert out["msg_type"] == "initial_finding"
    assert out["from"] == "MacroAgent"
    assert out["signal"] in ("bullish", "bearish", "neutral")
