import json, os, shutil, subprocess
PYTHON  = "/tool/pandora/bin/python3.12"
BASE    = "/home/lirawang/stock_team"
FIXTURE = f"{BASE}/tests/fixtures"

def setup():
    shutil.copy(f"{FIXTURE}/data_verified.json", f"{BASE}/data_verified.json")
    os.makedirs(f"{BASE}/findings", exist_ok=True)

def agent_finding(agent_script, agent_name):
    r = subprocess.run([PYTHON, f"{BASE}/agents/{agent_script}.py", "AMD"],
                       capture_output=True, text=True, cwd=BASE, timeout=60)
    assert r.returncode == 0, f"{agent_script} failed: {r.stderr}"
    return json.load(open(f"{BASE}/findings/{agent_name}.json"))

def test_tech_agent_has_master_fields():
    setup()
    out = agent_finding("tech_agent", "TechAgent")
    assert "master" in out
    assert "master_signal" in out
    assert "rule_signal" in out
    assert out["signal"] == out["master_signal"] or out["master_signal"] == "veto"

def test_risk_agent_has_stop_loss_pct():
    setup()
    out = agent_finding("risk_agent", "RiskAgent")
    assert "stop_loss_pct" in out
    # Taleb hard_stop_pct=0.07
    assert out["stop_loss_pct"] == 0.07 or out["stop_loss_pct"] is None

def test_fund_agent_signal_is_valid():
    setup()
    out = agent_finding("fund_agent", "FundAgent")
    assert out["master_signal"] in ("bullish", "bearish", "neutral", "veto")

def test_key_points_contain_master_insight():
    setup()
    out = agent_finding("tech_agent", "TechAgent")
    combined = " ".join(out.get("key_points", []))
    assert "[Minervini]" in combined or "veto" in out.get("master_signal", "")
