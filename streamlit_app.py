from assets.analytics_cache import atualizar_analytics_cache, consultar_analytics_cache
import threading
import yfinance as yf
import streamlit as st
import pandas as pd
from assets.analytics_cache import consultar_analytics_cache
from assets.database import listar_ativos, listar_historicos, inserir_ativo
import datetime
from assets.scrapping import Scraper
from assets.database import salvar_preco_atual, consultar_preco_atual, listar_ativos
import threading
import time

st.set_page_config(page_title="Dashboard Financeiro Interativo", layout="wide")

# Thread para atualizar preços dos ativos periodicamente
def atualizar_precos_periodicamente(intervalo=60):
    while True:
        ativos = listar_ativos()
        tickers = [a.ticker for a in ativos]
        for ticker in tickers:
            try:
                dados = buscar_preco_com_fallback(ticker)
                salvar_preco_atual(
                    ticker,
                    preco=dados['preco'],
                    variacao=dados['variacao'],
                    variacao_percentual=dados['variacao_percentual'],
                    atualizado_em=datetime.datetime.now()
                )
            except Exception:
                pass
        time.sleep(intervalo)

# Função utilitária para buscar preço com fallback para yfinance
def buscar_preco_com_fallback(ticker):
    try:
        scraper = Scraper(headless=True)
        scraper.start_driver()
        dados = scraper.scrape_stock(ticker)
        scraper.quit_driver()
        def to_float(val):
            if val is None:
                return None
            if isinstance(val, str):
                val = val.replace('%', '').replace(',', '.').strip()
            try:
                return float(val)
            except Exception:
                return None
        return {
            'preco': to_float(dados.get("regular_market_price")),
            'variacao': to_float(dados.get("regular_market_change")),
            'variacao_percentual': to_float(dados.get("regular_market_change_percent")),
        }
    except Exception:
        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info
            preco = info.get('regularMarketPrice') or info.get('previousClose')
            variacao = info.get('regularMarketChange') or (preco - info.get('previousClose') if preco and info.get('previousClose') else None)
            variacao_percentual = info.get('regularMarketChangePercent')
            return {
                'preco': preco,
                'variacao': variacao,
                'variacao_percentual': variacao_percentual,
            }
        except Exception:
            return {'preco': None, 'variacao': None, 'variacao_percentual': None}

# Inicia thread de atualização (apenas uma vez)
if 'thread_precos' not in st.session_state:
    thread = threading.Thread(target=atualizar_precos_periodicamente, args=(60,), daemon=True)
    thread.start()
    st.session_state['thread_precos'] = True



# Título simples
st.markdown("""
<h2 style='font-size:2rem; color:#0a3d62; margin-bottom:0.2em;'>💹 Dashboard Financeiro</h2>
<div style='font-size:1rem; color:#444; margin-bottom:1em;'>Acompanhe preços e destaques do mercado.</div>
""", unsafe_allow_html=True)

# Sidebar refinada

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920256.png", width=80)
    st.markdown("<h2 style='color:#0a3d62;'>Menu</h2>", unsafe_allow_html=True)
    menu = st.radio("Menu de opções", ["Filtros de Visualização", "Gerenciar Portfólio"], index=0, label_visibility="collapsed")
    scraper = Scraper(headless=True)
    ativos = listar_ativos()
    tickers = [a.ticker for a in ativos]

    if menu == "Filtros de Visualização":
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
    else:
        ticker_sel = st.session_state.get('ticker_sel')
        periodo_sel = st.session_state.get('periodo_sel')
        dias = st.session_state.get('dias')

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
                def buscar_e_salvar_preco():
                    from assets.database import salvar_preco_atual
                    dados = buscar_preco_com_fallback(novo_ativo)
                    salvar_preco_atual(
                        novo_ativo,
                        preco=dados['preco'],
                        variacao=dados['variacao'],
                        variacao_percentual=dados['variacao_percentual'],
                        atualizado_em=None
                    )
                # Buscar preço em thread para não travar o front
                threading.Thread(target=buscar_e_salvar_preco, daemon=True).start()
                with st.spinner(f"Coletando históricos de {novo_ativo} (5 anos)..."):
                    scraper.coletar_e_salvar_historico_ativos([novo_ativo], periodos='5Y')
                # Rodar analytics em thread
                threading.Thread(target=atualizar_analytics_cache, daemon=True).start()
                st.success(f"Ativo {novo_ativo} adicionado e históricos coletados!")
                st.rerun()
        st.subheader("Remover ativo")
        if tickers:
            remover_ativo = st.selectbox("Selecione para remover", tickers, key="remover_ativo")
            if st.button("🗑️ Remover ativo selecionado"):
                from assets.database import SessionLocal, Ativo, Historico, PrecoAtual
                session = SessionLocal()
                ativo_obj = session.query(Ativo).filter_by(ticker=remover_ativo).first()
                if ativo_obj:
                    session.query(Historico).filter_by(ativo_id=ativo_obj.id).delete()
                    session.query(PrecoAtual).filter_by(ativo_id=ativo_obj.id).delete()
                    session.delete(ativo_obj)
                    session.commit()
                    # Rodar analytics em thread
                    threading.Thread(target=atualizar_analytics_cache, daemon=True).start()
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


