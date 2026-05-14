import json, os, shutil, subprocess
PYTHON  = "/tool/pandora/bin/python3.12"
BASE    = "/home/lirawang/stock_team"
FIXTURE = f"{BASE}/tests/fixtures"

def setup():
    shutil.copy(f"{FIXTURE}/data_verified.json", f"{BASE}/data_verified.json")
    os.makedirs(f"{BASE}/findings", exist_ok=True)

def test_tech_agent_writes_finding():
    setup()
    r = subprocess.run([PYTHON, f"{BASE}/agents/tech_agent.py", "AMD"],
                       capture_output=True, text=True, cwd=BASE)
    assert r.returncode == 0
    out = json.load(open(f"{BASE}/findings/TechAgent.json", encoding="utf-8"))
    assert out["msg_type"] == "initial_finding"
    assert out["from"] == "TechAgent"
    assert out["signal"] in ("bullish", "bearish", "neutral")
    assert 0 <= out["confidence"] <= 100
    assert out["data_refs"]
    assert out["revision"] == 0

def test_tech_agent_rsi_above_75_reduces_confidence():
    setup()
    subprocess.run([PYTHON, f"{BASE}/agents/tech_agent.py", "AMD"], cwd=BASE)
    out = json.load(open(f"{BASE}/findings/TechAgent.json", encoding="utf-8"))
    kp = " ".join(out["key_points"])
    assert "超买" in kp or "overbought" in kp.lower()
