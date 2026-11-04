"""Teste de fumaça do app inteiro com dados sintéticos (roda no CI, onde o Streamlit está instalado)."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None
APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


@unittest.skipUnless(HAS_STREAMLIT, "Streamlit não instalado")
class AppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        env = {
            "MARKET_DATA": "fake",
            "DATABASE_URL": f"sqlite:///{self.tmp.name}/test.db",
            "DEFAULT_TICKERS": "AAA,BBB",
        }
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        # O Streamlit guarda caches no processo; sem limpar, um teste herda a carteira do anterior.
        import streamlit as st

        st.cache_resource.clear()
        st.cache_data.clear()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_app(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(APP, default_timeout=60)
        app.run()
        self.assertFalse(app.exception, [e.value for e in app.exception])
        return app

    def test_renders_dashboard_with_default_tickers(self):
        app = self.run_app()
        self.assertEqual(app.title[0].value, "💹 Dashboard Financeiro")
        self.assertEqual(app.sidebar.selectbox[0].options, ["AAA", "BBB"])
        labels = [metric.label for metric in app.metric]
        self.assertIn("Maior retorno em 12 meses", labels)
        self.assertIn("AAA agora", labels)
        trend = next(metric for metric in app.metric if metric.label.endswith("(AAA)"))
        self.assertIn(trend.value, {"Alta", "Baixa", "Estável"})
        self.assertTrue(any("Atualizado às" in caption.value for caption in app.caption))

    def test_ibovespa_is_selected_by_default(self):
        with mock.patch.dict(os.environ, {"DEFAULT_TICKERS": "AAA,^BVSP"}):
            app = self.run_app()
        self.assertEqual(app.sidebar.selectbox[0].value, "^BVSP")
        self.assertIn("^BVSP agora", [metric.label for metric in app.metric])

    def test_switching_ticker_and_period(self):
        app = self.run_app()
        app.sidebar.selectbox[0].select("BBB").run()
        app.sidebar.selectbox[1].select("1 mês").run()
        self.assertFalse(app.exception)
        self.assertIn("BBB agora", [metric.label for metric in app.metric])


if __name__ == "__main__":
    unittest.main()
