"""
Terminal dashboard — displays paper trading status, positions, and recent signals.
Reads from paper_trading/ and discussion_board.jsonl.
"""
import os, sys, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PT_DIR = os.path.join(BASE, "paper_trading")
BOARD_PATH = os.path.join(BASE, "discussion_board.jsonl")

W = 72

def hr(char="─"):
    return char * W


def load_board(n=20):
    """Load the last N messages from the discussion board."""
    if not os.path.exists(BOARD_PATH):
        return []
    with open(BOARD_PATH, encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    return lines[-n:]


def load_account(acct):
    """Load a paper trading account portfolio."""
    path = os.path.join(PT_DIR, acct, "portfolio.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def load_evolution(acct):
    """Load evolution log for an account."""
    path = os.path.join(PT_DIR, acct, "evolution.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def render():
    """Render the full terminal dashboard."""
    print("\033[2J\033[H", end="")  # clear screen
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"  RYN Stock Team Dashboard  │  {now}")
    print(hr("═"))

    # ── Paper trading accounts ──
    print(f"  {'Account':<12s} {'Equity':>10s} {'Return':>8s} {'Cash':>10s} {'Positions':>10s}")
    print(hr())

    for acct in ["strict", "base", "loose"]:
        port = load_account(acct)
        if not port:
            print(f"  {acct:<12s} {'--':>10s} {'--':>8s} {'--':>10s} {'--':>10s}")
            continue
        equity = port["cash"]
        for sym, pos in port.get("positions", {}).items():
            equity += pos["shares"] * pos.get("cost", 0)
        initial = port.get("initial_cash", 100000)
        ret = (equity - initial) / initial * 100
        n_pos = len(port.get("positions", {}))
        print(f"  {acct:<12s} ${equity:>9,.0f} {ret:>+7.1f}% ${port['cash']:>9,.0f} {n_pos:>10d}")

    # ── Open positions ──
    print()
    print("── Open Positions ──")
    has_positions = False
    for acct in ["strict", "base", "loose"]:
        port = load_account(acct)
        if not port:
            continue
        for sym, pos in port.get("positions", {}).items():
            has_positions = True
            mode_icon = "S" if pos.get("mode") == "swing" else "I"
            pnl_est = 0  # live prices not available in offline dashboard
            print(f"  [{acct[:1].upper()}] {sym} T{pos.get('tranche',1)} "
                  f"${pos['cost']:.2f} x{pos['shares']} "
                  f"stop=${pos['stop']:.2f} tgt=${pos['target1']:.2f} "
                  f"[{mode_icon}] {pos.get('mode_reason','')[:30]}")

    if not has_positions:
        print("  No open positions")

    # ── Recent signals from board ──
    print()
    print("── Recent Signals ──")
    board = load_board(20)
    findings = [m for m in board if m.get("msg_type") in ("initial_finding", "revision")]
    shown = set()
    for m in reversed(findings):
        key = (m.get("from", ""), m.get("symbol", ""))
        if key in shown:
            continue
        shown.add(key)
        agent = m.get("from", "").replace("Agent", "")
        sig = m.get("signal", "neutral")
        conf = m.get("confidence", 0)
        icon = {"bullish": "+", "bearish": "-", "neutral": "~"}.get(sig, "?")
        master = m.get("master", "")
        print(f"  {icon} {agent:<10s} [{master:<16s}] {sig:<8s} {conf}%  {m.get('symbol','')}")

    # ── Evolution summary ──
    print()
    print("── Recent Evolution Events ──")
    for acct in ["strict", "base", "loose"]:
        evo = load_evolution(acct)
        weekly = [e for e in evo if e.get("type") == "weekly_report"]
        if weekly:
            last = weekly[-1]
            print(f"  [{acct}] {last.get('time','')[:16]}")
            content = last.get("content", "")
            for line in content.split("\n")[:3]:
                print(f"    {line}")

    print()
    print(hr("═"))


if __name__ == "__main__":
    render()
