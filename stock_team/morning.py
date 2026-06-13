"""
早间例行程序 — 通过 session_manager 编排三步流程
用法: python3.12 morning.py [--symbols SYM1 SYM2 ...]

流程（由 session_manager 节点0编排）：
  Step 1: 组合风险快照
  Step 2: 候选池扫描（自动选标的）
  Step 3: 盘前分析（候选池 + 持仓 + 手动指定）

交互：各步骤输出结果后可继续对话调整
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_team.core.session_manager import run_node, add_symbol

def main():
    parser = argparse.ArgumentParser(description="晨间例行（session_manager 节点0）")
    parser.add_argument("--symbols", nargs="*", help="额外手动指定标的")
    args = parser.parse_args()

    if args.symbols:
        for sym in args.symbols:
            add_symbol(sym)

    result = run_node(0)
    print(result)

if __name__ == "__main__":
    main()
