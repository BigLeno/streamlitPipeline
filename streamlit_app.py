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

st.set_page_config(page_title="Dashboard Financeiro Interativo", layout="wide")

# Título e descrição sofisticados
titulo = """
<h1 style='font-size:2.5rem; color:#0a3d62; margin-bottom:0;'>💹 Dashboard Financeiro Interativo</h1>
<p style='font-size:1.2rem; color:#222; margin-top:0;'>Acompanhe, compare e explore ativos do mercado financeiro brasileiro em tempo real.<br>Ferramentas de análise, gráficos dinâmicos e gestão de portfólio em um só lugar.</p>
"""
st.markdown(titulo, unsafe_allow_html=True)

# Sidebar refinada
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920256.png", width=80)
    st.header("Gerencie seu Portfólio")
    scraper = Scraper(headless=True)
    if st.button("🔄 Atualizar banco (coletar históricos)"):
        with st.spinner("Coletando históricos de todos os ativos..."):
            scraper.coletar_e_salvar_historico_ativos([a.ticker for a in listar_ativos()], periodos='5Y')
        st.success("Banco atualizado!")
    novo_ativo = st.text_input("Adicionar novo ativo (ex: BBDC4.SA)")
    if st.button("➕ Adicionar ativo"):
        if novo_ativo:
            inserir_ativo(novo_ativo)
            st.success(f"Ativo {novo_ativo} adicionado!")
        else:
            st.warning("Digite um ticker válido.")
    ativos = listar_ativos()
    tickers = [a.ticker for a in ativos]
    remover_ativo = st.selectbox("Remover ativo", tickers)
    if st.button("🗑️ Remover ativo selecionado"):
        from assets.database import SessionLocal, Ativo, Historico
        session = SessionLocal()
        ativo_obj = session.query(Ativo).filter_by(ticker=remover_ativo).first()
        if ativo_obj:
            session.query(Historico).filter_by(ativo_id=ativo_obj.id).delete()
            session.delete(ativo_obj)
            session.commit()
            st.success(f"Ativo {remover_ativo} removido!")
        else:
            st.warning("Ativo não encontrado.")
        session.close()
        st.experimental_rerun()
    st.markdown("---")
    st.write(f"<span style='color:#0a3d62'><b>Ativos disponíveis:</b></span> {', '.join(tickers)}", unsafe_allow_html=True)
    st.header("Filtros de Visualização")
    periodos = {
        "1 mês": 30,
        "3 meses": 90,
        "6 meses": 180,
        "1 ano": 365,
        "5 anos": 5*365
    }
    ticker_sel = st.selectbox("Selecione o ativo", tickers, key="ticker_sel")
    periodo_sel = st.selectbox("Período", list(periodos.keys()), index=1, key="periodo_sel")
    dias = periodos[periodo_sel]

# Destaques do Mercado

# Destaques do Mercado (versão nativa Streamlit)
st.markdown("""
<div style='background: linear-gradient(90deg,#eaf6fb 60%,#f7f1e3 100%); border-radius:12px; padding:1.5rem 1rem 1rem 1rem; margin-bottom:2rem;'>
    <h2 style='color:#0a3d62; margin-bottom:0.5rem;'>✨ Destaques do Mercado</h2>
</div>
""", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Maior rentabilidade (12 meses)")
    ativo, rent = ativo_maior_rentabilidade_12m()
    if ativo:
        st.success(f"{ativo}", icon="⬆️")
        st.metric("Rentabilidade", f"{rent:.2%}")
    else:
        st.warning("Sem dados")
with col2:
    st.subheader("Menor rentabilidade (MM 3 meses)")
    ativo, rent = ativo_menor_rentabilidade_mm3m()
    if ativo:
        st.error(f"{ativo}", icon="⬇️")
        st.metric("Rentabilidade", f"{rent:.2%}")
    else:
        st.warning("Sem dados")
with col3:
    st.subheader("Maior tendência de crescimento (próx. mês)")
    ativo, tendencia = ativo_maior_tendencia_crescimento_1m()
    if ativo:
        st.info(f"{ativo}", icon="📈")
        st.metric("Coeficiente", f"{tendencia:.4f}")
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

st.caption("<span style='color:#888'>Desenvolvido com Streamlit e Python | Dados: Yahoo Finance</span>", unsafe_allow_html=True)
