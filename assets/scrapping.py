import datetime
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


def scrape_historical_data(driver, ticker_symbol, days=None, data_inicial=None, data_final=None):
    """Extrai dados históricos do Yahoo Finance para o ticker informado.
    days: número máximo de linhas (ignorado se datas forem passadas)
    data_inicial/data_final: strings 'YYYY-MM-DD' para montar a URL com period1/period2
    """
    import re
    import time
    def date_to_unix(date_str):
        return int(time.mktime(time.strptime(date_str, "%Y-%m-%d")))

    if data_inicial and data_final:
        period1 = date_to_unix(data_inicial)
        period2 = date_to_unix(data_final)
        url = f"https://finance.yahoo.com/quote/{ticker_symbol}/history/?period1={period1}&period2={period2}"
    else:
        url = f"https://finance.yahoo.com/quote/{ticker_symbol}/history"

    driver.get(url)
    try:
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        html = driver.page_source
        padrao_linha = re.compile(r'<tr.*?>\s*(<td.*?>.*?</td>\s*){7,}.*?</tr>', re.DOTALL)
        padrao_coluna = re.compile(r'<td.*?>(.*?)</td>', re.DOTALL)
        dados = []
        for match in re.finditer(padrao_linha, html):
            linha_html = match.group(0)
            colunas = padrao_coluna.findall(linha_html)
            if len(colunas) >= 7:
                dados.append([re.sub('<.*?>', '', c).replace('\n', '').strip() for c in colunas[:7]])
            if days is not None and data_inicial is None and len(dados) >= days:
                break
        df = pd.DataFrame(dados, columns=["Date", "Open", "High", "Low", "Close*", "Adj Close**", "Volume"])

        # Garante que o dado do dia atual esteja presente
        hoje = datetime.datetime.now().strftime('%b %d, %Y')
        if not (df['Date'] == hoje).any():
            stock = scrape_stock(driver, ticker_symbol)
            nova_linha = {
                "Date": hoje,
                "Open": stock.get("open_value", ""),
                "High": stock.get("regular_market_price", ""),
                "Low": stock.get("regular_market_price", ""),
                "Close*": stock.get("regular_market_price", ""),
                "Adj Close**": stock.get("regular_market_price", ""),
                "Volume": stock.get("volume", "")
            }
            df = pd.concat([pd.DataFrame([nova_linha]), df], ignore_index=True)

        df.to_csv(f"historical_{ticker_symbol}.csv", index=False)
        return df
    except Exception as e:
        print(f"[ERRO] Não foi possível extrair histórico de {ticker_symbol}: {e}")
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close*", "Adj Close**", "Volume"])
