import yfinance as yf
import datetime
from assets.scrapping import Scraper
from assets.database import salvar_preco_atual, listar_ativos

def to_float(val):
    if val is None:
        return None
    if isinstance(val, str):
        val = val.replace('%', '').replace(',', '.').strip()
    try:
        return float(val)
    except Exception:
        return None

def buscar_preco_com_fallback(ticker):
    """Busca preço via scraping, com fallback para yfinance."""
    try:
        scraper = Scraper(headless=True)
        scraper.start_driver()
        dados = scraper.scrape_stock(ticker)
        scraper.quit_driver()
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

def atualizar_precos_periodicamente(intervalo=60):
    """Thread: Atualiza preços dos ativos em background."""
    while True:
        ativos = listar_ativos()
        for ativo in ativos:
            try:
                dados = buscar_preco_com_fallback(ativo.ticker)
                salvar_preco_atual(
                    ativo.ticker,
                    preco=dados['preco'],
                    variacao=dados['variacao'],
                    variacao_percentual=dados['variacao_percentual'],
                    atualizado_em=datetime.datetime.now()
                )
            except Exception:
                pass
        import time
        time.sleep(intervalo)
