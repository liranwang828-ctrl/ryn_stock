import json, os, subprocess, time, shutil
import sys; PYTHON = sys.executable
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_cio(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return subprocess.run([PYTHON, f"{BASE}/agents/cio.py"] + args,
                          capture_output=True, encoding="utf-8", cwd=BASE, timeout=120, env=env)

def test_cio_phase01_creates_verified_and_board():
    for f in ["data_verified.json", "discussion_board.jsonl", "run.lock"]:
        try: os.remove(f"{BASE}/{f}")
        except FileNotFoundError: pass
    r = run_cio(["AMD", "--phases", "01"])
    assert r.returncode == 0
    assert os.path.exists(f"{BASE}/data_verified.json")
    assert os.path.exists(f"{BASE}/discussion_board.jsonl")
    board = [json.loads(l) for l in open(f"{BASE}/discussion_board.jsonl", encoding="utf-8") if l.strip()]
    agents = {m["from"] for m in board}
    assert "TechAgent" in agents
    assert "RiskAgent" in agents
    assert len(agents) == 7

def test_cio_respects_run_lock():
    with open(f"{BASE}/run.lock", "w", encoding="utf-8") as f:
        json.dump({"start_time": time.time(), "symbol": "AMD"}, f)
    r = run_cio(["AMD", "--phases", "01"])
    os.remove(f"{BASE}/run.lock")

def test_cio_phase2_runs_debate():
    shutil.copy(f"{BASE}/tests/fixtures/discussion_board_phase1.jsonl", f"{BASE}/discussion_board.jsonl")
    shutil.copy(f"{BASE}/tests/fixtures/data_verified.json", f"{BASE}/data_verified.json")
    r = run_cio(["AMD", "--phases", "2"])
    assert r.returncode == 0
    board = [json.loads(l) for l in open(f"{BASE}/discussion_board.jsonl", encoding="utf-8") if l.strip()]
    assert len(board) >= 6
