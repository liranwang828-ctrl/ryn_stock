import json


def test_resolve_tracking_symbol_maps_leveraged_tool_to_underlying(tmp_path):
    from stock_team.utils.capsule_utils import resolve_tracking_symbol, get_capsule_dir

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "leveraged_pairs.json").write_text(json.dumps({
        "MRVL": {"sym": "MRVU", "leverage": 2, "direction": "long"},
        "NBIS": {"sym": "NBIL", "leverage": 2, "direction": "long"},
    }), encoding="utf-8")

    assert resolve_tracking_symbol("MRVU", str(tmp_path)) == "MRVL"
    assert resolve_tracking_symbol("MUU", str(tmp_path)) == "MUU"
    assert resolve_tracking_symbol("mrvl", str(tmp_path)) == "MRVL"
    assert resolve_tracking_symbol("NVDA", str(tmp_path)) == "NVDA"
    assert get_capsule_dir("MRVU", str(tmp_path)).endswith(r"findings\symbols\MRVL")


def test_resolve_tracking_symbol_maps_runtime_leveraged_symbols_to_underlying(tmp_path):
    from stock_team.utils.capsule_utils import resolve_tracking_symbol, get_capsule_dir

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "leveraged_pairs.json").write_text(json.dumps({
        "MU": {"sym": "MUU", "leverage": 2, "direction": "long"},
        "COHR": {"sym": "COHX", "leverage": 2, "direction": "long"},
        "ORCL": {"sym": "ORCX", "leverage": 2, "direction": "long"},
        "INTC": {"sym": "INTW", "leverage": 2, "direction": "long"},
    }), encoding="utf-8")

    assert resolve_tracking_symbol("MUU", str(tmp_path)) == "MU"
    assert resolve_tracking_symbol("COHX", str(tmp_path)) == "COHR"
    assert resolve_tracking_symbol("ORCX", str(tmp_path)) == "ORCL"
    assert resolve_tracking_symbol("INTW", str(tmp_path)) == "INTC"
    assert get_capsule_dir("MUU", str(tmp_path)).endswith(r"findings\symbols\MU")
