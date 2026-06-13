import json, os, subprocess
import sys; PYTHON = sys.executable
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_community_agent_runs_and_writes_finding():
    os.makedirs(f"{BASE}/findings", exist_ok=True)
    r = subprocess.run([PYTHON, f"{BASE}/agents/community_agent.py", "AMD"],
                       capture_output=True, encoding="utf-8", cwd=BASE, timeout=60)
    assert r.returncode == 0
    out = json.load(open(f"{BASE}/findings/CommunityAgent.json", encoding="utf-8"))
    assert out["msg_type"] == "initial_finding"
    assert out["from"] == "CommunityAgent"
    assert out["signal"] in ("bullish", "bearish", "neutral")
    assert len(out["key_points"]) > 0
