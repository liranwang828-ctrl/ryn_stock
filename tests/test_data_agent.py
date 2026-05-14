import json, os, subprocess, sys, tempfile
PYTHON = "/tool/pandora/bin/python3.12"
BASE   = "/home/lirawang/stock_team"

def run_agent(args, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    r = subprocess.run([PYTHON, f"{BASE}/agents/data_agent.py"] + args,
                       capture_output=True, text=True, env=env, cwd=BASE)
    return r

def test_data_agent_writes_primary_json():
    r = run_agent(["AMD", "--light"])
    assert r.returncode == 0
    path = f"{BASE}/data_raw_primary.json"
    assert os.path.exists(path)
    data = json.load(open(path, encoding="utf-8"))
    assert data["symbol"] == "AMD"
    assert "close" in data["fields"]
    assert "volume" in data["fields"]

def test_data_agent_invalid_symbol_exits_2():
    r = run_agent(["INVALIDXXX"])
    assert r.returncode == 2

def test_data_agent_full_mode_has_persona_fields():
    r = run_agent(["AMD"])
    assert r.returncode == 0
    data = json.load(open(f"{BASE}/data_raw_primary.json", encoding="utf-8"))
    fields = data["fields"]
    for required in ["ma50", "ma150", "ma200", "volume_breakout_ratio",
                     "p_fcf", "de_ratio", "gross_margin", "price_chg_3m",
                     "correlation_with_spy", "vix", "spy_above_ma200"]:
        assert required in fields, f"Missing field: {required}"
