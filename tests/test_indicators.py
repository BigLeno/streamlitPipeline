import unittest

import numpy as np
import pandas as pd

from dashboard import indicators


def series(values, start="2026-01-01", freq="B"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq=freq), dtype=float)


class IndicatorsTest(unittest.TestCase):
    def test_cumulative_return(self):
        result = indicators.cumulative_return(series([10, 11, 9.9]))
        np.testing.assert_allclose(result.to_numpy(), [0, 0.1, -0.01])

    def test_drawdown(self):
        result = indicators.drawdown(series([100, 120, 90, 130]))
        np.testing.assert_allclose(result.to_numpy(), [0, 0, -0.25, 0])

    def test_rolling_volatility_of_constant_growth_is_zero(self):
        close = series(100 * 1.01 ** np.arange(30))
        result = indicators.rolling_volatility(close, window=21).dropna()
        np.testing.assert_allclose(result.to_numpy(), 0, atol=1e-12)

    def test_moving_average(self):
        result = indicators.moving_average(series([1, 2, 3, 4]), 2)
        np.testing.assert_allclose(result.to_numpy()[1:], [1.5, 2.5, 3.5])

    def test_rsi_bounds_and_extremes(self):
        rising = indicators.rsi(series(range(1, 40)))
        self.assertTrue(rising.iloc[:14].isna().all())
        self.assertEqual(rising.iloc[-1], 100)
        falling = indicators.rsi(series(range(40, 1, -1)))
        self.assertAlmostEqual(falling.iloc[-1], 0)
        noisy = indicators.rsi(series(100 + np.random.default_rng(1).normal(0, 1, 200).cumsum()))
        self.assertTrue(noisy.dropna().between(0, 100).all())

    def test_macd_of_constant_price_is_zero(self):
        result = indicators.macd(series([50] * 40))
        np.testing.assert_allclose(result.to_numpy(), 0)

    def test_monthly_returns_use_previous_month_close(self):
        close = pd.Series(
            [100, 110, 121, 133.1],
            index=pd.to_datetime(["2026-01-02", "2026-01-30", "2026-02-27", "2026-03-31"]),
        )
        table = indicators.monthly_returns(close)
        self.assertEqual(list(table.index), [2026])
        self.assertEqual(list(table.columns), list(range(1, 13)))
        np.testing.assert_allclose(table.loc[2026, [1, 2, 3]].to_numpy(), [0.10, 0.10, 0.10])
        self.assertTrue(table.loc[2026, 4:].isna().all())

    def test_monthly_returns_across_years(self):
        close = pd.Series([100, 90], index=pd.to_datetime(["2025-12-31", "2026-01-30"]))
        table = indicators.monthly_returns(close)
        self.assertAlmostEqual(table.loc[2026, 1], -0.10)

    def test_correlation_uses_common_dates(self):
        a = series([1, 2, 3, 2, 4, 5, 4, 6] * 4)
        b = a * 2
        c = series(list(reversed([1, 2, 3, 2, 4, 5, 4, 6] * 4)))
        result = indicators.returns_correlation({"A": a, "B": b, "C": c})
        self.assertAlmostEqual(result.loc["A", "B"], 1.0)
        self.assertLess(result.loc["A", "C"], 0)


if __name__ == "__main__":
    unittest.main()
