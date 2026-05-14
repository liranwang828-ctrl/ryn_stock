import json, sys, os
sys.path.insert(0, '/home/lirawang/stock_team')
from agents.persona_engine import PersonaEngine

FIXTURE_DIR = '/home/lirawang/stock_team/tests/fixtures'

def load(name):
    return json.load(open(f'{FIXTURE_DIR}/{name}', encoding="utf-8"))

def test_veto_triggered_when_volume_ratio_low():
    data    = load('persona_data.json')
    persona = load('mark_minervini.json')
    # volume_breakout_ratio=0.96 < 1.4 → veto
    result  = PersonaEngine().evaluate(data, persona)
    assert result['master_signal'] == 'veto'
    assert result['veto_triggered'] is not None
    assert result['master_confidence'] == 0

def test_no_veto_when_all_conditions_pass():
    data    = load('persona_data.json')
    persona = load('mark_minervini.json')
    data2   = {**data, 'volume_breakout_ratio': 1.6, 'ma50': 420, 'ma150': 380,
               'close': 450, 'ma200': 320}
    result  = PersonaEngine().evaluate(data2, persona)
    assert result['veto_triggered'] is None

def test_overbought_check_overrides_signal():
    data    = load('persona_data.json')
    persona = load('mark_minervini.json')
    data2   = {**data, 'volume_breakout_ratio': 1.6, 'rsi14': 85,
               'vcp_detected': False, 'ma50': 420, 'ma150': 380}
    result  = PersonaEngine().evaluate(data2, persona)
    assert result['master_signal'] == 'neutral'
    assert any('超买' in ins for ins in result['triggered_insights'])

def test_entry_score_accumulated():
    data    = load('persona_data.json')
    persona = load('mark_minervini.json')
    data2   = {**data, 'volume_breakout_ratio': 1.6, 'close': 450,
               'ma200': 320, 'ma50': 420, 'ma150': 380, 'rsi14': 65}
    result  = PersonaEngine().evaluate(data2, persona)
    assert result['entry_score'] >= 40

def test_debate_trigger_detected():
    data    = load('persona_data.json')
    persona = load('mark_minervini.json')
    board   = {'TechAgent': {'signal': 'bullish', 'confidence': 72},
               'FundAgent':  {'signal': 'bullish', 'confidence': 60}}
    result  = PersonaEngine().evaluate(data, persona, board_signals=board)
    assert result['debate_insight'] is not None
    assert '超买' in result['debate_insight']

def test_stop_loss_pct_returned():
    data    = load('persona_data.json')
    persona = load('mark_minervini.json')
    result  = PersonaEngine().evaluate(data, persona)
    assert result['stop_loss_pct'] == 0.08

def test_position_max_pct_returned():
    data    = load('persona_data.json')
    persona = load('mark_minervini.json')
    result  = PersonaEngine().evaluate(data, persona)
    assert result['position_max_pct'] == 10

# ─── 新增：分层知识库 + evaluate_with_questions 测试 ───────────────────────────

import pytest
from agents.persona_engine import load_persona_full

def test_load_persona_full_returns_worldview():
    """load_persona_full 应该加载 worldview.md 内容"""
    persona = load_persona_full("mark_minervini")
    assert "worldview" in persona
    assert len(persona["worldview"]) > 100

def test_load_persona_full_returns_questions():
    """load_persona_full 应该加载 questions.json"""
    persona = load_persona_full("mark_minervini")
    assert "questions" in persona
    assert len(persona["questions"]["sequence"]) >= 3

def test_early_stop_when_q1_fails():
    """Minervini Q1 失败时应返回标准早停输出"""
    engine = PersonaEngine()
    data = {"ma200": 200, "ma200_slope": -1, "current_price": 150}
    result = engine.evaluate_with_questions("mark_minervini", data)
    assert result["signal"] == "neutral"
    assert "Stage 2" in result["core_argument"]
    assert result["stopped_at_question"] == "q1"

def test_natural_adversaries_loaded():
    """自然对手应该从 questions.json 加载"""
    persona = load_persona_full("mark_minervini")
    assert "natural_adversaries" in persona["questions"]
    assert "peter_lynch" in persona["questions"]["natural_adversaries"]

def test_all_7_masters_loadable():
    """所有7位大师都应该可以加载"""
    masters = [
        "mark_minervini", "stan_druckenmiller", "howard_marks",
        "nassim_taleb", "george_soros", "jesse_livermore", "peter_lynch"
    ]
    for name in masters:
        p = load_persona_full(name)
        assert "worldview" in p, f"{name} missing worldview"
        assert "questions" in p, f"{name} missing questions"
