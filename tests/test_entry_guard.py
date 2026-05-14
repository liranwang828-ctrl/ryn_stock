"""
test_entry_guard.py — entry_guard.py 的 TDD 测试套件
运行：/tool/pandora/bin/python3.12 -m pytest tests/test_entry_guard.py -v
"""
import sys, os, json, tempfile, shutil
from unittest.mock import patch

sys.path.insert(0, os.path.expanduser("~/stock_team"))
from agents.entry_guard import parse_trade_input


# ════════════════════════════════════════════
# Task 1: parse_trade_input
# ════════════════════════════════════════════

def test_parse_buy_full():
    """'买了 MRVL $178 20股' 应解析为 buy 动作"""
    result = parse_trade_input("买了 MRVL $178 20股")
    assert result["action"] == "buy"
    assert result["symbol"] == "MRVL"
    assert result["price"] == 178.0
    assert result["shares"] == 20


def test_parse_sell_full():
    """'卖了 AAOI $213 10股' 应解析为 sell 动作"""
    result = parse_trade_input("卖了 AAOI $213 10股")
    assert result["action"] == "sell"
    assert result["symbol"] == "AAOI"
    assert result["price"] == 213.0
    assert result["shares"] == 10


def test_parse_stop_with_price():
    """'止损了 MRVL $173.5 20股' 应解析为 stop 动作"""
    result = parse_trade_input("止损了 MRVL $173.5 20股")
    assert result["action"] == "stop"
    assert result["symbol"] == "MRVL"
    assert result["price"] == 173.5
    assert result["shares"] == 20


def test_parse_stop_without_price():
    """'止损了 MRVL' 无价格时 price 应为 None"""
    result = parse_trade_input("止损了 MRVL")
    assert result["action"] == "stop"
    assert result["symbol"] == "MRVL"
    assert result["price"] is None
    assert result["shares"] is None


def test_parse_price_decimal():
    """价格含小数点应正确解析"""
    result = parse_trade_input("买了 NVDA $875.5 5股")
    assert result["price"] == 875.5
    assert result["shares"] == 5


def test_parse_price_without_dollar_sign():
    """价格不带$符号也应能解析"""
    result = parse_trade_input("买了 MRVL 178 20股")
    assert result["price"] == 178.0


def test_parse_lowercase_action():
    """动作关键词不区分大小写（中文不存在大小写，测试空格变体）"""
    result = parse_trade_input("买了MRVL $178 20股")   # 无空格
    assert result["action"] == "buy"
    assert result["symbol"] == "MRVL"


def test_parse_failure_returns_none():
    """非交易记录文本应返回 None"""
    assert parse_trade_input("今天大盘怎么样？") is None
    assert parse_trade_input("MRVL 分析一下") is None
    assert parse_trade_input("") is None


def test_parse_failure_missing_price():
    """格式缺少价格时返回 None（止损了无价格的特殊情况除外）"""
    # "买了 MRVL 20股" 缺少价格，应返回 None
    result = parse_trade_input("买了 MRVL 20股")
    assert result is None


def test_parse_symbol_uppercase():
    """股票代码应统一转大写"""
    result = parse_trade_input("买了 mrvl $178 20股")
    assert result["symbol"] == "MRVL"


# ════════════════════════════════════════════
# Task 2: generate_entry_card
# ════════════════════════════════════════════

from agents.entry_guard import generate_entry_card

# ── 测试用 daily_plan 数据 ────────────────────────────────────
FAKE_MRVL_PLAN = {
    "predicted_scene": "B",
    "actual_scene": "B",
    "catalyst": "AMD持股★★★",
    "catalyst_strength": 3,
    "watch_zone_lo": 175.53,
    "watch_zone_hi": 178.77,
    "t1_entry_hint": "VWAP附近缩量企稳，3根阳线后入",
    "t1_stop": 173.5,
    "t1_target1": 182.0,
    "t1_target2": 188.0,
    "t2_condition_a": "价格>T1成本×1.005 + 量比>0.85x",
    "t2_condition_b": "缩量回踩0.3-2.5% + 守VWAP",
    "t2_stop_mode": "t1_cost",
    "plan_status": "active",
    "actual_vwap": 177.3,
    "entered": False,
    "added_at": "2026-05-14T09:20:00Z",
    "atr": 9.5,
}


def _mock_get_plan(symbol, date_str=None):
    """mock：返回 MRVL 计划，其他返回 None"""
    return FAKE_MRVL_PLAN if symbol == "MRVL" else None


def test_card_contains_symbol():
    """卡片应包含股票代码"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    assert "MRVL" in card


def test_card_contains_stop():
    """卡片应包含止损数字 173.5"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    assert "173.5" in card, "卡片必须包含止损数字"


def test_card_contains_targets():
    """卡片应包含目标1和目标2"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    assert "182" in card, "卡片必须包含目标1"
    assert "188" in card, "卡片必须包含目标2"


def test_card_contains_entry_price():
    """卡片应包含入场价"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    assert "178" in card


