import json, os, shutil, subprocess
PYTHON  = "/tool/pandora/bin/python3.12"
BASE    = "/home/lirawang/stock_team"
FIXTURE = f"{BASE}/tests/fixtures"

def setup():
    shutil.copy(f"{FIXTURE}/discussion_board_phase1.jsonl", f"{BASE}/discussion_board.jsonl")

def test_strategy_agent_writes_result():
    setup()
    r = subprocess.run([PYTHON, f"{BASE}/agents/strategy_agent.py", "AMD"],
                       capture_output=True, text=True, cwd=BASE)
    assert r.returncode == 0
    result = json.load(open(f"{BASE}/strategy_result.json", encoding="utf-8"))
    assert result["symbol"] == "AMD"
    assert result["signal"] in ("bullish", "bearish", "neutral")
    assert 0 <= result["confidence"] <= 100
    assert "stop_loss" in result
    assert "key_points" in result

def test_strategy_weighted_score_bullish_majority():
    setup()
    subprocess.run([PYTHON, f"{BASE}/agents/strategy_agent.py", "AMD"], cwd=BASE)
    result = json.load(open(f"{BASE}/strategy_result.json", encoding="utf-8"))
    assert result["signal"] == "bullish"

def test_strategy_excludes_veto_agent():
    shutil.copy(f"{FIXTURE}/discussion_board_phase1.jsonl", f"{BASE}/discussion_board.jsonl")
    # Overwrite TechAgent line with a veto finding
    board = [json.loads(l) for l in open(f"{BASE}/discussion_board.jsonl") if l.strip()]
    new_board = []
    for m in board:
        if m.get("from") == "TechAgent":
            m["master_signal"] = "veto"
            m["signal"] = "neutral"
            m["confidence"] = 0
            m["veto_triggered"] = "不在Stage 2"
        new_board.append(m)
    with open(f"{BASE}/discussion_board.jsonl", "w") as f:
        for m in new_board:
            f.write(json.dumps(m) + "\n")
    subprocess.run([PYTHON, f"{BASE}/agents/strategy_agent.py", "AMD"], cwd=BASE)
    result = json.load(open(f"{BASE}/strategy_result.json", encoding="utf-8"))
    assert "veto_agents" in result
    assert "TechAgent" in result["veto_agents"]

def test_strategy_handles_null_stop_loss():
    setup()
    # Use normal board but RiskAgent has no stop_loss
    board = [json.loads(l) for l in open(f"{FIXTURE}/discussion_board_phase1.jsonl") if l.strip()]
    for m in board:
        if m.get("from") == "RiskAgent":
            m.pop("stop_loss", None)
            m["stop_loss_pct"] = None
    with open(f"{BASE}/discussion_board.jsonl", "w") as f:
        for m in board:
            f.write(json.dumps(m) + "\n")
    subprocess.run([PYTHON, f"{BASE}/agents/strategy_agent.py", "AMD"], cwd=BASE)
    result = json.load(open(f"{BASE}/strategy_result.json", encoding="utf-8"))
    assert "stop_loss" in result  # key exists, may be None
