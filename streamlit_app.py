


"""
streamlit_app.py
----------------
Dashboard Financeiro Interativo.
Módulo principal da aplicação Streamlit para visualização, cadastro e análise de ativos financeiros.
Utiliza scraping, yfinance, banco de dados local e analytics customizados.
"""

__author__ = "BigLeno"
__version__ = "1.0"

# === Imports ===
import threading
import datetime
from datetime import datetime as dt, time as dttime
import time
import pandas as pd
import streamlit as st
import yfinance as yf
import pytz

from assets.scrapping import Scraper
from assets.database import (
    listar_ativos, listar_historicos, inserir_ativo, consultar_preco_atual, salvar_preco_atual, atualizar_analytics_cache, consultar_analytics_cache)
from assets.finance_utils import to_float, buscar_preco_com_fallback, atualizar_precos_periodicamente


def mercado_eua_aberto() -> bool:
    """
    Verifica se o mercado dos EUA (NYSE/Nasdaq) está aberto agora.
    Returns:
        bool: True se aberto, False se fechado.
    """
    ny_tz = pytz.timezone('America/New_York')
    agora_ny = dt.now(ny_tz)
    weekday = agora_ny.weekday()
    if weekday >= 5:
        return False
    abertura = dttime(9, 30)
    fechamento = dttime(16, 0)
    return abertura <= agora_ny.time() <= fechamento


# Estado anterior do mercado (para trigger de atualização de analytics)
if 'mercado_aberto' not in st.session_state:
    st.session_state['mercado_aberto'] = None

# Checa status do mercado e atualiza analytics se mudou
mercado_aberto = mercado_eua_aberto()
if st.session_state['mercado_aberto'] is None:
    st.session_state['mercado_aberto'] = mercado_aberto
elif st.session_state['mercado_aberto'] != mercado_aberto:
    # Mudou o status: reprocessa analytics
    atualizar_analytics_cache()
    st.session_state['mercado_aberto'] = mercado_aberto



# === Exibe status do mercado dos EUA no topo do dashboard ===
ny_tz = pytz.timezone('America/New_York')
agora_ny = dt.now(ny_tz)
hora_str = agora_ny.strftime('%H:%M')
dia_semana = agora_ny.strftime('%A')

# Calcula tempo restante para fechamento (ou abertura)
abertura = dttime(9, 30)
fechamento = dttime(16, 0)
if mercado_aberto:
    fechamento_dt = agora_ny.replace(hour=16, minute=0, second=0, microsecond=0)
    tempo_restante = fechamento_dt - agora_ny
    if tempo_restante.total_seconds() < 0:
        tempo_restante_str = "-"
    else:
        horas, resto = divmod(int(tempo_restante.total_seconds()), 3600)
        minutos, _ = divmod(resto, 60)
        tempo_restante_str = f"Fecha em {horas}h {minutos}min"
    status_str = (
        f"<span style='color:#27ae60;font-weight:bold;'>🟢 Mercado dos EUA ABERTO</span>"
        f"<span style='color:#888;font-size:0.95em;'> ({dia_semana}, {hora_str} NY)</span> "
        f"<span style='color:#555;font-size:0.95em;' title='Tempo até o fechamento'>{tempo_restante_str}</span>"
    )
    tooltip = "O mercado está aberto (NYSE/Nasdaq, 9:30-16:00 NY)."
else:
    # Calcula tempo até próxima abertura (considerando finais de semana)
    proxima_abertura = agora_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    if agora_ny.time() >= fechamento:
        proxima_abertura += datetime.timedelta(days=1)
    while proxima_abertura.weekday() >= 5:
        proxima_abertura += datetime.timedelta(days=1)
    tempo_restante = proxima_abertura - agora_ny
    horas, resto = divmod(int(tempo_restante.total_seconds()), 3600)
    minutos, _ = divmod(resto, 60)
    tempo_restante_str = f"Abre em {horas}h {minutos}min"
    status_str = (
        f"<span style='color:#c0392b;font-weight:bold;'>🔴 Mercado dos EUA FECHADO</span>"
        f"<span style='color:#888;font-size:0.95em;'> ({dia_semana}, {hora_str} NY)</span> "
        f"<span style='color:#555;font-size:0.95em;' title='Tempo até a abertura'>{tempo_restante_str}</span>"
    )
    tooltip = "O mercado está fechado (NYSE/Nasdaq, 9:30-16:00 NY)."

st.markdown(f"""
<div style='display:flex;align-items:center;gap:0.5em;margin-bottom:0.7em;'>
  <span title='{tooltip}'>{status_str}</span>
</div>
""", unsafe_allow_html=True)


# === Configuração da Página ===
st.set_page_config(page_title="Dashboard Financeiro Interativo", layout="wide")




# Função utilitária para buscar preço com fallback para yfinance
def buscar_preco_com_fallback(ticker):
    """
    Busca o preço do ativo usando scraping e faz fallback para yfinance em caso de erro.
    Args:
        ticker (str): Ticker do ativo.
    Returns:
        dict: Preço, variação e variação percentual.
    """
    try:
        scraper = Scraper(headless=True)
        scraper.start_driver()
        dados = scraper.scrape_stock(ticker)
        scraper.quit_driver()
        def to_float_local(val):
            if val is None:
                return None
            if isinstance(val, str):
                val = val.replace('%', '').replace(',', '.').strip()
            try:
                return float(val)
            except Exception:
                return None
        return {
            'preco': to_float_local(dados.get("regular_market_price")),
            'variacao': to_float_local(dados.get("regular_market_change")),
            'variacao_percentual': to_float_local(dados.get("regular_market_change_percent")),
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
    Returns:
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
   
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920256.png", width=80)
    st.markdown("<h2 style='color:#0a3d62;'>Menu</h2>", unsafe_allow_html=True)
    menu = st.radio("Menu de opções", ["Filtros de Visualização", "Gerenciar Portfólio"], index=0, label_visibility="collapsed")
    ativos = listar_ativos()
    tickers = [a.ticker for a in ativos]


    # === Filtros de Visualização ===
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