def test_card_t2_path_a_uses_entry_price():
    """T2路径A应动态代入入场价（178 × 1.005 = 178.89）"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    # 178 × 1.005 = 178.89，卡片中应含此数字
    assert "178.89" in card or "178.9" in card, "T2路径A应显示入场价×1.005的计算结果"


def test_card_t2_path_b_present():
    """卡片应包含T2路径B触发条件"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    assert "路径B" in card


def test_card_scene_and_catalyst():
    """卡片应包含场景和催化剂"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    assert "场景B" in card or "场景" in card
    assert "AMD持股" in card


def test_card_no_plan_fallback():
    """无当日计划时应返回简版卡片并提示"""
    with patch("agents.entry_guard.get_plan", lambda sym, date_str=None: None):
        card = generate_entry_card("XXXX", entry_price=100.0, shares=10,
                                   date_str="2026-05-14")
    assert "XXXX" in card
    assert "无预计划" in card or "未找到" in card or "daily_plan" in card


def test_card_shares_in_ibkr_section():
    """IBKR参数区块应包含股数（风险计算）"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        card = generate_entry_card("MRVL", entry_price=178.0, shares=20,
                                   date_str="2026-05-14")
    assert "20" in card  # 20股


# ════════════════════════════════════════════
# Task 3: record_trade
# ════════════════════════════════════════════
# 注意：_mock_get_plan 和 FAKE_MRVL_PLAN 在 Task 2 的测试块中已定义，
# 此处直接引用。追加本块之前必须先追加 Task 2 的测试块。

from agents.entry_guard import record_trade

# ── 测试辅助：创建隔离的临时目录 ─────────────────────────────────

def _make_temp_env(initial_positions: dict = None):
    """
    创建临时 config/ 和 knowledge/ 目录，返回 tmpdir。
    调用者负责 shutil.rmtree(tmpdir)。
    """
    tmpdir = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmpdir, "config"))
    os.makedirs(os.path.join(tmpdir, "knowledge"))

    # 初始 positions.json
    positions = initial_positions or {"cash": 10000, "positions": {}}
    pos_path = os.path.join(tmpdir, "config", "positions.json")
    with open(pos_path, "w") as f:
        json.dump(positions, f)

    # 空 trading_history.jsonl
    hist_path = os.path.join(tmpdir, "knowledge", "trading_history.jsonl")
    open(hist_path, "w").close()

    return tmpdir


def _read_positions(tmpdir):
    with open(os.path.join(tmpdir, "config", "positions.json")) as f:
        return json.load(f)


def _read_history(tmpdir):
    path = os.path.join(tmpdir, "knowledge", "trading_history.jsonl")
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    return [json.loads(l) for l in lines]


def test_record_buy_new_position():
    """买入新标的：positions 中应新增该仓位"""
    tmpdir = _make_temp_env()
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="buy", price=178.0, shares=20,
                         date_str="2026-05-14")
        pos = _read_positions(tmpdir)
        assert "MRVL" in pos["positions"]
        mrvl = pos["positions"]["MRVL"]
        assert mrvl["shares"] == 20
        assert mrvl["cost"] == 178.0
    finally:
        shutil.rmtree(tmpdir)


def test_record_buy_appends_history():
    """买入后 trading_history.jsonl 应追加一条记录"""
    tmpdir = _make_temp_env()
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="buy", price=178.0, shares=20,
                         date_str="2026-05-14")
        history = _read_history(tmpdir)
        assert len(history) == 1
        rec = history[0]
        assert rec["type"] == "buy"
        assert rec["sym"] == "MRVL"
        assert rec["price"] == 178.0
        assert rec["shares"] == 20
    finally:
        shutil.rmtree(tmpdir)


def test_record_buy_history_includes_plan_fields():
    """历史记录应包含止损/目标/场景（来自 daily_plan）"""
    tmpdir = _make_temp_env()
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="buy", price=178.0, shares=20,
                         date_str="2026-05-14")
        history = _read_history(tmpdir)
        rec = history[0]
        assert "stop" in rec
        assert "target1" in rec
        assert "scene" in rec
    finally:
        shutil.rmtree(tmpdir)


def test_record_buy_add_to_existing_position():
    """已有仓位再买入：成本加权平均，股数累加"""
    initial = {
        "cash": 5000,
        "positions": {
            "MRVL": {"cost": 170.0, "shares": 10, "date": "2026-05-13", "note": "T1"}
        }
    }
    tmpdir = _make_temp_env(initial_positions=initial)
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="buy", price=178.0, shares=20,
                         date_str="2026-05-14")
        pos = _read_positions(tmpdir)
        mrvl = pos["positions"]["MRVL"]
        assert mrvl["shares"] == 30  # 10 + 20
        # 加权均价：(170*10 + 178*20) / 30 = (1700+3560)/30 = 175.33...
        expected_cost = round((170.0 * 10 + 178.0 * 20) / 30, 2)
        assert mrvl["cost"] == expected_cost
    finally:
        shutil.rmtree(tmpdir)


