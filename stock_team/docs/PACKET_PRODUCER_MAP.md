# Packet Producer Map

This mapping document binds execution modules in `stock_team` to their respective output Evidence Packets required by `investing-os`.

---

## 1. Map Matrix

| Target Evidence Packet | Producer Module | Input Files | Output Location | Smoke Test |
| :--- | :--- | :--- | :--- | :--- |
| **`pre_market_environment_packet`** | [cli.py](file:///d:/gemini/lianghua/stock_team/cli.py) | `--universe <json>` | `findings/pre-market-environment-packet.md` | `tests/unit/core/test_cli.py` |
| **`pre_market_packet`** | [cli.py](file:///d:/gemini/lianghua/stock_team/cli.py) | `--watchlist <json>`<br>`--decision-sheet <json>` | `findings/pre-market-packet-YYYY-MM-DD.md` | `tests/unit/core/test_cli.py` |
| **`contextual_trade_evidence_packet`**| [export_trade_evidence.py](file:///d:/gemini/lianghua/stock_team/core/export_trade_evidence.py) | `--fills <fills_md>` | `findings/contextual-trade-evidence-packet.md`| `tests/unit/core/test_evidence_exporter.py` |
| **`company_research_packet`** | [company_profile_fetcher.py](file:///d:/gemini/lianghua/stock_team/data_ingest/company_profile_fetcher.py) | `--symbol <SYM>` | `findings/company-packet-SYM.md` | `tests/unit/core/test_cli.py` |
| **`runtime_monitor_packet`** | [cli.py](file:///d:/gemini/lianghua/stock_team/cli.py) | `--symbols <symbols_csv>` | `findings/runtime-monitor-packet.md` | `tests/unit/core/test_cli.py` |

---

## 2. Identified Functional Gaps

As we progress towards full stable integration with `investing-os`, the following gaps are noted in the evidence generation pipeline:

### 2.1 Stage 0 Polygon Cache and Freshness Map
- **Gap**: The `market-context` (Stage 0) command pulls multiple symbols sequentially from Polygon.io. On repeating runs, this causes API limit exhaustion and socket timeouts.
- **Proposed Action**: Cache results inside `learning/dashboard_cache.json` or a dedicated `data_cache/` directory. Check cache timestamps to determine if they are fresher than 1 hour. Update headers to mark lines as `polygon_live` or `polygon_cache` accordingly.

### 2.2 Live Catalyst Calendar Integration
- **Gap**: News catalyst tables currently show fallback indicators or are populated with mock data if yfinance news fails.
- **Proposed Action**: Connect directly to Polygon's Reference News or Ticker Events API endpoint to parse corporate earnings dates, dividends, and macro announcements without subjective commentary.
