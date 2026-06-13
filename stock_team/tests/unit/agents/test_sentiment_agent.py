import json, os, shutil, subprocess
import sys; PYTHON = sys.executable
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def setup():
    shutil.copy(f"{BASE}/tests/fixtures/data_verified.json", f"{BASE}/data_verified.json")
    os.makedirs(f"{BASE}/findings", exist_ok=True)

def test_sentiment_agent_writes_finding():
    setup()
    r = subprocess.run([PYTHON, f"{BASE}/agents/sentiment_agent.py", "AMD"],
                       capture_output=True, encoding="utf-8", cwd=BASE)
    assert r.returncode == 0
    out = json.load(open(f"{BASE}/findings/SentimentAgent.json", encoding="utf-8"))
    assert out["msg_type"] == "initial_finding"
    assert out["from"] == "SentimentAgent"
    assert out["signal"] in ("bullish", "bearish", "neutral")
