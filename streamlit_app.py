
import streamlit as st
import pandas as pd
from assets.analytics import (
    ativo_maior_rentabilidade_12m,
    ativo_menor_rentabilidade_mm3m,
    ativo_maior_tendencia_crescimento_1m
)
from assets.database import listar_ativos, listar_historicos, inserir_ativo
import datetime
from assets.scrapping import Scraper

st.caption("Desenvolvido com Streamlit e Python | Dados: Yahoo Finance")

st.set_page_config(page_title="Analytics Financeiro", layout="wide")
st.title("📈 Analytics Financeiro")

# Sidebar para seleção

st.sidebar.header("Gerenciamento de Ativos e Banco")
scraper = Scraper(headless=True)

# Atualizar banco (coletar históricos de todos os ativos)
if st.sidebar.button("Atualizar banco (coletar históricos)"):
    with st.spinner("Coletando históricos de todos os ativos..."):
        scraper.coletar_e_salvar_historico_ativos([a.ticker for a in listar_ativos()], periodos='5Y')
    st.sidebar.success("Banco atualizado!")

# Adicionar novo ativo
novo_ativo = st.sidebar.text_input("Adicionar novo ativo (ex: BBDC4.SA)")
if st.sidebar.button("Adicionar ativo"):
    if novo_ativo:
        inserir_ativo(novo_ativo)
        st.sidebar.success(f"Ativo {novo_ativo} adicionado!")
    else:
        st.sidebar.warning("Digite um ticker válido.")

# Remover ativo
ativos = listar_ativos()
tickers = [a.ticker for a in ativos]
remover_ativo = st.sidebar.selectbox("Remover ativo", tickers)
if st.sidebar.button("Remover ativo selecionado"):
    from assets.database import SessionLocal, Ativo, Historico
    session = SessionLocal()
    ativo_obj = session.query(Ativo).filter_by(ticker=remover_ativo).first()
    if ativo_obj:
        session.query(Historico).filter_by(ativo_id=ativo_obj.id).delete()
        session.delete(ativo_obj)
        session.commit()
        st.sidebar.success(f"Ativo {remover_ativo} removido!")
    else:
        st.sidebar.warning("Ativo não encontrado.")
    session.close()
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.write(f"Ativos disponíveis: {', '.join(tickers)}")

# Filtros de visualização
st.sidebar.header("Filtros de Visualização")
periodos = {
    "1 mês": 30,
    "3 meses": 90,
    "6 meses": 180,
    "1 ano": 365,
    "5 anos": 5*365
}
ticker_sel = st.sidebar.selectbox("Selecione o ativo", tickers, key="ticker_sel")
periodo_sel = st.sidebar.selectbox("Período", list(periodos.keys()), index=1, key="periodo_sel")
dias = periodos[periodo_sel]

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


# Gráficos e preço atual
hoje = datetime.date.today()
data_inicio = hoje - datetime.timedelta(days=dias)
historicos = [h for h in listar_historicos(ticker_sel) if h.data >= data_inicio and h.preco_fechamento]

tab1, tab2, tab3 = st.tabs(["📉 Preço de Fechamento", "📊 Volume", "💲 Preço Atual (ao vivo)"])
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

# Preço atual ao vivo
with tab3:
    st.subheader(f"Preço Atual de {ticker_sel} (ao vivo)")
    if st.button("Atualizar preço agora"):
        with st.spinner("Buscando preço atual no Yahoo Finance..."):
            scraper.start_driver()
            dados = scraper.scrape_stock(ticker_sel)
            scraper.quit_driver()
        st.session_state['preco_atual'] = dados
    preco_atual = st.session_state.get('preco_atual', None)
    if preco_atual:
        st.metric("Preço Atual", preco_atual.get("regular_market_price", "-"))
        st.metric("Variação", preco_atual.get("regular_market_change", "-"))
        st.metric("Variação (%)", preco_atual.get("regular_market_change_percent", "-"))
    else:
        st.info("Clique em 'Atualizar preço agora' para ver o preço ao vivo.")

st.caption("Desenvolvido com Streamlit e Python | Dados: Yahoo Finance")
