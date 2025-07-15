import pandas as pd
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import TimeoutException

def scrape_stock(driver, ticker_symbol):
    """Realiza o scraping dos dados do ativo no Yahoo Finance."""
    url = f"https://finance.yahoo.com/quote/{ticker_symbol}"
    driver.get(url)
    try:
        consent_overlay = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".consent-overlay"))
        )
        accept_all_button = consent_overlay.find_element(By.CSS_SELECTOR, ".accept-all")
        accept_all_button.click()
    except TimeoutException:
        pass  # Cookie consent overlay missing
    stock = {"ticker": ticker_symbol}
    try:
        stock["regular_market_price"] = driver.find_element(
            By.CSS_SELECTOR,
            f'[data-symbol="{ticker_symbol}"][data-field="regularMarketPrice"]',
        ).text
    except Exception:
        stock["regular_market_price"] = ""
    try:
        stock["regular_market_change"] = driver.find_element(
            By.CSS_SELECTOR,
            f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChange"]',
        ).text
    except Exception:
        stock["regular_market_change"] = ""
    try:
        stock["regular_market_change_percent"] = (
            driver.find_element(
                By.CSS_SELECTOR,
                f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChangePercent"]',
            )
            .text.replace("(", "")
            .replace(")", "")
        )
    except Exception:
        stock["regular_market_change_percent"] = ""
    # Dados do resumo
    summary_fields = {
        "previous_close": "PREV_CLOSE-value",
        "open_value": "OPEN-value",
        "bid": "BID-value",
        "ask": "ASK-value",
        "days_range": "DAYS_RANGE-value",
        "week_range": "FIFTY_TWO_WK_RANGE-value",
        "volume": "TD_VOLUME-value",
        "avg_volume": "AVERAGE_VOLUME_3MONTH-value",
        "market_cap": "MARKET_CAP-value",
        "beta": "BETA_5Y-value",
        "pe_ratio": "PE_RATIO-value",
        "eps": "EPS_RATIO-value",
        "earnings_date": "EARNINGS_DATE-value",
        "dividend_yield": "DIVIDEND_AND_YIELD-value",
        "ex_dividend_date": "EX_DIVIDEND_DATE-value",
        "year_target_est": "ONE_YEAR_TARGET_PRICE-value",
    }
    for key, data_test in summary_fields.items():
        try:
            stock[key] = driver.find_element(
                By.CSS_SELECTOR, f'#quote-summary [data-test="{data_test}"]'
            ).text
        except Exception:
            stock[key] = ""
    return stock


def scrape_historical_data(driver, ticker_symbol, days=30):
    """Extrai dados históricos do Yahoo Finance para o ticker informado."""
    import re
    url = f"https://finance.yahoo.com/quote/{ticker_symbol}/history"
    driver.get(url)
    try:
        # Aguarda o HTML da página carregar
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        html = driver.page_source
        # Expressão regular para encontrar linhas da tabela de histórico
        # Cada linha tem 7 colunas principais (Date, Open, High, Low, Close*, Adj Close**, Volume)
        padrao_linha = re.compile(r'<tr.*?>\s*(<td.*?>.*?</td>\s*){7,}.*?</tr>', re.DOTALL)
        padrao_coluna = re.compile(r'<td.*?>(.*?)</td>', re.DOTALL)
        linhas = padrao_linha.findall(html)
        dados = []
        for match in re.finditer(padrao_linha, html):
            linha_html = match.group(0)
            colunas = padrao_coluna.findall(linha_html)
            if len(colunas) >= 7:
                # Limpa tags e espaços
                dados.append([re.sub('<.*?>', '', c).replace('\n', '').strip() for c in colunas[:7]])
            if len(dados) >= days:
                break
        df = pd.DataFrame(dados, columns=["Date", "Open", "High", "Low", "Close*", "Adj Close**", "Volume"])
        df.to_csv(f"historical_{ticker_symbol}.csv", index=False)
        return df
    except Exception as e:
        print(f"[ERRO] Não foi possível extrair histórico de {ticker_symbol}: {e}")
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close*", "Adj Close**", "Volume"])
