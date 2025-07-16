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
from assets.database import salvar_preco_atual, consultar_preco_atual, listar_ativos
import threading
import time

st.set_page_config(page_title="Dashboard Financeiro Interativo", layout="wide")

# Thread para atualizar preços dos ativos periodicamente
def atualizar_precos_periodicamente(intervalo=60):
    def to_float(val):
        if val is None:
            return None
        if isinstance(val, str):
            val = val.replace('%', '').replace(',', '').strip()
        try:
            return float(val)
        except Exception:
            return None
    scraper = Scraper(headless=True)
    while True:
        ativos = listar_ativos()
        tickers = [a.ticker for a in ativos]
        try:
            scraper.start_driver()
            for ticker in tickers:
                try:
                    dados = scraper.scrape_stock(ticker)
                    salvar_preco_atual(
                        ticker,
                        preco=to_float(dados.get("regular_market_price")),
                        variacao=to_float(dados.get("regular_market_change")),
                        variacao_percentual=to_float(dados.get("regular_market_change_percent")),
                        atualizado_em=datetime.datetime.now()
                    )
                except Exception:
                    pass
            scraper.quit_driver()
        except Exception:
            pass
        time.sleep(intervalo)

# Inicia thread de atualização (apenas uma vez)
if 'thread_precos' not in st.session_state:
    thread = threading.Thread(target=atualizar_precos_periodicamente, args=(60,), daemon=True)
    thread.start()
    st.session_state['thread_precos'] = True


# Título e descrição sempre visíveis
st.markdown("""
<h1 style='font-size:2.5rem; color:#0a3d62; margin-bottom:0;'>💹 Dashboard Financeiro Interativo</h1>
<p style='font-size:1.2rem; color:#222; margin-top:0;'>Acompanhe, compare e explore ativos do mercado financeiro brasileiro em tempo real.<br>Ferramentas de análise, gráficos dinâmicos e gestão de portfólio em um só lugar.</p>
""", unsafe_allow_html=True)

# Sidebar refinada

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920256.png", width=80)
    st.markdown("<h2 style='color:#0a3d62;'>Menu</h2>", unsafe_allow_html=True)
    menu = st.radio("Menu de opções", ["Filtros de Visualização", "Gerenciar Portfólio"], index=0, label_visibility="collapsed")
    scraper = Scraper(headless=True)
    ativos = listar_ativos()
    tickers = [a.ticker for a in ativos]

    # Filtros de Visualização sempre visíveis e primeiro
    st.subheader("Filtros de Visualização")
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

    if menu == "Gerenciar Portfólio":
        st.subheader("Adicionar novo ativo")
        novo_ativo = st.text_input("Ticker (ex: BBDC4.SA)", key="novo_ativo")
        if st.button("➕ Adicionar ativo"):
            if not novo_ativo:
                st.warning("Digite um ticker válido.")
            elif novo_ativo in tickers:
                st.error(f"O ativo {novo_ativo} já existe!")
            else:
                inserir_ativo(novo_ativo)
                with st.spinner(f"Coletando históricos de {novo_ativo} (5 anos)..."):
                    scraper.coletar_e_salvar_historico_ativos([novo_ativo], periodos='5Y')
                st.success(f"Ativo {novo_ativo} adicionado e históricos coletados!")
                st.rerun()
        st.subheader("Remover ativo")
        if tickers:
            remover_ativo = st.selectbox("Selecione para remover", tickers, key="remover_ativo")
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
                st.rerun()
        else:
            st.info("Nenhum ativo cadastrado.")
        st.markdown("---")




    # Valores padrão para visualização
    if 'ticker_sel' not in st.session_state:
        st.session_state['ticker_sel'] = tickers[0] if tickers else None
    if 'periodo_sel' not in st.session_state:
        st.session_state['periodo_sel'] = "3 meses"
    if 'dias' not in st.session_state:
        st.session_state['dias'] = 90

# Destaques do Mercado

# Destaques do Mercado (versão nativa Streamlit)

