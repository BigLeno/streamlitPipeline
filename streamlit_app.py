import streamlit as st
from assets.analytics import (
    ativo_maior_rentabilidade_12m,
    ativo_menor_rentabilidade_mm3m,
    ativo_maior_tendencia_crescimento_1m
)

st.set_page_config(page_title="Analytics Financeiro", layout="centered")
st.title("📈 Analytics Financeiro - Insights Obrigatórios")

st.header("Ativo com maior rentabilidade (12 meses)")
ativo, rent = ativo_maior_rentabilidade_12m()
if ativo:
    st.success(f"{ativo} ({rent:.2%} de retorno)")
else:
    st.warning("Não há dados suficientes para calcular.")

st.header("Ativo com menor rentabilidade (média móvel 3 meses)")
ativo, rent = ativo_menor_rentabilidade_mm3m()
if ativo:
    st.error(f"{ativo} ({rent:.2%} de retorno)")
else:
    st.warning("Não há dados suficientes para calcular.")

st.header("Ativo com maior tendência de crescimento (próximo mês)")
ativo, tendencia = ativo_maior_tendencia_crescimento_1m()
if ativo:
    st.info(f"{ativo} (coeficiente: {tendencia:.4f})")
else:
    st.warning("Não há dados suficientes para calcular.")

st.caption("Desenvolvido com Streamlit e Python | Dados: Yahoo Finance")
