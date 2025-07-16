
"""
scrapping.py
------------
Módulo de scraping para extração de dados financeiros do Yahoo Finance.
Inclui coleta de históricos, dados principais e resumo de ativos.
"""

import datetime
import os
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import TimeoutException
from assets.database import criar_banco, inserir_ativo, inserir_historico


class Scraper:
    """
    Classe principal para scraping de dados financeiros do Yahoo Finance.
    """

    @staticmethod
    def get_period_range(periodo: str, hoje: datetime.date = None):
        """
        Retorna a tupla (data_inicial, data_final) para o período informado.
        """
        """
        Retorna a tupla (data_inicial, data_final) para o período informado.
        """
        if hoje is None:
            hoje = datetime.date.today()
        periodos = {
            '1D': lambda h: (h - datetime.timedelta(days=1), h),
            '5D': lambda h: (h - datetime.timedelta(days=5), h),
            '3M': lambda h: (h - datetime.timedelta(days=90), h),
            '6M': lambda h: (h - datetime.timedelta(days=180), h),
            'YTD': lambda h: (h.replace(month=1, day=1), h),
            '1Y': lambda h: (h - datetime.timedelta(days=365), h),
            '5Y': lambda h: (h - datetime.timedelta(days=5*365), h),
        }
        if periodo not in periodos:
            raise ValueError(f"Período '{periodo}' não reconhecido.")
        return periodos[periodo](hoje)

    def coletar_e_salvar_historico_ativos(self, ativos: list, periodos='5Y'):
        """
        Coleta e salva no banco o histórico dos ativos para o(s) período(s) informado(s). Não salva CSV.
        """
        """
        Coleta e salva no banco o histórico dos ativos para o(s) período(s) informado(s). Não salva CSV.
        """
        criar_banco()
        self.start_driver()
        if isinstance(periodos, str):
            periodos = [periodos]
        hoje = datetime.date.today()
        for ticker in ativos:
            inserir_ativo(ticker)
            for periodo in periodos:
                data_inicial, data_final = self.get_period_range(periodo, hoje)
                print(f'Coletando histórico de {ticker} ({periodo})...')
                df = self.scrape_historical_data(
                    ticker_symbol=ticker,
                    data_inicial=self._date_to_str(data_inicial),
                    data_final=self._date_to_str(data_final)
                )
                for _, row in df.iterrows():
                    try:
                        data = row['Date']
                        if isinstance(data, str):
                            try:
                                data = datetime.datetime.strptime(data, '%d/%m/%Y').date()
                            except ValueError:
                                try:
                                    data = datetime.datetime.strptime(data, '%b %d, %Y').date()
                                except ValueError:
                                    raise ValueError(f"Formato de data não reconhecido: {data}")
                        if not isinstance(data, datetime.date):
                            raise ValueError(f"Data não é datetime.date: {data}")
                        inserir_historico(
                            ticker=ticker,
                            data=data,
                        preco_abertura=float(row['Open']) if row.get('Open') not in [None, '', 'N/A', '-'] else None,
                        preco_fechamento=float(row['Close*']) if row.get('Close*') not in [None, '', 'N/A', '-'] else None,
                        maximo=float(row['High']) if row.get('High') not in [None, '', 'N/A', '-'] else None,
                        minimo=float(row['Low']) if row.get('Low') not in [None, '', 'N/A', '-'] else None,
                        volume=float(row['Volume'].replace('.', '').replace(',', '')) if row.get('Volume') not in [None, '', 'N/A', '-'] else None
                        )
                    except Exception as e:
                        print(f'Erro ao inserir linha: {row} - {e}')
                print(f'Histórico de {ticker} inserido no banco.')
        self.quit_driver()
    PERIODOS = {
        '1D': lambda hoje: (hoje - datetime.timedelta(days=1), hoje),
        '5D': lambda hoje: (hoje - datetime.timedelta(days=5), hoje),
        '3M': lambda hoje: (hoje - datetime.timedelta(days=90), hoje),
        '6M': lambda hoje: (hoje - datetime.timedelta(days=180), hoje),
        'YTD': lambda hoje: (hoje.replace(month=1, day=1), hoje),
        '1Y': lambda hoje: (hoje - datetime.timedelta(days=365), hoje),
        '5Y': lambda hoje: (hoje - datetime.timedelta(days=5*365), hoje),
    }

    def __init__(self, headless=True, window_size=(1150, 1000)):
        """
        Inicializa o Scraper com opções do Selenium.
        """
        """Inicializa o Scraper com opções do Selenium."""
        self.headless = headless
        self.window_size = window_size
        self.driver = None

    def start_driver(self) -> None:
        """
        Inicializa o driver do Selenium Chrome.
        """
        """
        Inicializa o driver do Selenium Chrome.
        """
        options = Options()
        if self.headless:
            options.add_argument('--headless=new')
        self.driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )
        self.driver.set_window_size(*self.window_size)

    @staticmethod
    def _date_to_str(dt: datetime.datetime) -> str:
        """
        Converte um datetime para string no formato 'YYYY-MM-DD'.
        """
        """
        Converte um datetime para string no formato 'YYYY-MM-DD'.
        """
        return dt.strftime('%Y-%m-%d')

    @staticmethod
    def _date_to_unix(date_str: str) -> int:
        """
        Converte uma string de data 'YYYY-MM-DD' para timestamp Unix.
        """
        """
        Converte uma string de data 'YYYY-MM-DD' para timestamp Unix.
        """
        return int(time.mktime(time.strptime(date_str, "%Y-%m-%d")))

    def quit_driver(self) -> None:
        """
        Encerra o driver do Selenium se estiver ativo.
        """
        """
        Encerra o driver do Selenium se estiver ativo.
        """
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_stock(self, ticker_symbol: str) -> dict:
        """
        Realiza o scraping dos dados principais do ativo no Yahoo Finance.
        Args:
            ticker_symbol (str): Ticker do ativo.
        Returns:
            dict: Dicionário com os dados principais do ativo.
        """
        """
        Realiza o scraping dos dados principais do ativo no Yahoo Finance.
        Args:
            ticker_symbol (str): Ticker do ativo.
        Returns:
            dict: Dicionário com os dados principais do ativo.
        """
        url = f"https://finance.yahoo.com/quote/{ticker_symbol}"
        self.driver.get(url)
        self._accept_cookies()
        data = {}
        try:
            data["regular_market_price"] = self.driver.find_element(
                By.CSS_SELECTOR,
                f'[data-symbol="{ticker_symbol}"][data-field="regularMarketPrice"]',
            ).text
        except Exception:
            data["regular_market_price"] = ""
        try:
            data["regular_market_change"] = self.driver.find_element(
                By.CSS_SELECTOR,
                f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChange"]',
            ).text
        except Exception:
            data["regular_market_change"] = ""
        try:
            data["regular_market_change_percent"] = (
                self.driver.find_element(
                    By.CSS_SELECTOR,
                    f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChangePercent"]',
                )
                .text.replace("(", "").replace(")", "")
            )
        except Exception:
            data["regular_market_change_percent"] = ""
        return data

    def _accept_cookies(self) -> None:
        """
        Aceita cookies se o overlay estiver presente.
        """
        """Aceita cookies se o overlay estiver presente."""
        try:
            consent_overlay = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".consent-overlay"))
            )
            accept_all_button = consent_overlay.find_element(By.CSS_SELECTOR, ".accept-all")
            accept_all_button.click()
        except TimeoutException:
            pass

    def _get_market_data(self, ticker_symbol: str) -> dict:
        """
        Obtém preço, variação e variação percentual do ativo.
        """
        """Obtém preço, variação e variação percentual do ativo."""
        data = {}
        try:
            data["regular_market_price"] = self.driver.find_element(
                By.CSS_SELECTOR,
                f'[data-symbol="{ticker_symbol}"][data-field="regularMarketPrice"]',
            ).text
        except Exception:
            data["regular_market_price"] = ""
        try:
            data["regular_market_change"] = self.driver.find_element(
                By.CSS_SELECTOR,
                f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChange"]',
            ).text
        except Exception:
            data["regular_market_change"] = ""
        try:
            data["regular_market_change_percent"] = (
                self.driver.find_element(
                    By.CSS_SELECTOR,
                    f'[data-symbol="{ticker_symbol}"][data-field="regularMarketChangePercent"]',
                )
                .text.replace("(", "")
                .replace(")", "")
            )
        except Exception:
            data["regular_market_change_percent"] = ""
        return data

    def _get_summary_data(self, ticker_symbol: str) -> dict:
        """
        Obtém dados do resumo do ativo (ex: volume, PE, etc).
        """
        """Obtém dados do resumo do ativo (ex: volume, PE, etc)."""
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
        data = {}
        for key, data_test in summary_fields.items():
            try:
                data[key] = self.driver.find_element(
                    By.CSS_SELECTOR, f'#quote-summary [data-test="{data_test}"]'
                ).text
            except Exception:
                data[key] = ""
        return data

    def scrape_historical_data(self, ticker_symbol: str, days: int = None, data_inicial: str = None, data_final: str = None) -> pd.DataFrame:
        """
        Extrai dados históricos do Yahoo Finance para o ticker informado.
        Remove linhas de dividendos/splits e trata intervalos sem dados.
        Args:
            ticker_symbol (str): Ticker do ativo.
            days (int, opcional): Número máximo de linhas (ignorado se datas forem passadas).
            data_inicial (str, opcional): Data inicial no formato 'YYYY-MM-DD'.
            data_final (str, opcional): Data final no formato 'YYYY-MM-DD'.
        Returns:
            pd.DataFrame: DataFrame com os dados históricos limpos.
        """
        """
        Extrai dados históricos do Yahoo Finance para o ticker informado.
        Remove linhas de dividendos/splits e trata intervalos sem dados.
        Args:
            ticker_symbol (str): Ticker do ativo.
            days (int, opcional): Número máximo de linhas (ignorado se datas forem passadas).
            data_inicial (str, opcional): Data inicial no formato 'YYYY-MM-DD'.
            data_final (str, opcional): Data final no formato 'YYYY-MM-DD'.
        Returns:
            pd.DataFrame: DataFrame com os dados históricos limpos.
        """
        url = self._build_history_url(ticker_symbol, data_inicial, data_final)
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 40).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            html = self.driver.page_source
            dados = self._parse_historical_table(html, days, data_inicial)
            if not dados:
                print(f"[AVISO] Nenhum dado encontrado para {ticker_symbol} no intervalo solicitado.")
                return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close*", "Adj Close**", "Volume"])

            # Substitui valores vazios por 'N/A'
            df = pd.DataFrame(dados, columns=["Date", "Open", "High", "Low", "Close*", "Adj Close**", "Volume"])
            df.replace({'': 'N/A', None: 'N/A'}, inplace=True)
            self._add_today_if_missing(df, ticker_symbol)
            df = df.drop_duplicates(subset=["Date"], keep="first").reset_index(drop=True)
            return df
        except Exception as e:
            print(f"[ERRO] Não foi possível extrair histórico de {ticker_symbol}: {e}")
            return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close*", "Adj Close**", "Volume"])

    def _build_history_url(self, ticker_symbol: str, data_inicial: str, data_final: str) -> str:
        """
        Monta a URL de histórico do Yahoo Finance para o ticker e datas informadas.
        """
        """Monta a URL de histórico do Yahoo Finance para o ticker e datas informadas."""
        if data_inicial and data_final:
            period1 = self._date_to_unix(data_inicial)
            period2 = self._date_to_unix(data_final)
            return f"https://finance.yahoo.com/quote/{ticker_symbol}/history/?period1={period1}&period2={period2}"
        return f"https://finance.yahoo.com/quote/{ticker_symbol}/history"

    def _parse_historical_table(self, html: str, days: int = None, data_inicial: str = None) -> list:
        """
        Extrai e limpa as linhas válidas da tabela de histórico do HTML.
        """
        """Extrai e limpa as linhas válidas da tabela de histórico do HTML."""
        padrao_linha = re.compile(r'<tr.*?>\s*(<td.*?>.*?</td>\s*){7,}.*?</tr>', re.DOTALL)
        padrao_coluna = re.compile(r'<td.*?>(.*?)</td>', re.DOTALL)
        dados = []
        for match in re.finditer(padrao_linha, html):
            linha_html = match.group(0)
            colunas = padrao_coluna.findall(linha_html)
            if any('Dividend' in c or 'Split' in c for c in colunas):
                continue
            if len(colunas) >= 7:
                dados.append([re.sub('<.*?>', '', c).replace('\n', '').strip() for c in colunas[:7]])
            if days is not None and data_inicial is None and len(dados) >= days:
                break
        return dados

    def _add_today_if_missing(self, df: pd.DataFrame, ticker_symbol: str) -> None:
        """
        Adiciona linha do dia atual se não existir no DataFrame. Preenche campos vazios com 'N/A'.
        """
        """Adiciona linha do dia atual se não existir no DataFrame. Preenche campos vazios com 'N/A'."""
        hoje = datetime.datetime.now().strftime('%b %d, %Y')
        if not (df['Date'] == hoje).any():
            try:
                stock = self.scrape_stock(ticker_symbol)
                nova_linha = {
                    "Date": hoje,
                    "Open": stock.get("open_value", "N/A") or "N/A",
                    "High": stock.get("regular_market_price", "N/A") or "N/A",
                    "Low": stock.get("regular_market_price", "N/A") or "N/A",
                    "Close*": stock.get("regular_market_price", "N/A") or "N/A",
                    "Adj Close**": stock.get("regular_market_price", "N/A") or "N/A",
                    "Volume": stock.get("volume", "N/A") or "N/A"
                }
                df.loc[-1] = nova_linha
                df.index = df.index + 1
                df.sort_index(inplace=True)
            except Exception as e:
                print(f"[AVISO] Não foi possível adicionar linha do dia atual para {ticker_symbol}: {e}")

    def coletar_historico_ativos(self, ativos: list, periodos=None) -> None:
        """
        Coleta o histórico dos ativos informados, salvando arquivos para cada período solicitado na pasta 'historicos'.
        Args:
            ativos (list): Lista de tickers.
            periodos (list|str, opcional): Lista de períodos ou string única. Se None, usa ['6M', '1Y'].
        """
        """
        Coleta o histórico dos ativos informados, salvando arquivos para cada período solicitado na pasta 'historicos'.
        Args:
            ativos (list): Lista de tickers.
            periodos (list|str, opcional): Lista de períodos ou string única. Se None, usa ['6M', '1Y'].
        """
        os.makedirs('historicos', exist_ok=True)

        if periodos is None:
            periodos = ['6M', '1Y']
        elif isinstance(periodos, str):
            periodos = [periodos]

        hoje = datetime.datetime.today()
        self.start_driver()

        for ticker in ativos:
            for periodo in periodos:
                if periodo not in self.PERIODOS:
                    print(f"[ERRO] Período '{periodo}' não reconhecido. Pulando...")
                    continue
                data_inicial, data_final = self.PERIODOS[periodo](hoje)
                print(f"Coletando histórico de {ticker} ({periodo})...")
                try:
                    df = self.scrape_historical_data(
                        ticker,
                        data_inicial=self._date_to_str(data_inicial),
                        data_final=self._date_to_str(data_final)
                    )
                    if df.empty:
                        print(f"[ERRO] DataFrame vazio para {ticker} ({periodo}). Verifique se a tabela carregou corretamente.")
                    else:
                        df.to_csv(f"historicos/historical_{ticker}_{periodo}.csv", index=False)
                        print(f"Histórico salvo em historicos/historical_{ticker}_{periodo}.csv")
                except Exception as e:
                    print(f"[ERRO] Não foi possível coletar histórico de {ticker} ({periodo}): {e}")

        self.quit_driver()
