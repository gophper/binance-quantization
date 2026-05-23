import unittest
from unittest.mock import patch

import stockmenubar


class TestStooqMapping(unittest.TestCase):
    def test_stooq_symbol_us_default(self):
        self.assertEqual(stockmenubar._stooq_symbol("AAPL"), "aapl.us")
        self.assertEqual(stockmenubar._stooq_symbol("tsla"), "tsla.us")

    def test_stooq_symbol_market_suffix(self):
        self.assertEqual(stockmenubar._stooq_symbol("0700.HK"), "0700.hk")
        self.assertEqual(stockmenubar._stooq_symbol("0700.hk"), "0700.hk")


class TestStooqParsing(unittest.TestCase):
    def test_fetch_quote_stooq_parses_close(self):
        csv_body = (
            "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
            "tsla.us,2026-01-21,22:00:10,100,110,90,105.25,123\n"
        )

        class FakeResp:
            def __init__(self, text):
                self.text = text

            def raise_for_status(self):
                return None

        with patch.object(stockmenubar._SESSION, "get", return_value=FakeResp(csv_body)):
            q = stockmenubar.fetch_quote_stooq("TSLA")
            self.assertEqual(q.symbol, "TSLA")
            self.assertAlmostEqual(q.price, 105.25)


if __name__ == "__main__":
    unittest.main()

