"""Horário do pregão regular da bolsa americana (NYSE/Nasdaq)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
OPEN = time(9, 30)
CLOSE = time(16, 0)


@dataclass(frozen=True)
class MarketStatus:
    is_open: bool
    local_time: datetime
    next_change: datetime

    @property
    def time_to_change(self) -> timedelta:
        return self.next_change - self.local_time


def market_status(now: datetime) -> MarketStatus:
    """Estado do pregão no instante `now` (com fuso). Feriados não são considerados."""
    if now.tzinfo is None:
        raise ValueError("Informe um datetime com fuso horário.")
    local = now.astimezone(NEW_YORK)
    is_trading_day = local.weekday() < 5
    is_open = is_trading_day and OPEN <= local.time() < CLOSE

    if is_open:
        next_change = local.replace(hour=CLOSE.hour, minute=CLOSE.minute, second=0, microsecond=0)
    else:
        next_change = local.replace(hour=OPEN.hour, minute=OPEN.minute, second=0, microsecond=0)
        if not is_trading_day or local.time() >= CLOSE:
            next_change += timedelta(days=1)
        while next_change.weekday() >= 5:
            next_change += timedelta(days=1)
    return MarketStatus(is_open=is_open, local_time=local, next_change=next_change)


def format_duration(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    return f"{days}d {hours}h {minutes}min" if days else f"{hours}h {minutes}min"
