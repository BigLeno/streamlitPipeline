"""Dashboard financeiro: acompanhe preços, indicadores e destaques de uma carteira de ativos.

Rode com: streamlit run streamlit_app.py
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard import highlights, indicators
from dashboard.market_data import Quote, market_data_from_env, normalize_ticker
from dashboard.market_hours import format_duration, market_status
from dashboard.storage import Portfolio
from dashboard.sync import sync_history

st.set_page_config(page_title="Dashboard Financeiro", page_icon="💹", layout="wide")

PERIODS = {"1 mês": 30, "3 meses": 90, "6 meses": 180, "1 ano": 365, "5 anos": 5 * 365}
DEFAULT_TICKERS = os.getenv("DEFAULT_TICKERS", "^BVSP,PETR4.SA,VALE3.SA,ITUB4.SA,AAPL")
# Intervalo de atualização automática da cotação e do status do pregão.
REFRESH_SECONDS = 60
BRASILIA = ZoneInfo("America/Sao_Paulo")
COLORS = {"up": "#1a9850", "down": "#d73027", "line": "#1f4e79", "accent": "#e08214", "muted": "#8c8c8c"}


@st.cache_resource
def get_portfolio() -> Portfolio:
    portfolio = Portfolio(os.getenv("DATABASE_URL", "sqlite:///data/dashboard.db"))
    if not portfolio.tickers():
        for ticker in filter(None, (item.strip().upper() for item in DEFAULT_TICKERS.split(","))):
            portfolio.add(ticker)
    return portfolio


@st.cache_resource
def get_source():
    return market_data_from_env(os.getenv("MARKET_DATA", "yahoo"))


@st.cache_data(ttl=3600, show_spinner=False)
def synced(ticker: str, day: str) -> int:
    """Sincroniza o histórico uma vez por hora (o parâmetro `day` invalida o cache na virada do dia)."""
    return sync_history(get_portfolio(), get_source(), ticker, date.fromisoformat(day))


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def quote(ticker: str) -> Quote | None:
    return get_source().quote(ticker)


def closes(tickers: list[str]) -> dict[str, pd.Series]:
    portfolio = get_portfolio()
    return {ticker: portfolio.prices(ticker)["close"] for ticker in tickers}


@st.fragment(run_every=REFRESH_SECONDS)
def market_banner() -> None:
    status = market_status(datetime.now(timezone.utc))
    when = status.local_time.strftime("%a %H:%M")
    if status.is_open:
        st.success(f"🟢 Bolsa americana aberta ({when} em Nova York). Fecha em {format_duration(status.time_to_change)}.")
    else:
        st.info(f"🔴 Bolsa americana fechada ({when} em Nova York). Abre em {format_duration(status.time_to_change)}.")


def sidebar(tickers: list[str]) -> tuple[str | None, str]:
    portfolio = get_portfolio()
    with st.sidebar:
        st.header("Visualização")
        selected = st.selectbox("Ativo", tickers, index=0 if tickers else None, placeholder="Cadastre um ativo")
        period = st.selectbox("Período", list(PERIODS), index=3)

        st.header("Carteira")
        with st.form("add", clear_on_submit=True):
            new_ticker = normalize_ticker(st.text_input("Ticker", placeholder="ex.: BBDC4.SA, MSFT, IBOV"))
            if st.form_submit_button("Adicionar", width="stretch") and new_ticker:
                if new_ticker in tickers:
                    st.warning(f"{new_ticker} já está na carteira.")
                elif quote(new_ticker) is None:
                    st.error(
                        f"Não encontrei cotação para {new_ticker}. Confira o código no Yahoo Finance: "
                        "ações brasileiras terminam em .SA (PETR4.SA) e índices começam com ^ (^BVSP)."
                    )
                else:
                    portfolio.add(new_ticker)
                    with st.spinner(f"Baixando o histórico de {new_ticker}..."):
                        synced(new_ticker, date.today().isoformat())
                    st.rerun()

        if tickers:
            to_remove = st.selectbox("Remover", tickers, index=None, placeholder="Escolha um ativo")
            if st.button("Remover", disabled=to_remove is None, width="stretch"):
                portfolio.remove(to_remove)
                synced.clear()
                st.rerun()
    return selected, period


def highlight_metrics(all_closes: dict[str, pd.Series]) -> None:
    today = date.today()
    cards = [
        ("Maior retorno em 12 meses", highlights.best_return(all_closes, today), "{:+.1%}"),
        ("Pior tendência em 3 meses (MM21)", highlights.worst_moving_average_trend(all_closes, today), "{:+.1%}"),
        ("Maior tendência de alta (proj. 1 mês)", highlights.strongest_trend(all_closes, today), "{:+.1%}"),
    ]
    for column, (label, item, fmt) in zip(st.columns(3), cards, strict=True):
        if item is None:
            column.metric(label, "-")
        else:
            column.metric(label, item.ticker, fmt.format(item.value))


@st.fragment(run_every=REFRESH_SECONDS)
def quote_header(ticker: str) -> None:
    """Atualiza sozinho a cada minuto, sem recarregar o resto da página."""
    current = quote(ticker)
    if current is None:
        st.subheader(ticker)
        st.caption("Cotação indisponível no momento.")
        return
    delta = None
    if current.change is not None:
        delta = f"{current.change:+.2f} ({current.change_percent:+.2%})"
    st.metric(f"{ticker} agora", f"{current.price:,.2f}", delta)
    updated = datetime.now(BRASILIA).strftime("%H:%M:%S")
    st.caption(f"Atualizado às {updated} (Brasília). Cotações do Yahoo podem ter atraso de até 15 minutos.")


def price_chart(prices: pd.DataFrame) -> go.Figure:
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
    figure.add_trace(
        go.Candlestick(
            x=prices.index, open=prices["open"], high=prices["high"], low=prices["low"], close=prices["close"],
            name="Preço", increasing_line_color=COLORS["up"], decreasing_line_color=COLORS["down"],
        ),
        row=1, col=1,
    )
    figure.add_trace(go.Bar(x=prices.index, y=prices["volume"], name="Volume", marker_color=COLORS["muted"]), row=2, col=1)
    figure.update_layout(height=520, showlegend=False, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    figure.update_yaxes(title_text="Preço", row=1, col=1)
    figure.update_yaxes(title_text="Volume", row=2, col=1)
    return figure


def line(series: dict[str, pd.Series], y_title: str, percent: bool = False) -> go.Figure:
    figure = go.Figure()
    palette = [COLORS["line"], COLORS["accent"], COLORS["up"], COLORS["muted"]]
    for (name, values), color in zip(series.items(), palette, strict=False):
        figure.add_trace(go.Scatter(x=values.index, y=values * 100 if percent else values, name=name, line=dict(color=color)))
    figure.update_layout(height=380, yaxis_title=y_title, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified")
    return figure


def analysis_tabs(prices: pd.DataFrame, all_closes: dict[str, pd.Series]) -> None:
    close = prices["close"]
    tabs = st.tabs(
        ["Retorno acumulado", "Volatilidade", "Drawdown", "Médias móveis", "RSI e MACD", "Retornos mensais", "Correlação"]
    )

    charts = [
        line({"Retorno acumulado": indicators.cumulative_return(close)}, "%", percent=True),
        line({"Volatilidade 21d (anualizada)": indicators.rolling_volatility(close)}, "%", percent=True),
        line({"Drawdown": indicators.drawdown(close)}, "%", percent=True),
        line(
            {
                "Fechamento": close,
                "MM 21": indicators.moving_average(close, 21),
                "MM 63": indicators.moving_average(close, 63),
            },
            "Preço",
        ),
    ]
    for tab, chart in zip(tabs[:4], charts, strict=True):
        tab.plotly_chart(chart, width="stretch")

    rsi = indicators.rsi(close)
    rsi_figure = line({"RSI 14": rsi}, "RSI")
    rsi_figure.add_hline(y=70, line_dash="dot", line_color=COLORS["down"])
    rsi_figure.add_hline(y=30, line_dash="dot", line_color=COLORS["up"])
    rsi_figure.update_yaxes(range=[0, 100])
    macd = indicators.macd(close)
    tabs[4].plotly_chart(rsi_figure, width="stretch")
    tabs[4].plotly_chart(line({"MACD": macd["macd"], "Sinal": macd["signal"]}, "MACD"), width="stretch")

    monthly = indicators.monthly_returns(close) * 100
    heatmap = px.imshow(
        monthly, labels=dict(x="Mês", y="Ano", color="Retorno (%)"), x=[str(m) for m in monthly.columns],
        y=[str(y) for y in monthly.index], color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
        text_auto=".1f", aspect="auto",
    )
    tabs[5].plotly_chart(heatmap, width="stretch")

    available = {name: series for name, series in all_closes.items() if len(series) > 20}
    if len(available) < 2:
        tabs[6].info("Adicione pelo menos dois ativos para ver a correlação.")
    else:
        correlation = indicators.returns_correlation(available)
        tabs[6].plotly_chart(
            px.imshow(correlation, text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, aspect="auto"),
            width="stretch",
        )
        tabs[6].caption("Correlação dos retornos diários nas datas em comum de todo o histórico salvo.")


def main() -> None:
    st.title("💹 Dashboard Financeiro")
    market_banner()

    portfolio = get_portfolio()
    tickers = portfolio.tickers()
    today = date.today().isoformat()
    with st.spinner("Atualizando históricos..."):
        for ticker in tickers:
            synced(ticker, today)

    selected, period = sidebar(tickers)
    if not tickers or selected is None:
        st.info("Adicione um ativo na barra lateral para começar.")
        return

    all_closes = closes(tickers)
    st.subheader("Destaques da carteira")
    highlight_metrics(all_closes)
    st.divider()

    prices = portfolio.prices(selected)
    start = pd.Timestamp(date.today()) - pd.Timedelta(days=PERIODS[period])
    prices = prices[prices.index >= start]
    quote_header(selected)
    if len(prices) < 2:
        st.warning("Ainda não há histórico suficiente para este ativo.")
        return
    st.plotly_chart(price_chart(prices), width="stretch")
    st.subheader("Análises")
    analysis_tabs(prices, all_closes)
    st.caption("Dados: Yahoo Finance, via yfinance. Valores com atraso e sem garantia; não é recomendação de investimento.")


main()