# Destaques do Mercado (simples)
st.markdown("<b>Destaques do Mercado</b>", unsafe_allow_html=True)
analytics = {a.tipo: a for a in consultar_analytics_cache()}
col1, col2, col3 = st.columns(3)
with col1:
    a = analytics.get('maior_rent_12m')
    st.metric("Maior rent. 12m", f"{a.ticker if a and a.ticker else '-'}", f"{a.valor:.2%}" if a and a.valor is not None else "-")
with col2:
    a = analytics.get('menor_rent_mm3m')
    st.metric("Menor rent. MM3M", f"{a.ticker if a and a.ticker else '-'}", f"{a.valor:.2%}" if a and a.valor is not None else "-")
with col3:
    a = analytics.get('maior_tend_1m')
    st.metric("Maior tendência 1m", f"{a.ticker if a and a.ticker else '-'}", f"{a.valor:.4f}" if a and a.valor is not None else "-")

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
        "📈 Abertura",
        "📉 Fechamento",
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

        # Função para exibir preço atual logo abaixo do título do gráfico
        def to_float(val):
            if val is None:
                return None
            if isinstance(val, str):
                val = val.replace('%', '').replace(',', '').strip()
            try:
                return float(val)
            except Exception:
                return None
        def preco_atual_html():
            preco_obj = consultar_preco_atual(ticker_sel)
            if preco_obj:
                preco = to_float(preco_obj.preco)
                variacao = to_float(preco_obj.variacao)
                variacao_pct = to_float(preco_obj.variacao_percentual)
                cor = "#27ae60" if variacao is not None and variacao >= 0 else "#c0392b"
                variacao_str = f"{variacao:+.2f}" if variacao is not None else "-"
                variacao_pct_str = f"({variacao_pct:+.2f}%)" if variacao_pct is not None else ""
                return f"""
                    <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;'>
                      <span style='font-size:2.2rem;font-weight:bold;color:#222;'>
                        {preco if preco is not None else '-'}
                      </span>
                      <span style='font-size:1.3rem;font-weight:bold;color:{cor};margin-left:1.5rem;'>
                        {variacao_str} {variacao_pct_str}
                      </span>
                    </div>
                    <div style='font-size:0.9rem;color:#888;margin-bottom:0.5rem;'>Atualizado em: {preco_obj.atualizado_em.strftime('%d/%m/%Y %H:%M:%S')}</div>
                """
            else:
                return "<div style='color:#888;margin-bottom:0.5rem;'>Aguardando atualização automática do preço...</div>"

        with tab1:
            st.subheader(f"Preço de Abertura - {ticker_sel} ({periodo_sel})")
            st.markdown(preco_atual_html(), unsafe_allow_html=True)
            st.line_chart(df.set_index("Data")['Abertura'])
        with tab2:
            st.subheader(f"Preço de Fechamento - {ticker_sel} ({periodo_sel})")
            st.markdown(preco_atual_html(), unsafe_allow_html=True)
            st.line_chart(df.set_index("Data")['Fechamento'])
        with tab3:
            st.subheader(f"Preço Máximo - {ticker_sel} ({periodo_sel})")
            st.markdown(preco_atual_html(), unsafe_allow_html=True)
            st.line_chart(df.set_index("Data")['Máximo'])
        with tab4:
            st.subheader(f"Preço Mínimo - {ticker_sel} ({periodo_sel})")
            st.markdown(preco_atual_html(), unsafe_allow_html=True)
            st.line_chart(df.set_index("Data")['Mínimo'])
        with tab5:
            st.subheader(f"Volume - {ticker_sel} ({periodo_sel})")
            st.markdown(preco_atual_html(), unsafe_allow_html=True)
            st.bar_chart(df.set_index("Data")['Volume'])

st.caption("<span style='color:#888'>Desenvolvido com Streamlit e Python | Dados: Yahoo Finance</span>", unsafe_allow_html=True)
