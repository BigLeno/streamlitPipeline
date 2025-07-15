"""
Projeto: Extração de dados de ativos financeiros do Yahoo Finance
Autor: Seu Nome
Data: 15/07/2025
Descrição: Script para monitorar e extrair dados de ativos do segmento financeiro.
"""

from assets.config_assets import ATIVOS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import TimeoutException
import csv


def scrape_stock(driver, ticker_symbol):
    """Realiza o scraping dos dados do ativo no Yahoo Finance."""
    url = f'https://finance.yahoo.com/quote/{ticker_symbol}'
    driver.get(url)
    try:
        consent_overlay = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.consent-overlay')))
        accept_all_button = consent_overlay.find_element(By.CSS_SELECTOR, '.accept-all')
        accept_all_button.click()
    except TimeoutException:
        pass  # Cookie consent overlay missing
    stock = {'ticker': ticker_symbol}
    try:
        stock['regular_market_price'] = driver.find_element(By.CSS_SELECTOR, f'[data-symbol="{ticker_symbol}"][data-field="regularMarketPrice"]').text
    except Exception:
        stock['regular_market_price'] = ''
    try:
        stock['regular_market_change'] = driver.find_element(By.CSS_SELECTOR, f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChange"]').text
    except Exception:
        stock['regular_market_change'] = ''
    try:
        stock['regular_market_change_percent'] = driver.find_element(By.CSS_SELECTOR, f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChangePercent"]').text.replace('(', '').replace(')', '')
    except Exception:
        stock['regular_market_change_percent'] = ''
    # Dados do resumo
    summary_fields = {
        'previous_close': 'PREV_CLOSE-value',
        'open_value': 'OPEN-value',
        'bid': 'BID-value',
        'ask': 'ASK-value',
        'days_range': 'DAYS_RANGE-value',
        'week_range': 'FIFTY_TWO_WK_RANGE-value',
        'volume': 'TD_VOLUME-value',
        'avg_volume': 'AVERAGE_VOLUME_3MONTH-value',
        'market_cap': 'MARKET_CAP-value',
        'beta': 'BETA_5Y-value',
        'pe_ratio': 'PE_RATIO-value',
        'eps': 'EPS_RATIO-value',
        'earnings_date': 'EARNINGS_DATE-value',
        'dividend_yield': 'DIVIDEND_AND_YIELD-value',
        'ex_dividend_date': 'EX_DIVIDEND_DATE-value',
        'year_target_est': 'ONE_YEAR_TARGET_PRICE-value'
    }
    for key, data_test in summary_fields.items():
        try:
            stock[key] = driver.find_element(By.CSS_SELECTOR, f'#quote-summary [data-test="{data_test}"]').text
        except Exception:
            stock[key] = ''
    return stock


def main():
    print("Ativos monitorados:")
    for ativo in ATIVOS:
        print(f"- {ativo}")
    print("\nBuscando dados dos ativos...")
    options = Options()
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    driver.set_window_size(1150, 1000)
    stocks = []
    for ticker_symbol in ATIVOS:
        print(f"Buscando dados de {ticker_symbol}...")
        stocks.append(scrape_stock(driver, ticker_symbol))
    driver.quit()
    if stocks:
        csv_header = stocks[0].keys()
        with open('stocks.csv', 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, csv_header)
            dict_writer.writeheader()
            dict_writer.writerows(stocks)
        print("\nDados exportados para stocks.csv")
    else:
        print("Nenhum dado coletado.")


if __name__ == "__main__":
    main()