# Destaques do Mercado (fundo escuro)
st.markdown("""
<div style='background: linear-gradient(90deg,#232931 60%,#393e46 100%); border-radius:12px; padding:1.5rem 1rem 1rem 1rem; margin-bottom:2rem;'>
    <h2 style='color:#f8d90f; margin-bottom:0.5rem;'>✨ Destaques do Mercado</h2>
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

# Visualização principal
ticker_sel = st.session_state.get('ticker_sel')
periodo_sel = st.session_state.get('periodo_sel')
dias = st.session_state.get('dias')
if ticker_sel:
    if periodo_sel == "5 anos":
        # Mostra todos os dados disponíveis do ativo
        historicos = [h for h in listar_historicos(ticker_sel) if h.preco_fechamento]
    else:
        data_inicio = hoje - datetime.timedelta(days=dias)
        historicos = [h for h in listar_historicos(ticker_sel) if h.data >= data_inicio and h.preco_fechamento]
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "� Abertura",
        "� Fechamento",
        "🔼 Máximo",
        "🔽 Mínimo",
        "📊 Volume"
    ])
    if not historicos:
        tab1.warning("Não há dados suficientes para plotar o gráfico.")
        tab2.warning("Não há dados suficientes para plotar o gráfico.")
        tab3.warning("Não há dados suficientes para plotar o gráfico.")
        tab4.warning("Não há dados suficientes para plotar o gráfico.")
        tab5.warning("Não há dados suficientes para plotar o gráfico.")
    else:
        historicos.sort(key=lambda h: h.data)
        df = pd.DataFrame({
            "Data": [h.data for h in historicos],
            "Abertura": [h.preco_abertura for h in historicos],
            "Fechamento": [h.preco_fechamento for h in historicos],
            "Máximo": [h.maximo for h in historicos],
            "Mínimo": [h.minimo for h in historicos],
            "Volume": [h.volume for h in historicos]
        })

        # Preço Atual sempre acima do título do gráfico
        def to_float(val):
            if val is None:
                return None
            if isinstance(val, str):
                val = val.replace('%', '').replace(',', '').strip()
            try:
                return float(val)
            except Exception:
                return None
        preco_obj = consultar_preco_atual(ticker_sel)
        if preco_obj:
            preco = to_float(preco_obj.preco)
            variacao = to_float(preco_obj.variacao)
            variacao_pct = to_float(preco_obj.variacao_percentual)
            cor = "#27ae60" if variacao is not None and variacao >= 0 else "#c0392b"
            variacao_str = f"{variacao:+.2f}" if variacao is not None else "-"
            variacao_pct_str = f"({variacao_pct:+.2f}%)" if variacao_pct is not None else ""
            st.markdown(f"""
                <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;'>
                  <span style='font-size:2.2rem;font-weight:bold;color:#222;'>
                    {preco if preco is not None else '-'}
                  </span>
                  <span style='font-size:1.3rem;font-weight:bold;color:{cor};margin-left:1.5rem;'>
                    {variacao_str} {variacao_pct_str}
                  </span>
                </div>
                <div style='font-size:0.9rem;color:#888;margin-bottom:0.5rem;'>Atualizado em: {preco_obj.atualizado_em.strftime('%d/%m/%Y %H:%M:%S')}</div>
            """, unsafe_allow_html=True)
        else:
            st.info("Aguardando atualização automática do preço...")

        with tab1:
            st.subheader(f"Preço de Abertura - {ticker_sel} ({periodo_sel})")
            st.line_chart(df.set_index("Data")["Abertura"])
        with tab2:
            st.subheader(f"Preço de Fechamento - {ticker_sel} ({periodo_sel})")
            st.line_chart(df.set_index("Data")["Fechamento"])
        with tab3:
            st.subheader(f"Preço Máximo - {ticker_sel} ({periodo_sel})")
            st.line_chart(df.set_index("Data")["Máximo"])
        with tab4:
            st.subheader(f"Preço Mínimo - {ticker_sel} ({periodo_sel})")
            st.line_chart(df.set_index("Data")["Mínimo"])
        with tab5:
            st.subheader(f"Volume - {ticker_sel} ({periodo_sel})")
            st.bar_chart(df.set_index("Data")["Volume"])

st.caption("<span style='color:#888'>Desenvolvido com Streamlit e Python | Dados: Yahoo Finance</span>", unsafe_allow_html=True)
