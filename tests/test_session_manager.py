import sys, os, json, pytest
sys.path.insert(0, os.path.expanduser("~/stock_team"))

@pytest.fixture(autouse=True)
def tmp_state(monkeypatch, tmp_path):
    monkeypatch.setattr("agents.session_manager.BASE", str(tmp_path))
    yield tmp_path

from agents.session_manager import advance_node, get_status, NODE_NAMES

def test_initial_state_node1():
    status = get_status()
    assert status["node"] == 1
    assert status["node_name"] == NODE_NAMES[1]
    assert status["active_symbols"] == []

def test_advance_node():
    advance_node(2)
    status = get_status()
    assert status["node"] == 2
    assert status["node_name"] == NODE_NAMES[2]

def test_advance_node_invalid():
    with pytest.raises(ValueError):
        advance_node(0)
    with pytest.raises(ValueError):
        advance_node(7)

def test_add_symbol():
    from agents.session_manager import add_symbol
    add_symbol("MRVL")
    add_symbol("AAOI")
    status = get_status()
    assert "MRVL" in status["active_symbols"]
    assert "AAOI" in status["active_symbols"]

def test_add_symbol_dedup():
    from agents.session_manager import add_symbol
    add_symbol("MRVL")
    add_symbol("MRVL")
    assert get_status()["active_symbols"].count("MRVL") == 1

from agents.session_manager import push_alert, drain_alerts

def test_push_and_drain():
    push_alert("signal", "MRVL", "⚡入场信号 评分7.7/10",
               {"score": 7.7, "rs": 4.5, "stop": 173.5})
    push_alert("scene_change", "AAOI", "场景变化 B→D",
               {"from": "B", "to": "D"})
    alerts = drain_alerts()
    assert len(alerts) == 2
    assert alerts[0]["type"] == "signal"
    assert alerts[0]["symbol"] == "MRVL"
    assert alerts[1]["type"] == "scene_change"

def test_drain_clears_queue():
    push_alert("heartbeat", "ALL", "📊场景播报", {})
    drain_alerts()   # 消费
    assert drain_alerts() == []   # 再次应为空

def test_push_writes_discussion_board(tmp_state):
    push_alert("signal", "MRVL", "⚡入场信号", {"score": 8.0})
    board = os.path.join(str(tmp_state), "discussion_board.jsonl")
    assert os.path.exists(board)
    line = json.loads(open(board).readline())
    assert line["type"] == "signal"
    assert line["symbol"] == "MRVL"
    assert "time" in line

from agents.session_manager import handle_text
from unittest.mock import patch

def test_handle_text_trade_buy():
    with patch("agents.session_manager.handle_trade_text",
               return_value="MOCK_CARD") as mock_fn:
        result = handle_text("买了 MRVL $178 20股")
    mock_fn.assert_called_once()
    assert result == "MOCK_CARD"

def test_handle_text_trade_sell():
    with patch("agents.session_manager.handle_trade_text",
               return_value="MOCK_CARD") as mock_fn:
        result = handle_text("卖了 AAOI $213 10股")
    mock_fn.assert_called_once()

def test_handle_text_not_trade():
    result = handle_text("MRVL 今天还能买吗")
    assert result is None

def test_handle_text_stop_loss():
    with patch("agents.session_manager.handle_trade_text",
               return_value="MOCK_CARD") as mock_fn:
        result = handle_text("止损了 MRVL")
    mock_fn.assert_called_once()

from agents.session_manager import run_node
from unittest.mock import MagicMock

def test_run_node1_no_symbols():
    out = run_node(1)
    assert "节点1" in out
    assert "未指定标的" in out or "标的" in out

def test_run_node2_no_symbols():
    out = run_node(2)
    assert "未设置" in out or "标的" in out

def test_run_node1_calls_premarket(tmp_state):
    mock_result = MagicMock()
    mock_result.stdout = "盘前分析完成：MRVL RS+5%"
    mock_result.returncode = 0
    with patch("agents.session_manager.subprocess") as mock_sub:
        mock_sub.run.return_value = mock_result
        out = run_node(1, symbols=["MRVL", "AAOI"])
    mock_sub.run.assert_called_once()
    call_args = mock_sub.run.call_args[0][0]
    assert "premarket.py" in call_args[1]
    assert "MRVL" in call_args
    assert "AAOI" in call_args

def test_run_node2_calls_daily_plan(tmp_state):
    mock_result = MagicMock()
    mock_result.stdout = "计划生成完成"
    mock_result.returncode = 0
    with patch("agents.session_manager.subprocess") as mock_sub:
        mock_sub.run.return_value = mock_result
        out = run_node(2, symbols=["MRVL"])
    mock_sub.run.assert_called_once()
    call_args = mock_sub.run.call_args[0][0]
    assert "daily_plan.py" in call_args[1]
    assert "generate" in call_args

def test_run_node_updates_state(tmp_state):
    with patch("agents.session_manager.subprocess"):
        run_node(2, symbols=["MRVL", "AAOI"])
    status = get_status()
    assert status["node"] == 2
    assert "MRVL" in status["active_symbols"]

def test_run_node_includes_next_prompt():
    out = run_node(1)
    # 节点1结束后应有引导用户说关注标的的提示
    assert "标的" in out
