# tests/unit/core/test_evidence_exporter.py
import os
import sys
import unittest
from datetime import datetime, timedelta
import tempfile

from stock_team.core.export_trade_evidence import (
    parse_fills_markdown,
    shanghai_to_et,
    calculate_metrics
)

class TestEvidenceExporter(unittest.TestCase):

    def test_timezone_conversion(self):
        # Shanghai local time: 2026-06-04 22:28:37
        # Expected ET: 2026-06-04 10:28:37 (EDT summer saving, -12 hours)
        sh_time = "2026-06-04 22:28:37"
        et_time = shanghai_to_et(sh_time)
        self.assertEqual(et_time.year, 2026)
        self.assertEqual(et_time.month, 6)
        self.assertEqual(et_time.day, 4)
        self.assertEqual(et_time.hour, 10)
        self.assertEqual(et_time.minute, 28)
        self.assertEqual(et_time.second, 37)

    def test_parse_fills_markdown_table(self):
        markdown_content = """
# Journal Entry
| Time | Side | Quantity | Price | Amount | P/L |
|---|---:|---:|---:|---:|---:|
| 2026-06-04 22:28:37 | Buy | 100 | 31.44 | 3,144.00 | |
| 2026-06-04 22:37:27 | Buy | 50 | 30.64 | 1,532.00 | |
| 2026-06-05 03:56:56 | Sell | 100 | 29.40 | 2,940.00 | |
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md", encoding="utf-8") as temp:
            temp.write(markdown_content)
            temp_path = temp.name

        try:
            fills = parse_fills_markdown(temp_path)
            self.assertEqual(len(fills), 3)
            self.assertEqual(fills[0]["side"], "Buy")
            self.assertEqual(fills[0]["quantity"], 100)
            self.assertEqual(fills[0]["price"], 31.44)
            self.assertEqual(fills[1]["quantity"], 50)
            self.assertEqual(fills[2]["side"], "Sell")
            self.assertEqual(fills[2]["price"], 29.40)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_calculate_metrics(self):
        # Create mock regular market hours bars (09:30 to 16:00 ET)
        base_time = datetime(2026, 6, 4, 9, 30)
        bars = []
        for i in range(391):  # 390 minutes in regular session + 1
            curr_time = base_time + timedelta(minutes=i)
            # Make price climb and then drop
            price = 30.0 + (i / 100.0) if i < 200 else 32.0 - ((i - 200) / 100.0)
            bars.append({
                "time_et": curr_time,
                "open": price,
                "high": price + 0.05,
                "low": price - 0.05,
                "close": price,
                "volume": 1000
            })
            
        prev_close = 29.0
        metrics = calculate_metrics(bars, prev_close)
        
        self.assertIsNotNone(metrics)
        self.assertIn("open", metrics)
        self.assertIn("close", metrics)
        self.assertEqual(metrics["open"], 30.0)
        self.assertGreater(metrics["high"], 32.0)
        # Check high time is around i = 200 (12:50 ET)
        self.assertEqual(metrics["high_time_et"], "12:50")
        self.assertIn("day_change", metrics)
        self.assertIn("last_30m_change", metrics)
        self.assertIn("vwap", metrics)

if __name__ == "__main__":
    unittest.main()
