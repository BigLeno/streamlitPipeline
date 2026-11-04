"""Persistência do portfólio e do histórico de preços com SQLAlchemy (SQLite por padrão)."""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Date, Float, ForeignKey, String, UniqueConstraint, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from dashboard.market_data import PRICE_COLUMNS, empty_prices, to_date_index


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True)
    prices: Mapped[list[Price]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("asset_id", "date", name="uq_prices_asset_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    day: Mapped[datetime.date] = mapped_column("date", Date)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    asset: Mapped[Asset] = relationship(back_populates="prices")


class Portfolio:
    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:///:memory:"):
            Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)

    def tickers(self) -> list[str]:
        with Session(self.engine) as session:
            return list(session.scalars(select(Asset.ticker).order_by(Asset.ticker)))

    def add(self, ticker: str) -> bool:
        """Cadastra o ticker. Retorna False se ele já existia."""
        with Session(self.engine) as session:
            if session.scalar(select(Asset.id).where(Asset.ticker == ticker)):
                return False
            session.add(Asset(ticker=ticker))
            session.commit()
            return True

    def remove(self, ticker: str) -> None:
        with Session(self.engine) as session:
            asset = session.scalar(select(Asset).where(Asset.ticker == ticker))
            if asset:
                session.delete(asset)
                session.commit()

    def last_date(self, ticker: str) -> datetime.date | None:
        with Session(self.engine) as session:
            return session.scalar(
                select(func.max(Price.day)).join(Asset).where(Asset.ticker == ticker)
            )

    def save_prices(self, ticker: str, prices: pd.DataFrame) -> int:
        """Insere ou atualiza os preços por data. Rodar de novo com os mesmos dados não duplica linhas."""
        if prices.empty:
            return 0
        with Session(self.engine) as session:
            asset = session.scalar(select(Asset).where(Asset.ticker == ticker))
            if asset is None:
                raise KeyError(f"Ativo não cadastrado: {ticker}")
            days = [timestamp.date() for timestamp in prices.index]
            existing = {
                price.day: price
                for price in session.scalars(
                    select(Price).where(Price.asset_id == asset.id, Price.day.in_(days))
                )
            }
            for day, row in zip(days, prices.itertuples(index=False), strict=True):
                values = {column: _float_or_none(getattr(row, column)) for column in PRICE_COLUMNS}
                if day in existing:
                    for column, value in values.items():
                        setattr(existing[day], column, value)
                else:
                    session.add(Price(asset_id=asset.id, day=day, **values))
            session.commit()
        return len(days)

    def prices(self, ticker: str) -> pd.DataFrame:
        with Session(self.engine) as session:
            rows = session.execute(
                select(Price.day, Price.open, Price.high, Price.low, Price.close, Price.volume)
                .join(Asset)
                .where(Asset.ticker == ticker)
                .order_by(Price.day)
            ).all()
        if not rows:
            return empty_prices()
        frame = pd.DataFrame(rows, columns=["date", *PRICE_COLUMNS])
        return frame.set_index(to_date_index(frame.pop("date")))

    def close(self) -> None:
        self.engine.dispose()

    def delete_prices(self, ticker: str) -> None:
        with Session(self.engine) as session:
            asset_id = session.scalar(select(Asset.id).where(Asset.ticker == ticker))
            session.execute(delete(Price).where(Price.asset_id == asset_id))
            session.commit()


def _float_or_none(value) -> float | None:
    return None if pd.isna(value) else float(value)
