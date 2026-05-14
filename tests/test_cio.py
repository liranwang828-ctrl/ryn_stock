import json, os, subprocess, time, shutil
PYTHON = "/tool/pandora/bin/python3.12"
BASE   = "/home/lirawang/stock_team"

def run_cio(args):
    return subprocess.run([PYTHON, f"{BASE}/agents/cio.py"] + args,
                          capture_output=True, text=True, cwd=BASE, timeout=120)

def test_cio_phase01_creates_verified_and_board():
    for f in ["data_verified.json", "discussion_board.jsonl", "run.lock"]:
        try: os.remove(f"{BASE}/{f}")
        except FileNotFoundError: pass
    r = run_cio(["AMD", "--phases", "01"])
    assert r.returncode == 0
    assert os.path.exists(f"{BASE}/data_verified.json")
    assert os.path.exists(f"{BASE}/discussion_board.jsonl")
    board = [json.loads(l) for l in open(f"{BASE}/discussion_board.jsonl") if l.strip()]
    agents = {m["from"] for m in board}
    assert "TechAgent" in agents
    assert "RiskAgent" in agents
    assert len(agents) == 7

def test_cio_respects_run_lock():
    json.dump({"start_time": time.time(), "symbol": "AMD"},
              open(f"{BASE}/run.lock", "w"))
    r = run_cio(["AMD", "--phases", "01"])
    os.remove(f"{BASE}/run.lock")

def test_cio_phase2_runs_debate():
    shutil.copy(f"{BASE}/tests/fixtures/discussion_board_phase1.jsonl", f"{BASE}/discussion_board.jsonl")
    shutil.copy(f"{BASE}/tests/fixtures/data_verified.json", f"{BASE}/data_verified.json")
    r = run_cio(["AMD", "--phases", "2"])
    assert r.returncode == 0
    board = [json.loads(l) for l in open(f"{BASE}/discussion_board.jsonl") if l.strip()]
    assert len(board) >= 6
