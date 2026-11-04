import unittest
from datetime import date

import numpy as np
import pandas as pd

from dashboard import highlights

TODAY = date(2026, 11, 4)


def growth(rate, days=300):
    index = pd.bdate_range(end=TODAY, periods=days)
    return pd.Series(100 * (1 + rate) ** np.arange(days), index=index)


class HighlightsTest(unittest.TestCase):
    def setUp(self):
        self.closes = {"ALTA": growth(0.002), "QUEDA": growth(-0.001), "LATERAL": growth(0.0)}

    def test_best_return(self):
        best = highlights.best_return(self.closes, TODAY)
        self.assertEqual(best.ticker, "ALTA")
        self.assertGreater(best.value, 0.3)

    def test_worst_moving_average_trend(self):
        worst = highlights.worst_moving_average_trend(self.closes, TODAY)
        self.assertEqual(worst.ticker, "QUEDA")
        self.assertLess(worst.value, 0)

    def test_strongest_trend_projects_monthly_growth(self):
        best = highlights.strongest_trend(self.closes, TODAY)
        self.assertEqual(best.ticker, "ALTA")
        self.assertAlmostEqual(best.value, 1.002**21 - 1, places=6)

    def test_trend_is_comparable_between_price_levels(self):
        closes = {"BARATA": growth(0.003) / 50, "CARA": growth(0.001) * 50}
        self.assertEqual(highlights.strongest_trend(closes, TODAY).ticker, "BARATA")

    def test_not_enough_data(self):
        short = {"NOVO": growth(0.01, days=3)}
        self.assertIsNone(highlights.strongest_trend(short, TODAY))
        self.assertIsNone(highlights.worst_moving_average_trend(short, TODAY))
        self.assertIsNone(highlights.best_return({}, TODAY))


class DayTrendTest(unittest.TestCase):
    def test_open_market(self):
        trend = highlights.day_trend(0.012, market_open=True)
        self.assertEqual((trend.title, trend.direction), ("Tendência do dia", "Alta"))
        self.assertEqual(highlights.day_trend(-0.02, market_open=True).direction, "Baixa")

    def test_closed_market(self):
        trend = highlights.day_trend(-0.005, market_open=False)
        self.assertEqual((trend.title, trend.direction), ("Último fechamento", "Baixa"))

    def test_small_change_is_stable(self):
        self.assertEqual(highlights.day_trend(0.0004, market_open=True).direction, "Estável")
        self.assertEqual(highlights.day_trend(-0.0009, market_open=False).direction, "Estável")

    def test_without_quote(self):
        self.assertIsNone(highlights.day_trend(None, market_open=True))


if __name__ == "__main__":
    unittest.main()
