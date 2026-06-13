import json, os, shutil, subprocess
import sys; PYTHON = sys.executable
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FIXTURE = f"{BASE}/tests/fixtures"

def setup():
    shutil.copy(f"{FIXTURE}/strategy_result.json",          f"{BASE}/strategy_result.json")
    shutil.copy(f"{FIXTURE}/discussion_board_phase1.jsonl", f"{BASE}/discussion_board.jsonl")
    os.makedirs(f"{BASE}/reports", exist_ok=True)

def test_report_agent_prints_summary():
    setup()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([PYTHON, f"{BASE}/agents/report_agent.py", "AMD"],
                       capture_output=True, encoding="utf-8", cwd=BASE, env=env)
    assert r.returncode == 0
    assert "AMD" in r.stdout
    assert any(kw in r.stdout for kw in ["综合建议", "综合结论", "看涨", "看空", "中性"])

def test_report_agent_writes_html():
    setup()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    subprocess.run([PYTHON, f"{BASE}/agents/report_agent.py", "AMD"], cwd=BASE, env=env)
    from datetime import datetime, timezone
    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target_file = f"{BASE}/reports/{date_tag}_AMD.html"
    
    # Fallback to local timezone just in case timezone.utc vs local date differ
    if not os.path.exists(target_file):
        date_tag = datetime.now().strftime("%Y-%m-%d")
        target_file = f"{BASE}/reports/{date_tag}_AMD.html"
        
    assert os.path.exists(target_file), f"Expected report file does not exist: {target_file}"
    content = open(target_file, encoding="utf-8").read()
    assert "AMD" in content
