import json, os, shutil, subprocess
import sys; PYTHON = sys.executable
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = f"{BASE}/tests/fixtures"

def setup_fixtures():
    for f in ["data_raw_primary.json", "data_raw_secondary.json"]:
        shutil.copy(f"{FIXTURE}/{f}", f"{BASE}/{f}")

def test_verifier_marks_close_verified():
    setup_fixtures()
    r = subprocess.run([PYTHON, f"{BASE}/agents/verifier_agent.py"],
                       capture_output=True, encoding="utf-8", cwd=BASE)
    assert r.returncode == 0
    data = json.load(open(f"{BASE}/data_verified.json", encoding="utf-8"))
    assert data["fields"]["close"]["verified"] is True

def test_verifier_marks_volume_disputed():
    setup_fixtures()
    sec = json.load(open(f"{BASE}/data_raw_secondary.json", encoding="utf-8"))
    sec["fields"]["volume"]["value"] = 90000000  # >5% delta → disputed
    json.dump(sec, open(f"{BASE}/data_raw_secondary.json", "w", encoding="utf-8"))
    subprocess.run([PYTHON, f"{BASE}/agents/verifier_agent.py"], cwd=BASE)
    data = json.load(open(f"{BASE}/data_verified.json", encoding="utf-8"))
    assert data["fields"]["volume"]["verified"] is False
    assert "dispute_reason" in data["fields"]["volume"]
