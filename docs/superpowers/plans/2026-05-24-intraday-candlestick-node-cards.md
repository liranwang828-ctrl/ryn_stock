# Intraday Candlestick Node Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact intraday card visualization that shows the last 10 price-derived candlesticks per symbol with horizontal node lines, without increasing poll workload.

**Architecture:** The dashboard will render a lightweight SVG candlestick strip inside each intraday card using data that already exists in cached or persisted snapshots. Polling continues to write the same operational snapshots and dashboard cache, but it does not do any new heavy computation for chart rendering. The dashboard writer prepares a tiny per-symbol view model, and the template draws it as a self-contained SVG so there is no new client-side dependency.

**Tech Stack:** Python stdlib, existing JSON/JSONL dashboard pipeline, Jinja2 templates, inline SVG, pytest.

---

### Task 1: Add a compact intraday chart view model

**Files:**
- Modify: `agents/dashboard_writer.py`
- Modify: `tests/test_dashboard_writer.py`

- [ ] **Step 1: Write the failing test**

Add a focused regression test that proves the dashboard context exposes a 10-bar mini chart payload for a symbol with intraday history:

```python
def test_build_dashboard_context_includes_intraday_mini_chart(tmp_path):
    from agents.dashboard_writer import build_dashboard_context

    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()

    (base / "config" / "positions.json").write_text("{\"positions\": {}, \"_excluded\": []}", encoding="utf-8")
    (base / "config" / "poll_config.json").write_text("{\"default_symbols\": [\"NVDA\"]}", encoding="utf-8")

    intraday_path = base / "findings" / "intraday_snapshot_2026-05-24_NVDA.jsonl"
    intraday_path.write_text(
        "\n".join([
            "{\"ts\":\"09:30:00\",\"meta\":{\"sym\":\"NVDA\",\"date\":\"2026-05-24\"},\"price_now\":{\"price\":100.0},\"plan_vs_now\":{},\"node_snapshot\":{\"entry_base\":98.0,\"hard_stop\":95.0,\"flex_add\":104.0,\"flex_reduce\":108.0,\"target\":112.0}}",
            "{\"ts\":\"09:35:00\",\"meta\":{\"sym\":\"NVDA\",\"date\":\"2026-05-24\"},\"price_now\":{\"price\":101.0},\"plan_vs_now\":{},\"node_snapshot\":{\"entry_base\":98.0,\"hard_stop\":95.0,\"flex_add\":104.0,\"flex_reduce\":108.0,\"target\":112.0}}",
        ]) + "\n",
        encoding="utf-8",
    )

    ctx = build_dashboard_context("2026-05-24", symbols=["NVDA"], base_dir=str(base))

    assert ctx["intraday"]["NVDA"].get("mini_chart")
    assert len(ctx["intraday"]["NVDA"]["mini_chart"]["candles"]) <= 10
    assert ctx["intraday"]["NVDA"]["mini_chart"]["nodes"]["hard_stop"]["price"] == 95.0
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -k mini_chart -v
```

Expected: fail because `mini_chart` is not yet populated.

- [ ] **Step 3: Write the minimal implementation**

Add a helper in `agents/dashboard_writer.py` that derives a tiny chart payload from existing intraday JSONL rows or cached intraday state, without touching `poll.py`. The chart uses price-derived candles, not a new market-data fetch. Keep the payload minimal:

```python
def _build_mini_chart(rows: list[dict], node_snapshot: dict) -> dict:
    prices = []
    for row in rows[-10:]:
        price = (row.get("price_now") or {}).get("price")
        if price is not None:
            prices.append({
                "ts": row.get("ts"),
                "price": float(price),
                "chg_pct": float((row.get("price_now") or {}).get("chg_pct") or 0.0),
            })

    candles = []
    prev_close = prices[0]["price"] if prices else None
    for idx, point in enumerate(prices):
        close = point["price"]
        open_ = prev_close if prev_close is not None else close
        top = max(open_, close)
        bottom = min(open_, close)
        wick = max(0.2, abs(point["chg_pct"]) * 0.15)
        candles.append({
            "ts": point["ts"],
            "open": round(open_, 2),
            "high": round(top + wick, 2),
            "low": round(max(0.0, bottom - wick), 2),
            "close": round(close, 2),
            "dir": "up" if close >= open_ else "down",
        })
        prev_close = close

    return {
        "candles": candles,
        "nodes": {
            "entry_base": {"price": node_snapshot.get("entry_base"), "label": "entry_base"},
            "hard_stop": {"price": node_snapshot.get("hard_stop"), "label": "hard_stop"},
            "flex_add": {"price": node_snapshot.get("flex_add"), "label": "flex_add"},
            "flex_reduce": {"price": node_snapshot.get("flex_reduce"), "label": "flex_reduce"},
            "target": {"price": node_snapshot.get("target"), "label": "target"},
        },
    }
```

