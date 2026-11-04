import unittest
from datetime import date

import pandas as pd

from dashboard.market_data import FakeMarketData, Quote, market_data_from_env
from dashboard.sync import sync_history

TODAY = date(2026, 11, 4)


class FakeMarketDataTest(unittest.TestCase):
    def setUp(self):
        self.source = FakeMarketData(today=TODAY)

    def test_history_is_deterministic_and_consistent(self):
        first = self.source.history("ABC", date(2026, 1, 1))
        second = self.source.history("ABC", date(2026, 6, 1))
        self.assertEqual(list(first.columns), ["open", "high", "low", "close", "volume"])
        pd.testing.assert_series_equal(first["close"].loc["2026-06-01":], second["close"])
        self.assertTrue((first["high"] >= first["low"]).all())
        self.assertNotEqual(first["close"].iloc[-1], self.source.history("XYZ", date(2026, 1, 1))["close"].iloc[-1])

    def test_quote(self):
        quote = self.source.quote("ABC")
        self.assertIsInstance(quote, Quote)
        self.assertIsNone(self.source.quote("???"))

    def test_quote_change(self):
        quote = Quote(price=110, previous_close=100)
        self.assertEqual(quote.change, 10)
        self.assertAlmostEqual(quote.change_percent, 0.10)
        self.assertIsNone(Quote(price=1, previous_close=None).change_percent)

    def test_source_from_env(self):
        self.assertIsInstance(market_data_from_env("fake"), FakeMarketData)
        with self.assertRaises(ValueError):
            market_data_from_env("bloomberg")


class MemoryStore:
    def __init__(self):
        self.data = {}

    def last_date(self, ticker):
        prices = self.data.get(ticker)
        return None if prices is None or prices.empty else prices.index.max().date()

    def save_prices(self, ticker, prices):
        current = self.data.get(ticker, prices.iloc[0:0])
        merged = pd.concat([current, prices])
        self.data[ticker] = merged[~merged.index.duplicated(keep="last")].sort_index()
        return len(prices)


class RecordingSource(FakeMarketData):
    def __init__(self, today):
        super().__init__(today)
        self.starts = []

    def history(self, ticker, start):
        self.starts.append(start)
        return super().history(ticker, start)


class SyncTest(unittest.TestCase):
    def test_first_sync_downloads_five_years_then_only_the_gap(self):
        store, source = MemoryStore(), RecordingSource(date(2026, 10, 30))
        first = sync_history(store, source, "ABC", date(2026, 10, 30))
        self.assertGreater(first, 1200)
        self.assertEqual(source.starts[0], date(2021, 10, 31))

        source.today = TODAY
        sync_history(store, source, "ABC", TODAY)
        self.assertEqual(source.starts[1], date(2026, 10, 25))  # 5 dias de sobreposição
        self.assertEqual(store.last_date("ABC"), TODAY)
        self.assertFalse(store.data["ABC"].index.duplicated().any())


if __name__ == "__main__":
    unittest.main()
