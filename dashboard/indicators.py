"""Indicadores calculados a partir de séries de preços.

Todas as funções recebem séries do pandas indexadas por data e não acessam rede nem banco,
o que permite testá-las com dados sintéticos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def daily_returns(close: pd.Series) -> pd.Series:
    return close.pct_change()


def cumulative_return(close: pd.Series) -> pd.Series:
    """Retorno acumulado desde o primeiro preço da série (0.10 = 10%)."""
    return close / close.iloc[0] - 1


def rolling_volatility(close: pd.Series, window: int = 21) -> pd.Series:
    """Desvio padrão dos retornos diários na janela, anualizado."""
    return daily_returns(close).rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def drawdown(close: pd.Series) -> pd.Series:
    """Queda em relação ao maior preço anterior (-0.20 = 20% abaixo do pico)."""
    return close / close.cummax() - 1


def moving_average(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Índice de força relativa com a suavização de Wilder (0 a 100)."""
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    relative_strength = gains / losses
    result = 100 - 100 / (1 + relative_strength)
    # Sem perdas no período, o RSI é 100 por definição.
    return result.where(losses != 0, 100.0).where(gains.notna())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    signal_line = line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": line, "signal": signal_line, "histogram": line - signal_line})


def monthly_returns(close: pd.Series) -> pd.DataFrame:
    """Retorno de cada mês (último fechamento do mês contra o do mês anterior), em tabela ano x mês."""
    month_end = close.groupby([close.index.year, close.index.month]).last()
    returns = month_end.pct_change()
    # O primeiro mês não tem fechamento anterior: usa o primeiro preço disponível dele.
    first_year, first_month = month_end.index[0]
    first_price = close[(close.index.year == first_year) & (close.index.month == first_month)].iloc[0]
    returns.iloc[0] = month_end.iloc[0] / first_price - 1
    returns.index = returns.index.set_names(["ano", "mes"])
    return returns.unstack("mes").reindex(columns=range(1, 13))


def returns_correlation(closes: dict[str, pd.Series], min_periods: int = 20) -> pd.DataFrame:
    """Correlação dos retornos diários entre ativos, só nas datas em comum."""
    frame = pd.DataFrame(closes).dropna()
    return frame.pct_change().dropna().corr(min_periods=min_periods)
