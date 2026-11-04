"""Textos de ajuda dos cards e leitura, em linguagem simples, de cada análise.

As explicações (`HELP`) dizem como ler cada indicador. As funções `read_*` resumem o que o
indicador mostra agora para o ativo selecionado. Nada aqui é recomendação de investimento.
"""

from __future__ import annotations

import pandas as pd

HELP = {
    "best_return": (
        "Ativo da carteira com a maior variação de preço nos últimos 12 meses: compara o primeiro "
        "e o último fechamento do período. Não inclui dividendos."
    ),
    "worst_trend": (
        "Ativo cuja média móvel de 21 pregões (cerca de um mês) mais caiu nos últimos 3 meses. "
        "A média suaviza as oscilações do dia a dia e mostra a direção de fundo."
    ),
    "strongest_trend": (
        "Ajusta uma reta ao logaritmo do preço dos últimos 3 meses e projeta esse ritmo para os próximos "
        "21 pregões. É uma extrapolação do comportamento recente, não uma previsão."
    ),
    "quote": "Último preço disponível e a variação em relação ao fechamento do pregão anterior.",
    "candles": (
        "Cada candle é um pregão. Verde: fechou acima da abertura; vermelho: abaixo. O corpo vai da abertura ao "
        "fechamento e as linhas finas mostram a máxima e a mínima do dia. As barras de baixo são o volume negociado."
    ),
    "cumulative": (
        "Quanto teria rendido quem comprou no início do período escolhido e manteve até hoje. "
        "0% significa preço igual ao do início."
    ),
    "volatility": (
        "Intensidade das oscilações: desvio padrão dos retornos diários dos últimos 21 pregões, "
        "anualizado. Quanto maior, mais o preço sobe e desce, ou seja, mais risco. Ações costumam "
        "ficar entre 20% e 40% ao ano; índices, abaixo disso."
    ),
    "drawdown": (
        "Quanto o preço está abaixo do maior valor já atingido no período. -20% quer dizer 20% abaixo "
        "do pico. O ponto mais baixo do gráfico é o drawdown máximo: a maior perda para quem comprou no topo."
    ),
    "moving_averages": (
        "MM 21 é a média dos últimos 21 pregões (cerca de um mês) e MM 63, dos últimos 63 (cerca de três "
        "meses). Preço acima das médias indica tendência de alta; abaixo, de baixa. Quando a média curta "
        "cruza a longa para cima, é um sinal clássico de virada para alta."
    ),
    "rsi": (
        "O RSI (índice de força relativa) vai de 0 a 100 e compara a força das altas com a das baixas nos "
        "últimos 14 pregões. Acima de 70, o ativo subiu rápido demais (sobrecomprado); abaixo de 30, caiu "
        "rápido demais (sobrevendido)."
    ),
    "macd": (
        "O MACD é a diferença entre as médias exponenciais de 12 e 26 pregões, e a linha de sinal é a média "
        "de 9 pregões do próprio MACD. MACD acima do sinal indica força de alta; abaixo, força de baixa."
    ),
    "monthly": (
        "Cada célula é a variação do mês: último fechamento do mês contra o último do mês anterior. Verde é "
        "alta e vermelho é queda. Ajuda a ver meses fortes, fracos e possíveis padrões ao longo dos anos."
    ),
    "correlation": (
        "Mostra o quanto os retornos diários dos ativos andam juntos, de -1 a 1. Perto de 1, sobem e caem "
        "juntos (pouca diversificação). Perto de 0, são independentes. Negativo, costumam ir em sentidos "
        "opostos."
    ),
}

DISCLAIMER = "Indicadores técnicos descrevem o comportamento passado do preço e não são recomendação de investimento."

MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def pct(value: float, signed: bool = True) -> str:
    """Percentual no formato brasileiro: 0.1234 -> '+12,3%'."""
    text = f"{value:+.1%}" if signed else f"{value:.1%}"
    return text.replace(".", ",")


