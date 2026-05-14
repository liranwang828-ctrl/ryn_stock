import json, os, shutil, subprocess
PYTHON  = "/tool/pandora/bin/python3.12"
BASE    = "/home/lirawang/stock_team"
FIXTURE = f"{BASE}/tests/fixtures"

def setup():
    shutil.copy(f"{FIXTURE}/strategy_result.json",          f"{BASE}/strategy_result.json")
    shutil.copy(f"{FIXTURE}/discussion_board_phase1.jsonl", f"{BASE}/discussion_board.jsonl")
    os.makedirs(f"{BASE}/reports", exist_ok=True)

def test_report_agent_prints_summary():
    setup()
    r = subprocess.run([PYTHON, f"{BASE}/agents/report_agent.py", "AMD"],
                       capture_output=True, text=True, cwd=BASE)
    assert r.returncode == 0
    assert "AMD" in r.stdout
    assert any(kw in r.stdout for kw in ["综合建议", "综合结论", "看涨", "看空", "中性"])

def test_report_agent_writes_html():
    setup()
    subprocess.run([PYTHON, f"{BASE}/agents/report_agent.py", "AMD"], cwd=BASE)
    html_files = [f for f in os.listdir(f"{BASE}/reports") if f.endswith(".html")]
    assert len(html_files) > 0
    content = open(f"{BASE}/reports/{html_files[-1]}").read()
    assert "AMD" in content
