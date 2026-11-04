"""Atualização incremental do histórico de preços."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Protocol

import pandas as pd

from dashboard.market_data import MarketData

HISTORY_YEARS = 5
# Rebusca alguns dias já salvos para pegar correções da fonte (ex.: fechamento ajustado no dia seguinte).
OVERLAP_DAYS = 5


class PriceStore(Protocol):
    def last_date(self, ticker: str) -> date | None: ...

    def save_prices(self, ticker: str, prices: pd.DataFrame) -> int: ...


def sync_history(store: PriceStore, source: MarketData, ticker: str, today: date) -> int:
    """Baixa só o que falta do histórico do ticker e salva. Retorna o número de dias gravados."""
    last = store.last_date(ticker)
    if last is None:
        start = today - timedelta(days=365 * HISTORY_YEARS)
    else:
        start = last - timedelta(days=OVERLAP_DAYS)
    return store.save_prices(ticker, source.history(ticker, start))
