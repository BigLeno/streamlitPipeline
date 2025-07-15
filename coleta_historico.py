import os
from assets.config_assets import ATIVOS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from assets.scrapping import scrape_historical_data

# Pasta para salvar os históricos
os.makedirs('historicos', exist_ok=True)

ATIVOS = [ATIVOS[0]]

def main():
    options = Options()
    # REMOVA o modo headless para debug visual
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    driver.set_window_size(1150, 1000)
    from datetime import datetime, timedelta
    def date_to_str(dt):
        return dt.strftime('%Y-%m-%d')

    hoje = datetime.today()
    seis_meses_atras = hoje - timedelta(days=180)
    um_ano_atras = hoje - timedelta(days=365)

    for ticker in ATIVOS:
        print(f"Coletando histórico de {ticker} (últimos 6 meses)...")
        try:
            df = scrape_historical_data(
                driver, ticker,
                data_inicial=date_to_str(seis_meses_atras),
                data_final=date_to_str(hoje)
            )
            if df.empty:
                print(f"[ERRO] DataFrame vazio para {ticker}. Verifique se a tabela carregou corretamente.")
            else:
                df.to_csv(f"historicos/historical_{ticker}_6M.csv", index=False)
                print(f"Histórico salvo em historicos/historical_{ticker}_6M.csv")
        except Exception as e:
            print(f"[ERRO] Não foi possível coletar histórico de {ticker}: {e}")

        print(f"Coletando histórico de {ticker} (últimos 12 meses)...")
        try:
            df2 = scrape_historical_data(
                driver, ticker,
                data_inicial=date_to_str(um_ano_atras),
                data_final=date_to_str(hoje)
            )
            if df2.empty:
                print(f"[ERRO] DataFrame vazio para {ticker} (12 meses). Verifique se a tabela carregou corretamente.")
            else:
                df2.to_csv(f"historicos/historical_{ticker}_12M.csv", index=False)
                print(f"Histórico salvo em historicos/historical_{ticker}_12M.csv")
        except Exception as e:
            print(f"[ERRO] Não foi possível coletar histórico de {ticker} (12 meses): {e}")

    driver.quit()

if __name__ == "__main__":
    main()
