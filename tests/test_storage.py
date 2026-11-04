import importlib.util
import os
import unittest
from datetime import date

import pandas as pd

from dashboard.market_data import FakeMarketData

HAS_SQLALCHEMY = importlib.util.find_spec("sqlalchemy") is not None
# Na CI, os mesmos testes rodam também contra um PostgreSQL real.
DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@unittest.skipUnless(HAS_SQLALCHEMY, "SQLAlchemy não instalado")
class PortfolioTest(unittest.TestCase):
    def setUp(self):
        from dashboard.storage import Base, Portfolio

        self.portfolio = Portfolio(DATABASE_URL)
        self.base = Base
        self.prices = FakeMarketData(today=date(2026, 11, 4)).history("ABC", date(2026, 10, 1))

    def tearDown(self):
        self.base.metadata.drop_all(self.portfolio.engine)
        self.portfolio.close()

    def test_add_list_and_remove(self):
        self.assertTrue(self.portfolio.add("ABC"))
        self.assertFalse(self.portfolio.add("ABC"))
        self.portfolio.add("AAPL")
        self.assertEqual(self.portfolio.tickers(), ["AAPL", "ABC"])
        self.portfolio.remove("ABC")
        self.assertEqual(self.portfolio.tickers(), ["AAPL"])

    def test_save_is_idempotent_and_updates_values(self):
        self.portfolio.add("ABC")
        self.assertEqual(self.portfolio.save_prices("ABC", self.prices), len(self.prices))
        revised = self.prices.copy()
        revised.iloc[-1, revised.columns.get_loc("close")] = 999.0
        self.portfolio.save_prices("ABC", revised)

        stored = self.portfolio.prices("ABC")
        self.assertEqual(len(stored), len(self.prices))
        self.assertEqual(stored["close"].iloc[-1], 999.0)
        self.assertEqual(self.portfolio.last_date("ABC"), date(2026, 11, 4))
        self.assertEqual(list(stored.index), list(self.prices.index))
        self.assertEqual(stored.index.dtype, self.prices.index.dtype)

    def test_missing_values_become_null(self):
        self.portfolio.add("ABC")
        prices = self.prices.copy()
        prices.iloc[0, prices.columns.get_loc("volume")] = float("nan")
        self.portfolio.save_prices("ABC", prices)
        self.assertTrue(pd.isna(self.portfolio.prices("ABC")["volume"].iloc[0]))

    def test_remove_deletes_prices(self):
        self.portfolio.add("ABC")
        self.portfolio.save_prices("ABC", self.prices)
        self.portfolio.remove("ABC")
        self.portfolio.add("ABC")
        self.assertTrue(self.portfolio.prices("ABC").empty)
        self.assertIsNone(self.portfolio.last_date("ABC"))

    def test_unknown_ticker(self):
        with self.assertRaises(KeyError):
            self.portfolio.save_prices("NOPE", self.prices)


if __name__ == "__main__":
    unittest.main()
