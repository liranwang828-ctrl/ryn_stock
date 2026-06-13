# D:\gemini\lianghua\stock_team\run_intraday_loop.py
"""
Intraday Dashboard Polling Loop Runner
Runs the condition check and generates the premium HTML dashboard every 60 seconds.
Includes strict timeouts to guarantee that network glitches never freeze the session.
"""
import subprocess
import time
import sys
import os
from stock_team.utils.workspace_paths import investing_os_home, workspace_home

# Configuration paths
PYTHON_EXE = sys.executable
STOCK_TEAM_HOME = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = workspace_home(STOCK_TEAM_HOME)
BRAIN_HOME = investing_os_home(STOCK_TEAM_HOME)
GUIDANCE_PATH = os.path.join(BRAIN_HOME, "system", "simulations", "inputs", "intraday-guidance.NVDA-conditional.demo.json")
OUT_PATH = os.path.join(BRAIN_HOME, "system", "data", "packets", "intraday-dashboard-packet.md")

def main():
    print("==========================================================")
    print("INTRADAY DASHBOARD POLLING LOOP RUNNER")
    print("==========================================================")
    print(f"Interval: 60 seconds (aligned to K-line)")
    print(f"Subprocess Timeout: 20 seconds (bulletproof hang protection)")
    print(f"Input:  {GUIDANCE_PATH}")
    print(f"Output: {OUT_PATH}")
    print("Press Ctrl+C to terminate.")
    print("==========================================================")
    
    cmd = [
        PYTHON_EXE, "-m", "stock_team.cli", "intraday-dashboard",
        "--guidance", GUIDANCE_PATH,
        "--out", OUT_PATH
    ]
    
    while True:
        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            print(f"[{timestamp}] Checking conditions & updating dashboard...", end="", flush=True)
            
            # Execute CLI in a separate subprocess with a strict 20-second timeout.
            # Capture as raw bytes first, then decode using utf-8 with errors='ignore'.
            result = subprocess.run(
                cmd,
                cwd=WORKSPACE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20
            )
            
            stdout_str = result.stdout.decode("utf-8", errors="ignore")
            stderr_str = result.stderr.decode("utf-8", errors="ignore")
            
            if result.returncode == 0:
                print(" Success!")
            else:
                print(f" Failed (Exit code: {result.returncode})")
                # Print errors if any
                err_lines = [l.strip() for l in stderr_str.split("\n") if l.strip()]
                if err_lines:
                    print(f"  └─ Error details: {err_lines[-1]}")
                else:
                    out_lines = [l.strip() for l in stdout_str.split("\n") if l.strip()]
                    if out_lines:
                        print(f"  └─ CLI details: {out_lines[-1]}")
                        
        except subprocess.TimeoutExpired:
            print(" Timeout Expired (Forced killed after 20s)")
        except KeyboardInterrupt:
            print("\nPolling loop terminated by user.")
            break
        except Exception as e:
            print(f" Unexpected error: {e}")
            
        # Aligns sleep interval to precisely match 60-second bars
        elapsed = time.time() - start_time
        sleep_time = max(1, 60.0 - elapsed)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
