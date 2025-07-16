
"""
Dashboard Financeiro Interativo
--------------------------------
Módulo principal da aplicação Streamlit para visualização, cadastro e análise de ativos financeiros.
Utiliza scraping, yfinance, banco de dados local e analytics customizados.
"""

# === Imports ===
__author__ = "BigLeno"
__version__ = "1.0"

import streamlit as st
import pandas as pd
import threading
import time
import datetime
import yfinance as yf


from assets.scrapping import Scraper
from assets.database import listar_ativos, listar_historicos, inserir_ativo, consultar_preco_atual, salvar_preco_atual
from assets.analytics_cache import atualizar_analytics_cache, consultar_analytics_cache
from assets.finance_utils import to_float, buscar_preco_com_fallback, atualizar_precos_periodicamente


# === Configuração da Página ===

st.set_page_config(page_title="Dashboard Financeiro Interativo", layout="wide")



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

def buscar_e_salvar_preco() -> None:
    """
    Busca o preço do ativo recém-adicionado e salva no banco de dados.
    Executado em thread para não travar o front.
    """
    dados = buscar_preco_com_fallback(novo_ativo)
    salvar_preco_atual(
        novo_ativo,
        preco=dados['preco'],
        variacao=dados['variacao'],
        variacao_percentual=dados['variacao_percentual'],
        atualizado_em=None
    )
        
def preco_atual_html() -> str:
    """
    Gera HTML com o preço atual, variação e data/hora da última atualização do ativo selecionado.
    Retorna:
        str: HTML formatado para exibição no Streamlit.
    """
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


# === Inicialização da Thread de Preços ===
if 'thread_precos' not in st.session_state:
    thread = threading.Thread(target=atualizar_precos_periodicamente, args=(60,), daemon=True)
    thread.start()
    st.session_state['thread_precos'] = True




# === Título ===
st.markdown("""
<h2 style='font-size:2rem; color:#0a3d62; margin-bottom:0.2em;'>💹 Dashboard Financeiro</h2>
<div style='font-size:1rem; color:#444; margin-bottom:1em;'>Acompanhe preços e destaques do mercado.</div>
""", unsafe_allow_html=True)


# === Sidebar ===
with st.sidebar:
    """
    Barra lateral de navegação e filtros.
    Permite alternar entre visualização e gerenciamento de portfólio.
    """
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920256.png", width=80)
    st.markdown("<h2 style='color:#0a3d62;'>Menu</h2>", unsafe_allow_html=True)
    menu = st.radio("Menu de opções", ["Filtros de Visualização", "Gerenciar Portfólio"], index=0, label_visibility="collapsed")
    ativos = listar_ativos()
    tickers = [a.ticker for a in ativos]


    # === Filtros de Visualização ===
    if menu == "Filtros de Visualização":
        """
        Filtros para seleção de ativo e período de análise.
        """
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


    # === Gerenciar Portfólio ===
    if menu == "Gerenciar Portfólio":
        """
        Permite adicionar e remover ativos do portfólio.
        """
        st.subheader("Adicionar novo ativo")
        novo_ativo = st.text_input("Ticker (ex: BBDC4.SA)", key="novo_ativo")
        if st.button("➕ Adicionar ativo"):
            if not novo_ativo:
                st.warning("Digite um ticker válido.")
            elif novo_ativo in tickers:
                st.error(f"O ativo {novo_ativo} já existe!")
            else:
                inserir_ativo(novo_ativo)
                threading.Thread(target=buscar_e_salvar_preco, daemon=True).start()
                with st.spinner(f"Coletando históricos de {novo_ativo} (5 anos)..."):
                    Scraper(headless=True).coletar_e_salvar_historico_ativos([novo_ativo], periodos='5Y')
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

    # === Valores padrão para visualização ===
    if 'ticker_sel' not in st.session_state:
        st.session_state['ticker_sel'] = tickers[0] if tickers else None
    if 'periodo_sel' not in st.session_state:
        st.session_state['periodo_sel'] = "3 meses"
    if 'dias' not in st.session_state:
        st.session_state['dias'] = 90


# === Destaques do Mercado ===
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


# === Gráficos e Preço Atual ===
hoje = datetime.date.today()
ticker_sel = st.session_state.get('ticker_sel')
periodo_sel = st.session_state.get('periodo_sel')
dias = st.session_state.get('dias')
if ticker_sel:
    if periodo_sel == "5 anos":
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
        for tab in [tab1, tab2, tab3, tab4, tab5]:
            tab.warning("Não há dados suficientes para plotar o gráfico.")
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

        tab1.subheader(f"Preço de Abertura - {ticker_sel} ({periodo_sel})")
        tab1.markdown(preco_atual_html(), unsafe_allow_html=True)
        tab1.line_chart(df.set_index("Data")['Abertura'])
        tab2.subheader(f"Preço de Fechamento - {ticker_sel} ({periodo_sel})")
        tab2.markdown(preco_atual_html(), unsafe_allow_html=True)
        tab2.line_chart(df.set_index("Data")['Fechamento'])
        tab3.subheader(f"Preço Máximo - {ticker_sel} ({periodo_sel})")
        tab3.markdown(preco_atual_html(), unsafe_allow_html=True)
        tab3.line_chart(df.set_index("Data")['Máximo'])
        tab4.subheader(f"Preço Mínimo - {ticker_sel} ({periodo_sel})")
        tab4.markdown(preco_atual_html(), unsafe_allow_html=True)
        tab4.line_chart(df.set_index("Data")['Mínimo'])
        tab5.subheader(f"Volume - {ticker_sel} ({periodo_sel})")
        tab5.markdown(preco_atual_html(), unsafe_allow_html=True)
        tab5.bar_chart(df.set_index("Data")['Volume'])

st.caption("<span style='color:#888'>Desenvolvido com Streamlit e Python | Dados: Yahoo Finance</span>", unsafe_allow_html=True)
