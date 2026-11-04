"""Horário do pregão regular da bolsa americana (NYSE/Nasdaq) e da B3. Feriados não são considerados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
SAO_PAULO = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True)
class Market:
    name: str
    timezone: ZoneInfo
    open: time
    close: time

    def close_on(self, day: datetime) -> time:
        return self.close


class B3Market(Market):
    """A B3 acompanha o horário de verão americano: fecha às 17h quando ele vigora e às 18h fora dele."""

    def close_on(self, day: datetime) -> time:
        noon_new_york = day.astimezone(NEW_YORK).replace(hour=12, minute=0)
        return time(17, 0) if noon_new_york.dst() else time(18, 0)


NYSE = Market("Bolsa americana", NEW_YORK, time(9, 30), time(16, 0))
B3 = B3Market("B3", SAO_PAULO, time(10, 0), time(17, 0))


def market_for(ticker: str) -> Market:
    """B3 para ações brasileiras (.SA) e para o Ibovespa; bolsa americana para o resto."""
    ticker = ticker.upper()
    return B3 if ticker.endswith(".SA") or ticker == "^BVSP" else NYSE


@dataclass(frozen=True)
class MarketStatus:
    is_open: bool
    local_time: datetime
    next_change: datetime

    @property
    def time_to_change(self) -> timedelta:
        return self.next_change - self.local_time


def market_status(now: datetime, market: Market = NYSE) -> MarketStatus:
    """Estado do pregão no instante `now` (com fuso)."""
    if now.tzinfo is None:
        raise ValueError("Informe um datetime com fuso horário.")
    local = now.astimezone(market.timezone)
    close = market.close_on(local)
    is_trading_day = local.weekday() < 5
    is_open = is_trading_day and market.open <= local.time() < close

    if is_open:
        next_change = local.replace(hour=close.hour, minute=close.minute, second=0, microsecond=0)
    else:
        next_change = local.replace(hour=market.open.hour, minute=market.open.minute, second=0, microsecond=0)
        if not is_trading_day or local.time() >= close:
            next_change += timedelta(days=1)
        while next_change.weekday() >= 5:
            next_change += timedelta(days=1)
    return MarketStatus(is_open=is_open, local_time=local, next_change=next_change)


def format_duration(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    return f"{days}d {hours}h {minutes}min" if days else f"{hours}h {minutes}min"
