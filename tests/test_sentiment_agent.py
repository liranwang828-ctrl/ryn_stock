import json, os, shutil, subprocess
PYTHON = "/tool/pandora/bin/python3.12"
BASE   = "/home/lirawang/stock_team"

def setup():
    shutil.copy(f"{BASE}/tests/fixtures/data_verified.json", f"{BASE}/data_verified.json")
    os.makedirs(f"{BASE}/findings", exist_ok=True)

def test_sentiment_agent_writes_finding():
    setup()
    r = subprocess.run([PYTHON, f"{BASE}/agents/sentiment_agent.py", "AMD"],
                       capture_output=True, text=True, cwd=BASE)
    assert r.returncode == 0
    out = json.load(open(f"{BASE}/findings/SentimentAgent.json"))
    assert out["msg_type"] == "initial_finding"
    assert out["from"] == "SentimentAgent"
    assert out["signal"] in ("bullish", "bearish", "neutral")
