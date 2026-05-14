import json, os, shutil, subprocess
PYTHON = "/tool/pandora/bin/python3.12"
BASE   = "/home/lirawang/stock_team"

def setup():
    shutil.copy(f"{BASE}/tests/fixtures/data_verified.json", f"{BASE}/data_verified.json")
    os.makedirs(f"{BASE}/findings", exist_ok=True)

def test_risk_agent_includes_stop_loss():
    setup()
    r = subprocess.run([PYTHON, f"{BASE}/agents/risk_agent.py", "AMD"],
                       capture_output=True, text=True, cwd=BASE)
    assert r.returncode == 0
    out = json.load(open(f"{BASE}/findings/RiskAgent.json", encoding="utf-8"))
    assert out["msg_type"] == "initial_finding"
    assert any("止损" in kp or "stop" in kp.lower() for kp in out["key_points"])
    assert "stop_loss" in out