def _number(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _date(timestamp: pd.Timestamp) -> str:
    return timestamp.strftime("%d/%m/%Y")


def read_cumulative(cumulative: pd.Series) -> str | None:
    values = cumulative.dropna()
    if values.empty:
        return None
    total = values.iloc[-1]
    if abs(total) < 0.0005:
        return "No período, o ativo ficou estável."
    direction = "valorizou" if total > 0 else "desvalorizou"
    return f"No período, o ativo {direction} {pct(abs(total), signed=False)}."


def read_volatility(volatility: pd.Series) -> str | None:
    values = volatility.dropna()
    if values.empty:
        return None
    current, average = values.iloc[-1], values.mean()
    if current > average * 1.15:
        comparison = "acima da média do período: o ativo está oscilando mais que o normal"
    elif current < average * 0.85:
        comparison = "abaixo da média do período: o ativo está mais calmo que o normal"
    else:
        comparison = "perto da média do período"
    return f"Volatilidade atual de {pct(current, signed=False)} ao ano, {comparison} ({pct(average, signed=False)})."


def read_drawdown(drawdown: pd.Series) -> str | None:
    values = drawdown.dropna()
    if values.empty:
        return None
    worst_day = values.idxmin()
    text = f"Maior queda a partir de um topo: {pct(values.min())}, em {_date(worst_day)}."
    current = values.iloc[-1]
    if current > -0.005:
        return text + " Hoje o preço está no topo do período."
    return text + f" Hoje está {pct(abs(current), signed=False)} abaixo do topo."


def read_moving_averages(close: pd.Series, short: pd.Series, long: pd.Series) -> str | None:
    if close.empty or pd.isna(short.iloc[-1]):
        return None
    price = close.iloc[-1]
    if pd.isna(long.iloc[-1]):
        side = "acima" if price >= short.iloc[-1] else "abaixo"
        return f"O preço está {side} da MM 21. Ainda não há pregões suficientes para a MM 63."
    above = [name for name, avg in (("MM 21", short.iloc[-1]), ("MM 63", long.iloc[-1])) if price >= avg]
    if len(above) == 2:
        status = "acima das duas médias, sinal de tendência de alta"
    elif not above:
        status = "abaixo das duas médias, sinal de tendência de baixa"
    else:
        status = f"acima da {above[0]} e abaixo da outra, sem tendência definida"
    cross = "acima" if short.iloc[-1] >= long.iloc[-1] else "abaixo"
    return f"O preço está {status}. A MM 21 está {cross} da MM 63."


def read_rsi(rsi: pd.Series) -> str | None:
    values = rsi.dropna()
    if values.empty:
        return None
    current = values.iloc[-1]
    if current >= 70:
        zone = "zona de sobrecompra: o ativo subiu rápido e pode desacelerar"
    elif current <= 30:
        zone = "zona de sobrevenda: o ativo caiu rápido e pode desacelerar a queda"
    else:
        zone = "zona neutra"
    return f"RSI atual de {current:.0f}, {zone}."


def read_macd(macd: pd.DataFrame) -> str | None:
    values = macd.dropna()
    if len(values) < 2:
        return None
    now, before = values.iloc[-1], values.iloc[-2]
    side = "acima" if now["macd"] >= now["signal"] else "abaixo"
    strength = "força de alta" if side == "acima" else "força de baixa"
    crossed_now = (now["macd"] >= now["signal"]) != (before["macd"] >= before["signal"])
    suffix = " O cruzamento aconteceu no último pregão." if crossed_now else ""
    return f"O MACD está {side} da linha de sinal, indicando {strength}.{suffix}"


def read_monthly(monthly: pd.DataFrame) -> str | None:
    stacked = monthly.stack().dropna()
    if stacked.empty:
        return None
    (best_year, best_month), best = stacked.idxmax(), stacked.max()
    (worst_year, worst_month), worst = stacked.idxmin(), stacked.min()
    positive = (stacked > 0).mean()
    return (
        f"Melhor mês: {MONTHS[best_month - 1]}/{best_year} ({pct(best)}). "
        f"Pior mês: {MONTHS[worst_month - 1]}/{worst_year} ({pct(worst)}). "
        f"{positive:.0%} dos meses fecharam em alta."
    )


def read_correlation(correlation: pd.DataFrame, ticker: str) -> str | None:
    if ticker not in correlation.columns:
        return None
    others = correlation[ticker].drop(ticker).dropna()
    if others.empty:
        return None
    most, least = others.idxmax(), others.idxmin()
    text = f"{ticker} anda mais junto com {most} ({_number(others[most])})"
    if least != most:
        text += f" e menos com {least} ({_number(others[least])}), o que mais ajuda a diversificar"
    return text + "."
