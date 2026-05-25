def test_focus_symbols_are_treated_as_active():
    from agents.poll import classify_poll_symbols

    active, passive = classify_poll_symbols(
        ["MRVL", "RGTI", "BABA"],
        real_positions={},
        entry_decisions={},
        focus_stocks=["MRVL", "RGTI"],
    )

    assert "MRVL" in active
    assert "RGTI" in active
    assert "BABA" in passive
