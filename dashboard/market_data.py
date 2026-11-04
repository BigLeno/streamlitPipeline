"""Fontes de dados de mercado: Yahoo Finance (via yfinance) e uma fonte sintética para demo e testes."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PRICE_COLUMNS = ["open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class Quote:
    price: float
    previous_close: float | None

    @property
    def change(self) -> float | None:
        return None if self.previous_close is None else self.price - self.previous_close

    @property
    def change_percent(self) -> float | None:
        if not self.previous_close:
            return None
        return self.price / self.previous_close - 1


class MarketData(Protocol):
    def history(self, ticker: str, start: date) -> pd.DataFrame:
        """Preços diários desde `start`: índice de datas (sem fuso) e colunas PRICE_COLUMNS."""

    def quote(self, ticker: str) -> Quote | None:
        """Cotação mais recente, ou None se o ticker não existir."""


def to_date_index(values) -> pd.DatetimeIndex:
    """Índice de datas sem fuso e com unidade fixa, para que dados de fontes diferentes sejam comparáveis."""
    return pd.DatetimeIndex(pd.to_datetime(values), name="date").as_unit("ns")


def empty_prices() -> pd.DataFrame:
    return pd.DataFrame(columns=PRICE_COLUMNS, index=to_date_index([]), dtype=float)


class YahooMarketData:
    def history(self, ticker: str, start: date) -> pd.DataFrame:
        import yfinance as yf

        raw = yf.Ticker(ticker).history(start=start.isoformat(), interval="1d", auto_adjust=False)
        if raw.empty:
            return empty_prices()
        prices = raw.rename(columns=str.lower)[PRICE_COLUMNS]
        prices.index = to_date_index(raw.index.tz_localize(None).normalize())
        return prices.dropna(subset=["close"])

    def quote(self, ticker: str) -> Quote | None:
        import yfinance as yf

        try:
            info = yf.Ticker(ticker).fast_info
            price = info.last_price
            previous_close = info.previous_close
        except Exception:
            logger.warning("Cotação indisponível para %s", ticker, exc_info=True)
            return None
        if price is None or np.isnan(price):
            return None
        return Quote(price=float(price), previous_close=float(previous_close) if previous_close else None)


class FakeMarketData:
    """Passeio aleatório determinístico por ticker. Útil para demonstração sem internet e para testes."""

    def __init__(self, today: date | None = None) -> None:
        self.today = today or date.today()

    def history(self, ticker: str, start: date) -> pd.DataFrame:
        days = pd.bdate_range(start=start, end=self.today, name="date")
        if len(days) == 0:
            return empty_prices()
        seed = int(hashlib.sha256(ticker.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        # Gera desde uma data fixa para que o mesmo dia tenha sempre o mesmo preço.
        all_days = pd.bdate_range(start="2015-01-01", end=self.today)
        drift = rng.uniform(-0.0004, 0.0008)
        returns = rng.normal(drift, rng.uniform(0.01, 0.025), len(all_days))
        close = pd.Series(rng.uniform(10, 200) * np.exp(np.cumsum(returns)), index=all_days)
        close = close.loc[days]
        spread = close * rng.uniform(0.002, 0.02, len(close))
        return pd.DataFrame(
            {
                "open": close.shift(1).fillna(close).to_numpy(),
                "high": (close + spread).to_numpy(),
                "low": (close - spread).to_numpy(),
                "close": close.to_numpy(),
                "volume": rng.integers(100_000, 5_000_000, len(close)).astype(float),
            },
            index=to_date_index(days),
        )

    def quote(self, ticker: str) -> Quote | None:
        if not ticker or not ticker.lstrip("^").replace(".", "").replace("-", "").isalnum():
            return None
        recent = self.history(ticker, self.today - timedelta(days=10))
        if len(recent) < 2:
            return None
        return Quote(price=float(recent["close"].iloc[-1]), previous_close=float(recent["close"].iloc[-2]))


# Nomes populares que não são o código do Yahoo Finance.
TICKER_ALIASES = {
    "IBOV": "^BVSP",
    "IBOVESPA": "^BVSP",
    "BVSP": "^BVSP",
    "SP500": "^GSPC",
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOWJONES": "^DJI",
}


def normalize_ticker(text: str) -> str:
    """Padroniza o que o usuário digitou: maiúsculas, sem espaços e com apelidos resolvidos."""
    ticker = "".join(text.split()).upper()
    return TICKER_ALIASES.get(ticker, ticker)


def market_data_from_env(name: str) -> MarketData:
    if name == "fake":
        return FakeMarketData()
    if name in ("", "yahoo"):
        return YahooMarketData()
    raise ValueError(f'MARKET_DATA inválido: "{name}". Use "yahoo" ou "fake".')
