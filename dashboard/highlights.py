"""Destaques do portfólio: melhor retorno, pior tendência recente e maior tendência de alta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from dashboard.indicators import moving_average


@dataclass(frozen=True)
class Highlight:
    ticker: str
    value: float


def _window(close: pd.Series, today: date, days: int) -> pd.Series:
    start = pd.Timestamp(today - timedelta(days=days))
    return close[close.index >= start].dropna()


def best_return(closes: dict[str, pd.Series], today: date, days: int = 365) -> Highlight | None:
    """Ativo com maior retorno simples no período."""
    results = {}
    for ticker, close in closes.items():
        window = _window(close, today, days)
        if len(window) >= 2 and window.iloc[0] > 0:
            results[ticker] = window.iloc[-1] / window.iloc[0] - 1
    return _pick(results, max)


def worst_moving_average_trend(
    closes: dict[str, pd.Series], today: date, days: int = 90, window: int = 21
) -> Highlight | None:
    """Ativo cuja média móvel caiu mais no período (filtra o ruído do dia a dia)."""
    results = {}
    for ticker, close in closes.items():
        average = moving_average(_window(close, today, days), window).dropna()
        if len(average) >= 2 and average.iloc[0] > 0:
            results[ticker] = average.iloc[-1] / average.iloc[0] - 1
    return _pick(results, min)


def strongest_trend(
    closes: dict[str, pd.Series], today: date, days: int = 90, horizon: int = 21, min_points: int = 10
) -> Highlight | None:
    """Ativo com maior tendência de alta, projetada para `horizon` pregões.

    Ajusta uma reta ao logaritmo do preço. A inclinação é a variação percentual média por pregão,
    o que torna ativos de preços diferentes comparáveis.
    """
    results = {}
    for ticker, close in closes.items():
        window = _window(close, today, days)
        window = window[window > 0]
        if len(window) < min_points:
            continue
        slope = np.polyfit(np.arange(len(window)), np.log(window.to_numpy()), 1)[0]
        results[ticker] = float(np.expm1(slope * horizon))
    return _pick(results, max)


def _pick(results: dict[str, float], choose) -> Highlight | None:
    if not results:
        return None
    ticker = choose(results, key=results.get)
    return Highlight(ticker=ticker, value=float(results[ticker]))


# Variação abaixo disso (0,1%) é tratada como estável.
STABLE_THRESHOLD = 0.001


@dataclass(frozen=True)
class DayTrend:
    title: str
    direction: str  # "Alta", "Baixa" ou "Estável"
    change: float


def day_trend(change_percent: float | None, market_open: bool) -> DayTrend | None:
    """Direção do dia pela variação contra o fechamento anterior.

    Com o pregão aberto, indica para que lado o ativo caminha para fechar; com ele fechado,
    como foi o último fechamento. Não é previsão: só reflete a variação até o momento.
    """
    if change_percent is None:
        return None
    if abs(change_percent) < STABLE_THRESHOLD:
        direction = "Estável"
    else:
        direction = "Alta" if change_percent > 0 else "Baixa"
    title = "Tendência de fechamento" if market_open else "Último fechamento"
    return DayTrend(title=title, direction=direction, change=float(change_percent))