def test_record_sell_reduces_shares():
    """卖出后股数减少"""
    initial = {
        "cash": 5000,
        "positions": {
            "MRVL": {"cost": 178.0, "shares": 20, "date": "2026-05-14", "note": "T1"}
        }
    }
    tmpdir = _make_temp_env(initial_positions=initial)
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="sell", price=182.0, shares=10,
                         date_str="2026-05-14")
        pos = _read_positions(tmpdir)
        assert pos["positions"]["MRVL"]["shares"] == 10
    finally:
        shutil.rmtree(tmpdir)


def test_record_sell_all_removes_position():
    """卖出全部仓位：从 positions 中删除该股票"""
    initial = {
        "cash": 5000,
        "positions": {
            "MRVL": {"cost": 178.0, "shares": 20, "date": "2026-05-14", "note": "T1"}
        }
    }
    tmpdir = _make_temp_env(initial_positions=initial)
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="sell", price=182.0, shares=20,
                         date_str="2026-05-14")
        pos = _read_positions(tmpdir)
        assert "MRVL" not in pos["positions"]
    finally:
        shutil.rmtree(tmpdir)


def test_record_stop_appends_history():
    """止损记录应追加到 trading_history，type='stop'"""
    initial = {
        "cash": 5000,
        "positions": {
            "MRVL": {"cost": 178.0, "shares": 20, "date": "2026-05-14", "note": "T1"}
        }
    }
    tmpdir = _make_temp_env(initial_positions=initial)
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="stop", price=173.5, shares=20,
                         date_str="2026-05-14")
        history = _read_history(tmpdir)
        assert history[0]["type"] == "stop"
    finally:
        shutil.rmtree(tmpdir)


def test_record_atomic_write():
    """positions.json 写入应原子替换（无 .tmp 残留）"""
    tmpdir = _make_temp_env()
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            record_trade("MRVL", action="buy", price=178.0, shares=20,
                         date_str="2026-05-14")
        tmp_file = os.path.join(tmpdir, "config", "positions.json.tmp")
        assert not os.path.exists(tmp_file), ".tmp 文件应在写入后被删除"
    finally:
        shutil.rmtree(tmpdir)


# ════════════════════════════════════════════
# Task 4: handle_trade_text 集成测试
# ════════════════════════════════════════════

from agents.entry_guard import handle_trade_text


def test_handle_trade_text_buy_full_flow():
    """
    '买了 MRVL $178 20股' → parse → card（含止损）→ record（写文件）
    返回值应包含止损数字和写入成功的提示
    """
    tmpdir = _make_temp_env()
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            output = handle_trade_text("买了 MRVL $178 20股",
                                       date_str="2026-05-14")
        # 卡片部分：含止损
        assert "173.5" in output, "输出应包含止损数字"
        # 记录部分：写入成功
        assert "已记录" in output or "记录" in output
        # 验证文件已写入
        history = _read_history(tmpdir)
        assert len(history) == 1
        assert history[0]["sym"] == "MRVL"
    finally:
        shutil.rmtree(tmpdir)


def test_handle_trade_text_invalid_format():
    """非交易格式返回格式提示"""
    with patch("agents.entry_guard.get_plan", _mock_get_plan):
        output = handle_trade_text("今天大盘怎么样")
    assert "格式" in output or "买了" in output


def test_handle_trade_text_sell():
    """'卖了 MRVL $182 10股' → sell 记录写入"""
    initial = {
        "cash": 5000,
        "positions": {
            "MRVL": {"cost": 178.0, "shares": 20, "date": "2026-05-14", "note": "T1"}
        }
    }
    tmpdir = _make_temp_env(initial_positions=initial)
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            output = handle_trade_text("卖了 MRVL $182 10股",
                                       date_str="2026-05-14")
        pos = _read_positions(tmpdir)
        assert pos["positions"]["MRVL"]["shares"] == 10
        history = _read_history(tmpdir)
        assert history[0]["type"] == "sell"
    finally:
        shutil.rmtree(tmpdir)


def test_handle_trade_text_no_plan_still_records():
    """无当日计划时：显示简版卡片，但仍记录交易"""
    tmpdir = _make_temp_env()
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", lambda sym, date_str=None: None):
            output = handle_trade_text("买了 XXXX $50 10股",
                                       date_str="2026-05-14")
        # 简版卡片
        assert "XXXX" in output
        # 仍写入历史
        history = _read_history(tmpdir)
        assert len(history) == 1
    finally:
        shutil.rmtree(tmpdir)


def test_handle_trade_text_stop_no_price():
    """'止损了 MRVL' 无价格：仍能处理（price=None）"""
    initial = {
        "cash": 5000,
        "positions": {
            "MRVL": {"cost": 178.0, "shares": 20, "date": "2026-05-14", "note": "T1"}
        }
    }
    tmpdir = _make_temp_env(initial_positions=initial)
    try:
        with patch("agents.entry_guard.BASE", tmpdir), \
             patch("agents.entry_guard.get_plan", _mock_get_plan):
            output = handle_trade_text("止损了 MRVL", date_str="2026-05-14")
        # 不应报错
        assert "MRVL" in output
    finally:
        shutil.rmtree(tmpdir)
