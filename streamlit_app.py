
import streamlit as st
import pandas as pd
from assets.analytics import (
    ativo_maior_rentabilidade_12m,
    ativo_menor_rentabilidade_mm3m,
    ativo_maior_tendencia_crescimento_1m
)
from assets.database import listar_ativos, listar_historicos
import datetime

st.caption("Desenvolvido com Streamlit e Python | Dados: Yahoo Finance")

st.set_page_config(page_title="Analytics Financeiro", layout="wide")
st.title("📈 Analytics Financeiro")

# Sidebar para seleção
st.sidebar.header("Filtros de Visualização")
ativos = listar_ativos()
tickers = [a.ticker for a in ativos]
periodos = {
    "1 mês": 30,
    "3 meses": 90,
    "6 meses": 180,
    "1 ano": 365,
    "5 anos": 5*365
}
ticker_sel = st.sidebar.selectbox("Selecione o ativo", tickers)
periodo_sel = st.sidebar.selectbox("Período", list(periodos.keys()), index=1)
dias = periodos[periodo_sel]

st.sidebar.markdown("---")
st.sidebar.write(f"Ativos disponíveis: {', '.join(tickers)}")

# Insights obrigatórios
with st.expander("🔎 Insights obrigatórios", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Maior rentabilidade (12 meses)**")
        ativo, rent = ativo_maior_rentabilidade_12m()
        if ativo:
            st.success(f"{ativo}\n{rent:.2%}")
        else:
            st.warning("Sem dados")
    with col2:
        st.markdown("**Menor rentabilidade (MM 3 meses)**")
        ativo, rent = ativo_menor_rentabilidade_mm3m()
        if ativo:
            st.error(f"{ativo}\n{rent:.2%}")
        else:
            st.warning("Sem dados")
    with col3:
        st.markdown("**Maior tendência de crescimento (próx. mês)**")
        ativo, tendencia = ativo_maior_tendencia_crescimento_1m()
        if ativo:
            st.info(f"{ativo}\nCoef.: {tendencia:.4f}")
        else:
            st.warning("Sem dados")

st.markdown("---")

# Gráficos em abas
hoje = datetime.date.today()
data_inicio = hoje - datetime.timedelta(days=dias)
historicos = [h for h in listar_historicos(ticker_sel) if h.data >= data_inicio and h.preco_fechamento]

tab1, tab2 = st.tabs(["📉 Preço de Fechamento", "📊 Volume"])
if not historicos:
    tab1.warning("Não há dados suficientes para plotar o gráfico.")
    tab2.warning("Não há dados suficientes para plotar o gráfico.")
else:
    historicos.sort(key=lambda h: h.data)
    df = pd.DataFrame({
        "Data": [h.data for h in historicos],
        "Fechamento": [h.preco_fechamento for h in historicos],
        "Volume": [h.volume for h in historicos]
    })
    with tab1:
        st.subheader(f"Preço de Fechamento - {ticker_sel} ({periodo_sel})")
        st.line_chart(df.set_index("Data")["Fechamento"])
    with tab2:
        st.subheader(f"Volume - {ticker_sel} ({periodo_sel})")
        st.bar_chart(df.set_index("Data")["Volume"])

st.caption("Desenvolvido com Streamlit e Python | Dados: Yahoo Finance")