Attach the result to each symbol in `build_dashboard_context()` as `intraday[sym]["mini_chart"]`.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -k mini_chart -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/dashboard_writer.py tests/test_dashboard_writer.py
git commit -m "feat: add mini intraday chart view model"
```

---

### Task 2: Render the candlestick card in the template

**Files:**
- Modify: `templates/daily_dashboard.html.j2`
- Modify: `templates/styles.css.j2`

- [ ] **Step 1: Write the failing template expectation**

Add a regression test that renders the dashboard HTML and asserts the mini chart scaffold is present:

```python
def test_dashboard_renders_mini_candle_card_markup(tmp_path):
    from agents.dashboard_writer import write_dashboard

    base = tmp_path
    (base / "findings").mkdir()
    (base / "reports").mkdir()
    (base / "config").mkdir()
    (base / "learning").mkdir()
    (base / "config" / "positions.json").write_text("{\"positions\": {}, \"_excluded\": []}", encoding="utf-8")
    (base / "config" / "poll_config.json").write_text("{\"default_symbols\": [\"NVDA\"]}", encoding="utf-8")
    (base / "findings" / "intraday_snapshot_2026-05-24_NVDA.jsonl").write_text(
        "{\"ts\":\"09:30:00\",\"meta\":{\"sym\":\"NVDA\",\"date\":\"2026-05-24\"},\"price_now\":{\"price\":100.0},\"plan_vs_now\":{},\"node_snapshot\":{\"entry_base\":98.0,\"hard_stop\":95.0,\"flex_add\":104.0,\"flex_reduce\":108.0,\"target\":112.0}}\n",
        encoding="utf-8",
    )

    out = write_dashboard("2026-05-24", symbols=["NVDA"], base_dir=str(base))
    html = (base / "reports" / "daily_dashboard_2026-05-24.html").read_text(encoding="utf-8")

    assert out.endswith("daily_dashboard_2026-05-24.html")
    assert "mini-candle-strip" in html
    assert "node-line" in html
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -k mini_candle_card -v
```

Expected: fail because the template does not yet include the new markup.

- [ ] **Step 3: Write the template markup**

Add a compact intraday card block to `templates/daily_dashboard.html.j2` that uses the `mini_chart` payload and renders:

```jinja2
<div class="mini-candle-card">
  <div class="mini-candle-head">
    <span class="mini-candle-symbol">{{ sym }}</span>
    <span class="mini-candle-meta">{{ intraday[sym].price_now.price }}</span>
  </div>
  <svg class="mini-candle-strip" viewBox="0 0 520 240" role="img" aria-label="intraday candlestick chart">
    {% set chart = intraday[sym].get('mini_chart') or {} %}
    {% for candle in chart.get('candles') or [] %}
      {# draw candle body and wick here #}
    {% endfor %}
    {% for name, node in (chart.get('nodes') or {}).items() %}
      {# draw horizontal node line across the strip here #}
    {% endfor %}
  </svg>
</div>
```

Update `templates/styles.css.j2` to keep the card compact and readable:

```css
.mini-candle-card { border: 1px solid rgba(255,255,255,.06); border-radius: 12px; padding: 10px; background: rgba(255,255,255,.02); }
  .mini-candle-strip { width: 100%; height: 240px; display: block; }
  .mini-node-line { stroke-width: 1.6; opacity: 0.9; }
  .mini-node-label { font-size: 11px; font-weight: 700; }
```

Keep the layout in the left variant only: a full-width candlestick strip with horizontal node lines running across the chart.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
python -m pytest tests/test_dashboard_writer.py -k mini_candle_card -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/daily_dashboard.html.j2 templates/styles.css.j2 tests/test_dashboard_writer.py
git commit -m "feat: render intraday candlestick node cards"
```

---

### Task 3: Verify dashboard load and keep poll cost flat

**Files:**
- Modify: `agents/dashboard_writer.py`
- Modify: `agents/dashboard_server.py` only if needed for a smoke check

- [ ] **Step 1: Write the verification check**

Confirm the homepage still renders and the new chart does not trigger any new poll-side work. The important check is that the dashboard consumes the already-written intraday snapshots and cache only.

- [ ] **Step 2: Run the smoke tests**

Run:
```bash
python -m py_compile agents/dashboard_writer.py agents/poll.py
python agents/dashboard_server.py
```

Then open:
```text
http://127.0.0.1:8080/
```

Expected: dashboard loads, intraday cards show the new candlestick strip, and no extra work was added to `poll.py` beyond existing snapshot writes.

- [ ] **Step 3: Commit**

```bash
git add agents/dashboard_writer.py agents/dashboard_server.py
git commit -m "chore: verify candlestick intraday dashboard render"
```

---

## Verification Notes

- Keep the chart rendering entirely read-only from the dashboard side.
- Do not add new per-tick analysis in `poll.py`.
- Use the existing intraday JSONL/cache inputs as the only data source.
- Prefer SVG over a new JS charting library to keep the page light.
