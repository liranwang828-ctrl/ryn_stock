"""
大规模随机参数搜索 — 自动保存增量结果
目标：找到 PF >= 1.3 且 WinRate >= 35% 的参数组合
每100轮自动分析一次当前最优解
"""
import sys, os, json, random, time
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scripts.joint_backtest_engine import run_joint_backtest

TICKERS = ['ARM','NVDA','SNOW','AMD','COHR','VST','SYM','AVGO','MRVL','ANET','CSCO','LITE','MU','TSM','VRT']
RESULTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'findings', 'random_search_v2.jsonl')
SUMMARY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'findings', 'random_search_v2_summary.json')

# ── 搜索空间 ────────────────────────────────────────────
SPACE = {
    'vc_threshold_pct':         [15.0, 25.0, 40.0, 60.0, 100.0],
    'atr_stop_multiplier':      [1.5, 2.0, 2.5, 3.0, 3.5],
    'rs_strong_threshold':      [1.5, 1.8, 2.0, 2.2, 2.5, 3.0],
    'ml_score_threshold':       [0.70, 0.75, 0.80, 0.85],
    'ml_confirm_bars':          [1, 2, 3],
    't1_wait_bars':             [2, 3, 5, 8],
    'entry_cutoff_time':        ['11:00', '11:30', '12:00', '13:00', '13:30'],
    'stop_freeze_bars':         [2, 3, 4, 5, 6],
    'hwm_trail_pct':            [0.950, 0.960, 0.965, 0.970, 0.975],
    'trailing_stop_type':       ['HighWaterMark', 'MA20'],
    'stop_loss_type':           ['ATR', 'OpenLow'],
    'use_noise_delay':          [False, True],
    'use_t2_confirm':           [False],
    'profit_lock_threshold':    [1.03, 1.04, 1.05, 1.06, 1.08],
    'tightened_trailing_stop_pct': [0.975, 0.980, 0.985, 0.990],
    'open_high_vol_multiplier': [1.0, 1.2, 1.5],
    'ma20_trail_atr_multiplier':[0.3, 0.5, 0.7, 1.0],
    'bracket_stop_loss_pct':    [0.8],
}

def sample_params(rng):
    return {k: rng.choice(v) for k, v in SPACE.items()}

def load_existing():
    results = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        results.append(json.loads(line))
                    except:
                        pass
    return results

def save_result(rec):
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

def print_leaderboard(results, top_n=10):
    valid = [r for r in results if r.get('pf', 0) > 0 and r.get('win_rate', 0) > 0]
    # Score = PF * sqrt(win_rate) * (1 + return/100)
    for r in valid:
        r['_score'] = r['pf'] * (r['win_rate'] ** 0.5) * max(0.1, 1 + r['total_return'] / 100)
    ranked = sorted(valid, key=lambda x: x['_score'], reverse=True)[:top_n]

    print(f"\n{'='*80}")
    print(f"  TOP {top_n} 参数组合  |  已测试 {len(results)} 轮  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    print(f"  {'#':<3} {'收益':>7} {'Alpha':>7} {'胜率':>6} {'PF':>5} {'盈亏比':>6} {'交易':>5}  关键参数")
    print(f"  {'-'*75}")
    for i, r in enumerate(ranked, 1):
        alpha = r['total_return'] - r.get('qqq_return', 21.29)
        key = (f"ATR={r['params']['atr_stop_multiplier']}  "
               f"VC={r['params']['vc_threshold_pct']:.0f}%  "
               f"RS={r['params']['rs_strong_threshold']}  "
               f"HWM={r['params']['hwm_trail_pct']}  "
               f"cutoff={r['params']['entry_cutoff_time']}")
        print(f"  {i:<3} {r['total_return']:>+6.2f}%  {alpha:>+6.2f}%  "
              f"{r['win_rate']:>5.1f}%  {r['pf']:>5.2f}  {r['payoff_ratio']:>5.2f}x  "
              f"{r['trades']:>5}  {key}")

    # Save summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_tested': len(results),
        'top_results': ranked[:5],
        'pf_gt_1_2_count': sum(1 for r in valid if r['pf'] >= 1.2),
        'pf_gt_1_3_count': sum(1 for r in valid if r['pf'] >= 1.3),
        'best_pf': max((r['pf'] for r in valid), default=0),
        'best_return': max((r['total_return'] for r in valid), default=0),
        'best_win_rate': max((r['win_rate'] for r in valid), default=0),
    }
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  PF>=1.2: {summary['pf_gt_1_2_count']}轮  |  PF>=1.3: {summary['pf_gt_1_3_count']}轮  "
          f"|  最佳PF={summary['best_pf']:.2f}  |  最佳收益={summary['best_return']:+.2f}%")
    print(f"{'='*80}\n")
    return ranked

# ── 主循环 ────────────────────────────────────────────
MAX_ROUNDS = 2000
REPORT_EVERY = 50
SEED = int(time.time())

print(f"启动随机搜索 | 种子={SEED} | 目标={MAX_ROUNDS}轮 | 每{REPORT_EVERY}轮汇报")
print(f"结果文件: {RESULTS_FILE}\n")

rng = random.Random(SEED)
all_results = load_existing()
start_round = len(all_results)
print(f"已加载 {start_round} 条历史结果，从第 {start_round+1} 轮继续\n")

for round_idx in range(start_round, MAX_ROUNDS):
    params = sample_params(rng)
    rules = {
        'use_barbell': False,
        'methodology_15_low_catalyst_rs': params
    }
    t0 = time.time()
    try:
        m = run_joint_backtest(TICKERS, days=90, custom_rules=rules, verbose=False)
        elapsed = time.time() - t0
        if m:
            rec = {
                'round': round_idx + 1,
                'total_return': m['total_return_pct'],
                'qqq_return': m.get('qqq_return_pct', 21.29),
                'max_drawdown': m['max_drawdown_pct'],
                'win_rate': m['win_rate_pct'],
                'pf': m['profit_factor'],
                'trades': m['trades_count'],
                'payoff_ratio': m['payoff_ratio'],
                'sortino': m.get('sortino_ratio', 0),
                'params': params,
                'elapsed_s': round(elapsed, 1),
                'ts': datetime.now().isoformat()
            }
            all_results.append(rec)
            save_result(rec)

            # 实时打印进度
            alpha = rec['total_return'] - rec['qqq_return']
            flag = '🏆' if rec['pf'] >= 1.3 else '⭐' if rec['pf'] >= 1.2 else '  '
            print(f"  [{round_idx+1:>4}] {flag} 收益{rec['total_return']:>+6.2f}%  "
                  f"Alpha{alpha:>+6.2f}%  胜率{rec['win_rate']:>5.1f}%  PF={rec['pf']:.2f}  "
                  f"({elapsed:.1f}s)  ATR={params['atr_stop_multiplier']}  "
                  f"VC={params['vc_threshold_pct']:.0f}  RS={params['rs_strong_threshold']}")

        # 每N轮输出排行榜
        if (round_idx + 1) % REPORT_EVERY == 0:
            print_leaderboard(all_results)

    except Exception as e:
        print(f"  [{round_idx+1:>4}] ERROR: {e}")

print("\n搜索完成！")
print_leaderboard(all_results, top_n=15)
