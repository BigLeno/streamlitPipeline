import unittest

import numpy as np
import pandas as pd

from dashboard import explanations as ex
from dashboard import indicators


def series(values, start="2026-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


class ExplanationsTest(unittest.TestCase):
    def test_every_card_and_tab_has_help(self):
        expected = {
            "best_return", "worst_trend", "strongest_trend", "quote", "candles", "cumulative", "volatility",
            "drawdown", "moving_averages", "rsi", "macd", "monthly", "correlation",
        }
        self.assertEqual(set(ex.HELP), expected)
        self.assertTrue(all(len(text) > 40 for text in ex.HELP.values()))

    def test_pct_uses_brazilian_format(self):
        self.assertEqual(ex.pct(0.1234), "+12,3%")
        self.assertEqual(ex.pct(-0.05), "-5,0%")
        self.assertEqual(ex.pct(0.2, signed=False), "20,0%")

    def test_cumulative(self):
        self.assertEqual(ex.read_cumulative(series([0, 0.05, 0.123])), "No período, o ativo valorizou 12,3%.")
        self.assertIn("desvalorizou 8,0%", ex.read_cumulative(series([0, -0.08])))
        self.assertIn("estável", ex.read_cumulative(series([0, 0.0001])))
        self.assertIsNone(ex.read_cumulative(series([])))

    def test_volatility_compares_with_average(self):
        calm_then_wild = series([0.1] * 50 + [0.4])
        self.assertIn("acima da média", ex.read_volatility(calm_then_wild))
        self.assertIn("perto da média", ex.read_volatility(series([0.2] * 30)))

    def test_drawdown(self):
        dd = indicators.drawdown(series([100, 120, 90, 108]))
        text = ex.read_drawdown(dd)
        self.assertIn("-25,0%", text)
        self.assertIn("05/01/2026", text)  # terceiro pregão de 2026
        self.assertIn("10,0% abaixo do topo", text)
        self.assertIn("no topo", ex.read_drawdown(indicators.drawdown(series([1, 2, 3]))))

    def test_moving_averages(self):
        rising = series(np.linspace(10, 20, 100))
        text = ex.read_moving_averages(
            rising, indicators.moving_average(rising, 21), indicators.moving_average(rising, 63)
        )
        self.assertIn("acima das duas médias", text)
        self.assertIn("MM 21 está acima da MM 63", text)
        short = series(np.linspace(10, 20, 30))
        self.assertIn("Ainda não há pregões suficientes", ex.read_moving_averages(
            short, indicators.moving_average(short, 21), indicators.moving_average(short, 63)
        ))

    def test_rsi_zones(self):
        self.assertIn("sobrecompra", ex.read_rsi(series([50, 75])))
        self.assertIn("sobrevenda", ex.read_rsi(series([50, 25])))
        self.assertIn("neutra", ex.read_rsi(series([50, 55])))

    def test_macd_cross(self):
        macd = pd.DataFrame({"macd": [-1.0, 0.5], "signal": [0.0, 0.0]})
        text = ex.read_macd(macd)
        self.assertIn("acima da linha de sinal", text)
        self.assertIn("último pregão", text)

    def test_monthly(self):
        close = pd.Series(
            [100, 110, 99, 108.9],
            index=pd.to_datetime(["2026-01-02", "2026-01-30", "2026-02-27", "2026-03-31"]),
        )
        text = ex.read_monthly(indicators.monthly_returns(close))
        self.assertIn("Melhor mês: jan/2026 (+10,0%)", text)
        self.assertIn("Pior mês: fev/2026 (-10,0%)", text)
        self.assertIn("67% dos meses", text)

    def test_correlation(self):
        corr = pd.DataFrame(
            [[1, 0.9, -0.2], [0.9, 1, 0.1], [-0.2, 0.1, 1]], index=["A", "B", "C"], columns=["A", "B", "C"]
        )
        self.assertEqual(
            ex.read_correlation(corr, "A"),
            "A anda mais junto com B (0,90) e menos com C (-0,20), o que mais ajuda a diversificar.",
        )
        self.assertIsNone(ex.read_correlation(corr, "Z"))


if __name__ == "__main__":
    unittest.main()
